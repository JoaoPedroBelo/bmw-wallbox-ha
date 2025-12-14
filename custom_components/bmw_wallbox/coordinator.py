"""OCPP Coordinator for BMW Wallbox integration.

Author: João Belo
Independent open-source project for BMW-branded Delta Electronics wallboxes.
Not affiliated with BMW, Delta Electronics, or any other company.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import logging
import ssl
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp, call, call_result
from ocpp.v201.datatypes import (
    ChargingProfileType,
    ChargingSchedulePeriodType,
    ChargingScheduleType,
    ComponentType,
    IdTokenType,
    SetVariableDataType,
    VariableType,
)
from ocpp.v201.enums import (
    AttributeEnumType,
    ChargingProfileKindEnumType,
    ChargingProfilePurposeEnumType,
    ChargingRateUnitEnumType,
    IdTokenEnumType,
    RegistrationStatusEnumType,
    RequestStartStopStatusEnumType,
    ResetEnumType,
    ResetStatusEnumType,
)
import websockets

from .const import CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class WallboxChargePoint(cp):
    """ChargePoint handler for the BMW wallbox."""

    def __init__(
        self, charge_point_id: str, websocket, coordinator: BMWWallboxCoordinator
    ):
        """Initialize the ChargePoint."""
        super().__init__(charge_point_id, websocket)
        self.coordinator = coordinator
        self.current_transaction_id: str | None = None
        _LOGGER.info("Initialized ChargePoint: %s", charge_point_id)

    @on("BootNotification")
    async def on_boot_notification(self, charging_station, reason, **kwargs):
        """Handle BootNotification from wallbox."""
        _LOGGER.info("Boot Notification received from %s", self.id)
        _LOGGER.debug("Charging Station: %s", charging_station)

        # Store device info
        self.coordinator.device_info = {
            "model": charging_station.get("model", "Unknown"),
            "vendor": charging_station.get("vendor_name", "BMW"),
            "serial_number": charging_station.get("serial_number", "Unknown"),
            "firmware_version": charging_station.get("firmware_version", "Unknown"),
        }

        return call_result.BootNotification(
            current_time=datetime.utcnow().isoformat(),
            interval=10,
            status=RegistrationStatusEnumType.accepted,
        )

    @on("StatusNotification")
    async def on_status_notification(
        self, timestamp, connector_status, evse_id, connector_id, **kwargs
    ):
        """Handle StatusNotification."""
        _LOGGER.info(
            "📡 StatusNotification: EVSE=%s, Connector=%s, Status=%s",
            evse_id,
            connector_id,
            connector_status,
        )

        # Update coordinator data
        self.coordinator.data["connector_status"] = connector_status
        self.coordinator.data["evse_id"] = evse_id
        self.coordinator.data["connector_id"] = connector_id
        self.coordinator.async_set_updated_data(self.coordinator.data)

        return call_result.StatusNotification()

    @on("MeterValues")
    async def on_meter_values(self, evse_id, meter_value, **kwargs):
        """Handle MeterValues from wallbox (triggered or periodic)."""
        _LOGGER.info("📊 MeterValues received for EVSE %s", evse_id)

        for mv in meter_value:
            timestamp = mv.get("timestamp")
            _LOGGER.debug("  Timestamp: %s", timestamp)

            for sample in mv.get("sampled_value", []):
                measurand = sample.get("measurand", "Energy.Active.Import.Register")
                value = sample.get("value")
                phase = sample.get("phase")
                context = sample.get("context")

                _LOGGER.info(
                    "  📈 %s = %s (phase=%s, context=%s)",
                    measurand,
                    value,
                    phase,
                    context,
                )

                # Update coordinator data
                if measurand == "Power.Active.Import":
                    self.coordinator.data["power"] = float(value)
                elif measurand == "Energy.Active.Import.Register":
                    # Use wallbox value directly
                    self.coordinator.data["energy_session"] = float(value)
                    # Only update energy_total if new value is positive and >= current
                    # This prevents utility meters from being corrupted by 0/reset values
                    new_energy = float(value) / 1000.0
                    current_energy = self.coordinator.data.get("energy_total")
                    if new_energy > 0 and (
                        current_energy is None or new_energy >= current_energy
                    ):
                        self.coordinator.data["energy_total"] = new_energy
                    else:
                        _LOGGER.debug(
                            "Ignoring energy_total update: new=%.3f kWh, current=%s kWh "
                            "(value must be > 0 and >= current)",
                            new_energy,
                            current_energy,
                        )
                elif measurand == "Current.Import":
                    if phase == "L1-N":
                        self.coordinator.data["current_l1"] = float(value)
                    elif phase == "L2-N":
                        self.coordinator.data["current_l2"] = float(value)
                    elif phase == "L3-N":
                        self.coordinator.data["current_l3"] = float(value)
                    else:
                        self.coordinator.data["current"] = float(value)
                elif measurand == "Voltage":
                    if phase == "L1-N":
                        self.coordinator.data["voltage_l1"] = float(value)
                    elif phase == "L2-N":
                        self.coordinator.data["voltage_l2"] = float(value)
                    elif phase == "L3-N":
                        self.coordinator.data["voltage_l3"] = float(value)
                    else:
                        self.coordinator.data["voltage"] = float(value)
        self.coordinator.async_set_updated_data(self.coordinator.data)
        return call_result.MeterValues()

    @on("Heartbeat")
    async def on_heartbeat(self, **kwargs):
        """Handle Heartbeat from wallbox."""
        _LOGGER.debug("Heartbeat from %s", self.id)

        # Update connection status
        self.coordinator.data["connected"] = True
        self.coordinator.data["last_heartbeat"] = datetime.utcnow()

        return call_result.Heartbeat(current_time=datetime.utcnow().isoformat())

    @on("TransactionEvent")
    async def on_transaction_event(
        self,
        event_type,
        timestamp,
        trigger_reason,
        seq_no,
        transaction_info,
        **kwargs,
    ):
        """Handle TransactionEvent - contains all the sensor data!"""
        _LOGGER.info(
            "📊 TransactionEvent: type=%s, reason=%s, seq=%s, state=%s",
            event_type,
            trigger_reason,
            seq_no,
            transaction_info.get("charging_state", "Unknown"),
        )

        # Extract transaction ID
        self.current_transaction_id = transaction_info.get("transaction_id")
        self.coordinator.current_transaction_id = self.current_transaction_id

        # Update coordinator data with basic transaction info
        self.coordinator.data.update(
            {
                "transaction_id": self.current_transaction_id,
                "charging_state": transaction_info.get("charging_state", "Unknown"),
                "event_type": event_type,
                "trigger_reason": trigger_reason,
                "sequence_number": seq_no,
                "last_update": timestamp,
                "stopped_reason": transaction_info.get("stopped_reason"),
            }
        )

        # Extract ID token info
        id_token = kwargs.get("id_token", {})
        if id_token:
            self.coordinator.data["id_token"] = id_token.get("id_token")
            self.coordinator.data["id_token_type"] = id_token.get("type")

        # Extract meter values if present
        meter_value = kwargs.get("meter_value", [])
        if meter_value:
            _LOGGER.info("📊 Processing %d meter value(s)", len(meter_value))
            measurands_found = []
            for mv in meter_value:
                for sample in mv.get("sampled_value", []):
                    measurand = sample.get("measurand")
                    value = sample.get("value")
                    phase = sample.get("phase")
                    context = sample.get("context")
                    location = sample.get("location")

                    measurands_found.append(
                        f"{measurand}={value}" + (f"[{phase}]" if phase else "")
                    )
                    _LOGGER.info(
                        "  📈 %s = %s (phase=%s, context=%s, location=%s)",
                        measurand,
                        value,
                        phase,
                        context,
                        location,
                    )

                    # Store context and location for all measurands
                    if context:
                        self.coordinator.data["context"] = context
                    if location:
                        self.coordinator.data["location"] = location

                    # Power measurements
                    if measurand == "Power.Active.Import":
                        self.coordinator.data["power"] = float(value)
                    elif measurand == "Power.Active.Export":
                        self.coordinator.data["power_active_export"] = float(value)
                    elif measurand == "Power.Reactive.Import":
                        self.coordinator.data["power_reactive_import"] = float(value)
                    elif measurand == "Power.Reactive.Export":
                        self.coordinator.data["power_reactive_export"] = float(value)
                    elif measurand == "Power.Offered":
                        self.coordinator.data["power_offered"] = float(value)
                    elif measurand == "Power.Factor":
                        self.coordinator.data["power_factor"] = float(value)

                    # Energy measurements
                    elif measurand == "Energy.Active.Import.Register":
                        # Use wallbox value directly
                        self.coordinator.data["energy_session"] = float(value)
                        # Only update energy_total if new value is positive and >= current
                        # This prevents utility meters from being corrupted by 0/reset values
                        new_energy = float(value) / 1000.0
                        current_energy = self.coordinator.data.get("energy_total")
                        if new_energy > 0 and (
                            current_energy is None or new_energy >= current_energy
                        ):
                            self.coordinator.data["energy_total"] = new_energy
                        else:
                            _LOGGER.debug(
                                "Ignoring energy_total update: new=%.3f kWh, "
                                "current=%s kWh (value must be > 0 and >= current)",
                                new_energy,
                                current_energy,
                            )
                    elif measurand == "Energy.Active.Export.Register":
                        self.coordinator.data["energy_active_export"] = (
                            float(value) / 1000
                        )
                    elif measurand == "Energy.Reactive.Import.Register":
                        self.coordinator.data["energy_reactive_import"] = (
                            float(value) / 1000
                        )
                    elif measurand == "Energy.Reactive.Export.Register":
                        self.coordinator.data["energy_reactive_export"] = (
                            float(value) / 1000
                        )

                    # Current measurements (per phase)
                    elif measurand == "Current.Import":
                        current_value = float(value)
                        if phase == "L1":
                            self.coordinator.data["current_l1"] = current_value
                        elif phase == "L2":
                            self.coordinator.data["current_l2"] = current_value
                        elif phase == "L3":
                            self.coordinator.data["current_l3"] = current_value
                        else:
                            # Total or unspecified - store as main current
                            self.coordinator.data["current"] = current_value

                        _LOGGER.debug("Current: value=%s, phase=%s", value, phase)

                    # Voltage measurements (per phase)
                    elif measurand == "Voltage":
                        if phase == "L1" or phase == "L1-N":
                            self.coordinator.data["voltage_l1"] = float(value)
                        elif phase == "L2" or phase == "L2-N":
                            self.coordinator.data["voltage_l2"] = float(value)
                        elif phase == "L3" or phase == "L3-N":
                            self.coordinator.data["voltage_l3"] = float(value)
                        else:
                            # Average or unspecified
                            self.coordinator.data["voltage"] = float(value)

                    # Other measurements
                    elif measurand == "Frequency":
                        self.coordinator.data["frequency"] = float(value)
                    elif measurand == "Temperature":
                        self.coordinator.data["temperature"] = float(value)

            # Log all measurands found for debugging
            if measurands_found:
                _LOGGER.info("📊 All measurands: %s", ", ".join(measurands_found))
        else:
            _LOGGER.debug("No meter_value in TransactionEvent")

        # Extract other fields
        if "number_of_phases_used" in kwargs:
            self.coordinator.data["phases_used"] = kwargs["number_of_phases_used"]

        # === POST-PROCESSING: Calculate missing values ===

        power = self.coordinator.data.get("power", 0) or 0
        voltage = self.coordinator.data.get("voltage", 0) or 0
        phases = self.coordinator.data.get("phases_used", 1) or 1

        # If voltage not reported but we have power, use typical EU grid voltage
        if (voltage == 0 or voltage is None) and power > 0:
            # Use typical EU single-phase voltage (230V)
            voltage = 230.0
            self.coordinator.data["voltage"] = voltage
            _LOGGER.debug("Using typical grid voltage: 230V (not reported by wallbox)")

        # Calculate voltage from per-phase if main voltage is missing
        if voltage == 0 or voltage is None:
            l1 = self.coordinator.data.get("voltage_l1", 0) or 0
            l2 = self.coordinator.data.get("voltage_l2", 0) or 0
            l3 = self.coordinator.data.get("voltage_l3", 0) or 0
            if l1 or l2 or l3:
                active = [x for x in [l1, l2, l3] if x > 0]
                if active:
                    voltage = sum(active) / len(active)
                    self.coordinator.data["voltage"] = voltage
                    _LOGGER.debug("Calculated voltage from phases: %.0fV", voltage)

        # Calculate total current from per-phase if main current is missing
        if (
            self.coordinator.data["current"] == 0
            or self.coordinator.data["current"] is None
        ):
            l1 = self.coordinator.data.get("current_l1", 0) or 0
            l2 = self.coordinator.data.get("current_l2", 0) or 0
            l3 = self.coordinator.data.get("current_l3", 0) or 0
            if l1 or l2 or l3:
                # Use average of active phases
                active = [x for x in [l1, l2, l3] if x > 0]
                if active:
                    self.coordinator.data["current"] = sum(active) / len(active)
                    _LOGGER.debug(
                        "Calculated current from phases: %.1fA",
                        self.coordinator.data["current"],
                    )

        # Calculate current from power and voltage if still missing
        if (
            (
                self.coordinator.data["current"] == 0
                or self.coordinator.data["current"] is None
            )
            and power > 0
            and voltage > 0
        ):
            # I = P / (V * phases * sqrt(3) for 3-phase, or V for 1-phase)
            if phases == 3:
                calculated_current = power / (voltage * 1.732)  # sqrt(3) ≈ 1.732
            else:
                calculated_current = power / voltage
            self.coordinator.data["current"] = round(calculated_current, 1)
            _LOGGER.info(
                "✓ Calculated current: %.1fA (from P=%dW, V=%.0fV, %d-phase)",
                calculated_current,
                power,
                voltage,
                phases,
            )

        # Smart connector status - derive from charging state if not explicitly set
        if self.coordinator.data.get("connector_status") == "Unknown":
            charging_state = self.coordinator.data.get("charging_state")
            if charging_state in [
                "Charging",
                "SuspendedEV",
                "SuspendedEVSE",
                "EVConnected",
            ]:
                self.coordinator.data["connector_status"] = "Occupied"
            elif charging_state == "Available":
                self.coordinator.data["connector_status"] = "Available"
            elif charging_state == "Faulted":
                self.coordinator.data["connector_status"] = "Faulted"

        # Trigger update
        self.coordinator.async_set_updated_data(self.coordinator.data)

        return call_result.TransactionEvent()

    @on("NotifyReport")
    async def on_notify_report(
        self, request_id, seq_no, generated_at, report_data, **kwargs
    ):
        """Handle NotifyReport - configuration data."""
        _LOGGER.debug("Notify Report: request_id=%s, seq=%s", request_id, seq_no)
        return call_result.NotifyReport()

    @on("SecurityEventNotification")
    async def on_security_event_notification(self, type, timestamp, **kwargs):
        """Handle SecurityEventNotification - wallbox security events like time sync."""
        _LOGGER.debug("Security Event: type=%s, timestamp=%s", type, timestamp)
        return call_result.SecurityEventNotification()


class BMWWallboxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching BMW Wallbox data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

        self.config = config
        self.server = None
        self.charge_point: WallboxChargePoint | None = None
        self.current_transaction_id: str | None = None
        self.device_info: dict[str, Any] = {}

        # Initialize data
        self.data: dict[str, Any] = {
            "connected": False,
            "charging_state": "Unknown",
            "power": 0.0,
            "energy_total": None,  # None until first valid reading (prevents 0 corruption)
            "energy_session": 0.0,
            "current": 0.0,
            "voltage": 0.0,
            "transaction_id": None,
            "connector_status": "Unknown",
            "evse_id": 1,
            "connector_id": 1,
            "phases_used": 1,
            "last_heartbeat": None,
            "event_type": None,
            "trigger_reason": None,
            "stopped_reason": None,
            "sequence_number": 0,
            "last_update": None,
            "id_token": None,
            "id_token_type": None,
            "context": None,
            "location": None,
            # Additional power measurements
            "power_active_export": None,
            "power_reactive_import": None,
            "power_reactive_export": None,
            "power_offered": None,
            "power_factor": None,
            # Additional energy measurements
            "energy_active_export": None,
            "energy_reactive_import": None,
            "energy_reactive_export": None,
            # Per-phase measurements
            "current_l1": None,
            "current_l2": None,
            "current_l3": None,
            "voltage_l1": None,
            "voltage_l2": None,
            "voltage_l3": None,
            # Other measurements
            "frequency": None,
            "temperature": None,
            # Configurable settings
            "led_brightness": 46,  # Default from capabilities report
            "current_limit": config.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT),
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the wallbox."""
        # The data is updated in real-time by OCPP message handlers
        # This just returns the current state
        return self.data

    async def async_configure_wallbox_for_pause_resume(self) -> None:
        """Configure wallbox to allow pause/resume without ending transaction.

        Sets StopTxOnEVSideDisconnect to false so we can use SetChargingProfile(0A)
        to pause without the transaction ending.
        """
        if not self.charge_point:
            return

        _LOGGER.info("🔧 Configuring wallbox for pause/resume support...")

        try:
            # Try to set StopTxOnEVSideDisconnect to false
            set_var = SetVariableDataType(
                attribute_type=AttributeEnumType.actual,
                attribute_value="false",
                component=ComponentType(name="TxCtrlr"),
                variable=VariableType(name="StopTxOnEVSideDisconnect"),
            )

            response = await asyncio.wait_for(
                self.charge_point.call(call.SetVariables(set_variable_data=[set_var])),
                timeout=15.0,
            )

            if response.set_variable_result:
                result = response.set_variable_result[0]
                status = result.get("attribute_status", "Unknown")
                _LOGGER.info("StopTxOnEVSideDisconnect configuration: %s", status)
                if status == "Accepted":
                    _LOGGER.info("✅ Wallbox configured for pause/resume!")
                else:
                    _LOGGER.warning(
                        "⚠️ Could not configure StopTxOnEVSideDisconnect: %s", status
                    )
        except Exception as e:
            _LOGGER.warning("Could not configure StopTxOnEVSideDisconnect: %s", e)

    async def async_start_server(self) -> None:
        """Start the OCPP WebSocket server."""
        _LOGGER.info("Starting OCPP server on port %s", self.config["port"])

        # Setup SSL context - load_cert_chain is blocking, run in executor
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        await self.hass.async_add_executor_job(
            ssl_context.load_cert_chain,
            self.config["ssl_cert"],
            self.config["ssl_key"],
        )

        async def on_connect(websocket):
            """Handle new wallbox connection."""
            # Get path from websocket for newer websockets library
            path = (
                websocket.request.path
                if hasattr(websocket, "request")
                else websocket.path
            )
            charge_point_id = path.strip("/")
            _LOGGER.info("Wallbox connected: %s", charge_point_id)

            self.charge_point = WallboxChargePoint(charge_point_id, websocket, self)
            self.data["connected"] = True
            self.async_set_updated_data(self.data)

            # Request meter values on connect to get current energy
            asyncio.create_task(self._request_meter_values_on_connect())

            # Configure wallbox for pause/resume support
            asyncio.create_task(self.async_configure_wallbox_for_pause_resume())

            try:
                await self.charge_point.start()
            except websockets.exceptions.ConnectionClosed:
                _LOGGER.warning("Wallbox disconnected: %s", charge_point_id)
                self.data["connected"] = False
                self.async_set_updated_data(self.data)

        # Start server
        self.server = await websockets.serve(
            on_connect,
            "0.0.0.0",
            self.config["port"],
            subprotocols=["ocpp2.0.1"],
            ssl=ssl_context,
        )

        _LOGGER.info("OCPP server started successfully")

    async def _request_meter_values_on_connect(self) -> None:
        """Request meter values after wallbox connects."""
        # Wait for connection to stabilize
        await asyncio.sleep(3)
        if self.charge_point:
            _LOGGER.info("Requesting meter values on connect...")
            await self.async_trigger_meter_values()

    async def async_stop_server(self) -> None:
        """Stop the OCPP server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            _LOGGER.info("OCPP server stopped")

    async def async_start_charging(
        self, status_callback=None, allow_nuke: bool = True
    ) -> dict:
        """Start/resume charging using SetChargingProfile(32A).

        If there's an existing transaction, uses SetChargingProfile to resume.
        If no transaction, uses RequestStartTransaction to create one.

        NUKE OPTION: If all attempts fail and allow_nuke=True, reboots the wallbox
        as a last resort (~60 seconds downtime).

        Returns a dict with:
            - success: bool
            - message: str (user-friendly message)
            - action: str (what was done)
        """
        _LOGGER.info("🟢 START CHARGING REQUESTED")

        result = {
            "success": False,
            "message": "",
            "action": "failed",
        }

        # Check if wallbox is connected
        if not self.charge_point:
            result["message"] = "Wallbox not connected"
            _LOGGER.error("❌ No wallbox connected")
            return result

        charging_state = self.data.get("charging_state")
        power = self.data.get("power", 0)

        _LOGGER.info(
            "Current state: charging_state=%s, power=%sW, tx_id=%s",
            charging_state,
            power,
            self.current_transaction_id,
        )

        # Already charging?
        if charging_state == "Charging" and power > 0:
            result["success"] = True
            result["message"] = "Already charging"
            result["action"] = "already_charging"
            return result

        # If there's an existing transaction, try to resume with SetChargingProfile
        if self.current_transaction_id:
            if status_callback:
                await status_callback("Resuming charging...")

            _LOGGER.info("▶️ Transaction exists - resuming with SetChargingProfile")
            resume_result = await self.async_resume_charging()

            if resume_result["success"]:
                result["success"] = True
                result["message"] = "Charging resumed! ⚡"
                result["action"] = "resumed"
                return result
            _LOGGER.warning(
                "Resume failed: %s - will try RequestStartTransaction",
                resume_result["message"],
            )
            # Don't nuke yet - let RequestStartTransaction try first

        if status_callback:
            await status_callback("Starting charging session...")

        _LOGGER.info("📤 Sending RequestStartTransaction...")
        try:
            # Use configured RFID token if available, otherwise no authorization
            rfid_token = self.config.get("rfid_token", "")
            if rfid_token:
                _LOGGER.info("Using RFID token: %s", rfid_token)
                id_token = IdTokenType(
                    id_token=rfid_token,
                    type=IdTokenEnumType.local,
                )
            else:
                _LOGGER.info("No RFID configured, using NoAuthorization")
                id_token = IdTokenType(
                    id_token="",
                    type=IdTokenEnumType.no_authorization,
                )

            response = await asyncio.wait_for(
                self.charge_point.call(
                    call.RequestStartTransaction(
                        id_token=id_token,
                        remote_start_id=int(datetime.utcnow().timestamp()),
                        evse_id=1,
                    )
                ),
                timeout=15.0,
            )

            _LOGGER.info("RequestStartTransaction response: %s", response.status)

            if response.status == RequestStartStopStatusEnumType.accepted:
                # Store the transaction ID from response if available
                if hasattr(response, "transaction_id") and response.transaction_id:
                    self.current_transaction_id = response.transaction_id
                    self.data["transaction_id"] = response.transaction_id
                    _LOGGER.info("New transaction ID: %s", response.transaction_id)

                # Wait for transaction to establish, then send SetChargingProfile to enable current
                await asyncio.sleep(2)

                max_current = self.data.get(
                    "current_limit", self.config.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
                )
                _LOGGER.info(
                    "⚡ Sending SetChargingProfile(%dA) to enable current...",
                    max_current,
                )

                try:
                    # Need to get the current transaction ID (might be from response or from TransactionEvent)
                    tx_id = self.current_transaction_id or self.data.get(
                        "transaction_id"
                    )
                    if tx_id:
                        start_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

                        schedule = ChargingScheduleType(
                            id=1,
                            start_schedule=start_time,
                            charging_rate_unit=ChargingRateUnitEnumType.amps,
                            charging_schedule_period=[
                                ChargingSchedulePeriodType(
                                    start_period=0, limit=float(max_current)
                                )
                            ],
                        )

                        profile = ChargingProfileType(
                            id=999,
                            stack_level=0,
                            charging_profile_purpose=ChargingProfilePurposeEnumType.tx_profile,
                            charging_profile_kind=ChargingProfileKindEnumType.absolute,
                            transaction_id=tx_id,
                            charging_schedule=[schedule],
                        )

                        profile_response = await asyncio.wait_for(
                            self.charge_point.call(
                                call.SetChargingProfile(
                                    evse_id=1, charging_profile=profile
                                )
                            ),
                            timeout=15.0,
                        )
                        _LOGGER.info(
                            "SetChargingProfile response: %s", profile_response.status
                        )

                        # Wait for charging to ramp up and request meter values
                        _LOGGER.info("⏳ Waiting 5 seconds for charging to ramp up...")
                        await asyncio.sleep(5)
                        await self.async_trigger_meter_values()

                except Exception as e:
                    _LOGGER.warning(
                        "SetChargingProfile failed: %s (charging may still work)", e
                    )

                result["success"] = True
                result["message"] = "Charging started! ⚡"
                result["action"] = "started"
            else:
                result["message"] = (
                    f"Start rejected: {response.status}. Is the car connected?"
                )
                result["action"] = "rejected"

                # 💣 NUKE OPTION: If everything failed and nuke is allowed, reboot wallbox
                if allow_nuke:
                    _LOGGER.warning(
                        "💣 NUKE OPTION: All start methods failed, rebooting wallbox..."
                    )
                    if status_callback:
                        await status_callback(
                            "💣 NUKE: Rebooting wallbox (last resort)..."
                        )

                    nuke_result = await self.async_reset_wallbox(status_callback)
                    if nuke_result["success"]:
                        result["message"] = (
                            "💣 Wallbox rebooting (~60s). Charging will auto-start."
                        )
                        result["action"] = "nuked"
                        result["success"] = (
                            True  # Consider it success since reboot works
                        )
                    else:
                        result["message"] = (
                            f"All methods failed. Nuke also failed: {nuke_result['message']}"
                        )

            return result

        except TimeoutError:
            result["message"] = "Command timed out - wallbox not responding"
            _LOGGER.error("RequestStartTransaction timed out!")
        except Exception as err:
            result["message"] = f"Error: {err!s}"
            _LOGGER.error("Failed to start charging: %s", err)

        # 💣 NUKE OPTION: If we got here due to exception and nuke is allowed
        if not result["success"] and allow_nuke:
            _LOGGER.warning(
                "💣 NUKE OPTION: Start failed with error, rebooting wallbox..."
            )
            if status_callback:
                await status_callback("💣 NUKE: Rebooting wallbox (last resort)...")

            nuke_result = await self.async_reset_wallbox(status_callback)
            if nuke_result["success"]:
                result["message"] = (
                    "💣 Wallbox rebooting (~60s). Charging will auto-start."
                )
                result["action"] = "nuked"
                result["success"] = True

        return result

    async def async_reset_wallbox(self, status_callback=None) -> dict:
        """Reset the wallbox to clear stuck transaction state.

        This sends Reset(Immediate) which:
        1. Ends any stuck transaction
        2. Reboots the wallbox (~60 seconds)
        3. After reboot, a new transaction auto-starts if cable is plugged in
        """
        _LOGGER.info("🔄 RESET WALLBOX REQUESTED")

        result = {
            "success": False,
            "message": "",
            "action": "reset",
        }

        if not self.charge_point:
            result["message"] = "Wallbox not connected"
            return result

        if status_callback:
            await status_callback("Sending reset command to wallbox...")

        try:
            response = await asyncio.wait_for(
                self.charge_point.call(call.Reset(type=ResetEnumType.immediate)),
                timeout=15.0,
            )

            _LOGGER.info("Reset response: %s", response.status)

            if response.status == ResetStatusEnumType.accepted:
                result["success"] = True
                result["message"] = (
                    "Reset accepted - wallbox is rebooting (~60 seconds)"
                )

                # Mark as disconnected since it will reboot
                self.data["connected"] = False
                self.current_transaction_id = None
                self.data["transaction_id"] = None
                self.async_set_updated_data(self.data)
            else:
                result["message"] = f"Reset rejected: {response.status}"

            return result

        except TimeoutError:
            result["message"] = "Reset command timed out"
            return result
        except Exception as err:
            result["message"] = f"Reset error: {err!s}"
            _LOGGER.error("Reset failed: %s", err)
            return result

    async def async_start_charging_with_reset(self, status_callback=None) -> dict:
        """Full start sequence - resets if needed, waits, then starts.

        This handles the complete flow including stuck transaction recovery.
        """
        _LOGGER.info("🚀 FULL START SEQUENCE INITIATED")

        # First try to start normally
        if status_callback:
            await status_callback("Checking wallbox status...")

        result = await self.async_start_charging(status_callback)

        # If it worked or doesn't need reset, return
        if result["success"] or not result.get("needs_reset"):
            return result

        # Need to reset first
        if status_callback:
            await status_callback("Transaction stuck - resetting wallbox...")

        reset_result = await self.async_reset_wallbox(status_callback)

        if not reset_result["success"]:
            return reset_result

        # Wait for reboot
        if status_callback:
            await status_callback("Wallbox rebooting - please wait ~60 seconds...")

        _LOGGER.info("⏳ Waiting for wallbox to reboot...")

        # Wait in chunks so we can update status
        for i in range(12):  # 12 x 5 = 60 seconds
            await asyncio.sleep(5)
            remaining = 60 - (i + 1) * 5
            if status_callback and remaining > 0:
                await status_callback(f"Wallbox rebooting - {remaining}s remaining...")

        # Wait for reconnection
        if status_callback:
            await status_callback("Waiting for wallbox to reconnect...")

        # Wait up to 30 more seconds for reconnection
        for i in range(6):
            await asyncio.sleep(5)
            if self.data.get("connected") and self.current_transaction_id:
                _LOGGER.info("✅ Wallbox reconnected with new transaction")
                break

        if not self.data.get("connected"):
            return {
                "success": False,
                "message": "Wallbox did not reconnect after reset. Check the wallbox.",
                "action": "reconnect_failed",
            }

        # Now try to start again
        if status_callback:
            await status_callback("Sending start command...")

        return await self.async_start_charging(status_callback)

    async def async_refresh_transaction_id(self) -> str | None:
        """Query the wallbox to get/verify the current transaction ID.

        Uses GetTransactionStatus to verify the transaction is still active.
        Returns the transaction_id if valid, None otherwise.
        """
        if not self.charge_point:
            _LOGGER.warning("Cannot refresh transaction ID - no wallbox connected")
            return None

        if not self.current_transaction_id:
            _LOGGER.debug("No transaction ID to refresh")
            return None

        _LOGGER.info(
            "🔄 Refreshing transaction status for: %s", self.current_transaction_id
        )

        try:
            response = await asyncio.wait_for(
                self.charge_point.call(
                    call.GetTransactionStatus(
                        transaction_id=self.current_transaction_id
                    )
                ),
                timeout=10.0,
            )

            _LOGGER.info(
                "GetTransactionStatus response: ongoing=%s, messages_in_queue=%s",
                response.ongoing_indicator
                if hasattr(response, "ongoing_indicator")
                else "N/A",
                response.messages_in_queue
                if hasattr(response, "messages_in_queue")
                else "N/A",
            )

            # If transaction is ongoing, the ID is valid
            if hasattr(response, "ongoing_indicator") and response.ongoing_indicator:
                _LOGGER.info(
                    "✅ Transaction %s is still active", self.current_transaction_id
                )
                return self.current_transaction_id
            _LOGGER.warning(
                "⚠️ Transaction %s may have ended (ongoing=%s)",
                self.current_transaction_id,
                getattr(response, "ongoing_indicator", None),
            )
            # Transaction might have ended - clear it
            # But don't clear yet, let the caller decide
            return self.current_transaction_id

        except TimeoutError:
            _LOGGER.warning("GetTransactionStatus timed out")
            return self.current_transaction_id  # Return existing ID, let command try
        except Exception as err:
            _LOGGER.warning("GetTransactionStatus failed: %s", err)
            return self.current_transaction_id  # Return existing ID, let command try

    async def async_pause_charging(self) -> dict:
        """Pause charging via SetChargingProfile(0A) - EVCC-style.

        This pauses charging without ending the transaction!
        Much better than RequestStopTransaction which creates stuck states.
        """
        _LOGGER.info("⏸️ PAUSE CHARGING - SetChargingProfile(0A)")

        result = {"success": False, "message": ""}

        if not self.charge_point:
            result["message"] = "Wallbox not connected"
            return result

        # Refresh transaction ID from wallbox before attempting pause
        await self.async_refresh_transaction_id()

        if not self.current_transaction_id:
            result["message"] = "No active charging session"
            return result

        # Check if already paused (power is 0)
        power = self.data.get("power", 0) or 0
        if power == 0:
            result["success"] = True
            result["message"] = "Charging already paused"
            _LOGGER.info("Already at 0W - no need to send pause command")
            return result

        _LOGGER.info(
            "Using transaction_id: %s (power=%sW)", self.current_transaction_id, power
        )

        try:
            # First clear ALL existing profiles to ensure clean state (like resume does)
            _LOGGER.info("Clearing ALL charging profiles first...")
            try:
                clear_response = await asyncio.wait_for(
                    self.charge_point.call(call.ClearChargingProfile()), timeout=10.0
                )
                _LOGGER.info("ClearChargingProfile response: %s", clear_response.status)
            except Exception as e:
                _LOGGER.debug("ClearChargingProfile failed (OK to ignore): %s", e)

            start_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

            schedule = ChargingScheduleType(
                id=1,
                start_schedule=start_time,
                charging_rate_unit=ChargingRateUnitEnumType.amps,
                charging_schedule_period=[
                    ChargingSchedulePeriodType(start_period=0, limit=0.0)
                ],
            )

            # Use stackLevel=0 for highest priority (same as resume)
            profile = ChargingProfileType(
                id=999,
                stack_level=0,
                charging_profile_purpose=ChargingProfilePurposeEnumType.tx_profile,
                charging_profile_kind=ChargingProfileKindEnumType.absolute,
                transaction_id=self.current_transaction_id,
                charging_schedule=[schedule],
            )

            response = await asyncio.wait_for(
                self.charge_point.call(
                    call.SetChargingProfile(evse_id=1, charging_profile=profile)
                ),
                timeout=15.0,
            )

            _LOGGER.info("Pause response: %s", response.status)

            # Log additional status info if available
            if hasattr(response, "status_info") and response.status_info:
                _LOGGER.info(
                    "Pause status_info: reason=%s, additional=%s",
                    response.status_info.get("reason_code", "N/A"),
                    response.status_info.get("additional_info", "N/A"),
                )

            if response.status == "Accepted":
                result["success"] = True
                result["message"] = "Charging paused"
            else:
                reason = ""
                if hasattr(response, "status_info") and response.status_info:
                    reason = f" ({response.status_info.get('reason_code', '')})"
                result["message"] = f"Pause rejected: {response.status}{reason}"

            return result

        except TimeoutError:
            result["message"] = "Command timed out"
            return result
        except Exception as err:
            result["message"] = f"Error: {err!s}"
            _LOGGER.error("Failed to pause: %s", err)
            return result

    async def async_resume_charging(self, current_limit: float | None = None) -> dict:
        """Resume charging via SetChargingProfile - EVCC-style.

        Args:
            current_limit: Current limit in Amps. If None, uses the tracked user preference.
        """
        # Use tracked user preference if no limit specified
        if current_limit is None:
            current_limit = self.data.get(
                "current_limit", self.config.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT)
            )

        _LOGGER.info("▶️ RESUME CHARGING - SetChargingProfile(%dA)", current_limit)

        result = {"success": False, "message": ""}

        if not self.charge_point:
            result["message"] = "Wallbox not connected"
            return result

        # Refresh transaction ID from wallbox before attempting resume
        await self.async_refresh_transaction_id()

        if not self.current_transaction_id:
            result["message"] = "No active session - try starting first"
            return result

        _LOGGER.info("Using transaction_id: %s", self.current_transaction_id)

        try:
            # First clear ALL existing profiles to ensure clean state
            _LOGGER.info("Clearing ALL charging profiles first...")
            try:
                # Clear without specifying ID = clear all profiles
                clear_response = await asyncio.wait_for(
                    self.charge_point.call(call.ClearChargingProfile()), timeout=10.0
                )
                _LOGGER.info(
                    "ClearChargingProfile (all) response: %s", clear_response.status
                )
            except Exception as e:
                _LOGGER.debug("ClearChargingProfile failed (OK to ignore): %s", e)

            start_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

            schedule = ChargingScheduleType(
                id=1,
                start_schedule=start_time,
                charging_rate_unit=ChargingRateUnitEnumType.amps,
                charging_schedule_period=[
                    ChargingSchedulePeriodType(
                        start_period=0, limit=float(current_limit)
                    )
                ],
            )

            # Use stackLevel=0 for highest priority
            profile = ChargingProfileType(
                id=999,
                stack_level=0,
                charging_profile_purpose=ChargingProfilePurposeEnumType.tx_profile,
                charging_profile_kind=ChargingProfileKindEnumType.absolute,
                transaction_id=self.current_transaction_id,
                charging_schedule=[schedule],
            )

            response = await asyncio.wait_for(
                self.charge_point.call(
                    call.SetChargingProfile(evse_id=1, charging_profile=profile)
                ),
                timeout=15.0,
            )

            _LOGGER.info("Resume response: %s", response.status)

            # Log additional status info if available
            if hasattr(response, "status_info") and response.status_info:
                _LOGGER.info(
                    "Resume status_info: reason=%s, additional=%s",
                    response.status_info.get("reason_code", "N/A"),
                    response.status_info.get("additional_info", "N/A"),
                )

            if response.status == "Accepted":
                result["success"] = True
                result["message"] = f"Charging resumed at {current_limit}A"

                # Trigger meter values refresh after 3 seconds so power reading updates
                async def delayed_refresh():
                    await asyncio.sleep(3)
                    await self.async_trigger_meter_values()

                asyncio.create_task(delayed_refresh())
            else:
                reason = ""
                if hasattr(response, "status_info") and response.status_info:
                    reason = f" ({response.status_info.get('reason_code', '')})"
                result["message"] = f"Resume rejected: {response.status}{reason}"

            return result

        except TimeoutError:
            result["message"] = "Command timed out"
            return result
        except Exception as err:
            result["message"] = f"Error: {err!s}"
            _LOGGER.error("Failed to resume: %s", err)
            return result

    async def async_stop_charging(self) -> dict:
        """Stop/pause charging using SetChargingProfile(0A).

        This pauses charging WITHOUT ending the transaction, so we can resume later.
        Much better than RequestStopTransaction which puts the charger in Finishing
        state and prevents restart.

        Returns a dict with:
            - success: bool
            - message: str (user-friendly message)
        """
        _LOGGER.info("⏹️ STOP CHARGING - SetChargingProfile(0A)")
        return await self.async_pause_charging()

    async def async_set_current_limit(self, limit: float) -> bool:
        """Set charging current limit via SetChargingProfile.

        IMPORTANT: This only works during an active charging session!
        The BMW wallbox requires a transaction_id for tx_profile to work.

        Args:
            limit: Current limit in Amps (0 = pause, max = full speed)

        Returns:
            True if command was accepted, False otherwise
        """
        if not self.charge_point:
            _LOGGER.error("❌ No wallbox connected - cannot set current limit")
            return False

        if not self.current_transaction_id:
            _LOGGER.error(
                "❌ No active transaction - current limit requires an active charging session! "
                "Start charging first, then you can adjust the current limit."
            )
            return False

        _LOGGER.info(
            "⚡ Setting current limit to %sA for transaction %s",
            limit,
            self.current_transaction_id,
        )

        try:
            start_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

            schedule = ChargingScheduleType(
                id=1,
                start_schedule=start_time,
                charging_rate_unit=ChargingRateUnitEnumType.amps,
                charging_schedule_period=[
                    ChargingSchedulePeriodType(start_period=0, limit=float(limit))
                ],
            )

            # Always use tx_profile with the active transaction
            profile = ChargingProfileType(
                id=999,
                stack_level=1,
                charging_profile_purpose=ChargingProfilePurposeEnumType.tx_profile,
                charging_profile_kind=ChargingProfileKindEnumType.absolute,
                charging_schedule=[schedule],
                transaction_id=self.current_transaction_id,
            )

            _LOGGER.debug(
                "Sending SetChargingProfile: evse=1, profile_id=999, tx=%s, limit=%sA",
                self.current_transaction_id,
                limit,
            )

            response = await asyncio.wait_for(
                self.charge_point.call(
                    call.SetChargingProfile(evse_id=1, charging_profile=profile)
                ),
                timeout=15.0,
            )

            # Log the full response for debugging
            _LOGGER.info(
                "SetChargingProfile response: status=%s (type=%s)",
                response.status,
                type(response.status).__name__,
            )

            # Handle both string and enum status
            status_str = str(response.status)
            if status_str == "Accepted" or "accepted" in status_str.lower():
                _LOGGER.info("✅ Current limit set to %sA - accepted by wallbox", limit)
                # Track the new limit for future start/resume operations
                self.data["current_limit"] = limit
                self.async_set_updated_data(self.data)
                return True
            _LOGGER.warning(
                "⚠️ Current limit rejected by wallbox: %s. "
                "This can happen if the car is not drawing power or the session ended.",
                response.status,
            )
            return False

        except TimeoutError:
            _LOGGER.error("❌ Set current limit timed out - wallbox not responding!")
            return False
        except Exception as err:
            _LOGGER.error("❌ Failed to set current limit: %s", err, exc_info=True)
            return False

    async def async_trigger_meter_values(self) -> bool:
        """Trigger wallbox to send meter values immediately.

        This uses TriggerMessage to request the wallbox send current meter readings.
        Useful for debugging or getting fresh data.
        """
        if not self.charge_point:
            _LOGGER.error("No wallbox connected")
            return False

        _LOGGER.info("🔄 Triggering meter values update...")

        try:
            from ocpp.v201 import call as ocpp_call
            from ocpp.v201.enums import MessageTriggerEnumType

            response = await asyncio.wait_for(
                self.charge_point.call(
                    ocpp_call.TriggerMessage(
                        requested_message=MessageTriggerEnumType.meter_values,
                        evse={"id": 1, "connector_id": 1},
                    )
                ),
                timeout=15.0,
            )

            _LOGGER.info("TriggerMessage response: %s", response.status)
            return response.status == "Accepted"

        except TimeoutError:
            _LOGGER.error("TriggerMessage timed out!")
            return False
        except Exception as err:
            _LOGGER.error("Failed to trigger meter values: %s", err, exc_info=True)
            return False

    async def async_set_led_brightness(self, brightness: int) -> bool:
        """Set LED brightness via SetVariables (0-100%).

        Uses OCPP 2.0.1 SetVariables command to configure the wallbox LED.
        """
        if not self.charge_point:
            _LOGGER.error("No wallbox connected")
            return False

        # Clamp value to valid range
        brightness = max(0, min(100, brightness))

        _LOGGER.info("Setting LED brightness to %d%%", brightness)

        try:
            set_var = SetVariableDataType(
                attribute_type=AttributeEnumType.actual,
                attribute_value=str(brightness),
                component=ComponentType(name="ChargingStation"),
                variable=VariableType(name="StatusLedBrightness"),
            )

            response = await asyncio.wait_for(
                self.charge_point.call(call.SetVariables(set_variable_data=[set_var])),
                timeout=15.0,
            )

            # Check result
            if response.set_variable_result:
                result = response.set_variable_result[0]
                status = result.get("attribute_status", "Unknown")
                _LOGGER.info("Set LED brightness response: %s", status)

                if status == "Accepted":
                    return True
                # Log rejection reason if available
                status_info = result.get("attribute_status_info", {})
                reason = (
                    status_info.get("reason_code", "")
                    if isinstance(status_info, dict)
                    else ""
                )
                _LOGGER.warning("LED brightness rejected: %s %s", status, reason)
                return False

            return False

        except TimeoutError:
            _LOGGER.error("Set LED brightness timed out!")
            return False
        except Exception as err:
            _LOGGER.error("Failed to set LED brightness: %s", err)
            return False
