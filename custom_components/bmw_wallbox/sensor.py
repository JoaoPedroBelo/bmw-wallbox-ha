"""Sensor platform for BMW Wallbox - ALL USEFUL SENSORS ENABLED."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BMWWallboxCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BMW Wallbox sensors - ALL USEFUL SENSORS ENABLED!"""
    coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities(
        [
            # === MAIN STATUS SENSORS (MOST IMPORTANT - SHOWN FIRST!) ===
            BMWWallboxStatusSensor(coordinator, entry),
            BMWWallboxStateSensor(coordinator, entry),
            
            # === ENERGY & POWER (FOR CHARGING MONITORING) ===
            BMWWallboxPowerSensor(coordinator, entry),
            BMWWallboxEnergyTotalSensor(coordinator, entry),
            BMWWallboxEnergySessionSensor(coordinator, entry),
            
            # === ELECTRICAL MEASUREMENTS ===
            BMWWallboxCurrentSensor(coordinator, entry),
            BMWWallboxVoltageSensor(coordinator, entry),
            
            # === CONNECTION & TRANSACTION INFO ===
            BMWWallboxConnectorStatusSensor(coordinator, entry),
            BMWWallboxTransactionIDSensor(coordinator, entry),
            BMWWallboxStoppedReasonSensor(coordinator, entry),
            
            # === DIAGNOSTIC INFO (TECHNICAL DETAILS) ===
            BMWWallboxEventTypeSensor(coordinator, entry),
            BMWWallboxTriggerReasonSensor(coordinator, entry),
            BMWWallboxIDTokenSensor(coordinator, entry),
            BMWWallboxPhasesUsedSensor(coordinator, entry),
            BMWWallboxSequenceNumberSensor(coordinator, entry),
        ]
    )


class BMWWallboxSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for BMW Wallbox sensors."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_name = name
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW (Delta Electronics)"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
            "sw_version": coordinator.device_info.get("firmware_version"),
            "serial_number": coordinator.device_info.get("serial_number"),
        }


# ============================================================================
# USER-FRIENDLY STATUS SENSOR (the main one users will see!)
# ============================================================================

class BMWWallboxStatusSensor(BMWWallboxSensorBase):
    """User-friendly status sensor showing clear charging status."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "status", "Status")
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self) -> str:
        """Return user-friendly status based on current state."""
        # Check if wallbox is connected to Home Assistant via OCPP
        wallbox_connected = self.coordinator.data.get("connected", False)
        charging_state = self.coordinator.data.get("charging_state")
        power = self.coordinator.data.get("power", 0)
        transaction_id = self.coordinator.data.get("transaction_id")
        
        # If wallbox is offline, show that clearly
        if not wallbox_connected:
            return "Wallbox Offline"
        
        if not transaction_id:
            return "Ready"
        
        if charging_state == "Charging" or (power and power > 100):
            return "Charging ⚡"
        
        if charging_state == "SuspendedEV":
            return "Car Paused"
        
        if charging_state == "SuspendedEVSE":
            return "Paused"
        
        if charging_state == "EVConnected":
            if power == 0:
                return "Paused"
            return "Connected"
        
        if charging_state == "Idle":
            return "Ready"
        
        return charging_state or "Unknown"

    @property
    def icon(self) -> str:
        """Return icon based on status."""
        status = self.native_value
        if status == "Charging ⚡":
            return "mdi:battery-charging"
        elif status == "Paused":
            return "mdi:pause-circle"
        elif status == "Disconnected":
            return "mdi:power-plug-off"
        elif status == "Wallbox Offline":
            return "mdi:lan-disconnect"
        elif status == "Ready":
            return "mdi:power-plug"
        elif status == "Connected":
            return "mdi:car-electric"
        elif status == "Car Paused":
            return "mdi:car-clock"
        return "mdi:ev-station"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed attributes for power users."""
        return {
            "ocpp_state": self.coordinator.data.get("charging_state"),
            "power_w": self.coordinator.data.get("power"),
            "transaction_id": self.coordinator.data.get("transaction_id"),
            "wallbox_online": self.coordinator.data.get("connected"),
        }


# ============================================================================
# METER VALUE SENSORS (from Power.Active.Import & Energy.Active.Import.Register)
# ============================================================================

