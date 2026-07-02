---
name: testing
description: Testing conventions for the BMW Wallbox integration — pytest, HA fixtures, entity/handler/command patterns. Tests are MANDATORY for every new entity, handler, and command.
user-invocable: false
---

# Testing Rules — MANDATORY

**Every new sensor, control, OCPP handler, or coordinator command MUST have tests. No exceptions.**

Read `custom_components/bmw_wallbox/docs/TESTING.md` and `tests/conftest.py` before writing tests.

## Running tests

```bash
.venv/bin/pytest tests/ -q                          # all tests
.venv/bin/pytest tests/test_sensor.py -v            # one file
.venv/bin/pytest tests/test_sensor.py::test_power_sensor -v   # one test
.venv/bin/pytest tests/ --cov=custom_components.bmw_wallbox   # coverage
```

Tests are async (`asyncio_mode = "auto"` in `pyproject.toml`) — no `@pytest.mark.asyncio` needed.

## Fixtures (from `tests/conftest.py`)

- `mock_coordinator` — `BMWWallboxCoordinator` with populated `coordinator.data` and `current_transaction_id`.
- `mock_config_entry` — `ConfigEntry` with test config (`port`, `charge_point_id`, ssl paths).
- `mock_wallbox_charge_point` — `WallboxChargePoint` for OCPP testing (`call = AsyncMock(...)`).

## Patterns

### Sensor

```python
async def test_power_sensor(hass, mock_coordinator, mock_config_entry):
    sensor = BMWWallboxPowerSensor(mock_coordinator, mock_config_entry)
    assert sensor.native_value == 7000.0
    assert sensor.native_unit_of_measurement == "W"
    assert sensor.device_class == "power"
```

### Control (button / number)

```python
async def test_start_button(hass, mock_coordinator, mock_config_entry):
    button = BMWWallboxStartButton(mock_coordinator, mock_config_entry, hass)
    await button.async_press()
    mock_coordinator.async_start_charging.assert_called_once()
```

### Availability that depends on a transaction

```python
async def test_requires_transaction(hass, mock_coordinator, mock_config_entry):
    number = BMWWallboxCurrentLimitNumber(mock_coordinator, mock_config_entry)
    mock_coordinator.current_transaction_id = "test-123"
    assert number.available is True
    mock_coordinator.current_transaction_id = None
    assert number.available is False
```

## Rules

- **Arrange-Act-Assert**; one behavior per test; descriptive names (`test_current_limit_requires_active_transaction`).
- Test edge cases: `None`/missing values, disconnected state, rejected OCPP responses, timeouts.
- Mock external dependencies: `patch("os.path.isfile", ...)`, `charge_point.call = AsyncMock(...)`.
- Test error paths, not just happy paths.
- No skipped or commented-out tests.

## Checklist before marking work complete

- [ ] Test added/updated in `tests/` using the shared fixtures
- [ ] Value, properties (name/unit/device_class), and `unique_id` tested
- [ ] `None`/missing and availability paths tested
- [ ] Action tested (for buttons/switches/numbers)
- [ ] `.venv/bin/pytest tests/ -q` passes
