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
    NotifyEVChargingNeedsStatusEnumType,
    RegistrationStatusEnumType,
    RequestStartStopStatusEnumType,
    ResetEnumType,
    ResetStatusEnumType,
)
import websockets

from .const import (
    CONF_MAX_CURRENT,
    CONF_SCAN_INTERVAL,
    DEFAULT_MAX_CURRENT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# --- OCPP call serialisation / timeout (issue #14) ---
# The ocpp library serialises outgoing calls and matches every response to its
# request through an internal queue (see charge_point._get_specific_response).
# Cancelling a call() while it is still waiting for a response - which a short
# external asyncio.wait_for does - leaves the wallbox's late reply orphaned in
# that queue with no waiter. The next call then reads that stale reply first
# ("Ignoring response with unknown unique id"), so every response is off by one
# and SetChargingProfile appears to be ignored while the current stays stuck at
# its previous value. Under a house-load automation firing SetChargingProfile
# repeatedly (concurrently with the background meter poll) the orphans pile up
# and the desync becomes permanent.
#
# Fix: let the library's own response_timeout be the single authority on how
# long to wait (never a shorter external one that cancels mid-flight) and keep
# only a slightly longer backstop for a genuinely wedged socket.
OCPP_RESPONSE_TIMEOUT = 20.0
OCPP_CALL_BACKSTOP_TIMEOUT = 30.0


def _compute_live_current(
    data: dict[str, Any],
    reported_total: float | None,
    power: float | None,
    voltage: float | None,
    phases: int,
) -> float | None:
    """Best-effort live charging current in amps, recomputed every meter update.

    Recomputed on every MeterValues/TransactionEvent so the sensor never sticks
    at a stale value once power or phase currents change (issue #15).

    Order of preference, by observed reliability on the BMW/Delta firmware:
    1. the average of the active per-phase currents (these update correctly),
    2. a value derived from power and voltage (always fresh while charging),
    3. a directly reported non-phased Current.Import - LAST resort, because this
       firmware leaves that total register frozen at the pre-limit value while
       the per-phase readings track reality.
    Returns None when nothing usable is available.
    """
    active = [
        x
        for x in (
            data.get("current_l1") or 0,
            data.get("current_l2") or 0,
            data.get("current_l3") or 0,
        )
        if x > 0
    ]
    if active:
        return round(sum(active) / len(active), 1)

    if power and power > 0 and voltage and voltage > 0:
        if phases == 3:
            return round(power / (voltage * 1.732), 1)  # sqrt(3) ≈ 1.732
        return round(power / voltage, 1)

    if reported_total is not None:
        return round(reported_total, 1)

    return None


class WallboxChargePoint(cp):
    """ChargePoint handler for the BMW wallbox."""

    def __init__(
        self,
        charge_point_id: str,
        websocket,
        coordinator: BMWWallboxCoordinator,
        response_timeout: float = OCPP_RESPONSE_TIMEOUT,
    ):
        """Initialize the ChargePoint.

        ``response_timeout`` is the single authority on how long we wait for a
        wallbox reply; command paths must not wrap ``call()`` in a shorter
        timeout (issue #14 - see OCPP_RESPONSE_TIMEOUT).
        """
        super().__init__(charge_point_id, websocket, response_timeout=response_timeout)
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

        reported_total_current = None  # non-phased Current.Import seen this event
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
                    if phase in ("L1", "L1-N"):
                        self.coordinator.data["current_l1"] = float(value)
                    elif phase in ("L2", "L2-N"):
                        self.coordinator.data["current_l2"] = float(value)
                    elif phase in ("L3", "L3-N"):
                        self.coordinator.data["current_l3"] = float(value)
                    else:
                        reported_total_current = float(value)
                elif measurand == "Voltage":
                    if phase == "L1-N":
                        self.coordinator.data["voltage_l1"] = float(value)
                    elif phase == "L2-N":
                        self.coordinator.data["voltage_l2"] = float(value)
                    elif phase == "L3-N":
                        self.coordinator.data["voltage_l3"] = float(value)
                    else:
                        self.coordinator.data["voltage"] = float(value)

        # Recompute the live current so the sensor never sticks (issue #15)
        self.coordinator.data["current"] = _compute_live_current(
            self.coordinator.data,
            reported_total_current,
            self.coordinator.data.get("power") or 0,
            self.coordinator.data.get("voltage") or 0,
            self.coordinator.data.get("phases_used", 1) or 1,
        )

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

        # On a fresh session start, push the configured limit immediately so the
        # wallbox doesn't run at full power until the next poll (issue #15).
        if event_type == "Started":
            asyncio.create_task(
                self.coordinator.async_apply_limit_on_transaction_start()
            )

        # When charging resumes from a suspended state, re-push the limit: the
        # Delta firmware discards TxProfiles it accepted while suspended, so the
        # session would otherwise draw the hardware maximum (issue #19).
        previous_state = self.coordinator.data.get("charging_state")
        new_state = transaction_info.get("charging_state")
        if (
            event_type == "Updated"
            and new_state == "Charging"
            and previous_state in ("SuspendedEV", "SuspendedEVSE")
        ):
            asyncio.create_task(
                self.coordinator.async_apply_limit_on_charging_resumed()
            )

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
        reported_total_current = None  # non-phased Current.Import seen this event
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
                            # Total or unspecified - prefer this as the live current
                            reported_total_current = current_value

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

        # === Live charging current (issue #15) ===
        # Recompute on every event so the sensor never sticks at a stale value
        # once power/phase currents change. Priority: directly reported total →
        # per-phase average → derived from power/voltage.
        self.coordinator.data["current"] = _compute_live_current(
            self.coordinator.data, reported_total_current, power, voltage, phases
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

        # Session ended — clear live readings so the sensors don't stay frozen at
        # the last value once charging stops (issue #15).
        if event_type == "Ended":
            for key in ("current", "power", "current_l1", "current_l2", "current_l3"):
                self.coordinator.data[key] = 0

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

    @on("NotifyEvent")
    async def on_notify_event(self, **kwargs):
        """Handle NotifyEvent (OCPP 2.0.1).

        Some chargers send this frequently. We accept it to avoid repeated
        NotImplementedError / KeyError that can overload HA logs and event loop.
        """
        _LOGGER.debug("NotifyEvent received: %s", kwargs)
        return call_result.NotifyEvent()

    @on("NotifyEVChargingNeeds")
    async def on_notify_ev_charging_needs(self, **kwargs):
        """Handle NotifyEVChargingNeeds (OCPP 2.0.1 / ISO 15118).

        BMW Wallbox Plus Gen 4 (Delta) firmware sends this during the EV
        charging negotiation. Without a registered handler the ocpp library
        replies with a CallError (NotImplementedError) and floods the HA log.
        Acknowledging it cleanly (Accepted) stops the error spam and keeps the
        OCPP session healthy. Same approach as NotifyEvent. See issue #14.
        """
        _LOGGER.debug("NotifyEVChargingNeeds received: %s", kwargs)
        return call_result.NotifyEVChargingNeeds(
            status=NotifyEVChargingNeedsStatusEnumType.accepted
        )

    @on("NotifyChargingLimit")
    async def on_notify_charging_limit(self, **kwargs):
        """Handle NotifyChargingLimit (OCPP 2.0.1).

        The BMW/Delta Gen 4 firmware sends this (even with no car charging, e.g.
        chargingLimitSource 'SO') to report an externally imposed charging limit.
        Without a handler the ocpp library replies with a CallError
        (NotImplementedError) and floods the HA log. We just acknowledge it. See
        issue #14, same approach as NotifyEVChargingNeeds / NotifyEvent.
        """
        _LOGGER.debug("NotifyChargingLimit received: %s", kwargs)
        return call_result.NotifyChargingLimit()

    @on("ClearedChargingLimit")
    async def on_cleared_charging_limit(self, **kwargs):
        """Handle ClearedChargingLimit (OCPP 2.0.1).

        The counterpart of NotifyChargingLimit - sent when an external charging
        limit is lifted. Acknowledged for the same reason (issue #14).
        """
        _LOGGER.debug("ClearedChargingLimit received: %s", kwargs)
        return call_result.ClearedChargingLimit()


class BMWWallboxCoordinator(DataUpdateCoordinator):
    """Class to manage fetching BMW Wallbox data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict[str, Any],
    ) -> None:
        """Initialize."""
        scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

        self.config = config
        self.server = None
        self.charge_point: WallboxChargePoint | None = None
        self.current_transaction_id: str | None = None
        self.device_info: dict[str, Any] = {}
        # Serialises every outbound OCPP call (see _ocpp_call, issue #14).
        self._call_lock = asyncio.Lock()
        # Serialises whole limit-change sequences (see async_set_current_limit).
        self._limit_lock = asyncio.Lock()

        # Initialize data
        self.data: dict[str, Any] = {
            "connected": False,
            "charging_state": "Unknown",
            "power": 0.0,
            "energy_total": None,  # None until first valid reading (prevents 0 corruption)
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

    async def _ocpp_call(self, payload: Any) -> Any:
        """Send one OCPP request, serialised and with a single authoritative timeout.

        Every wallbox command and background poll funnels through here so that:

        * only one request is ever in flight - this keeps multi-step sequences
          (e.g. ClearChargingProfile then SetChargingProfile) from interleaving
          with the periodic meter poll, and
        * ``call()`` is never wrapped in a timeout shorter than the library's own
          ``response_timeout``. A shorter external timeout used to cancel the
          request mid-flight; the wallbox's late reply was then orphaned in the
          ocpp response queue, desyncing every following response so
          SetChargingProfile appeared ignored and the current stuck at its
          previous value (issue #14).

        Raises ``TimeoutError`` if the wallbox never answers (backstop), or
        ``RuntimeError`` if no wallbox is connected.
        """
        if not self.charge_point:
            raise RuntimeError("Wallbox not connected")
        async with self._call_lock:
            return await asyncio.wait_for(
                self.charge_point.call(payload), OCPP_CALL_BACKSTOP_TIMEOUT
            )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the wallbox."""
        # When there's an active transaction, proactively request fresh meter values.
        # Some wallboxes don't include meter_value in TransactionEvent messages,
        # so we can't rely purely on push-based updates.
        if self.charge_point and self.current_transaction_id:
            await self.async_trigger_meter_values()
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

            response = await self._ocpp_call(
                call.SetVariables(set_variable_data=[set_var])
            )

            if response.set_variable_result:
                result = response.set_variable_result[0]
                status = result.get("attribute_status", "Unknown")
                _LOGGER.info("StopTxOnEVSideDisconnect configuration: %s", status)
                if status == "Accepted":
                    _LOGGER.info("✅ Wallbox configured for pause/resume!")
                else:
                    # Delta Gen 4 firmware rejects this variable, yet pause still
                    # works via a 0A SetChargingProfile - so this is informational,
                    # not a real failure (issue #14).
                    _LOGGER.info(
                        "StopTxOnEVSideDisconnect not settable (%s); pause/resume "
                        "still works via a 0A charging profile",
                        status,
                    )
        except Exception as e:
            _LOGGER.warning("Could not configure StopTxOnEVSideDisconnect: %s", e)

    async def async_start_server(self) -> None:
        """Start the OCPP WebSocket server."""
        rfid = self.config.get("rfid_token", "")
        _LOGGER.info(
            "Starting OCPP server on port %s (RFID token: %s)",
            self.config["port"],
            f"{rfid[:4]}...{rfid[-4:]}"
            if len(rfid) > 8
            else ("configured" if rfid else "not configured"),
        )

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

            # Recover transaction state (id_token, transaction_id) after HA restart
            asyncio.create_task(self._recover_transaction_on_connect())

            # Install TxDefaultProfile so the first session starts at the limit
            asyncio.create_task(self._apply_default_limit_on_connect())

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

    async def _recover_transaction_on_connect(self) -> None:
        """Recover active transaction state after wallbox connects.

        After HA restart, current_transaction_id and id_token reset to None.
        Trigger a TransactionEvent so the wallbox reports any ongoing transaction.
        """
        await asyncio.sleep(5)
        if not self.charge_point:
            return

        _LOGGER.info("🔄 Recovering transaction state on connect...")
        try:
            from ocpp.v201 import call as ocpp_call
            from ocpp.v201.enums import MessageTriggerEnumType

            response = await self._ocpp_call(
                ocpp_call.TriggerMessage(
                    requested_message=MessageTriggerEnumType.transaction_event,
                    evse={"id": 1, "connector_id": 1},
                )
            )

            _LOGGER.info("Transaction recovery trigger response: %s", response.status)
            if response.status == "Accepted":
                _LOGGER.info(
                    "✅ Transaction recovery triggered - waiting for TransactionEvent"
                )
            else:
                _LOGGER.info(
                    "No active transaction to recover (response: %s)", response.status
                )

        except TimeoutError:
            _LOGGER.warning("Transaction recovery trigger timed out")
        except Exception as err:
            _LOGGER.warning("Could not recover transaction state: %s", err)

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

            response = await self._ocpp_call(
                call.RequestStartTransaction(
                    id_token=id_token,
                    remote_start_id=int(datetime.utcnow().timestamp()),
                    evse_id=1,
                )
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
                    "current_limit",
                    self.config.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT),
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

                        profile_response = await self._ocpp_call(
                            call.SetChargingProfile(evse_id=1, charging_profile=profile)
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
            response = await self._ocpp_call(call.Reset(type=ResetEnumType.immediate))

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
            response = await self._ocpp_call(
                call.GetTransactionStatus(transaction_id=self.current_transaction_id)
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

    async def async_pause_charging(self, allow_nuke: bool = True) -> dict:
        """Pause charging via SetChargingProfile(0A) - EVCC-style.

        This pauses charging without ending the transaction!
        Much better than RequestStopTransaction which creates stuck states.

        NUKE OPTION: If pause fails and allow_nuke=True, reboots the wallbox
        as a last resort to stop charging (~60 seconds downtime).
        """
        _LOGGER.info("⏸️ PAUSE CHARGING - SetChargingProfile(0A)")

        result = {"success": False, "message": "", "action": "failed"}

        if not self.charge_point:
            result["message"] = "Wallbox not connected"
            # Can't nuke if not connected
            return result

        # Refresh transaction ID from wallbox before attempting pause
        await self.async_refresh_transaction_id()

        if not self.current_transaction_id:
            result["message"] = "No active charging session"
            return result

        # Refresh meter values before checking power (may be stale)
        await self.async_trigger_meter_values()

        # Check if already paused (power is 0 AND charging state confirms it)
        power = self.data.get("power", 0) or 0
        charging_state = self.data.get("charging_state", "")
        if power == 0 and charging_state not in ("Charging", "EVDetected"):
            result["success"] = True
            result["message"] = "Charging already paused"
            result["action"] = "already_paused"
            _LOGGER.info(
                "Already at 0W (state=%s) - no need to send pause command",
                charging_state,
            )
            return result

        _LOGGER.info(
            "Using transaction_id: %s (power=%sW)", self.current_transaction_id, power
        )

        try:
            # First clear ALL existing profiles to ensure clean state (like resume does)
            _LOGGER.info("Clearing ALL charging profiles first...")
            try:
                clear_response = await self._ocpp_call(call.ClearChargingProfile())
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

            response = await self._ocpp_call(
                call.SetChargingProfile(evse_id=1, charging_profile=profile)
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
                result["action"] = "paused"
            else:
                reason = ""
                if hasattr(response, "status_info") and response.status_info:
                    reason = f" ({response.status_info.get('reason_code', '')})"

                # 💣 NUKE OPTION: If pause rejected and nuke is allowed, reboot wallbox
                if allow_nuke:
                    _LOGGER.warning(
                        "💣 NUKE OPTION: Pause rejected (%s), rebooting wallbox to force stop!",
                        response.status,
                    )
                    nuke_result = await self.async_reset_wallbox()
                    if nuke_result["success"]:
                        result["success"] = True
                        result["message"] = (
                            "💣 Wallbox rebooting (~60s) to force stop charging"
                        )
                        result["action"] = "nuked"
                    else:
                        result["message"] = (
                            f"Pause rejected and reboot failed: {nuke_result['message']}"
                        )
                        result["action"] = "nuke_failed"
                else:
                    result["message"] = f"Pause rejected: {response.status}{reason}"

            return result

        except TimeoutError:
            _LOGGER.error("Pause command timed out!")
            # 💣 NUKE OPTION: If timeout and nuke is allowed, reboot wallbox
            if allow_nuke:
                _LOGGER.warning(
                    "💣 NUKE OPTION: Pause timed out, rebooting wallbox to force stop!"
                )
                nuke_result = await self.async_reset_wallbox()
                if nuke_result["success"]:
                    result["success"] = True
                    result["message"] = (
                        "💣 Wallbox rebooting (~60s) to force stop charging"
                    )
                    result["action"] = "nuked"
                else:
                    result["message"] = (
                        f"Pause timed out and reboot failed: {nuke_result['message']}"
                    )
                    result["action"] = "nuke_failed"
            else:
                result["message"] = "Command timed out"
            return result

        except Exception as err:
            _LOGGER.error("Failed to pause: %s", err)
            # 💣 NUKE OPTION: If exception and nuke is allowed, reboot wallbox
            if allow_nuke:
                _LOGGER.warning(
                    "💣 NUKE OPTION: Pause failed with error, rebooting wallbox to force stop!"
                )
                nuke_result = await self.async_reset_wallbox()
                if nuke_result["success"]:
                    result["success"] = True
                    result["message"] = (
                        "💣 Wallbox rebooting (~60s) to force stop charging"
                    )
                    result["action"] = "nuked"
                else:
                    result["message"] = (
                        f"Pause error and reboot failed: {nuke_result['message']}"
                    )
                    result["action"] = "nuke_failed"
            else:
                result["message"] = f"Error: {err!s}"
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
                clear_response = await self._ocpp_call(call.ClearChargingProfile())
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

            response = await self._ocpp_call(
                call.SetChargingProfile(evse_id=1, charging_profile=profile)
            )

            _LOGGER.info("Resume response: %s", response.status)

            # Log additional status info if available
            if hasattr(response, "status_info") and response.status_info:
                _LOGGER.info(
                    "Resume status_info: reason=%s, additional=%s",
                    response.status_info.get("reason_code", "N/A"),
                    response.status_info.get("additional_info", "N/A"),
                )

            # The clear-all above also wiped the persistent TxDefaultProfile.
            # Reinstall it: the Delta firmware accepts a TxProfile sent while
            # the transaction is suspended but silently discards it, so without
            # this safety net the session resumes at the hardware maximum until
            # the next limit change (issue #19).
            try:
                await self._send_charging_profile(
                    float(current_limit),
                    purpose=ChargingProfilePurposeEnumType.tx_default_profile,
                    profile_id=998,
                    stack_level=0,
                )
            except Exception as err:
                _LOGGER.warning(
                    "Could not reinstall TxDefaultProfile after resume: %s", err
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

    async def async_stop_charging(self, allow_nuke: bool = True) -> dict:
        """Stop/pause charging using SetChargingProfile(0A).

        This pauses charging WITHOUT ending the transaction, so we can resume later.
        Much better than RequestStopTransaction which puts the charger in Finishing
        state and prevents restart.

        NUKE OPTION: If pause fails and allow_nuke=True, reboots the wallbox
        as a last resort to stop charging (~60 seconds downtime).

        Returns a dict with:
            - success: bool
            - message: str (user-friendly message)
            - action: str (what was done: paused, nuked, etc.)
        """
        _LOGGER.info("⏹️ STOP CHARGING - SetChargingProfile(0A)")
        return await self.async_pause_charging(allow_nuke=allow_nuke)

    async def _send_charging_profile(
        self,
        limit: float,
        *,
        purpose: ChargingProfilePurposeEnumType,
        profile_id: int,
        stack_level: int,
        transaction_id: str | None = None,
    ) -> bool:
        """Build and send a SetChargingProfile, returning True if accepted.

        Shared by the TxDefaultProfile (applies from the start of every session,
        no transaction needed) and TxProfile (active session) code paths.
        """
        start_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        schedule = ChargingScheduleType(
            id=1,
            start_schedule=start_time,
            charging_rate_unit=ChargingRateUnitEnumType.amps,
            charging_schedule_period=[
                ChargingSchedulePeriodType(start_period=0, limit=float(limit))
            ],
        )

        profile_kwargs: dict[str, Any] = {}
        if transaction_id is not None:
            profile_kwargs["transaction_id"] = transaction_id

        profile = ChargingProfileType(
            id=profile_id,
            stack_level=stack_level,
            charging_profile_purpose=purpose,
            charging_profile_kind=ChargingProfileKindEnumType.absolute,
            charging_schedule=[schedule],
            **profile_kwargs,
        )

        _LOGGER.debug(
            "Sending SetChargingProfile: evse=1, id=%s, purpose=%s, tx=%s, limit=%sA",
            profile_id,
            purpose,
            transaction_id,
            limit,
        )

        response = await self._ocpp_call(
            call.SetChargingProfile(evse_id=1, charging_profile=profile)
        )

        status_str = str(response.status)
        accepted = status_str == "Accepted" or "accepted" in status_str.lower()
        if accepted:
            _LOGGER.info("✅ %s set to %sA - accepted by wallbox", purpose, limit)
        elif purpose == ChargingProfilePurposeEnumType.tx_default_profile:
            # Some firmware (BMW/Delta Gen 4) doesn't accept a persistent
            # TxDefaultProfile but honours the per-session TxProfile we send
            # alongside it, so the limit still applies. Keep this informational
            # rather than a scary warning (issue #14).
            _LOGGER.info(
                "%s (%sA) not accepted by wallbox: %s - the per-session profile "
                "still applies the limit",
                purpose,
                limit,
                response.status,
            )
        else:
            # Surface the wallbox's own reason for the rejection - essential to
            # debug firmware-specific refusals (issue #14).
            reason = ""
            status_info = getattr(response, "status_info", None)
            if status_info:
                if isinstance(status_info, dict):
                    reason = (
                        f" (reason={status_info.get('reason_code', '?')},"
                        f" info={status_info.get('additional_info', '')})"
                    )
                else:
                    reason = f" (status_info={status_info})"
            _LOGGER.warning(
                "⚠️ %s (%sA) rejected by wallbox: %s%s",
                purpose,
                limit,
                response.status,
                reason,
            )
        return accepted

    async def async_set_current_limit(self, limit: float) -> bool:
        """Set charging current limit via SetChargingProfile.

        Sends a TxDefaultProfile so the limit also applies from the very start of
        the next session (fixes the cold-start overshoot, issue #15), plus a
        TxProfile bound to the active transaction so it takes effect immediately
        on the current session.

        The OCPP sequence runs shielded from cancellation. HA cancels in-flight
        service calls when e.g. a ``mode: restart`` automation re-triggers; an
        abort between ClearChargingProfile and SetChargingProfile left the
        wallbox with no profile at all, and the wallbox's late reply was
        orphaned in the ocpp response queue ("Ignoring response with unknown
        unique id"). The shield lets the sequence finish in the background
        while the cancellation still propagates to the caller.

        Args:
            limit: Current limit in Amps (max = full speed)

        Returns:
            True if at least one profile was accepted, False otherwise
        """
        if not self.charge_point:
            _LOGGER.error("❌ No wallbox connected - cannot set current limit")
            return False
        return await asyncio.shield(self._set_current_limit(limit))

    async def _set_current_limit(self, limit: float) -> bool:
        """Run the clear/set profile sequence (see async_set_current_limit).

        ``_limit_lock`` serialises whole sequences: a shielded sequence that
        outlived its cancelled caller must not interleave with the next one,
        or the newer SetChargingProfile reuses ids 999/998 without a Clear in
        between and the Delta firmware rejects it as a duplicate.
        """
        async with self._limit_lock:
            return await self._run_limit_sequence(limit)

    async def _run_limit_sequence(self, limit: float) -> bool:
        """Clear existing profiles and install the new limit."""
        _LOGGER.info(
            "⚡ Setting current limit to %sA (tx=%s)",
            limit,
            self.current_transaction_id,
        )

        try:
            # The Delta firmware does NOT replace an existing profile with the
            # same id/stack - it rejects the duplicate. After any start/resume
            # (which installs TxProfile id=999) every mid-session limit change
            # was therefore Rejected (issue #14 retest, seen live). Clear first,
            # exactly like the proven pause/resume paths do, then reinstall.
            if self.current_transaction_id:
                try:
                    clear_response = await self._ocpp_call(call.ClearChargingProfile())
                    _LOGGER.debug(
                        "ClearChargingProfile before limit change: %s",
                        clear_response.status,
                    )
                except Exception as e:
                    _LOGGER.debug("ClearChargingProfile failed (OK to ignore): %s", e)

            # TxProfile takes effect immediately on the running session.
            # stack_level 0 matches the pause/resume paths; some Delta firmware
            # rejects any higher level (ChargingProfileMaxStackLevel=0), and
            # TxProfile already outranks TxDefaultProfile by purpose alone.
            ok_tx = False
            if self.current_transaction_id:
                ok_tx = await self._send_charging_profile(
                    limit,
                    purpose=ChargingProfilePurposeEnumType.tx_profile,
                    profile_id=999,
                    stack_level=0,
                    transaction_id=self.current_transaction_id,
                )

            # TxDefaultProfile persists across sessions and applies from the
            # start of the next transaction - prevents the startup overshoot.
            # Sent after the TxProfile so the running session is limited first.
            ok_default = await self._send_charging_profile(
                limit,
                purpose=ChargingProfilePurposeEnumType.tx_default_profile,
                profile_id=998,
                stack_level=0,
            )

            if ok_default or ok_tx:
                # Track the new limit for future start/resume/connect operations
                self.data["current_limit"] = limit
                self.async_set_updated_data(self.data)
                return True

            _LOGGER.warning(
                "⚠️ Current limit %sA not applied (no profile accepted)", limit
            )
            return False

        except TimeoutError:
            _LOGGER.error("❌ Set current limit timed out - wallbox not responding!")
            return False
        except Exception as err:
            _LOGGER.error("❌ Failed to set current limit: %s", err, exc_info=True)
            return False

    async def async_apply_limit_on_transaction_start(self) -> None:
        """Push the configured limit right when a session starts (issue #15).

        Without this the wallbox charges at full power until the next poll picks
        up the transaction, which can trip the supplier's main breaker.
        """
        limit = self.data.get("current_limit")
        if not limit:
            return
        _LOGGER.info("🚀 Transaction started - applying %sA immediately", limit)
        await self.async_set_current_limit(limit)

    async def async_apply_limit_on_charging_resumed(self) -> None:
        """Re-apply the configured limit when charging resumes (issue #19).

        The Delta Gen 4 firmware returns Accepted for TxProfiles sent while the
        transaction is SuspendedEV/SuspendedEVSE but silently discards them, so
        once current actually starts flowing the session runs unrestricted.
        Re-sending the profiles in the Charging state is the proven-working
        path (issue #14 retest).
        """
        limit = self.data.get("current_limit")
        if not limit:
            return
        _LOGGER.info("🔁 Charging resumed - re-applying %sA limit", limit)
        await self.async_set_current_limit(limit)

    async def _apply_default_limit_on_connect(self) -> None:
        """Install the TxDefaultProfile after the wallbox connects (issue #15).

        Ensures the very first session after a (re)connect already starts at the
        configured limit instead of full power.
        """
        # Let the connection settle and the pause/resume config run first.
        await asyncio.sleep(5)
        if not self.charge_point:
            return
        limit = self.data.get("current_limit")
        if not limit:
            return
        try:
            await self._send_charging_profile(
                limit,
                purpose=ChargingProfilePurposeEnumType.tx_default_profile,
                profile_id=998,
                stack_level=0,
            )
        except Exception as err:
            # Best-effort - never let this block the connection handler.
            _LOGGER.warning("Could not install TxDefaultProfile on connect: %s", err)

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

            response = await self._ocpp_call(
                ocpp_call.TriggerMessage(
                    requested_message=MessageTriggerEnumType.meter_values,
                    evse={"id": 1, "connector_id": 1},
                )
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

            response = await self._ocpp_call(
                call.SetVariables(set_variable_data=[set_var])
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
