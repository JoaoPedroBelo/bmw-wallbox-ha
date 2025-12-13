# BMW Wallbox Integration - Entity Development Guide

## Entity Overview

| Platform | File | Count | Base Class |
|----------|------|-------|------------|
| Sensor | `sensor.py` | 19 | `BMWWallboxSensorBase` |
| Binary Sensor | `binary_sensor.py` | 2 | `BMWWallboxBinarySensorBase` |
| Button | `button.py` | 2 | `BMWWallboxButtonBase` |
| Number | `number.py` | 2 | Direct `CoordinatorEntity` |
| Switch | `switch.py` | 1 | Direct `CoordinatorEntity` |

---

## Entity Class Hierarchy

```
CoordinatorEntity (Home Assistant)
    │
    ├── SensorEntity
    │       └── BMWWallboxSensorBase          # sensor.py:64-86
    │               ├── BMWWallboxStatusSensor
    │               ├── BMWWallboxPowerSensor
    │               ├── BMWWallboxEnergyTotalSensor           # For Energy Dashboard
    │               ├── BMWWallboxEnergySessionSensor         # Per-session tracking
    │               ├── BMWWallboxEnergyDailySensor           # Resets at midnight
    │               ├── BMWWallboxEnergyWeeklySensor          # Resets Monday
    │               ├── BMWWallboxEnergyMonthlySensor         # Resets 1st of month
    │               ├── BMWWallboxEnergyYearlySensor          # Resets Jan 1st
    │               ├── BMWWallboxCurrentSensor
    │               ├── BMWWallboxVoltageSensor
    │               ├── BMWWallboxStateSensor
    │               ├── BMWWallboxConnectorStatusSensor
    │               ├── BMWWallboxTransactionIDSensor
    │               ├── BMWWallboxStoppedReasonSensor
    │               ├── BMWWallboxEventTypeSensor
    │               ├── BMWWallboxTriggerReasonSensor
    │               ├── BMWWallboxIDTokenSensor
    │               ├── BMWWallboxPhasesUsedSensor
    │               └── BMWWallboxSequenceNumberSensor
    │
    ├── BinarySensorEntity
    │       └── BMWWallboxBinarySensorBase    # binary_sensor.py:39-58
    │               ├── BMWWallboxChargingBinarySensor
    │               └── BMWWallboxConnectedBinarySensor
    │
    ├── ButtonEntity
    │       └── BMWWallboxButtonBase          # button.py:38-96
    │               ├── BMWWallboxStartButton
    │               └── BMWWallboxStopButton
    │
    ├── NumberEntity
    │       ├── BMWWallboxCurrentLimitNumber  # number.py:34-106
    │       └── BMWWallboxLEDBrightnessNumber # number.py:109-143
    │
    └── SwitchEntity
            └── BMWWallboxChargingSwitch      # switch.py:27-58
```

---

## Base Class: BMWWallboxSensorBase

**Location:** `sensor.py:64-86`

```python
class BMWWallboxSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for BMW Wallbox sensors."""

    def __init__(
        self,
        coordinator: BMWWallboxCoordinator,
        entry: ConfigEntry,
        sensor_type: str,    # Unique suffix for entity ID
        name: str,           # Display name
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        # Unique ID: {config_entry_id}_{sensor_type}
        self._attr_unique_id = f"{entry.entry_id}_{sensor_type}"
        
        # Display name
        self._attr_name = name
        
        # Device grouping - REQUIRED for all entities
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW (Delta Electronics)"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
            "sw_version": coordinator.device_info.get("firmware_version"),
            "serial_number": coordinator.device_info.get("serial_number"),
        }
```

### Key Points

1. **Always extend both** `CoordinatorEntity` AND the platform entity class
2. **Call `super().__init__(coordinator)`** - passes coordinator to CoordinatorEntity
3. **Set `_attr_unique_id`** - must be unique across all entities
4. **Set `_attr_device_info`** - groups entities under same device in HA

---

## Template: Adding a New Sensor

### Step 1: Add Constant to `const.py`

```python
# const.py - add entity suffix constant
SENSOR_NEW_METRIC: Final = "new_metric"
```

### Step 2: Add Data Field to Coordinator

```python
# coordinator.py - in BMWWallboxCoordinator.__init__()
self.data: dict[str, Any] = {
    # ... existing fields ...
    "new_metric": None,  # Add new field with default
}
```

### Step 3: Extract Value in OCPP Handler

```python
# coordinator.py - in WallboxChargePoint.on_transaction_event()
# Inside the meter_value processing loop:
elif measurand == "New.Metric.Name":
    self.coordinator.data["new_metric"] = float(value)
```

### Step 4: Create Sensor Class

