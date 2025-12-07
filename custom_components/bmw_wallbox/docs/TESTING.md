# BMW Wallbox Integration - Testing Guide

## Test Structure

```
tests/
├── __init__.py           # Package marker
├── conftest.py           # Shared fixtures
├── test_sensor.py        # Sensor entity tests
├── test_binary_sensor.py # Binary sensor tests (if exists)
├── test_button.py        # Button entity tests
├── test_number.py        # Number entity tests
├── test_config_flow.py   # Config flow tests
└── test_coordinator.py   # Coordinator tests (if exists)
```

---

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component
```

### Run All Tests

```bash
# From project root
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_sensor.py -v
```

### Run Specific Test

```bash
pytest tests/test_sensor.py::test_power_sensor -v
```

### Run with Coverage

```bash
pytest tests/ --cov=custom_components.bmw_wallbox --cov-report=html
```

---

## Fixtures (conftest.py)

**Location:** `tests/conftest.py`

### mock_coordinator

Mock `BMWWallboxCoordinator` with test data.

```python
@pytest.fixture
def mock_coordinator():
    """Mock BMWWallboxCoordinator."""
    coordinator = MagicMock()
    coordinator.data = {
        "connected": True,
        "charging_state": "Charging",
        "power": 7000.0,
        "energy_total": 25.5,
        "current": 30.0,
        "voltage": 230.0,
        "transaction_id": "test-transaction-123",
        "connector_status": "Charging",
        "evse_id": 1,
        "connector_id": 1,
        "phases_used": 1,
        "current_limit": 32.0,
    }
    coordinator.device_info = {
        "model": "EIAW-E22KTSE6B04",
        "vendor": "BMW",
        "serial_number": "TEST123",
        "firmware_version": "1.0.0",
    }
    coordinator.current_transaction_id = "test-transaction-123"
    coordinator.async_start_charging = AsyncMock(return_value=True)
    coordinator.async_stop_charging = AsyncMock(return_value=True)
    coordinator.async_set_current_limit = AsyncMock(return_value=True)
    coordinator.async_set_updated_data = MagicMock()
    return coordinator
```

**Usage:**
```python
async def test_something(mock_coordinator):
    # mock_coordinator is ready to use
    assert mock_coordinator.data["power"] == 7000.0
```

---

### mock_config_entry

Mock `ConfigEntry` with test configuration.

```python
@pytest.fixture
def mock_config_entry():
    """Mock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = {
        "port": 9000,
        "ssl_cert": "/ssl/fullchain.pem",
        "ssl_key": "/ssl/privkey.pem",
        "charge_point_id": "DE*BMW*TEST123",
        "rfid_token": "04a125f2fc1194",
        "max_current": 32,
    }
    return entry
```

**Usage:**
```python
async def test_something(mock_config_entry):
    # Access config data
    assert mock_config_entry.data["port"] == 9000
```

---

### mock_wallbox_charge_point

Mock `WallboxChargePoint` for testing OCPP interactions.

```python
@pytest.fixture
def mock_wallbox_charge_point():
    """Mock WallboxChargePoint."""
    with patch("custom_components.bmw_wallbox.coordinator.WallboxChargePoint") as mock:
        charge_point = AsyncMock()
        charge_point.current_transaction_id = "test-transaction-123"
        charge_point.call = AsyncMock()
        mock.return_value = charge_point
        yield charge_point
```

---

## Testing Sensors

**File:** `tests/test_sensor.py`

### Basic Sensor Test

```python
from custom_components.bmw_wallbox.sensor import BMWWallboxPowerSensor

async def test_power_sensor(hass, mock_coordinator, mock_config_entry):
    """Test power sensor returns correct value."""
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    
    # Test value
    assert sensor.native_value == 7000.0
    
    # Test unit
    assert sensor.native_unit_of_measurement == "W"
    
    # Test device class
    assert sensor.device_class == "power"
```

### Test Sensor with Extra Attributes

```python
from custom_components.bmw_wallbox.sensor import BMWWallboxStateSensor

async def test_state_sensor_attributes(hass, mock_coordinator, mock_config_entry):
    """Test state sensor extra attributes."""
    sensor = BMWWallboxStateSensor(mock_coordinator, mock_config_entry)
    
    attrs = sensor.extra_state_attributes
    assert attrs["evse_id"] == 1
    assert attrs["connector_id"] == 1
```

### Test Sensor Data Changes

```python
async def test_sensor_updates_with_data(hass, mock_coordinator, mock_config_entry):
    """Test sensor updates when coordinator data changes."""
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    
    # Initial value
    assert sensor.native_value == 7000.0
    
    # Update coordinator data
    mock_coordinator.data["power"] = 5000.0
    
    # Value should reflect change
    assert sensor.native_value == 5000.0
```

### Test Sensor Availability

```python
async def test_sensor_unavailable_when_disconnected(hass, mock_coordinator, mock_config_entry):
    """Test sensor shows unavailable when disconnected."""
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    
    # Connected - has value
    mock_coordinator.data["connected"] = True
    assert sensor.native_value == 7000.0
    
    # Disconnected - no value
    mock_coordinator.data["connected"] = False
    mock_coordinator.data["power"] = None
    assert sensor.native_value is None
```

---

## Testing Buttons

**File:** `tests/test_button.py`

### Basic Button Test

```python
from custom_components.bmw_wallbox.button import BMWWallboxStartButton

async def test_start_button(hass, mock_coordinator, mock_config_entry):
    """Test start charging button."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    
    # Test properties
    assert button.name == "Start Charging"
    assert button._base_icon == "mdi:play"
    
    # Test press
    await button.async_press()
    
    # Verify coordinator method was called
    mock_coordinator.async_start_charging.assert_called_once()
