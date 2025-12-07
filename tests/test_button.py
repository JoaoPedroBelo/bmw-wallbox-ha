"""Test BMW Wallbox buttons."""
import pytest

from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.button import (
    BMWWallboxStartButton,
    BMWWallboxStopButton,
)


async def test_start_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test start charging button."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry)
    
    assert button.name == "Start Charging"
    assert button.icon == "mdi:play"
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_start_charging.assert_called_once()


async def test_stop_button(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test stop charging button."""
    button = BMWWallboxStopButton(mock_coordinator, mock_config_entry)
    
    assert button.name == "Stop Charging"
    assert button.icon == "mdi:stop"
    
    # Press button
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_stop_charging.assert_called_once()