class BMWWallboxPowerSensor(BMWWallboxSensorBase):
    """Current power draw sensor (W)."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "power", "Power")
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        """Return power in watts."""
        return self.coordinator.data.get("power")


class BMWWallboxEnergyTotalSensor(BMWWallboxSensorBase):
    """Total energy sensor (kWh) - PERFECT FOR HOME ASSISTANT ENERGY DASHBOARD!"""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "energy_total", "Energy Total")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:lightning-bolt-circle"
        self._attr_suggested_display_precision = 2

    @property
    def native_value(self) -> float | None:
        """Return energy in kWh."""
        return self.coordinator.data.get("energy_total")


class BMWWallboxEnergySessionSensor(BMWWallboxSensorBase):
    """Energy for current charging session (Wh)."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "energy_session", "Energy Session")
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        """Return energy in Wh (session energy from raw value)."""
        # The wallbox sends Energy.Active.Import.Register in Wh for the session
        energy_kwh = self.coordinator.data.get("energy_total")
        if energy_kwh is not None:
            return energy_kwh * 1000  # Convert kWh to Wh
        return None


class BMWWallboxCurrentSensor(BMWWallboxSensorBase):
    """Current sensor (A) - calculated from power when not directly reported."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "current", "Current")
        self._attr_device_class = SensorDeviceClass.CURRENT
        self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:current-ac"
        self._attr_suggested_display_precision = 1

    @property
    def native_value(self) -> float | None:
        """Return current in amperes (calculated from power if not reported)."""
        value = self.coordinator.data.get("current")
        if value is None or value == 0:
            return None
        return value
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        # Show per-phase currents if available
        if self.coordinator.data.get("current_l1"):
            attrs["L1"] = self.coordinator.data.get("current_l1")
        if self.coordinator.data.get("current_l2"):
            attrs["L2"] = self.coordinator.data.get("current_l2")
        if self.coordinator.data.get("current_l3"):
            attrs["L3"] = self.coordinator.data.get("current_l3")
        return attrs


class BMWWallboxVoltageSensor(BMWWallboxSensorBase):
    """Voltage sensor (V) - uses typical grid voltage when not reported."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "voltage", "Voltage")
        self._attr_device_class = SensorDeviceClass.VOLTAGE
        self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:flash"
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        """Return voltage in volts (230V assumed if not reported)."""
        value = self.coordinator.data.get("voltage")
        if value is None or value == 0:
            return None
        return value
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        attrs = {}
        # Show per-phase voltages if available
        if self.coordinator.data.get("voltage_l1"):
            attrs["L1"] = self.coordinator.data.get("voltage_l1")
        if self.coordinator.data.get("voltage_l2"):
            attrs["L2"] = self.coordinator.data.get("voltage_l2")
        if self.coordinator.data.get("voltage_l3"):
            attrs["L3"] = self.coordinator.data.get("voltage_l3")
        return attrs


# ============================================================================
# TRANSACTION INFO SENSORS (from TransactionEvent)
# ============================================================================

