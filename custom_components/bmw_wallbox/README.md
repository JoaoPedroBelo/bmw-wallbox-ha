# BMW Wallbox Home Assistant Integration

Custom Home Assistant integration for BMW wallboxes (Delta Electronics EIAW-E22KTSE6B04) using OCPP 2.0.1 protocol.

## Features

### Sensors (37 Total!)

**Core Sensors (Always Enabled):**
- **Power** (W) - Real-time power consumption
- **Energy Total** (kWh) - Total energy delivered (lifetime)
- **Energy Session** (Wh) - Energy for current charging session
- **Current** (A) - Charging current (total/average)
- **Voltage** (V) - Line voltage (total/average)
- **Charging State** - Current state (Charging/SuspendedEV/Idle)
- **Connector Status** - Physical connector state (Available/Occupied/etc.)
- **Transaction ID** - Current charging session UUID
- **Event Type** - Transaction event type (Started/Updated/Ended)
- **Trigger Reason** - Event trigger (MeterValuePeriodic/ChargingStateChanged/etc.)
- **Stopped Reason** - Why charging stopped
- **ID Token** - RFID/authorization token
- **Sequence Number** - Message sequence counter
- **Last Update** - Timestamp of last data update

**Advanced Sensors (Disabled by Default - Enable if Needed):**
- **Power Measurements**: Active Export, Reactive Import/Export, Offered, Power Factor
- **Energy Measurements**: Active Export, Reactive Import/Export
- **Per-Phase Current**: L1, L2, L3 (for 3-phase installations)
- **Per-Phase Voltage**: L1, L2, L3 (for 3-phase installations)
- **Other**: Frequency (Hz), Temperature (°C), State of Charge (%)

### Binary Sensors
- **Charging** - ON when actively charging
- **Connected** - ON when wallbox is connected via OCPP

### Controls
- **Start Charging** button - Initiates charging session
- **Stop Charging** button - Stops current session
- **Charging** switch - Toggle charging on/off
- **Current Limit** slider (0-32A) - Set maximum charging current

## Installation

### Prerequisites

1. **SSL Certificates**: The wallbox requires valid SSL certificates for secure communication
   - If using Home Assistant OS, the certificates are typically at:
     - `/ssl/fullchain.pem`
     - `/ssl/privkey.pem`

2. **Wallbox Configuration**: Your wallbox must be configured to connect to your Home Assistant instance
   - OCPP URL: `wss://your-ha-domain:9000/CHARGE_POINT_ID`
   - Protocol: OCPP 2.0.1 with Security profile

### HACS Installation

1. Add this repository to HACS as a custom repository
2. Search for "BMW Wallbox" in HACS
3. Click "Install"
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/bmw_wallbox` folder to your Home Assistant `config/custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "BMW Wallbox"
4. Enter the following information:
   - **WebSocket Port**: Default is 9000
   - **SSL Certificate Path**: Path to your SSL certificate (e.g., `/ssl/fullchain.pem`)
   - **SSL Key Path**: Path to your SSL private key (e.g., `/ssl/privkey.pem`)
   - **Charge Point ID**: Your wallbox's charge point ID (e.g., `DE*BMW*ETEST1234567890AB`)
   - **RFID Token** (optional): Token for RequestStartTransaction
   - **Maximum Current**: Maximum allowed current (6-32A)

5. Click **Submit**
6. The integration will start the OCPP server and wait for the wallbox to connect

## Usage

### Basic Control

**Start Charging:**
```yaml
service: button.press
target:
  entity_id: button.wallbox_start_charging
```

**Stop Charging:**
```yaml
service: button.press
target:
  entity_id: button.wallbox_stop_charging
```

**Set Current Limit:**
```yaml
service: number.set_value
target:
  entity_id: number.wallbox_current_limit
data:
  value: 16  # Set to 16A
```

### Example Automations

**Start charging when solar production > 5kW:**
```yaml
automation:
  - alias: "Solar Charging"
    trigger:
      - platform: numeric_state
        entity_id: sensor.solar_power
        above: 5000
    condition:
      - condition: state
        entity_id: binary_sensor.wallbox_charging
        state: "off"
    action:
      - service: button.press
        target:
          entity_id: button.wallbox_start_charging
```

**Dynamic current limiting based on house load:**
```yaml
automation:
  - alias: "Dynamic Current Limit"
    trigger:
      - platform: state
        entity_id: sensor.house_power
    condition:
      - condition: state
        entity_id: binary_sensor.wallbox_charging
        state: "on"
    action:
      - service: number.set_value
        target:
          entity_id: number.wallbox_current_limit
        data:
          value: >
            {% set available = 32 - (states('sensor.house_power')|float / 230) %}
            {{ [6, [available|round, 32]|min]|max }}
```

**Stop charging at 80% battery:**
```yaml
automation:
  - alias: "Stop at 80%"
    trigger:
      - platform: numeric_state
        entity_id: sensor.car_battery_level
        above: 80
    action:
      - service: button.press
        target:
          entity_id: button.wallbox_stop_charging
```

### Energy Dashboard Integration

The integration automatically provides energy sensors compatible with Home Assistant's Energy Dashboard:

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption**
3. Select **sensor.wallbox_energy_total**

## Troubleshooting

### Wallbox Not Connecting

1. **Check SSL Certificates**: Ensure the paths are correct and files are readable
2. **Check Firewall**: Port 9000 must be accessible from the wallbox
3. **Check Wallbox Configuration**: Verify the OCPP URL is correct
4. **Check Logs**: Look for errors in Home Assistant logs

### Commands Not Working

1. **Check Connection**: Ensure `binary_sensor.wallbox_connected` is ON
2. **Check Transaction**: Some commands require an active transaction
3. **Check Logs**: Look for rejection messages in the logs

### Energy Not Updating

Energy values are only updated during active charging sessions with `TransactionEvent` messages. If charging isn't active, the last value will be retained.

## Technical Details

### OCPP Protocol

This integration implements OCPP 2.0.1 with Security profile:
- Acts as Central System (server)
- Wallbox connects as Charge Point (client)
- Uses WebSocket Secure (wss://)
- Supports all standard OCPP 2.0.1 messages

### Supported OCPP Messages

**Incoming (from wallbox):**
- BootNotification
- StatusNotification
- Heartbeat
- TransactionEvent
- NotifyReport

**Outgoing (to wallbox):**
- RequestStartTransaction
- RequestStopTransaction
- SetChargingProfile
- GetReport

## Support

For issues or questions:
- Check the [GitHub Issues](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/issues)
- Review Home Assistant logs for error messages

## License

MIT License

## Author

**Developed by João Belo**

This is an independent, open-source integration created by João Belo for BMW-branded Delta Electronics wallboxes. This project is not affiliated with, endorsed by, or sponsored by BMW, Delta Electronics, or any other company.

