"""Test BMW Wallbox number entities."""
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from custom_components.bmw_wallbox.number import BMWWallboxCurrentLimitNumber


async def test_current_limit_number(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test current limit number entity."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    assert number.name == "Current Limit"
    assert number.native_unit_of_measurement == "A"
    assert number.native_min_value == 0
    assert number.native_max_value == 32
    assert number.native_step == 1


async def test_current_limit_available_with_transaction(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit is available when there's an active transaction."""
    mock_coordinator.data["connected"] = True
    mock_coordinator.current_transaction_id = "tx123"
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    assert number.available is True


async def test_current_limit_unavailable_without_transaction(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test current limit is unavailable when there's no active transaction."""
    mock_coordinator.data["connected"] = True
    mock_coordinator.current_transaction_id = None
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    assert number.available is False


async def test_set_current_limit(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test setting current limit with active transaction."""
    # Setup: connected with active transaction
    mock_coordinator.charge_point = object()  # Mock charge point
    mock_coordinator.current_transaction_id = "tx123"
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    # Set to 16A
    await number.async_set_native_value(16.0)
    
    # Verify coordinator method was called with correct value
    mock_coordinator.async_set_current_limit.assert_called_once_with(16.0)
    assert mock_coordinator.data["current_limit"] == 16.0


async def test_set_current_limit_no_transaction_raises(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test setting current limit without transaction raises error."""
    mock_coordinator.charge_point = object()  # Mock charge point
    mock_coordinator.current_transaction_id = None
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    with pytest.raises(HomeAssistantError, match="No active charging session"):
        await number.async_set_native_value(16.0)


async def test_set_current_limit_not_connected_raises(
    hass: HomeAssistant, mock_coordinator, mock_config_entry
) -> None:
    """Test setting current limit when not connected raises error."""
    mock_coordinator.charge_point = None
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    with pytest.raises(HomeAssistantError, match="Wallbox not connected"):
        await number.async_set_native_value(16.0)


async def test_current_limit_range(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test current limit respects min/max values."""
    mock_coordinator.charge_point = object()
    mock_coordinator.current_transaction_id = "tx123"
    
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    # Test min value (0A = pause)
    await number.async_set_native_value(0.0)
    mock_coordinator.async_set_current_limit.assert_called_with(0.0)
    
    # Test max value (32A)
    await number.async_set_native_value(32.0)
    mock_coordinator.async_set_current_limit.assert_called_with(32.0)