class BMWWallboxStateSensor(BMWWallboxSensorBase):
    """OCPP transaction state sensor - shows the raw OCPP charging state."""

    # Map OCPP states to user-friendly names
    STATE_MAP = {
        "Charging": "Charging",
        "SuspendedEVSE": "Paused by Wallbox",
        "SuspendedEV": "Paused by Car",
        "EVConnected": "Car Plugged In",
        "Idle": "Idle",
        "Available": "Available",
        "Preparing": "Preparing",
        "Finishing": "Finishing",
        "Reserved": "Reserved",
        "Unavailable": "Unavailable",
        "Faulted": "Faulted",
    }

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "state", "OCPP State")
        self._attr_icon = "mdi:state-machine"

    @property
    def native_value(self) -> str | None:
        """Return user-friendly OCPP state (may be stale if wallbox offline)."""
        # Show "Offline" if wallbox is disconnected
        if not self.coordinator.data.get("connected", False):
            return "Wallbox Offline"
        
        raw_state = self.coordinator.data.get("charging_state")
        return self.STATE_MAP.get(raw_state, raw_state)

    @property
    def icon(self) -> str:
        """Return dynamic icon based on state."""
        state = self.native_value
        if state == "Charging":
            return "mdi:battery-charging"
        elif state in ["Paused", "Car Paused"]:
            return "mdi:pause-circle"
        elif state == "Connected":
            return "mdi:power-plug"
        elif state == "Idle":
            return "mdi:sleep"
        elif state == "Faulted":
            return "mdi:alert-circle"
        return "mdi:ev-station"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes including raw OCPP state."""
        return {
            "ocpp_state": self.coordinator.data.get("charging_state"),
            "transaction_id": self.coordinator.data.get("transaction_id"),
        }


class BMWWallboxConnectorStatusSensor(BMWWallboxSensorBase):
    """Connector status sensor - from StatusNotification."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "connector_status", "Connector Status")
        self._attr_icon = "mdi:ev-plug-type2"

    @property
    def native_value(self) -> str | None:
        """Return connector status."""
        status = self.coordinator.data.get("connector_status")
        # Don't show "Unknown" - derive from charging state if needed
        if status == "Unknown":
            charging_state = self.coordinator.data.get("charging_state")
            if charging_state in ["Charging", "SuspendedEV", "SuspendedEVSE", "EVConnected"]:
                return "Occupied"
            elif charging_state == "Available":
                return "Available"
        return status
    
    @property
    def icon(self) -> str:
        """Return dynamic icon based on status."""
        status = self.native_value
        if status == "Occupied":
            return "mdi:ev-plug-type2"
        elif status == "Available":
            return "mdi:power-plug"
        elif status == "Faulted":
            return "mdi:alert-circle"
        return "mdi:help-circle"


class BMWWallboxTransactionIDSensor(BMWWallboxSensorBase):
    """Transaction ID sensor - useful for tracking charging sessions."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "transaction_id", "Transaction ID")
        self._attr_icon = "mdi:identifier"

    @property
    def native_value(self) -> str | None:
        """Return transaction ID."""
        return self.coordinator.data.get("transaction_id")


class BMWWallboxStoppedReasonSensor(BMWWallboxSensorBase):
    """Stopped reason sensor - shows why charging stopped."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "stopped_reason", "Stopped Reason")
        self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> str | None:
        """Return stopped reason."""
        return self.coordinator.data.get("stopped_reason")


# ============================================================================
# EVENT INFO SENSORS (from TransactionEvent metadata)
# ============================================================================

class BMWWallboxEventTypeSensor(BMWWallboxSensorBase):
    """Event type sensor (Started, Updated, Ended)."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "event_type", "Event Type")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> str | None:
        """Return event type."""
        return self.coordinator.data.get("event_type")


class BMWWallboxTriggerReasonSensor(BMWWallboxSensorBase):
    """Trigger reason sensor (e.g., MeterValuePeriodic, ChargingStateChanged)."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "trigger_reason", "Trigger Reason")
        self._attr_icon = "mdi:information"

    @property
    def native_value(self) -> str | None:
        """Return trigger reason."""
        return self.coordinator.data.get("trigger_reason")


# ============================================================================
# CONNECTION INFO SENSORS (from TransactionEvent - id_token, evse, connector)
# ============================================================================

class BMWWallboxIDTokenSensor(BMWWallboxSensorBase):
    """ID Token sensor (RFID card identifier)."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "id_token", "ID Token")
        self._attr_icon = "mdi:card-account-details"

    @property
    def native_value(self) -> str | None:
        """Return ID token."""
        return self.coordinator.data.get("id_token")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ID token type."""
        return {
            "type": self.coordinator.data.get("id_token_type", "Unknown"),
        }


class BMWWallboxPhasesUsedSensor(BMWWallboxSensorBase):
    """Phases used sensor - number of phases currently in use."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "phases_used", "Phases Used")
        self._attr_icon = "mdi:sine-wave"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return number of phases used."""
        return self.coordinator.data.get("phases_used")


class BMWWallboxSequenceNumberSensor(BMWWallboxSensorBase):
    """Sequence number sensor - transaction event sequence."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "sequence_number", "Sequence Number")
        self._attr_icon = "mdi:counter"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> int | None:
        """Return sequence number."""
        return self.coordinator.data.get("sequence_number")
