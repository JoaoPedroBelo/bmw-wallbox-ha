"""Test BMW Wallbox buttons."""
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.button import (
    BMWWallboxRefreshButton,
    BMWWallboxRebootButton,
    BMWWallboxStartButton,
    BMWWallboxStopButton,
)


async def test_start_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test start charging button."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    
    assert button.name == "Start Charging"
    assert button._base_icon == "mdi:play"
    assert button.icon == "mdi:play"  # Not processing
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_start_charging.assert_called_once()


async def test_stop_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test stop charging button."""
    button = BMWWallboxStopButton(mock_coordinator, mock_config_entry, hass)
    
    assert button.name == "Stop Charging"
    assert button._base_icon == "mdi:pause"
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_stop_charging.assert_called_once()


async def test_reboot_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test reboot wallbox button."""
    mock_coordinator.async_reset_wallbox = AsyncMock(return_value={"success": True, "message": "Rebooting"})
    
    button = BMWWallboxRebootButton(mock_coordinator, mock_config_entry, hass)
    
    assert button.name == "Reboot Wallbox"
    assert button._base_icon == "mdi:restart"
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_reset_wallbox.assert_called_once()


async def test_refresh_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test refresh data button."""
    mock_coordinator.async_trigger_meter_values = AsyncMock(return_value=True)
    
    button = BMWWallboxRefreshButton(mock_coordinator, mock_config_entry, hass)
    
    assert button.name == "Refresh Data"
    assert button._base_icon == "mdi:refresh"
    assert button._attr_entity_registry_enabled_default is False  # Disabled by default
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_trigger_meter_values.assert_called_once()


async def test_button_processing_state(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test button shows loading icon when processing."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    
    # Before processing
    assert button.available is True
    assert button.icon == "mdi:play"
    
    # During processing
    button._is_processing = True
    assert button.available is False
    assert button.icon == "mdi:loading"
    
    # After processing
    button._is_processing = False
    assert button.available is True
    assert button.icon == "mdi:play"


async def test_button_prevents_double_press(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test button prevents double press while processing."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    button._is_processing = True
    
    # Try to press while already processing
    await button.async_press()
    
    # Method should not be called
    mock_coordinator.async_start_charging.assert_not_called()
