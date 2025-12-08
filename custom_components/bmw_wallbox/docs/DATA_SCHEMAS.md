# BMW Wallbox Integration - Data Schemas

## Coordinator Data Schema

The `coordinator.data` dictionary is the single source of truth for all entity state. Located in `coordinator.py`.

### Complete Schema

```python
coordinator.data: dict[str, Any] = {
    # ═══════════════════════════════════════════════════════════════════
    # CONNECTION STATUS
    # ═══════════════════════════════════════════════════════════════════
    "connected": bool,           # True if OCPP WebSocket connected
                                 # Default: False
                                 # Source: on_connect(), on_heartbeat()

    "last_heartbeat": datetime | None,  # Last heartbeat timestamp
                                        # Default: None
                                        # Source: on_heartbeat()

    # ═══════════════════════════════════════════════════════════════════
    # CHARGING STATE
    # ═══════════════════════════════════════════════════════════════════
    "charging_state": str,       # OCPP charging state
                                 # Values: "Charging", "SuspendedEVSE", "SuspendedEV",
                                 #         "EVConnected", "Idle", "Unknown"
                                 # Default: "Unknown"
                                 # Source: TransactionEvent.transaction_info.charging_state

    "connector_status": str,     # Physical connector status
                                 # Values: "Available", "Occupied", "Reserved",
                                 #         "Unavailable", "Faulted", "Unknown"
                                 # Default: "Unknown"
                                 # Source: StatusNotification.connector_status

    "evse_id": int,              # EVSE identifier (always 1 for single-port)
                                 # Default: 1
                                 # Source: StatusNotification.evse_id

    "connector_id": int,         # Connector identifier (always 1)
                                 # Default: 1
                                 # Source: StatusNotification.connector_id

    # ═══════════════════════════════════════════════════════════════════
    # TRANSACTION INFO
    # ═══════════════════════════════════════════════════════════════════
    "transaction_id": str | None,  # Active transaction UUID
                                   # Default: None
                                   # Source: TransactionEvent.transaction_info.transaction_id

    "event_type": str | None,    # Transaction event type
                                 # Values: "Started", "Updated", "Ended"
                                 # Default: None
                                 # Source: TransactionEvent.event_type

    "trigger_reason": str | None,  # Why event was triggered
                                   # Values: "Authorized", "CablePluggedIn", "ChargingStateChanged",
                                   #         "MeterValuePeriodic", "StopAuthorized", etc.
                                   # Default: None
                                   # Source: TransactionEvent.trigger_reason

    "stopped_reason": str | None,  # Why charging stopped
                                   # Values: "EVDisconnected", "Remote", "Local", etc.
                                   # Default: None
                                   # Source: TransactionEvent.transaction_info.stopped_reason

    "sequence_number": int,      # Message sequence counter
                                 # Default: 0
                                 # Source: TransactionEvent.seq_no

    "last_update": str | None,   # ISO timestamp of last update
                                 # Default: None
                                 # Source: TransactionEvent.timestamp

    # ═══════════════════════════════════════════════════════════════════
    # AUTHORIZATION
    # ═══════════════════════════════════════════════════════════════════
    "id_token": str | None,      # RFID token identifier
                                 # Default: None
                                 # Source: TransactionEvent.id_token.id_token

    "id_token_type": str | None,  # Token type
                                  # Values: "Central", "Local", "NoAuthorization"
                                  # Default: None
                                  # Source: TransactionEvent.id_token.type

    # ═══════════════════════════════════════════════════════════════════
    # POWER MEASUREMENTS (from TransactionEvent meter_value)
    # ═══════════════════════════════════════════════════════════════════
    "power": float,              # Active power import (W)
                                 # Default: 0.0
                                 # Measurand: "Power.Active.Import"

    "power_active_export": float | None,  # Active power export (W)
                                          # Default: None
                                          # Measurand: "Power.Active.Export"

    "power_reactive_import": float | None,  # Reactive power import (VAr)
                                            # Default: None
                                            # Measurand: "Power.Reactive.Import"

    "power_reactive_export": float | None,  # Reactive power export (VAr)
                                            # Default: None
                                            # Measurand: "Power.Reactive.Export"

    "power_offered": float | None,  # Maximum power offered (W)
                                    # Default: None
                                    # Measurand: "Power.Offered"

    "power_factor": float | None,  # Power factor (0.0-1.0)
                                   # Default: None
                                   # Measurand: "Power.Factor"

    # ═══════════════════════════════════════════════════════════════════
    # ENERGY MEASUREMENTS (from TransactionEvent meter_value)
    # ═══════════════════════════════════════════════════════════════════
    "energy_total": float,       # Total cumulative energy (kWh) - for Energy Dashboard
                                 # Default: 0.0
                                 # Calculated: energy_cumulative + last_session_energy
                                 # Note: Never resets, accumulates across all sessions

    "energy_session": float,     # Current session energy (Wh)
                                 # Default: 0.0
                                 # Measurand: "Energy.Active.Import.Register" (raw)
    
    "energy_cumulative": float,  # Cumulative energy from completed sessions (kWh)
                                 # Default: 0.0
                                 # Updated: When new session detected (energy drop)
    
    "last_session_energy": float,  # Last seen session energy for session detection (kWh)
                                   # Default: 0.0
                                   # Used to detect session end and add to cumulative
    
    # Period-based energy tracking (auto-reset)
    "energy_daily": float,       # Daily energy (kWh) - resets at midnight
                                 # Default: 0.0
    
    "energy_weekly": float,      # Weekly energy (kWh) - resets Monday midnight
                                 # Default: 0.0
    
    "energy_monthly": float,     # Monthly energy (kWh) - resets 1st of month
                                 # Default: 0.0
    
    "energy_yearly": float,      # Yearly energy (kWh) - resets January 1st
                                 # Default: 0.0
    
    # Reset timestamp tracking
    "last_reset_daily": datetime | None,    # Last daily reset timestamp
                                            # Default: None
    
    "last_reset_weekly": datetime | None,   # Last weekly reset timestamp
                                             # Default: None
    
    "last_reset_monthly": datetime | None,  # Last monthly reset timestamp
                                             # Default: None
    
    "last_reset_yearly": datetime | None,   # Last yearly reset timestamp
                                             # Default: None

    "energy_active_export": float | None,  # Energy exported (kWh)
                                           # Default: None
                                           # Measurand: "Energy.Active.Export.Register"

    "energy_reactive_import": float | None,  # Reactive energy import (kVArh)
                                             # Default: None
                                             # Measurand: "Energy.Reactive.Import.Register"

    "energy_reactive_export": float | None,  # Reactive energy export (kVArh)
                                             # Default: None
                                             # Measurand: "Energy.Reactive.Export.Register"

    # ═══════════════════════════════════════════════════════════════════
    # CURRENT MEASUREMENTS (from TransactionEvent meter_value)
    # ═══════════════════════════════════════════════════════════════════
    "current": float,            # Total/average current (A)
                                 # Default: 0.0
                                 # Measurand: "Current.Import" (no phase)

    "current_l1": float | None,  # Phase L1 current (A)
                                 # Default: None
                                 # Measurand: "Current.Import", phase="L1"

    "current_l2": float | None,  # Phase L2 current (A)
                                 # Default: None
                                 # Measurand: "Current.Import", phase="L2"

    "current_l3": float | None,  # Phase L3 current (A)
                                 # Default: None
                                 # Measurand: "Current.Import", phase="L3"

    # ═══════════════════════════════════════════════════════════════════
    # VOLTAGE MEASUREMENTS (from TransactionEvent meter_value)
    # ═══════════════════════════════════════════════════════════════════
    "voltage": float,            # Average/total voltage (V)
                                 # Default: 0.0
                                 # Measurand: "Voltage" (no phase)

    "voltage_l1": float | None,  # Phase L1 voltage (V)
                                 # Default: None
                                 # Measurand: "Voltage", phase="L1" or "L1-N"

    "voltage_l2": float | None,  # Phase L2 voltage (V)
                                 # Default: None
                                 # Measurand: "Voltage", phase="L2" or "L2-N"

    "voltage_l3": float | None,  # Phase L3 voltage (V)
                                 # Default: None
                                 # Measurand: "Voltage", phase="L3" or "L3-N"

    # ═══════════════════════════════════════════════════════════════════
    # OTHER MEASUREMENTS
    # ═══════════════════════════════════════════════════════════════════
    "frequency": float | None,   # Grid frequency (Hz)
                                 # Default: None
                                 # Measurand: "Frequency"

    "temperature": float | None,  # Temperature (°C)
                                  # Default: None
                                  # Measurand: "Temperature"

    "soc": float | None,         # State of Charge (%)
                                 # Default: None
                                 # Measurand: "SoC"

    "phases_used": int,          # Number of phases in use
                                 # Default: 1
                                 # Source: TransactionEvent.number_of_phases_used

    # ═══════════════════════════════════════════════════════════════════
    # CONTEXT INFO (from TransactionEvent meter_value)
    # ═══════════════════════════════════════════════════════════════════
    "context": str | None,       # Measurement context
                                 # Values: "Sample.Periodic", "Transaction.Begin", etc.
                                 # Default: None
                                 # Source: sampled_value.context

    "location": str | None,      # Measurement location
                                 # Values: "Outlet", "Cable", "EV"
                                 # Default: None
                                 # Source: sampled_value.location

    # ═══════════════════════════════════════════════════════════════════
    # CONFIGURABLE SETTINGS
    # ═══════════════════════════════════════════════════════════════════
    "led_brightness": int,       # LED brightness (0-100%)
                                 # Default: 46 (from wallbox capabilities report)

    "current_limit": float,      # Current limit set by user (A)
                                 # Default: max_current from config
                                 # Set via: async_set_current_limit()
}
```

