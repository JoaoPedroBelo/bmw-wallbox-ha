# BMW Wallbox Integration - Constants Reference

**File:** `const.py`

All constants are defined using `typing.Final` for type safety.

---

## Domain

```python
DOMAIN: Final = "bmw_wallbox"
```

**Usage:**
- Integration identifier in Home Assistant
- Key for `hass.data[DOMAIN]`
- Device identifier tuple: `(DOMAIN, charge_point_id)`

---

## Configuration Constants

Used in `config_flow.py` for config entry data.

| Constant | Value | Description |
|----------|-------|-------------|
| `CONF_PORT` | `"port"` | WebSocket server port |
| `CONF_SSL_CERT` | `"ssl_cert"` | Path to SSL certificate file |
| `CONF_SSL_KEY` | `"ssl_key"` | Path to SSL private key file |
| `CONF_CHARGE_POINT_ID` | `"charge_point_id"` | Wallbox identifier string |
| `CONF_RFID_TOKEN` | `"rfid_token"` | RFID token for authorization |
| `CONF_MAX_CURRENT` | `"max_current"` | Maximum charging current (A) |

**Access pattern:**
```python
port = entry.data[CONF_PORT]
# or
port = self.config.get("port")
```

---

## Default Values

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_PORT` | `9000` | Default WebSocket server port |
| `DEFAULT_MAX_CURRENT` | `32` | Default maximum current (Amps) |

**Usage in config flow:**
```python
vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
vol.Optional(CONF_MAX_CURRENT, default=DEFAULT_MAX_CURRENT): vol.All(
    vol.Coerce(int), vol.Range(min=6, max=32)
),
```

---

## Update Interval

```python
UPDATE_INTERVAL: Final = 10  # seconds
```

**Usage:** DataUpdateCoordinator polling interval (though data is pushed via OCPP, not polled).

---

## Sensor Entity Suffixes

Used to create unique entity IDs: `{config_entry_id}_{SENSOR_*}`

| Constant | Value | Entity Purpose |
|----------|-------|----------------|
| `SENSOR_POWER` | `"power"` | Power consumption (W) |
| `SENSOR_ENERGY_SESSION` | `"energy_session"` | Session energy (Wh) |
| `SENSOR_ENERGY_TOTAL` | `"energy_total"` | Total energy (kWh) |
| `SENSOR_STATE` | `"state"` | Charging state |
| `SENSOR_TRANSACTION_ID` | `"transaction_id"` | Transaction UUID |
| `SENSOR_CURRENT` | `"current"` | Charging current (A) |
| `SENSOR_VOLTAGE` | `"voltage"` | Line voltage (V) |
| `SENSOR_CONNECTOR_STATUS` | `"connector_status"` | Connector status |
| `SENSOR_EVENT_TYPE` | `"event_type"` | Transaction event type |
| `SENSOR_TRIGGER_REASON` | `"trigger_reason"` | Event trigger reason |
| `SENSOR_STOPPED_REASON` | `"stopped_reason"` | Stop reason |
| `SENSOR_ID_TOKEN` | `"id_token"` | RFID token |
| `SENSOR_SEQ_NO` | `"seq_no"` | Sequence number |
| `SENSOR_LAST_UPDATE` | `"last_update"` | Last update timestamp |
| `SENSOR_FREQUENCY` | `"frequency"` | Grid frequency (Hz) |
| `SENSOR_POWER_FACTOR` | `"power_factor"` | Power factor |
| `SENSOR_TEMPERATURE` | `"temperature"` | Temperature (°C) |
| `SENSOR_SOC` | `"soc"` | State of Charge (%) |
| `SENSOR_CURRENT_L1` | `"current_l1"` | Phase L1 current |
| `SENSOR_CURRENT_L2` | `"current_l2"` | Phase L2 current |
| `SENSOR_CURRENT_L3` | `"current_l3"` | Phase L3 current |
| `SENSOR_VOLTAGE_L1` | `"voltage_l1"` | Phase L1 voltage |
| `SENSOR_VOLTAGE_L2` | `"voltage_l2"` | Phase L2 voltage |
| `SENSOR_VOLTAGE_L3` | `"voltage_l3"` | Phase L3 voltage |
| `SENSOR_POWER_ACTIVE_EXPORT` | `"power_active_export"` | Active power export |
| `SENSOR_POWER_REACTIVE_IMPORT` | `"power_reactive_import"` | Reactive power import |
| `SENSOR_POWER_REACTIVE_EXPORT` | `"power_reactive_export"` | Reactive power export |
| `SENSOR_POWER_OFFERED` | `"power_offered"` | Power offered |
| `SENSOR_ENERGY_ACTIVE_EXPORT` | `"energy_active_export"` | Energy export |
| `SENSOR_ENERGY_REACTIVE_IMPORT` | `"energy_reactive_import"` | Reactive energy import |
| `SENSOR_ENERGY_REACTIVE_EXPORT` | `"energy_reactive_export"` | Reactive energy export |

**Usage:**
```python
from .const import SENSOR_POWER

