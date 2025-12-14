# BMW Wallbox (OCPP) Integration

Control and monitor your BMW-branded Delta Electronics wallbox using Home Assistant via OCPP 2.0.1 protocol.

## 🆕 What's New in v1.3.0

### 🚨 Major Fix: Reliable Pause/Resume Charging

This release completely rewrites charging control, fixing critical issues:

| Problem | Solution |
|---------|----------|
| ❌ "Pause" button always rejected | ✅ EVCC-style `SetChargingProfile(0A)` |
| ❌ Cannot restart after stopping | ✅ Keep transaction alive, just set current to 0 |
| ❌ Charging starts but 0W power | ✅ Send `SetChargingProfile(32A)` after start |
| ❌ Car ends session when paused | ✅ Configure `StopTxOnEVSideDisconnect=false` |

**💣 NUKE Option:** If all else fails, automatically reboots wallbox as last resort.

See [CHANGELOG.md](https://github.com/JoaoPedroBelo/bmw-wallbox-ha/blob/main/CHANGELOG.md) for full details.

---

## Features

- **Real-time Monitoring**: Power, energy, current, voltage, and charging state
- **Smart Control**: Start/pause/resume charging with EVCC-style current control
- **💣 NUKE Recovery**: Automatic wallbox reboot if all start methods fail
- **Energy Dashboard**: Compatible with Home Assistant's built-in Energy Dashboard
- **OCPP 2.0.1**: Full protocol support with WebSocket secure connection

## Supported Hardware

- BMW-branded Delta Electronics wallboxes (Model: EIAW-E22KTSE6B04)
- Any OCPP 2.0.1 compatible wallbox may work (untested)

## Quick Start

1. Install via HACS
2. Configure SSL certificates (required for OCPP)
3. Add integration and enter your wallbox details
4. Start charging from Home Assistant!

## How Charging Control Works

This integration uses **EVCC-style** charging control:

| Action | What Happens |
|--------|--------------|
| **Start** | `RequestStartTransaction` + `SetChargingProfile(32A)` |
| **Pause** | `SetChargingProfile(0A)` - transaction stays alive |
| **Resume** | `SetChargingProfile(32A)` - instant resume |
| **NUKE** | `Reset(Immediate)` - reboot wallbox (~60s) |

This approach avoids the OCPP "Finishing" state problem that prevents restarting after `RequestStopTransaction`.

## Author

**Developed by João Belo**

This is an independent, open-source integration for BMW-branded wallboxes. Not affiliated with BMW or Delta Electronics.

For documentation and support, visit the [GitHub repository](https://github.com/JoaoPedroBelo/bmw-wallbox-ha).
