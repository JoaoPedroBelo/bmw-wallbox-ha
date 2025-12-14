"""Test BMW Wallbox number entities."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.components.number import NumberMode
from homeassistant.const import UnitOfElectricCurrent
from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.number import BMWWallboxCurrentLimitNumber


async def test_current_limit_number_attributes(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit number entity attributes."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    assert number.name == "Charging Current Limit"
    assert number.icon == "mdi:current-ac"
    assert number.native_min_value == 6
    assert number.native_max_value == 32  # From mock_config_entry max_current
    assert number.native_step == 1
    assert number.mode == NumberMode.SLIDER
    assert number.native_unit_of_measurement == UnitOfElectricCurrent.AMPERE


async def test_current_limit_number_value(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit number returns correct value."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    # Value from coordinator.data
    assert number.native_value == 32.0  # From mock_coordinator.data["current_limit"]

    # Change the value
    mock_coordinator.data["current_limit"] = 16.0
    assert number.native_value == 16.0


async def test_current_limit_number_fallback(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit number falls back to config when no data."""
    # Remove current_limit from data
    del mock_coordinator.data["current_limit"]

    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    # Should fall back to config's max_current
    assert number.native_value == 32  # From mock_config_entry.data["max_current"]


async def test_current_limit_set_with_active_transaction(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test setting current limit with an active transaction."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    # Set new value
    await number.async_set_native_value(20.0)

    # Should update coordinator.data
    assert mock_coordinator.data["current_limit"] == 20
    mock_coordinator.async_set_updated_data.assert_called_with(mock_coordinator.data)

    # Should call async_set_current_limit since there's an active transaction
    mock_coordinator.async_set_current_limit.assert_called_once_with(20)


async def test_current_limit_set_without_transaction(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test setting current limit without an active transaction."""
    # No active transaction
    mock_coordinator.current_transaction_id = None

    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    # Set new value
    await number.async_set_native_value(16.0)

    # Should update coordinator.data
    assert mock_coordinator.data["current_limit"] == 16
    mock_coordinator.async_set_updated_data.assert_called_with(mock_coordinator.data)

    # Should NOT call async_set_current_limit since there's no active transaction
    mock_coordinator.async_set_current_limit.assert_not_called()


async def test_current_limit_device_info(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit number has correct device info."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    assert number.device_info is not None
    assert ("bmw_wallbox", "DE*BMW*TEST123") in number.device_info["identifiers"]
    assert number.device_info["name"] == "BMW Wallbox"
    assert number.device_info["manufacturer"] == "BMW"
    assert number.device_info["model"] == "EIAW-E22KTSE6B04"


async def test_current_limit_unique_id(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit number has correct unique ID."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    assert number.unique_id == "test_entry_id_current_limit"


async def test_current_limit_handles_failed_command(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit handles failed wallbox command gracefully."""
    # Make the command fail
    mock_coordinator.async_set_current_limit = AsyncMock(return_value=False)

    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)

    # Set new value - should not raise even if command fails
    await number.async_set_native_value(24.0)

    # Should still update coordinator.data (for next start/resume)
    assert mock_coordinator.data["current_limit"] == 24
    mock_coordinator.async_set_current_limit.assert_called_once_with(24)
