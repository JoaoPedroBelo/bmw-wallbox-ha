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
SENSOR_EVENT_TYPE: Final = "event_type"
SENSOR_TRIGGER_REASON: Final = "trigger_reason"
SENSOR_STOPPED_REASON: Final = "stopped_reason"
SENSOR_ID_TOKEN: Final = "id_token"
SENSOR_SEQ_NO: Final = "seq_no"
SENSOR_LAST_UPDATE: Final = "last_update"
SENSOR_FREQUENCY: Final = "frequency"
SENSOR_POWER_FACTOR: Final = "power_factor"
SENSOR_TEMPERATURE: Final = "temperature"
SENSOR_SOC: Final = "soc"
SENSOR_CURRENT_L1: Final = "current_l1"
SENSOR_CURRENT_L2: Final = "current_l2"
SENSOR_CURRENT_L3: Final = "current_l3"
SENSOR_VOLTAGE_L1: Final = "voltage_l1"
SENSOR_VOLTAGE_L2: Final = "voltage_l2"
SENSOR_VOLTAGE_L3: Final = "voltage_l3"
SENSOR_POWER_ACTIVE_EXPORT: Final = "power_active_export"
SENSOR_POWER_REACTIVE_IMPORT: Final = "power_reactive_import"
SENSOR_POWER_REACTIVE_EXPORT: Final = "power_reactive_export"
SENSOR_POWER_OFFERED: Final = "power_offered"
SENSOR_ENERGY_ACTIVE_EXPORT: Final = "energy_active_export"
SENSOR_ENERGY_REACTIVE_IMPORT: Final = "energy_reactive_import"
SENSOR_ENERGY_REACTIVE_EXPORT: Final = "energy_reactive_export"

BINARY_SENSOR_CHARGING: Final = "charging"
BINARY_SENSOR_CONNECTED: Final = "connected"
BINARY_SENSOR_CAR_CONNECTED: Final = "car_connected"
BINARY_SENSOR_AVAILABLE: Final = "available"

BUTTON_START: Final = "start"
BUTTON_STOP: Final = "stop"
BUTTON_REBOOT: Final = "reboot"

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