---

## Config Entry Schema

Configuration stored in `entry.data` after config flow. Defined in `config_flow.py`.

```python
entry.data: dict[str, Any] = {
    "port": int,                # WebSocket server port
                                # Default: 9000
                                # Validation: 1-65535
                                # Constant: CONF_PORT

    "ssl_cert": str,            # Path to SSL certificate file
                                # Default: "/ssl/fullchain.pem"
                                # Validation: File must exist
                                # Constant: CONF_SSL_CERT

    "ssl_key": str,             # Path to SSL private key file
                                # Default: "/ssl/privkey.pem"
                                # Validation: File must exist
                                # Constant: CONF_SSL_KEY

    "charge_point_id": str,     # Wallbox identifier
                                # Required, no default
                                # Example: "DE*BMW*ETEST1234567890AB"
                                # Constant: CONF_CHARGE_POINT_ID

    "rfid_token": str,          # RFID token for authorization
                                # Optional, default: ""
                                # Used in RequestStartTransaction
                                # Constant: CONF_RFID_TOKEN

    "max_current": int,         # Maximum allowed current (A)
                                # Default: 32
                                # Validation: 6-32
                                # Constant: CONF_MAX_CURRENT
}
```

### Config Flow Schema (Voluptuous)

```python
# config_flow.py
STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Required(CONF_SSL_CERT, default="/ssl/fullchain.pem"): str,
    vol.Required(CONF_SSL_KEY, default="/ssl/privkey.pem"): str,
    vol.Required(CONF_CHARGE_POINT_ID): str,
    vol.Optional(CONF_RFID_TOKEN, default=""): str,
    vol.Optional(CONF_MAX_CURRENT, default=DEFAULT_MAX_CURRENT): vol.All(
        vol.Coerce(int), vol.Range(min=6, max=32)
    ),
})
```