```

### Test Button with Loading State

```python
async def test_button_loading_state(hass, mock_coordinator, mock_config_entry):
    """Test button shows loading state during action."""
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    
    # Initially not processing
    assert button._is_processing is False
    
    # During press, _is_processing should be True
    # (Note: actual testing requires more complex async handling)
```

---

## Testing Number Entities

**File:** `tests/test_number.py`

### Basic Number Test

```python
from custom_components.bmw_wallbox.number import BMWWallboxCurrentLimitNumber

async def test_current_limit_number(hass, mock_coordinator, mock_config_entry):
    """Test current limit number entity."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    # Test properties
    assert number.name == "Current Limit"
    assert number.native_min_value == 0
    assert number.native_max_value == 32
    assert number.native_step == 1
    
    # Test value
    assert number.native_value == 32.0
```

### Test Number Set Value

```python
async def test_current_limit_set_value(hass, mock_coordinator, mock_config_entry):
    """Test setting current limit value."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    # Set new value
    await number.async_set_native_value(16.0)
    
    # Verify coordinator method was called
    mock_coordinator.async_set_current_limit.assert_called_once_with(16.0)
```

### Test Number Availability

```python
async def test_current_limit_requires_transaction(hass, mock_coordinator, mock_config_entry):
    """Test current limit is unavailable without transaction."""
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    
    # With transaction - available
    mock_coordinator.current_transaction_id = "test-123"
    mock_coordinator.data["connected"] = True
    assert number.available is True
    
    # Without transaction - unavailable
    mock_coordinator.current_transaction_id = None
    assert number.available is False
```

---

## Testing Config Flow

**File:** `tests/test_config_flow.py`

### Test Successful Configuration

```python
from homeassistant import config_entries
from custom_components.bmw_wallbox.const import DOMAIN

async def test_config_flow_success(hass):
    """Test successful config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    
    # Mock file existence for SSL validation
    with patch("os.path.isfile", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "port": 9000,
                "ssl_cert": "/ssl/fullchain.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result2["type"] == "create_entry"
    assert result2["title"] == "BMW Wallbox (DE*BMW*TEST123)"
```

### Test Invalid SSL Certificate

```python
async def test_config_flow_invalid_cert(hass):
    """Test config flow with invalid SSL certificate."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    # SSL file doesn't exist
    with patch("os.path.isfile", return_value=False):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "port": 9000,
                "ssl_cert": "/nonexistent/cert.pem",
                "ssl_key": "/ssl/privkey.pem",
                "charge_point_id": "DE*BMW*TEST123",
            },
        )
    
    assert result2["type"] == "form"
    assert result2["errors"]["base"] == "invalid_ssl_cert"
```

---

## Testing Coordinator

### Mock OCPP Messages

```python
from unittest.mock import AsyncMock, patch

