# BMW Wallbox Integration - AI Context File

> **For AI Assistants:** Read this file first to understand the project structure, domain concepts, and critical rules before making any modifications.

## Project Overview

**Name:** BMW Wallbox Home Assistant Integration  
**Domain:** `bmw_wallbox`  
**Version:** 1.0.0  
**Author:** João Belo  
**Protocol:** OCPP 2.0.1 (Open Charge Point Protocol)  
**Target Hardware:** BMW-branded Delta Electronics wallboxes (Model: EIAW-E22KTSE6B04)

### What This Integration Does

This integration allows Home Assistant to control and monitor BMW electric vehicle wallboxes. It acts as an **OCPP Central System (CSMS)** - the wallbox connects TO Home Assistant, not the other way around.

```
┌─────────────┐     WebSocket (wss://)     ┌─────────────────┐
│  BMW        │ ──────────────────────────►│  Home Assistant │
│  Wallbox    │     OCPP 2.0.1 Messages    │  (This Code)    │
│  (Client)   │ ◄──────────────────────────│  (Server)       │
└─────────────┘                            └─────────────────┘
```

---

## File Map

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 72 | Integration entry point. Sets up platforms, starts/stops OCPP server |
| `coordinator.py` | ~900 | **Core file.** OCPP WebSocket server, message handlers, charging commands |
| `config_flow.py` | 110 | Configuration UI for adding the integration |
| `const.py` | 78 | All constants: domain, config keys, entity suffixes, attributes |
| `sensor.py` | 430 | 15 sensor entities (power, energy, voltage, current, states) |
| `binary_sensor.py` | 96 | 2 binary sensors (charging active, OCPP connected) |
| `button.py` | 156 | Start/Stop charging buttons with loading states |
| `number.py` | 144 | Current limit slider (0-32A), LED brightness (0-100%) |
| `switch.py` | 60 | Charging on/off toggle switch |
| `strings.json` | 29 | UI strings for config flow |
| `translations/en.json` | 29 | English translations |
| `manifest.json` | 14 | Integration metadata, dependencies |

---

## Domain Glossary

| Term | Definition |
|------|------------|
| **OCPP** | Open Charge Point Protocol - standard for EV charger communication |
| **CSMS** | Charging Station Management System - the server (Home Assistant in our case) |
| **Charge Point** | The wallbox/charger device that connects to CSMS |
| **EVSE** | Electric Vehicle Supply Equipment - the physical charging connector |
| **Transaction** | A charging session, identified by `transaction_id` |
| **Measurand** | A type of measurement (Power.Active.Import, Voltage, Current.Import, etc.) |
| **TransactionEvent** | OCPP message containing meter values and charging state updates |
| **SetChargingProfile** | OCPP command to control charging current (0A = pause, 32A = full) |
| **SuspendedEVSE** | Charging paused by the wallbox (our pause command) |
| **SuspendedEV** | Charging paused by the vehicle (car's decision) |

---

## Critical Rules

### 1. Transaction Required for Current Control
```python
# SetChargingProfile ONLY works when there's an active transaction
if not self.current_transaction_id:
    # This will FAIL - cannot set charging profile without transaction
    return False
```
**Location:** `coordinator.py:async_set_current_limit()` (line 759-832)

### 2. EVCC-Style Pause Pattern (IMPORTANT!)
**DO NOT** use `RequestStopTransaction` to stop charging - it causes stuck transaction states.

**DO** use `SetChargingProfile` with 0A limit to pause:
```python
# Correct: Pause charging (keeps transaction alive)
await self.async_pause_charging()  # Sets current to 0A

# Correct: Resume charging
await self.async_resume_charging(32.0)  # Sets current to 32A

# WRONG: This causes stuck states!
# await self.charge_point.call(call.RequestStopTransaction(...))
```
**Location:** `coordinator.py:async_pause_charging()` (line 589-669)

### 3. All Data Flows Through Coordinator
Entities read from `self.coordinator.data` dictionary. Never store state in entities.
```python
@property
def native_value(self) -> float | None:
    return self.coordinator.data.get("power")  # Always read from coordinator
```

### 4. Async Commands Need Timeout
All OCPP commands must use `asyncio.wait_for()` with timeout:
```python
response = await asyncio.wait_for(
    self.charge_point.call(call.SomeCommand(...)),
    timeout=15.0  # Always 15 seconds
)
```

### 5. Device Info Required on All Entities
Every entity must include `device_info` for proper grouping in HA:
```python
self._attr_device_info = {
    "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
    "name": "BMW Wallbox",
    "manufacturer": coordinator.device_info.get("vendor", "BMW"),
    "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
}
```

---

## Quick Reference: Common Tasks

### "How do I add a new sensor?"
1. Add constant to `const.py`: `SENSOR_NEW_THING: Final = "new_thing"`
2. Add data field to `coordinator.py` in `__init__` data dict
3. Extract value in `on_transaction_event()` handler
4. Create sensor class in `sensor.py` extending `BMWWallboxSensorBase`
5. Add to `async_setup_entry()` entities list

**See:** `docs/ENTITIES.md` for full template

### "How do I add a new OCPP message handler?"
1. Add handler method to `WallboxChargePoint` class in `coordinator.py`
2. Decorate with `@on("MessageName")`
3. Update `coordinator.data` with extracted values
4. Call `self.coordinator.async_set_updated_data(self.coordinator.data)`

**See:** `docs/OCPP_HANDLERS.md` for full template

### "How do I send a command to the wallbox?"
1. Check `self.charge_point` exists (wallbox connected)
2. For charging commands, check `self.current_transaction_id` exists
3. Use `await asyncio.wait_for(self.charge_point.call(...), timeout=15.0)`
4. Handle response status

**See:** `docs/COORDINATOR.md` for API reference

### "How do I add a new configurable setting?"
1. Add to config schema in `config_flow.py`
2. Add constant to `const.py`
3. Add validation in `validate_input()`
4. Access via `self.config["setting_name"]` in coordinator

**See:** `docs/DATA_SCHEMAS.md` for config schema

---

## Coordinator Data Fields Reference

The `coordinator.data` dictionary is the single source of truth. Key fields:

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `connected` | bool | Heartbeat | Wallbox OCPP connection status |
| `power` | float | TransactionEvent | Current power draw (W) |
| `energy_total` | float | TransactionEvent | Total energy (kWh) |
| `current` | float | TransactionEvent | Charging current (A) |
| `voltage` | float | TransactionEvent | Line voltage (V) |
| `charging_state` | str | TransactionEvent | Charging/SuspendedEVSE/Idle/etc |
| `transaction_id` | str | TransactionEvent | Active session UUID |
| `connector_status` | str | StatusNotification | Available/Occupied/etc |

**Full schema:** See `docs/DATA_SCHEMAS.md`

---

## Testing

Tests are in `/tests/` folder:
- `conftest.py` - Shared fixtures
- `test_sensor.py` - Sensor entity tests
- `test_button.py` - Button entity tests
- `test_config_flow.py` - Config flow tests
- `test_number.py` - Number entity tests

Run tests:
```bash
pytest tests/ -v
```

**See:** `docs/TESTING.md` for testing guide