self._attr_unique_id = f"{entry.entry_id}_{SENSOR_POWER}"
```

---

## Binary Sensor Entity Suffixes

| Constant | Value | Entity Purpose |
|----------|-------|----------------|
| `BINARY_SENSOR_CHARGING` | `"charging"` | Is actively charging |
| `BINARY_SENSOR_CONNECTED` | `"connected"` | OCPP connection status |
| `BINARY_SENSOR_CAR_CONNECTED` | `"car_connected"` | Car connected to charger |
| `BINARY_SENSOR_AVAILABLE` | `"available"` | Charger available |

**Usage:**
```python
from .const import BINARY_SENSOR_CHARGING

self._attr_unique_id = f"{entry.entry_id}_{BINARY_SENSOR_CHARGING}"
```

---

## Button Entity Suffixes

| Constant | Value | Entity Purpose |
|----------|-------|----------------|
| `BUTTON_START` | `"start"` | Start charging button |
| `BUTTON_STOP` | `"stop"` | Stop/pause charging button |

**Usage:**
```python
from .const import BUTTON_START

self._attr_unique_id = f"{entry.entry_id}_{BUTTON_START}"
```

---

## Number Entity Suffixes

| Constant | Value | Entity Purpose |
|----------|-------|----------------|
| `NUMBER_CURRENT_LIMIT` | `"current_limit"` | Charging current limit slider |
| `NUMBER_LED_BRIGHTNESS` | `"led_brightness"` | LED brightness slider |

**Usage:**
```python
from .const import NUMBER_CURRENT_LIMIT

self._attr_unique_id = f"{entry.entry_id}_{NUMBER_CURRENT_LIMIT}"
```

---

## Switch Entity Suffixes

| Constant | Value | Entity Purpose |
|----------|-------|----------------|
| `SWITCH_CHARGING` | `"charging_control"` | Charging on/off toggle |

**Usage:**
```python
from .const import SWITCH_CHARGING

self._attr_unique_id = f"{entry.entry_id}_{SWITCH_CHARGING}"
```

---

## Attribute Constants

Used for `extra_state_attributes` keys.

| Constant | Value | Description |
|----------|-------|-------------|
| `ATTR_TRANSACTION_ID` | `"transaction_id"` | Transaction UUID |
| `ATTR_CHARGING_STATE` | `"charging_state"` | OCPP charging state |
| `ATTR_EVSE_ID` | `"evse_id"` | EVSE identifier |
| `ATTR_CONNECTOR_ID` | `"connector_id"` | Connector identifier |
| `ATTR_PHASES_USED` | `"phases_used"` | Number of phases in use |
| `ATTR_ID_TOKEN_TYPE` | `"id_token_type"` | Type of ID token |
| `ATTR_CONTEXT` | `"context"` | Measurement context |
| `ATTR_LOCATION` | `"location"` | Measurement location |
| `ATTR_PHASE` | `"phase"` | Phase identifier |

**Usage:**
```python
from .const import ATTR_TRANSACTION_ID, ATTR_CHARGING_STATE