async def test_coordinator_handles_transaction_event(hass, mock_config_entry):
    """Test coordinator processes TransactionEvent."""
    with patch("websockets.serve", new_callable=AsyncMock):
        coordinator = BMWWallboxCoordinator(hass, mock_config_entry.data)
        
        # Simulate TransactionEvent data
        coordinator.data["power"] = 7200.0
        coordinator.data["charging_state"] = "Charging"
        coordinator.data["transaction_id"] = "test-123"
        
        assert coordinator.data["power"] == 7200.0
        assert coordinator.data["charging_state"] == "Charging"
```

### Test Charging Commands

```python
async def test_start_charging_no_transaction(mock_coordinator):
    """Test start charging creates new transaction when none exists."""
    mock_coordinator.current_transaction_id = None
    mock_coordinator.charge_point = AsyncMock()
    
    result = await mock_coordinator.async_start_charging()
    
    # Should attempt RequestStartTransaction
    assert mock_coordinator.charge_point.call.called
```

---

## Template: Adding Tests for New Entity

### Step 1: Create Test File (if needed)

```python
# tests/test_new_entity.py
"""Test BMW Wallbox new entity."""
import pytest

from homeassistant.core import HomeAssistant

from custom_components.bmw_wallbox.new_entity import BMWWallboxNewEntity
```

### Step 2: Write Basic Test

```python
async def test_new_entity_value(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test new entity returns correct value."""
    # Add test data to mock
    mock_coordinator.data["new_field"] = "test_value"
    
    # Create entity
    entity = BMWWallboxNewEntity(mock_coordinator, mock_config_entry)
    
    # Assert value
    assert entity.native_value == "test_value"
```

### Step 3: Test Properties

```python
async def test_new_entity_properties(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test new entity properties."""
    entity = BMWWallboxNewEntity(mock_coordinator, mock_config_entry)
    
    # Test unique ID
    assert entity.unique_id == f"{mock_config_entry.entry_id}_new_entity"
    
    # Test device info exists
    assert entity.device_info is not None
    assert "identifiers" in entity.device_info
```

### Step 4: Test Edge Cases

```python
async def test_new_entity_none_value(hass: HomeAssistant, mock_coordinator, mock_config_entry):
    """Test new entity handles None value."""
    mock_coordinator.data["new_field"] = None
    
    entity = BMWWallboxNewEntity(mock_coordinator, mock_config_entry)
    
    assert entity.native_value is None
```

---

## Best Practices

### 1. Use Fixtures for Common Setup

```python
# Good: Use fixtures
async def test_something(mock_coordinator, mock_config_entry):
    entity = SomeEntity(mock_coordinator, mock_config_entry)

# Avoid: Duplicate setup in every test
async def test_something():
    coordinator = MagicMock()
    coordinator.data = {...}  # Duplicated
    entry = MagicMock()
    entry.data = {...}  # Duplicated
```

### 2. Test One Thing Per Test

```python
# Good: One assertion focus
async def test_power_value(mock_coordinator, mock_config_entry):
    sensor = PowerSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == 7000.0

async def test_power_unit(mock_coordinator, mock_config_entry):
    sensor = PowerSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_unit_of_measurement == "W"

# Avoid: Multiple unrelated assertions
async def test_power_sensor(mock_coordinator, mock_config_entry):
    sensor = PowerSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == 7000.0
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.device_class == "power"
    # Too many things
```

### 3. Test Edge Cases

```python
# Test None/missing values
async def test_handles_none(mock_coordinator, mock_config_entry):
    mock_coordinator.data["power"] = None
    sensor = PowerSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value is None

# Test disconnected state
async def test_disconnected(mock_coordinator, mock_config_entry):
    mock_coordinator.data["connected"] = False
    # ...
```

### 4. Use Descriptive Test Names

```python
# Good: Describes what is being tested
async def test_current_limit_requires_active_transaction():
    pass

# Avoid: Vague names
async def test_number():
    pass
```

### 5. Mock External Dependencies

```python
# Mock file system
with patch("os.path.isfile", return_value=True):
    # Test code

# Mock websockets
with patch("websockets.serve", new_callable=AsyncMock):
    # Test code

# Mock OCPP call
mock_coordinator.charge_point.call = AsyncMock(return_value=response)
```

---

## Checklist: New Entity Tests

- [ ] Test entity value/state
- [ ] Test entity properties (name, unit, device_class)
- [ ] Test unique_id format
- [ ] Test device_info exists
- [ ] Test extra_state_attributes (if any)
- [ ] Test None/missing value handling
- [ ] Test availability conditions (if any)
- [ ] Test actions (for buttons/switches/numbers)
