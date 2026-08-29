"""Binary sensor platform for BMW Wallbox."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_CHARGING,
    BINARY_SENSOR_CONNECTED,
    BINARY_SENSOR_FAULT,
    DOMAIN,
)
from .coordinator import BMWWallboxCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BMW Wallbox binary sensors."""
    coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            # Connection status should be first (most important!)
            BMWWallboxConnectedBinarySensor(coordinator, entry),
            BMWWallboxChargingBinarySensor(coordinator, entry),
            BMWWallboxFaultBinarySensor(coordinator, entry),
        ]
    )


class BMWWallboxBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Base class for BMW Wallbox binary sensors."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
            "sw_version": coordinator.device_info.get("firmware_version"),
            "serial_number": coordinator.device_info.get("serial_number"),
        }


class BMWWallboxChargingBinarySensor(BMWWallboxBinarySensorBase):
    """Binary sensor for charging status."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_CHARGING)
        self._attr_name = "Charging"
        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING

    @property
    def is_on(self) -> bool:
        """Return true if actively charging (power > 100W)."""
        # Check power draw instead of state, as state can be "EVConnected" even when charging
        power = self.coordinator.data.get("power", 0)
        return power > 100  # Consider charging if drawing more than 100W


class BMWWallboxConnectedBinarySensor(BMWWallboxBinarySensorBase):
    """Binary sensor for OCPP connection status between wallbox and Home Assistant."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_CONNECTED)
        self._attr_name = "Wallbox Online"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool:
        """Return true if wallbox is connected to Home Assistant via OCPP."""
        # Consider connected if we've received a heartbeat in the last 30 seconds
        last_heartbeat = self.coordinator.data.get("last_heartbeat")
        if last_heartbeat and isinstance(last_heartbeat, datetime):
            return (datetime.utcnow() - last_heartbeat) < timedelta(seconds=30)
        return self.coordinator.data.get("connected", False)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes."""
        last_heartbeat = self.coordinator.data.get("last_heartbeat")
        return {
            "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None,
        }


class BMWWallboxFaultBinarySensor(BMWWallboxBinarySensorBase):
    """Fault indicator (connector Faulted or a stuck transaction-bound TxProfile).

    A mid-session connector ``Faulted`` is what silently orphaned the
    transaction on the Delta firmware (issue #25); ``stuck_tx_profile`` flags a
    leftover TxProfile the box refuses to clear (reboot needed). Entity only -
    the integration never sends push notifications; the user wires their own.
    """

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the fault binary sensor."""
        super().__init__(coordinator, entry, BINARY_SENSOR_FAULT)
        self._attr_name = "Fault"
        self._attr_device_class = BinarySensorDeviceClass.PROBLEM
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool:
        """Return True when the wallbox reports a fault or a stuck profile."""
        return bool(
            self.coordinator.data.get("wallbox_fault")
            or self.coordinator.data.get("stuck_tx_profile")
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the last fault reason and whether a profile is stuck."""
        attrs: dict[str, str] = {}
        if self.coordinator.data.get("last_fault"):
            attrs["last_fault"] = self.coordinator.data["last_fault"]
        if self.coordinator.data.get("last_fault_time"):
            attrs["last_fault_time"] = self.coordinator.data["last_fault_time"]
        attrs["stuck_tx_profile"] = str(
            bool(self.coordinator.data.get("stuck_tx_profile"))
        )
        return attrs
