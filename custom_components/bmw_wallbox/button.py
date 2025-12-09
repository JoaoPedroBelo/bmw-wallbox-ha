"""Button platform for BMW Wallbox."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BUTTON_REBOOT, BUTTON_START, BUTTON_STOP, DOMAIN
from .coordinator import BMWWallboxCoordinator

BUTTON_REFRESH = "refresh_data"

_LOGGER = logging.getLogger(__name__)

# Minimum loading time for visual feedback (seconds)
MIN_LOADING_TIME = 1.5


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BMW Wallbox buttons."""
    coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            BMWWallboxStartButton(coordinator, entry, hass),
            BMWWallboxStopButton(coordinator, entry, hass),
            BMWWallboxRebootButton(coordinator, entry, hass),
            BMWWallboxRefreshButton(coordinator, entry, hass),
        ]
    )


class BMWWallboxButtonBase(CoordinatorEntity, ButtonEntity):
    """Base class for BMW Wallbox buttons."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
        button_type: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.hass = hass
        self._attr_unique_id = f"{entry.entry_id}_{button_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
            "sw_version": coordinator.device_info.get("firmware_version"),
            "serial_number": coordinator.device_info.get("serial_number"),
        }
        self._is_processing = False
        self._base_icon = None  # Set by subclasses

    @property
    def available(self) -> bool:
        """Return if entity is available (disabled during processing)."""
        return not self._is_processing and super().available

    @property
    def icon(self) -> str:
        """Return the icon (loading spinner when processing)."""
        if self._is_processing:
            return "mdi:loading"
        return self._base_icon

    async def _async_press_with_loading(self, action_coro) -> None:
        """Wrap button action with loading state."""
        if self._is_processing:
            _LOGGER.debug("Button already processing, ignoring press")
            return

        self._is_processing = True
        self.async_write_ha_state()

        start_time = asyncio.get_event_loop().time()

        try:
            await action_coro
        finally:
            # Ensure minimum loading time for visual feedback
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed < MIN_LOADING_TIME:
                await asyncio.sleep(MIN_LOADING_TIME - elapsed)

            self._is_processing = False
            self.async_write_ha_state()


class BMWWallboxStartButton(BMWWallboxButtonBase):
    """Smart Start button - starts new session or resumes paused charging."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, hass, BUTTON_START)
        self._attr_name = "Start Charging"
        self._base_icon = "mdi:play"

    async def async_press(self) -> None:
        """Handle the button press - smart start/resume."""
        await self._async_press_with_loading(self._do_start_charging())

    async def _do_start_charging(self) -> None:
        """Execute the start charging action."""
        _LOGGER.info("▶️ Start Charging button pressed")

        try:
            # Smart start: RequestStartTransaction or SetChargingProfile(32A) as needed
            result = await self.coordinator.async_start_charging()

            if result["success"]:
                _LOGGER.info("✅ Start charging successful: %s", result.get("action"))
            else:
                _LOGGER.warning("❌ Start charging failed: %s", result["message"])

        except Exception as err:
            _LOGGER.error("Start button exception: %s", err, exc_info=True)


class BMWWallboxStopButton(BMWWallboxButtonBase):
    """Smart Stop button - pauses charging (can be resumed with Start)."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, hass, BUTTON_STOP)
        self._attr_name = "Stop Charging"
        self._base_icon = "mdi:pause"  # Pause icon since it's actually pausing

    async def async_press(self) -> None:
        """Handle the button press - pauses charging (can resume with Start)."""
        await self._async_press_with_loading(self._do_stop_charging())

    async def _do_stop_charging(self) -> None:
        """Execute the stop charging action."""
        _LOGGER.info("⏸️ Stop/Pause Charging button pressed")

        try:
            # Uses SetChargingProfile(0A) - keeps transaction alive!
            result = await self.coordinator.async_stop_charging()

            if result["success"]:
                _LOGGER.info("✅ Charging paused successfully")
            else:
                _LOGGER.warning("❌ Pause charging failed: %s", result["message"])

        except Exception as err:
            _LOGGER.error("Stop button exception: %s", err, exc_info=True)


class BMWWallboxRebootButton(BMWWallboxButtonBase):
    """Reboot button - reboots the wallbox (takes ~60 seconds)."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, hass, BUTTON_REBOOT)
        self._attr_name = "Reboot Wallbox"
        self._base_icon = "mdi:restart"

    async def async_press(self) -> None:
        """Handle the button press - reboot wallbox."""
        await self._async_press_with_loading(self._do_reboot())

    async def _do_reboot(self) -> None:
        """Execute the reboot action."""
        _LOGGER.info("🔄 Reboot Wallbox button pressed")

        try:
            result = await self.coordinator.async_reset_wallbox()

            if result["success"]:
                _LOGGER.info(
                    "✅ Wallbox reboot initiated - will reconnect in ~60 seconds"
                )
            else:
                _LOGGER.warning("❌ Wallbox reboot failed: %s", result["message"])

        except Exception as err:
            _LOGGER.error("Reboot button exception: %s", err, exc_info=True)


class BMWWallboxRefreshButton(BMWWallboxButtonBase):
    """Refresh Data button - triggers wallbox to send fresh meter values."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, hass, BUTTON_REFRESH)
        self._attr_name = "Refresh Data"
        self._base_icon = "mdi:refresh"
        self._attr_entity_registry_enabled_default = (
            False  # Hidden by default (diagnostic)
        )

    async def async_press(self) -> None:
        """Handle the button press - trigger meter values."""
        await self._async_press_with_loading(self._do_refresh())

    async def _do_refresh(self) -> None:
        """Execute the refresh action."""
        _LOGGER.info("🔄 Refresh Data button pressed")

        try:
            success = await self.coordinator.async_trigger_meter_values()

            if success:
                _LOGGER.info("✅ Meter values refresh triggered - check logs for data")
            else:
                _LOGGER.warning("❌ Failed to trigger meter values refresh")

        except Exception as err:
            _LOGGER.error("Refresh button exception: %s", err, exc_info=True)
