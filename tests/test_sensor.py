"""Test BMW Wallbox sensors."""
from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.sensor import (
    BMWWallboxCurrentSensor,
    BMWWallboxEnergyTotalSensor,
    BMWWallboxPowerSensor,
    BMWWallboxStateSensor,
    BMWWallboxTransactionIDSensor,
    BMWWallboxVoltageSensor,
)


async def test_power_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test power sensor."""
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == 7000.0
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.device_class == "power"


async def test_energy_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test energy sensor."""
    sensor = BMWWallboxEnergyTotalSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == 25.5
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"


async def test_state_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test state sensor."""
    sensor = BMWWallboxStateSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == "Charging"
    assert sensor.icon == "mdi:ev-station"
    
    attrs = sensor.extra_state_attributes
    assert attrs["evse_id"] == 1
    assert attrs["connector_id"] == 1


async def test_transaction_id_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test transaction ID sensor."""
    sensor = BMWWallboxTransactionIDSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == "test-transaction-123"


async def test_current_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test current sensor."""
    sensor = BMWWallboxCurrentSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == 30.0
    assert sensor.native_unit_of_measurement == "A"


async def test_voltage_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test voltage sensor."""
    sensor = BMWWallboxVoltageSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == 230.0
    assert sensor.native_unit_of_measurement == "V"


async def test_sensor_availability(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test sensor shows unavailable when disconnected."""
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    
    # Sensor should be available when connected
    mock_coordinator.data["connected"] = True
    assert sensor.native_value == 7000.0
    
    # Update coordinator to disconnected
    mock_coordinator.data["connected"] = False
    mock_coordinator.data["power"] = None
    
    assert sensor.native_value is None