---

## OCPP Message Schemas

### Incoming: TransactionEvent

The main data source for meter values and charging state.

```python
# Handler: WallboxChargePoint.on_transaction_event()
# Location: coordinator.py:110-230

TransactionEvent = {
    "event_type": str,           # "Started" | "Updated" | "Ended"
    "timestamp": str,            # ISO 8601 timestamp
    "trigger_reason": str,       # "Authorized" | "CablePluggedIn" | "MeterValuePeriodic" | ...
    "seq_no": int,               # Sequence number
    "transaction_info": {
        "transaction_id": str,   # UUID of transaction
        "charging_state": str,   # "Charging" | "SuspendedEVSE" | "SuspendedEV" | "EVConnected" | "Idle"
        "stopped_reason": str | None,  # "EVDisconnected" | "Remote" | ...
    },
    "id_token": {                # Optional
        "id_token": str,         # RFID token value
        "type": str,             # "Central" | "Local" | "NoAuthorization"
    },
    "meter_value": [             # Optional, list of meter value groups
        {
            "timestamp": str,
            "sampled_value": [
                {
                    "value": str,           # Numeric value as string
                    "measurand": str,       # "Power.Active.Import" | "Voltage" | "Current.Import" | ...
                    "phase": str | None,    # "L1" | "L2" | "L3" | "L1-N" | None
                    "context": str | None,  # "Sample.Periodic" | "Transaction.Begin" | ...
                    "location": str | None, # "Outlet" | "Cable" | "EV"
                }
            ]
        }
    ],
    "number_of_phases_used": int | None,  # 1, 2, or 3
}
```

### Incoming: StatusNotification

Connector status updates.

