"""The BMW Wallbox integration.

Author: João Belo
Independent open-source project for BMW-branded Delta Electronics wallboxes.
Not affiliated with BMW, Delta Electronics, or any other company.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import BMWWallboxCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BMW Wallbox from a config entry."""
    _LOGGER.debug("Setting up BMW Wallbox integration")

    # Create coordinator
    coordinator = BMWWallboxCoordinator(hass, entry.data)

    # Store coordinator
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Start OCPP server
    try:
        await coordinator.async_start_server()
    except Exception as err:
        _LOGGER.error("Failed to start OCPP server: %s", err)
        raise ConfigEntryNotReady from err

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("BMW Wallbox integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading BMW Wallbox integration")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Stop OCPP server
        coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]
        await coordinator.async_stop_server()

        # Remove coordinator
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