```python
# sensor.py - add new sensor class

class BMWWallboxNewMetricSensor(BMWWallboxSensorBase):
    """Sensor for new metric."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(
            coordinator, 
            entry, 
            SENSOR_NEW_METRIC,  # From const.py
            "New Metric"        # Display name
        )
        # Set sensor attributes
        self._attr_device_class = SensorDeviceClass.POWER  # or appropriate class
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        return self.coordinator.data.get("new_metric")
```

### Step 5: Register in `async_setup_entry`

```python
# sensor.py - add to async_setup_entry()
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BMWWallboxCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([
        # ... existing sensors ...
        BMWWallboxNewMetricSensor(coordinator, entry),  # Add new sensor
    ])
```

---

## Template: Adding a New Binary Sensor

### Step 1: Add Constant

```python
# const.py
BINARY_SENSOR_NEW_STATE: Final = "new_state"
```

### Step 2: Add Data Field

```python
# coordinator.py - in __init__()
self.data: dict[str, Any] = {
    # ... existing fields ...
    "new_state": False,  # Boolean field
}
```

### Step 3: Create Binary Sensor Class

```python
# binary_sensor.py

class BMWWallboxNewStateBinarySensor(BMWWallboxBinarySensorBase):
    """Binary sensor for new state."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, BINARY_SENSOR_NEW_STATE)
        self._attr_name = "New State"
        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY  # or appropriate

    @property
    def is_on(self) -> bool:
        """Return true if condition is met."""
        return self.coordinator.data.get("new_state", False)
```

### Step 4: Register

```python
# binary_sensor.py - in async_setup_entry()
async_add_entities([
    # ... existing ...
    BMWWallboxNewStateBinarySensor(coordinator, entry),
])
```

---

## Template: Adding a New Button

### Step 1: Add Constant

```python
# const.py
BUTTON_NEW_ACTION: Final = "new_action"
```

### Step 2: Add Coordinator Method (if needed)

```python
# coordinator.py
async def async_new_action(self) -> dict:
    """Perform new action."""
    if not self.charge_point:
        return {"success": False, "message": "Not connected"}
    
    try:
        response = await asyncio.wait_for(
            self.charge_point.call(call.SomeCommand(...)),
            timeout=15.0
        )
        return {"success": True, "message": "Done"}
    except Exception as err:
        return {"success": False, "message": str(err)}
```

### Step 3: Create Button Class

```python
# button.py

class BMWWallboxNewActionButton(BMWWallboxButtonBase):
    """Button for new action."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry, hass: HomeAssistant) -> None:
        super().__init__(coordinator, entry, hass, BUTTON_NEW_ACTION)
        self._attr_name = "New Action"
        self._base_icon = "mdi:gesture-tap"

    async def async_press(self) -> None:
        """Handle button press."""
        await self._async_press_with_loading(self._do_action())

    async def _do_action(self) -> None:
        """Execute the action."""
        result = await self.coordinator.async_new_action()
        if result["success"]:
            _LOGGER.info("Action successful")
        else:
            _LOGGER.warning("Action failed: %s", result["message"])
```

### Step 4: Register

```python
# button.py - in async_setup_entry()
async_add_entities([
    # ... existing ...
    BMWWallboxNewActionButton(coordinator, entry, hass),
])
```

---

## Template: Adding a New Number Entity

### Step 1: Add Constant

```python
# const.py
NUMBER_NEW_SETTING: Final = "new_setting"
```

### Step 2: Add Coordinator Method

```python
# coordinator.py
async def async_set_new_setting(self, value: int) -> bool:
    """Set new setting value."""
    if not self.charge_point:
        return False
    
    try:
        # Send OCPP command
        response = await asyncio.wait_for(
            self.charge_point.call(call.SetVariables(...)),
            timeout=15.0
        )
        return response.status == "Accepted"
    except Exception:
        return False
```

### Step 3: Create Number Class

```python
# number.py

class BMWWallboxNewSettingNumber(CoordinatorEntity, NumberEntity):
    """Number entity for new setting."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{NUMBER_NEW_SETTING}"
        self._attr_name = "New Setting"
        self._attr_icon = "mdi:tune"
        self._attr_native_unit_of_measurement = PERCENTAGE  # or appropriate
        self._attr_native_min_value = 0
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_mode = NumberMode.SLIDER
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
            "manufacturer": coordinator.device_info.get("vendor", "BMW"),
            "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
        }

    @property
    def native_value(self) -> float:
        """Return current value."""
        return self.coordinator.data.get("new_setting", 50)

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        success = await self.coordinator.async_set_new_setting(int(value))
        if success:
            self.coordinator.data["new_setting"] = int(value)
            self.async_write_ha_state()
```

### Step 4: Register

```python
# number.py - in async_setup_entry()
async_add_entities([
    # ... existing ...
    BMWWallboxNewSettingNumber(coordinator, entry),
])
```

---

## Template: Adding a New Switch

### Step 1: Add Constant

```python
# const.py
SWITCH_NEW_TOGGLE: Final = "new_toggle"
```

### Step 2: Create Switch Class

