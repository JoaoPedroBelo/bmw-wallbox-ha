"""Test BMW Wallbox binary sensors."""
from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.binary_sensor import (
    BMWWallboxChargingBinarySensor,
    BMWWallboxConnectedBinarySensor,
)


async def test_charging_binary_sensor_on(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test charging binary sensor when actively charging."""
    mock_coordinator.data["power"] = 7000.0
    
    sensor = BMWWallboxChargingBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.name == "Charging"
    assert sensor.device_class == "battery_charging"
    assert sensor.is_on is True  # Power > 100W


async def test_charging_binary_sensor_off(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test charging binary sensor when not charging."""
    mock_coordinator.data["power"] = 50.0  # Below 100W threshold
    
    sensor = BMWWallboxChargingBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.is_on is False


async def test_charging_binary_sensor_zero_power(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test charging binary sensor with zero power."""
    mock_coordinator.data["power"] = 0
    
    sensor = BMWWallboxChargingBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.is_on is False


async def test_connected_binary_sensor_on(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor when wallbox is online."""
    mock_coordinator.data["connected"] = True
    mock_coordinator.data["last_heartbeat"] = datetime.utcnow()
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.name == "Wallbox Online"
    assert sensor.device_class == "connectivity"
    assert sensor.is_on is True


async def test_connected_binary_sensor_off(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor when wallbox is offline."""
    mock_coordinator.data["connected"] = False
    mock_coordinator.data["last_heartbeat"] = None
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.is_on is False


async def test_connected_binary_sensor_stale_heartbeat(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor with stale heartbeat."""
    # Heartbeat older than 30 seconds
    mock_coordinator.data["last_heartbeat"] = datetime.utcnow() - timedelta(seconds=35)
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.is_on is False


async def test_connected_binary_sensor_recent_heartbeat(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor with recent heartbeat."""
    # Heartbeat within 30 seconds
    mock_coordinator.data["last_heartbeat"] = datetime.utcnow() - timedelta(seconds=10)
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    assert sensor.is_on is True


async def test_connected_binary_sensor_attributes(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor extra attributes."""
    heartbeat_time = datetime.utcnow()
    mock_coordinator.data["last_heartbeat"] = heartbeat_time
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    attrs = sensor.extra_state_attributes
    assert "last_heartbeat" in attrs
    assert attrs["last_heartbeat"] == heartbeat_time.isoformat()


async def test_connected_binary_sensor_no_heartbeat_attributes(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connected binary sensor attributes when no heartbeat."""
    mock_coordinator.data["last_heartbeat"] = None
    
    sensor = BMWWallboxConnectedBinarySensor(mock_coordinator, mock_config_entry)
    
    attrs = sensor.extra_state_attributes
    assert attrs["last_heartbeat"] is None

