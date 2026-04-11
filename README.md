# BMW Wallbox Home Assistant Integration

[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-6B4FBB?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Tests](https://img.shields.io/github/actions/workflow/status/JoaoPedroBelo/bmw-wallbox-ha/tests.yml?style=for-the-badge&label=Tests)](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/actions/workflows/tests.yml)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/JoaoPedroBelo/bmw-wallbox-ha/validate.yml?style=for-the-badge&label=HACS)](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/JoaoPedroBelo/bmw-wallbox-ha?style=for-the-badge)](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases)
[![License](https://img.shields.io/github/license/JoaoPedroBelo/bmw-wallbox-ha?style=for-the-badge)](LICENSE)
[![Maintainer](https://img.shields.io/badge/Maintainer-%40JoaoPedroBelo-blue?style=for-the-badge)](https://github.com/JoaoPedroBelo)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=JoaoPedroBelo&repository=bmw-wallbox-ha&category=integration)

---

A comprehensive Home Assistant custom integration for BMW-branded wallboxes (Delta Electronics EIAW-E22KTSE6B04) using the OCPP 2.0.1 protocol.

## ✨ Features

- **🔌 Real-time Monitoring**: Track power, energy, current, voltage, and charging state
- **🎮 Smart Control**: Start/stop charging, set current limits dynamically
- **📊 20 Entities**: Sensors, binary sensors, buttons, and controls
- **⚡ Energy Dashboard**: Full integration with Home Assistant's Energy Dashboard
- **🔒 Secure**: Uses OCPP 2.0.1 with WebSocket Secure (WSS) connection
- **🏠 Local Control**: No cloud required - runs entirely on your local network

## 🚀 Quick Start

### Installation via HACS

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/JoaoPedroBelo/bmw-wallbox-ha`
5. Select category "Integration"
6. Click "Add"
7. Find "BMW Wallbox (OCPP)" in HACS and click "Install"
8. Restart Home Assistant

### Configuration

> ⚠️ **Important:** BMW/Mini wallboxes require **valid SSL certificates** with a matching hostname. Self-signed certificates or IP addresses will not work. See the **[SSL Certificate Setup Guide](custom_components/bmw_wallbox/docs/SSL_SETUP.md)** for detailed instructions using Cloudflare + Let's Encrypt.

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "BMW Wallbox"
4. Enter your configuration:
   - **WebSocket Port**: Default is 9000
   - **SSL Certificate Path**: Path to your SSL certificate (e.g., `/ssl/fullchain.pem`)
   - **SSL Key Path**: Path to your SSL private key (e.g., `/ssl/privkey.pem`)
   - **Charge Point ID**: Your wallbox's unique ID (format: `DE*BMW*XXXXXXXXXXXXXXXXX`)
   - **RFID Token** (optional): Authorization token
   - **Maximum Current**: Maximum allowed current (6-32A)

### Configure Your Wallbox

Update your BMW wallbox OCPP settings to point to your Home Assistant:
- **OCPP URL**: `wss://local.yourdomain.com:9000` (must use a hostname, not an IP)
- **Charge Station ID**: Must match the Charge Point ID in Home Assistant
- **Protocol**: OCPP 2.0.1

## 📖 Documentation

Comprehensive documentation is available in the [`docs`](custom_components/bmw_wallbox/docs/) folder:

- **[SSL Certificate Setup](custom_components/bmw_wallbox/docs/SSL_SETUP.md)**: **Required** - How to set up valid SSL certificates (Cloudflare + Let's Encrypt)
- **[Architecture](custom_components/bmw_wallbox/docs/ARCHITECTURE.md)**: Technical architecture overview
- **[Energy Sensors](custom_components/bmw_wallbox/docs/ENERGY_SENSORS.md)**: Energy tracking and Utility Meter setup
- **[OCPP Handlers](custom_components/bmw_wallbox/docs/OCPP_HANDLERS.md)**: OCPP message handling details
- **[Wallbox Capabilities](custom_components/bmw_wallbox/docs/WALLBOX_CAPABILITIES.md)**: Full OCPP inventory dump and hardware limitations
- **[Testing Guide](custom_components/bmw_wallbox/docs/TESTING.md)**: Development and testing information
- **[Troubleshooting](custom_components/bmw_wallbox/docs/TROUBLESHOOTING.md)**: Common issues and solutions

## 🎯 Entities

### Sensors (13)
- Power (W), Energy Total (kWh)
- Current (A), Voltage (V)
- Status, Charging State, Connector Status
- Transaction ID, Stopped Reason
- Event Type, Trigger Reason, ID Token
- Phases Used, Sequence Number

### Binary Sensors (2)
- Connected (ON when wallbox is connected via OCPP)
- Charging (ON when actively charging)

### Controls (5)
- Start / Stop / Reboot / Refresh buttons
- Current Limit slider (6-32A)

## 🏗️ Example Automations

### Solar-Powered Charging
```yaml
automation:
  - alias: "Start charging with excess solar"
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

### Dynamic Current Limiting
```yaml
automation:
  - alias: "Adjust current based on house load"
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

## 🔧 Supported Hardware

- **BMW Wallbox**: Delta Electronics EIAW-E22KTSE6B04
- **Mini Wallbox Plus**: Delta Electronics EIAW-E22KTSE6B15 (same hardware, different branding)
- **Potential**: Any OCPP 2.0.1 compatible Delta Electronics wallbox (untested)

## 🛠️ Technical Details

- **Protocol**: OCPP 2.0.1 with Security profile
- **Architecture**: Acts as OCPP Central System (server)
- **Connection**: WebSocket Secure (WSS)
- **Integration Type**: Local Push (no polling required)
- **Home Assistant**: Compatible with 2023.1.0+

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

**João Belo** ([@JoaoPedroBelo](https://github.com/JoaoPedroBelo))

## ⚠️ Disclaimer

This is an independent, open-source integration created for BMW-branded Delta Electronics wallboxes. This project is not affiliated with, endorsed by, or sponsored by BMW AG, BMW Group, Delta Electronics, or any related companies.

## 🐛 Issues & Support

For issues or questions:
- [GitHub Issues](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/issues)
- Review Home Assistant logs for error messages
- Check the [Troubleshooting Guide](custom_components/bmw_wallbox/docs/TROUBLESHOOTING.md)

## ⭐ Show Your Support

If you find this integration useful, please consider giving it a star on GitHub!