```python
# switch.py

class BMWWallboxNewToggleSwitch(CoordinatorEntity, SwitchEntity):
    """Switch entity for new toggle."""

    def __init__(self, coordinator: BMWWallboxCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{SWITCH_NEW_TOGGLE}"
        self._attr_name = "New Toggle"
        self._attr_icon = "mdi:toggle-switch"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
            "name": "BMW Wallbox",
        }

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self.coordinator.data.get("new_toggle_state", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.coordinator.async_enable_new_toggle()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.coordinator.async_disable_new_toggle()
```

---

## Dynamic Icons

Some entities change icon based on state. Example from `sensor.py`:

```python
class BMWWallboxStatusSensor(BMWWallboxSensorBase):
    
    @property
    def icon(self) -> str:
        """Return icon based on status."""
        status = self.native_value
        if status == "Charging ⚡":
            return "mdi:battery-charging"
        elif status == "Paused":
            return "mdi:pause-circle"
        elif status == "Disconnected":
            return "mdi:power-plug-off"
        elif status == "Ready":
            return "mdi:power-plug"
        elif status == "Connected":
            return "mdi:car-electric"
        elif status == "Car Paused":
            return "mdi:car-clock"
        return "mdi:ev-station"
```

---

## Extra State Attributes

Add additional data to entities via `extra_state_attributes`:

```python
class BMWWallboxStateSensor(BMWWallboxSensorBase):
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        return {
            "ocpp_state": self.coordinator.data.get("charging_state"),
            "transaction_id": self.coordinator.data.get("transaction_id"),
        }
```

---

## Entity Availability

Control when entities are available:

```python
class BMWWallboxCurrentLimitNumber(CoordinatorEntity, NumberEntity):
    
    @property
    def available(self) -> bool:
        """Return True if entity is available.
        
        Current limit only works when there's an active transaction.
        """
        return (
            super().available
            and self.coordinator.data.get("connected", False)
            and self.coordinator.current_transaction_id is not None
        )
```

---

## Energy Sensors

The integration provides comprehensive energy tracking with automatic period-based resets.

### Energy Total Sensor

**Purpose:** Lifetime cumulative energy tracking for Home Assistant Energy Dashboard

**Implementation:**
- Uses `state_class: TOTAL_INCREASING` for proper Energy Dashboard integration
- Accumulates energy across ALL charging sessions
- Never resets - provides true lifetime totals
- Calculated as: `energy_cumulative + current_session_energy`

**Session End Detection:**
- Monitors energy value for drops > 0.1 kWh
- When detected, adds last session's final value to cumulative counters
- Ensures no energy is lost between sessions

**Usage:**
```yaml
# Add to Energy Dashboard
Settings → Dashboards → Energy → Individual Devices
Select: sensor.energy_total
```

### Period-Based Energy Sensors

Four sensors that automatically reset at specific intervals:

| Sensor | Reset Schedule | Icon | Use Case |
|--------|---------------|------|----------|
| **Energy Daily** | Midnight every day | calendar-today | Daily usage patterns |
| **Energy Weekly** | Monday at midnight | calendar-week | Work vs weekend comparison |
| **Energy Monthly** | 1st of each month | calendar-month | Billing cycles |
| **Energy Yearly** | January 1st | calendar | Annual consumption |

**Implementation Details:**
- All use `state_class: TOTAL_INCREASING` for statistics
- Values calculated as: `period_base + current_session_energy`
- Include `last_reset` timestamp in extra attributes
- Reset logic runs on every TransactionEvent
- Persist across Home Assistant restarts

**Example Attributes:**
```python
sensor.bmw_wallbox_energy_daily:
  state: 12.5  # kWh
  attributes:
    last_reset: "2025-12-08T00:00:00"
    unit_of_measurement: "kWh"
    device_class: "energy"
    state_class: "total_increasing"
```

**Automation Example:**
```yaml
automation:
  - alias: "High Daily Charging Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bmw_wallbox_energy_daily
        above: 50
    action:
      - service: notify.mobile_app
        data:
          message: "High charging usage: {{ states('sensor.bmw_wallbox_energy_daily') }} kWh today"
```

### Energy Session Sensor

**Purpose:** Track energy for current charging session only

**Implementation:**
- Reports energy in Wh (not kWh) for precision
- Resets when new session starts
- Useful for per-charge monitoring

---

## Checklist: New Entity

When adding a new entity, ensure:

- [ ] Constant added to `const.py`
- [ ] Data field added to `coordinator.data` with default
- [ ] Data extraction added to appropriate OCPP handler (if needed)
- [ ] Entity class created extending appropriate base
- [ ] `_attr_unique_id` set using `{entry.entry_id}_{constant}`
- [ ] `_attr_name` set for display
- [ ] `_attr_device_info` set for device grouping
- [ ] Entity registered in `async_setup_entry()`
- [ ] Test added to appropriate test file