```python
# Handler: WallboxChargePoint.on_status_notification()
# Location: coordinator.py:79-97

StatusNotification = {
    "timestamp": str,            # ISO 8601 timestamp
    "connector_status": str,     # "Available" | "Occupied" | "Reserved" | "Unavailable" | "Faulted"
    "evse_id": int,              # EVSE identifier (1)
    "connector_id": int,         # Connector identifier (1)
}
```

### Incoming: BootNotification

Device information on startup.

```python
# Handler: WallboxChargePoint.on_boot_notification()
# Location: coordinator.py:59-77

BootNotification = {
    "charging_station": {
        "model": str,            # e.g., "EIAW-E22KTSE6B04"
        "vendor_name": str,      # e.g., "BMW"
        "serial_number": str,    # Wallbox serial
        "firmware_version": str, # Firmware version
    },
    "reason": str,               # "PowerUp" | "RemoteReset" | ...
}
```

### Incoming: Heartbeat

Connection keepalive.

```python
# Handler: WallboxChargePoint.on_heartbeat()
# Location: coordinator.py:99-108

Heartbeat = {}  # No payload
```

---

## Outgoing Command Schemas

### SetChargingProfile

Control charging current.

```python
# Method: BMWWallboxCoordinator.async_set_current_limit()
# Location: coordinator.py:759-832

SetChargingProfile = {
    "evse_id": int,              # Always 1
    "charging_profile": {
        "id": int,               # Profile ID (999)
        "stack_level": int,      # Priority (1)
        "charging_profile_purpose": str,  # "TxProfile"
        "charging_profile_kind": str,     # "Absolute"
        "charging_schedule": [{
            "id": int,
            "start_schedule": str,        # ISO timestamp
            "charging_rate_unit": str,    # "A" (Amps)
            "charging_schedule_period": [{
                "start_period": int,      # 0 (immediate)
                "limit": float,           # Current in Amps (0 = pause, 32 = full)
            }]
        }],
        "transaction_id": str,   # REQUIRED - active transaction ID
    }
}
```

### RequestStartTransaction

Start a new charging session.

```python
# Method: BMWWallboxCoordinator.async_start_charging()
# Location: coordinator.py:363-469

RequestStartTransaction = {
    "id_token": {
        "id_token": str,         # RFID token from config
        "type": str,             # "Local"
    },
    "remote_start_id": int,      # Unique ID (timestamp)
    "evse_id": int,              # Always 1
}
```

### SetVariables

Configure wallbox settings.

```python
# Method: BMWWallboxCoordinator.async_set_led_brightness()
# Location: coordinator.py:834-886

SetVariables = {
    "set_variable_data": [{
        "attribute_type": str,   # "Actual"
        "attribute_value": str,  # Value as string
        "component": {
            "name": str,         # "ChargingStation"
        },
        "variable": {
            "name": str,         # "StatusLedBrightness"
        }
    }]
}
```

### Reset

Reboot the wallbox.

```python
# Method: BMWWallboxCoordinator.async_reset_wallbox()
# Location: coordinator.py:471-524

Reset = {
    "type": str,                 # "Immediate" | "OnIdle"
}
```

---

## Entity Attribute Schemas

### Sensor: Status

```python
extra_state_attributes = {
    "charging_state": str,       # Raw OCPP charging state
    "power_w": float,            # Current power in watts
    "transaction_id": str | None,  # Active transaction
    "wallbox_connected": bool,   # OCPP connection status
}
```

### Sensor: Charging State

```python
extra_state_attributes = {
    "ocpp_state": str,           # Raw OCPP state value
    "transaction_id": str | None,  # Active transaction
}
```

### Sensor: ID Token

```python
extra_state_attributes = {
    "type": str,                 # "Central" | "Local" | "Unknown"
}
```

---

## Device Info Schema

All entities must include device info for proper grouping.

```python
# Pattern used in all entity classes
self._attr_device_info = {
    "identifiers": {(DOMAIN, entry.data["charge_point_id"])},
    "name": "BMW Wallbox",
    "manufacturer": coordinator.device_info.get("vendor", "BMW"),
    "model": coordinator.device_info.get("model", "EIAW-E22KTSE6B04"),
    "sw_version": coordinator.device_info.get("firmware_version"),
    "serial_number": coordinator.device_info.get("serial_number"),
}
```

### Coordinator Device Info

Populated from BootNotification.

```python
coordinator.device_info: dict[str, str] = {
    "model": str,                # From charging_station.model
    "vendor": str,               # From charging_station.vendor_name
    "serial_number": str,        # From charging_station.serial_number
    "firmware_version": str,     # From charging_station.firmware_version
}
```
