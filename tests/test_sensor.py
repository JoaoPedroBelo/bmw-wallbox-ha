"""Test BMW Wallbox sensors."""
from datetime import datetime
from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.sensor import (
    BMWWallboxConnectorStatusSensor,
    BMWWallboxCurrentSensor,
    BMWWallboxEnergyDailySensor,
    BMWWallboxEnergyMonthlySensor,
    BMWWallboxEnergySessionSensor,
    BMWWallboxEnergyTotalSensor,
    BMWWallboxEnergyWeeklySensor,
    BMWWallboxEnergyYearlySensor,
    BMWWallboxEventTypeSensor,
    BMWWallboxIDTokenSensor,
    BMWWallboxPhasesUsedSensor,
    BMWWallboxPowerSensor,
    BMWWallboxSequenceNumberSensor,
    BMWWallboxStateSensor,
    BMWWallboxStatusSensor,
    BMWWallboxStoppedReasonSensor,
    BMWWallboxTransactionIDSensor,
    BMWWallboxTriggerReasonSensor,
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


async def test_status_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test user-friendly status sensor."""
    sensor = BMWWallboxStatusSensor(mock_coordinator, mock_config_entry)
    
    # Charging state
    mock_coordinator.data["connected"] = True
    mock_coordinator.data["charging_state"] = "Charging"
    mock_coordinator.data["power"] = 7000.0
    mock_coordinator.data["transaction_id"] = "test-123"
    
    assert sensor.native_value == "Charging ⚡"
    assert sensor.icon == "mdi:battery-charging"


async def test_status_sensor_offline(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test status sensor when wallbox is offline."""
    sensor = BMWWallboxStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connected"] = False
    
    assert sensor.native_value == "Wallbox Offline"
    assert sensor.icon == "mdi:lan-disconnect"


async def test_status_sensor_paused(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test status sensor when charging is paused."""
    sensor = BMWWallboxStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connected"] = True
    mock_coordinator.data["charging_state"] = "SuspendedEVSE"
    mock_coordinator.data["transaction_id"] = "test-123"
    
    assert sensor.native_value == "Paused"
    assert sensor.icon == "mdi:pause-circle"


async def test_status_sensor_ready(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test status sensor when ready."""
    sensor = BMWWallboxStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connected"] = True
    mock_coordinator.data["transaction_id"] = None
    
    assert sensor.native_value == "Ready"
    assert sensor.icon == "mdi:power-plug"


async def test_status_sensor_attributes(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test status sensor extra attributes."""
    sensor = BMWWallboxStatusSensor(mock_coordinator, mock_config_entry)
    
    attrs = sensor.extra_state_attributes
    assert "ocpp_state" in attrs
    assert "power_w" in attrs
    assert "transaction_id" in attrs
    assert "wallbox_online" in attrs


async def test_energy_session_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test energy session sensor."""
    sensor = BMWWallboxEnergySessionSensor(mock_coordinator, mock_config_entry)
    
    # 25.5 kWh should be converted to 25500 Wh
    assert sensor.native_value == 25500.0
    assert sensor.native_unit_of_measurement == "Wh"
    assert sensor.device_class == "energy"


async def test_connector_status_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connector status sensor."""
    sensor = BMWWallboxConnectorStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connector_status"] = "Occupied"
    
    assert sensor.native_value == "Occupied"
    assert sensor.icon == "mdi:ev-plug-type2"


async def test_connector_status_sensor_unknown(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connector status derives from charging state when unknown."""
    sensor = BMWWallboxConnectorStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connector_status"] = "Unknown"
    mock_coordinator.data["charging_state"] = "Charging"
    
    assert sensor.native_value == "Occupied"


async def test_connector_status_sensor_available(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test connector status sensor when available."""
    sensor = BMWWallboxConnectorStatusSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connector_status"] = "Available"
    
    assert sensor.native_value == "Available"
    assert sensor.icon == "mdi:power-plug"


async def test_stopped_reason_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test stopped reason sensor."""
    sensor = BMWWallboxStoppedReasonSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["stopped_reason"] = "EVDisconnected"
    
    assert sensor.native_value == "EVDisconnected"


async def test_event_type_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test event type sensor."""
    sensor = BMWWallboxEventTypeSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["event_type"] = "Updated"
    
    assert sensor.native_value == "Updated"


async def test_trigger_reason_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test trigger reason sensor."""
    sensor = BMWWallboxTriggerReasonSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["trigger_reason"] = "MeterValuePeriodic"
    
    assert sensor.native_value == "MeterValuePeriodic"


async def test_id_token_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test ID token sensor."""
    sensor = BMWWallboxIDTokenSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["id_token"] = "00000000000000"
    mock_coordinator.data["id_token_type"] = "Local"
    
    assert sensor.native_value == "00000000000000"
    
    attrs = sensor.extra_state_attributes
    assert attrs["type"] == "Local"


async def test_phases_used_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test phases used sensor."""
    sensor = BMWWallboxPhasesUsedSensor(mock_coordinator, mock_config_entry)
    
    assert sensor.native_value == 1


async def test_sequence_number_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test sequence number sensor."""
    sensor = BMWWallboxSequenceNumberSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["sequence_number"] = 42
    
    assert sensor.native_value == 42


async def test_state_sensor_map(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test state sensor maps OCPP states to user-friendly names."""
    sensor = BMWWallboxStateSensor(mock_coordinator, mock_config_entry)
    
    # Test various states
    test_states = {
        "Charging": "Charging",
        "SuspendedEVSE": "Paused by Wallbox",
        "SuspendedEV": "Paused by Car",
        "EVConnected": "Car Plugged In",
        "Idle": "Idle",
    }
    
    for ocpp_state, expected_value in test_states.items():
        mock_coordinator.data["charging_state"] = ocpp_state
        assert sensor.native_value == expected_value


async def test_state_sensor_offline(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test state sensor shows offline when disconnected."""
    sensor = BMWWallboxStateSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["connected"] = False
    
    assert sensor.native_value == "Wallbox Offline"


async def test_current_sensor_with_phases(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test current sensor shows per-phase currents in attributes."""
    sensor = BMWWallboxCurrentSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["current_l1"] = 10.5
    mock_coordinator.data["current_l2"] = 11.2
    mock_coordinator.data["current_l3"] = 9.8
    
    attrs = sensor.extra_state_attributes
    assert attrs["L1"] == 10.5
    assert attrs["L2"] == 11.2
    assert attrs["L3"] == 9.8


async def test_current_sensor_zero_returns_none(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test current sensor returns None when zero."""
    sensor = BMWWallboxCurrentSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["current"] = 0
    
    assert sensor.native_value is None


async def test_voltage_sensor_with_phases(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test voltage sensor shows per-phase voltages in attributes."""
    sensor = BMWWallboxVoltageSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["voltage_l1"] = 230.0
    mock_coordinator.data["voltage_l2"] = 231.0
    mock_coordinator.data["voltage_l3"] = 229.0
    
    attrs = sensor.extra_state_attributes
    assert attrs["L1"] == 230.0
    assert attrs["L2"] == 231.0
    assert attrs["L3"] == 229.0


async def test_voltage_sensor_zero_returns_none(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test voltage sensor returns None when zero."""
    sensor = BMWWallboxVoltageSensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["voltage"] = 0
    
    assert sensor.native_value is None


async def test_energy_daily_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test daily energy sensor."""
    sensor = BMWWallboxEnergyDailySensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["energy_daily"] = 5.5
    mock_coordinator.data["last_session_energy"] = 2.3
    
    assert sensor.native_value == 7.8  # 5.5 + 2.3
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"


async def test_energy_daily_sensor_with_last_reset(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test daily energy sensor includes last reset in attributes."""
    sensor = BMWWallboxEnergyDailySensor(mock_coordinator, mock_config_entry)
    
    reset_time = datetime(2025, 12, 8, 0, 0, 0)
    mock_coordinator.data["energy_daily"] = 10.0
    mock_coordinator.data["last_session_energy"] = 0.0
    mock_coordinator.data["last_reset_daily"] = reset_time
    
    attrs = sensor.extra_state_attributes
    assert attrs["last_reset"] == "2025-12-08T00:00:00"


async def test_energy_weekly_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test weekly energy sensor."""
    sensor = BMWWallboxEnergyWeeklySensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["energy_weekly"] = 15.2
    mock_coordinator.data["last_session_energy"] = 3.8
    
    assert sensor.native_value == 19.0  # 15.2 + 3.8
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"


async def test_energy_weekly_sensor_with_last_reset(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test weekly energy sensor includes last reset in attributes."""
    sensor = BMWWallboxEnergyWeeklySensor(mock_coordinator, mock_config_entry)
    
    reset_time = datetime(2025, 12, 8, 0, 0, 0)
    mock_coordinator.data["energy_weekly"] = 25.0
    mock_coordinator.data["last_session_energy"] = 0.0
    mock_coordinator.data["last_reset_weekly"] = reset_time
    
    attrs = sensor.extra_state_attributes
    assert attrs["last_reset"] == "2025-12-08T00:00:00"


async def test_energy_monthly_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test monthly energy sensor."""
    sensor = BMWWallboxEnergyMonthlySensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["energy_monthly"] = 120.5
    mock_coordinator.data["last_session_energy"] = 5.5
    
    assert sensor.native_value == 126.0  # 120.5 + 5.5
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"


async def test_energy_monthly_sensor_with_last_reset(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test monthly energy sensor includes last reset in attributes."""
    sensor = BMWWallboxEnergyMonthlySensor(mock_coordinator, mock_config_entry)
    
    reset_time = datetime(2025, 12, 1, 0, 0, 0)
    mock_coordinator.data["energy_monthly"] = 150.0
    mock_coordinator.data["last_session_energy"] = 0.0
    mock_coordinator.data["last_reset_monthly"] = reset_time
    
    attrs = sensor.extra_state_attributes
    assert attrs["last_reset"] == "2025-12-01T00:00:00"


async def test_energy_yearly_sensor(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test yearly energy sensor."""
    sensor = BMWWallboxEnergyYearlySensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["energy_yearly"] = 1250.0
    mock_coordinator.data["last_session_energy"] = 12.5
    
    assert sensor.native_value == 1262.5  # 1250.0 + 12.5
    assert sensor.native_unit_of_measurement == "kWh"
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"


async def test_energy_yearly_sensor_with_last_reset(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test yearly energy sensor includes last reset in attributes."""
    sensor = BMWWallboxEnergyYearlySensor(mock_coordinator, mock_config_entry)
    
    reset_time = datetime(2025, 1, 1, 0, 0, 0)
    mock_coordinator.data["energy_yearly"] = 2000.0
    mock_coordinator.data["last_session_energy"] = 0.0
    mock_coordinator.data["last_reset_yearly"] = reset_time
    
    attrs = sensor.extra_state_attributes
    assert attrs["last_reset"] == "2025-01-01T00:00:00"


async def test_energy_period_sensors_no_current_session(hass: HomeAssistant, mock_coordinator, mock_config_entry) -> None:
    """Test period energy sensors when no current session."""
    daily_sensor = BMWWallboxEnergyDailySensor(mock_coordinator, mock_config_entry)
    weekly_sensor = BMWWallboxEnergyWeeklySensor(mock_coordinator, mock_config_entry)
    monthly_sensor = BMWWallboxEnergyMonthlySensor(mock_coordinator, mock_config_entry)
    yearly_sensor = BMWWallboxEnergyYearlySensor(mock_coordinator, mock_config_entry)
    
    mock_coordinator.data["energy_daily"] = 10.0
    mock_coordinator.data["energy_weekly"] = 20.0
    mock_coordinator.data["energy_monthly"] = 100.0
    mock_coordinator.data["energy_yearly"] = 500.0
    mock_coordinator.data["last_session_energy"] = 0.0
    
    assert daily_sensor.native_value == 10.0
    assert weekly_sensor.native_value == 20.0
    assert monthly_sensor.native_value == 100.0
    assert yearly_sensor.native_value == 500.0