@property
def extra_state_attributes(self) -> dict[str, Any]:
    return {
        ATTR_TRANSACTION_ID: self.coordinator.data.get("transaction_id"),
        ATTR_CHARGING_STATE: self.coordinator.data.get("charging_state"),
    }
```

---

## Naming Conventions

### Entity Suffix Pattern
- Snake_case: `sensor_power`, `binary_sensor_charging`
- Descriptive: Indicates what the entity represents
- Unique across entity types: No collision between sensor and binary_sensor

### Config Key Pattern
- Snake_case: `port`, `ssl_cert`, `charge_point_id`
- Matches Home Assistant conventions

### Attribute Key Pattern
- Snake_case: `transaction_id`, `charging_state`
- Matches data dict keys

---

## Adding New Constants

When adding a new entity:

1. **Add suffix constant:**
```python
# const.py
SENSOR_NEW_METRIC: Final = "new_metric"
```

2. **Add data key (if different):**
Usually the data key matches the suffix, but if not:
```python
# In coordinator data dict
"new_metric_value": None,
```

3. **Add attribute constant (if exposing as attribute):**
```python
ATTR_NEW_METRIC: Final = "new_metric"
```

4. **Import in entity file:**
```python
from .const import SENSOR_NEW_METRIC
```

---

## Complete const.py Reference

```python
"""Constants for the BMW Wallbox integration."""
from typing import Final

DOMAIN: Final = "bmw_wallbox"

# Configuration
CONF_PORT: Final = "port"
CONF_SSL_CERT: Final = "ssl_cert"
CONF_SSL_KEY: Final = "ssl_key"
CONF_CHARGE_POINT_ID: Final = "charge_point_id"
CONF_RFID_TOKEN: Final = "rfid_token"
CONF_MAX_CURRENT: Final = "max_current"

# Defaults
DEFAULT_PORT: Final = 9000
DEFAULT_MAX_CURRENT: Final = 32

# Update interval
UPDATE_INTERVAL: Final = 10  # seconds

# Entity unique ID suffixes
SENSOR_POWER: Final = "power"
SENSOR_ENERGY_SESSION: Final = "energy_session"
SENSOR_ENERGY_TOTAL: Final = "energy_total"
SENSOR_STATE: Final = "state"
SENSOR_TRANSACTION_ID: Final = "transaction_id"
SENSOR_CURRENT: Final = "current"
SENSOR_VOLTAGE: Final = "voltage"
SENSOR_CONNECTOR_STATUS: Final = "connector_status"
# ... (see full list above)

BINARY_SENSOR_CHARGING: Final = "charging"
BINARY_SENSOR_CONNECTED: Final = "connected"
BINARY_SENSOR_CAR_CONNECTED: Final = "car_connected"
BINARY_SENSOR_AVAILABLE: Final = "available"

BUTTON_START: Final = "start"
BUTTON_STOP: Final = "stop"

NUMBER_CURRENT_LIMIT: Final = "current_limit"
NUMBER_LED_BRIGHTNESS: Final = "led_brightness"

SWITCH_CHARGING: Final = "charging_control"

# Attributes
ATTR_TRANSACTION_ID: Final = "transaction_id"
ATTR_CHARGING_STATE: Final = "charging_state"
ATTR_EVSE_ID: Final = "evse_id"
ATTR_CONNECTOR_ID: Final = "connector_id"
ATTR_PHASES_USED: Final = "phases_used"
ATTR_ID_TOKEN_TYPE: Final = "id_token_type"
ATTR_CONTEXT: Final = "context"
ATTR_LOCATION: Final = "location"
ATTR_PHASE: Final = "phase"
```
