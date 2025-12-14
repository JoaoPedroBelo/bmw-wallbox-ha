"""Number platform for BMW Wallbox.

Author: João Belo
Independent open-source project for BMW-branded Delta Electronics wallboxes.
Not affiliated with BMW, Delta Electronics, or any other company.
"""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT, DOMAIN, NUMBER_CURRENT_LIMIT
from .coordinator import BMWWallboxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BMW Wallbox number entities."""
    coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BMWWallboxCurrentLimitNumber(coordinator, entry),
        ]
    )


class BMWWallboxCurrentLimitNumber(CoordinatorEntity, NumberEntity):
    """Number entity for charging current limit.

    This slider allows users to set the charging current limit (in Amps).
    The value is used when starting or resuming charging sessions.
    If there's an active charging session, changing the slider will
    immediately update the wallbox.
    """

    _attr_native_min_value = 6  # Minimum safe charging current
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:current-ac"
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{NUMBER_CURRENT_LIMIT}"
        self._attr_name = "Charging Current Limit"
        self._attr_native_max_value = entry.data.get(
            CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT
        )
        # Device info for grouping
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
            "sw_version": coordinator.device_info.get("firmware_version"),
            "serial_number": coordinator.device_info.get("serial_number"),
        }

    @property
    def native_value(self) -> float:
        """Return current limit value."""
        return self.coordinator.data.get(
            "current_limit",
            self._entry.data.get(CONF_MAX_CURRENT, DEFAULT_MAX_CURRENT),
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set new current limit.

        Updates the tracked value immediately for UI responsiveness.
        If there's an active charging session, also sends the command to the wallbox.
        """
        int_value = int(value)

        # Update tracked value immediately (for UI responsiveness)
        self.coordinator.data["current_limit"] = int_value
        self.coordinator.async_set_updated_data(self.coordinator.data)

        # If there's an active transaction, also send to wallbox
        if self.coordinator.current_transaction_id:
            success = await self.coordinator.async_set_current_limit(int_value)
            if not success:
                _LOGGER.warning(
                    "Failed to send current limit to wallbox (will apply on next start)"
                )
