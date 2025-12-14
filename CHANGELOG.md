# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2024-12-14

### 🚨 Major Fix: Reliable Pause/Resume Charging

This release completely rewrites how the integration controls charging, fixing critical issues that made pause/resume unreliable or impossible.

---

### The Problem We Solved

#### Issue 1: "Pause Charging" Button Always Rejected ❌

**Symptoms:**
- Pressing "Stop/Pause Charging" resulted in `Rejected` response
- Logs showed: `SetChargingProfile response: Rejected`
- Charging continued despite pressing stop

**Root Cause:**
The previous implementation used incorrect `SetChargingProfile` parameters. The wallbox requires specific profile settings including proper `stack_level`, `transaction_id`, and clearing existing profiles first.

---

#### Issue 2: Cannot Restart After Stopping 🔒

**Symptoms:**
- `RequestStopTransaction` worked and stopped charging
- But `RequestStartTransaction` was always `Rejected` afterwards
- Only unplugging the cable or rebooting the wallbox would fix it

**Root Cause:**
This is actually **defined by the OCPP specification**! After `RequestStopTransaction`, the charger enters "Finishing" state. From this state, **it is NOT allowed to start a new transaction with an IdTag**. This affects ALL OCPP-compliant chargers.

Source: [Teltonika Community Discussion](https://community.teltonika.lt/t/re-starting-charging-via-ocpp-fails/13750/2)

---

#### Issue 3: Charging Starts but No Power Delivered ⚡️

**Symptoms:**
- `RequestStartTransaction` returned `Accepted`
- But power stayed at 0W
- Car showed "Preparing" but never charged

**Root Cause:**
The wallbox accepted the transaction but wasn't told to allow current flow. We now send `SetChargingProfile(32A)` immediately after starting a transaction to enable power delivery.

---

#### Issue 4: Car Ends Session When Paused 🔌

**Symptoms:**
- Using `SetChargingProfile(0A)` to pause worked
- But then the car detected 0A available and stopped the session
- Transaction ended automatically

**Root Cause:**
The wallbox had `StopTxOnEVSideDisconnect` enabled (default). When the car stops drawing power (because we set 0A), the wallbox ends the transaction. We now attempt to configure this setting to `false` on connect.

---

### The Solution: EVCC-Style Charging Control 🔌

Named after the popular [EVCC](https://evcc.io/) project, this approach controls charging by adjusting current limits instead of starting/stopping transactions:

| User Action | Old (Broken) Method | New (Working) Method |
|-------------|---------------------|----------------------|
| **Pause** | `RequestStopTransaction` → Stuck in "Finishing" | `SetChargingProfile(0A)` → Transaction stays alive |
| **Resume** | `RequestStartTransaction` → Rejected | `SetChargingProfile(32A)` → Instant resume |
| **Start (new)** | `RequestStartTransaction` → No power | `RequestStartTransaction` + `SetChargingProfile(32A)` |

**Benefits:**
- ✅ No stuck transactions
- ✅ Instant pause/resume
- ✅ No wallbox reset needed
- ✅ Perfect for solar charging (adjust current dynamically)
- ✅ Works with BMW wallbox quirks

---

### 💣 NUKE Option: Last Resort Recovery

If all else fails, the integration can now automatically reboot the wallbox:

```
START pressed
    ↓
Try SetChargingProfile(32A) to resume existing transaction
    ↓ (if fails)
Try RequestStartTransaction + SetChargingProfile(32A)
    ↓ (if fails)
💣 NUKE: Reset(Immediate) → Wallbox reboots (~60 seconds)
    ↓
Charging auto-starts after reboot (if cable plugged in)
```

The NUKE is:
- Enabled by default (can disable with `allow_nuke=False`)
- Only triggers after ALL other methods fail
- Takes ~60 seconds for wallbox to reboot
- Charging usually auto-starts after reboot

---

### New Features

- **Smart RFID handling** - Uses your configured RFID token, or `no_authorization` if RFID is disabled
- **Transaction ID refresh** - Queries wallbox via `GetTransactionStatus` before operations
- **Wallbox auto-configuration** - Sets `StopTxOnEVSideDisconnect=false` on connect
- **Better logging** - Detailed logs for debugging charging issues

---

### Documentation Updates 📊

All documentation now includes **Mermaid flowcharts** for visual understanding:

- **COORDINATOR.md** - Start charging decision tree, NUKE flow, data architecture
- **PATTERNS.md** - Decision trees for all charging operations
- **TROUBLESHOOTING.md** - Diagnostic flowcharts for:
  - SSL/connection errors
  - Command rejections
  - Stuck transactions
  - Quick diagnostic checklist

---

### Test Suite Fixed ✅

All **85 tests** now pass:

- Button tests - Fixed entity ID mocking for Home Assistant
- Config flow tests - Fixed integration loading in test environment
- Coordinator tests - Fixed async task cleanup and timeout assertions
- Sensor tests - Updated for new icon and attribute values

---

### Technical Changes

**New coordinator methods:**
- `async_refresh_transaction_id()` - Verify transaction is still active
- `async_configure_wallbox_for_pause_resume()` - Set wallbox config on connect

**Modified methods:**
- `async_start_charging(allow_nuke=True)` - Smart start with NUKE fallback
- `async_pause_charging()` - EVCC-style pause via `SetChargingProfile(0A)`
- `async_resume_charging()` - EVCC-style resume via `SetChargingProfile(32A)`
- `async_stop_charging()` - Now calls `async_pause_charging()` internally

**pytest configuration:**
- Added `asyncio_mode = "auto"` for proper async test support

## [1.2.1] - 2024-12-13

### Fixed
- **Energy sensors showing 0** - Fixed issue where Energy Total and Energy Session showed 0.00 after Home Assistant restart
- Now automatically requests meter values when wallbox connects
- Simplified energy tracking to use wallbox values directly

### Changed
- Removed unnecessary energy accumulation logic
- Energy sensors now display values directly from wallbox

## [1.2.0] - 2024-12-13

### Changed
- **BREAKING: Removed period energy sensors** - Daily, weekly, monthly, and yearly energy sensors have been removed
- Use Home Assistant's built-in **Utility Meter** helper instead for period-based tracking
- This provides better persistence, customizable reset times, and tariff support

### Added
- **Documentation** - Added comprehensive guide in README for setting up Utility Meter helpers
- Step-by-step instructions for UI and YAML configuration
- Examples for cost tracking with peak/off-peak tariffs

### Why This Change?
The custom period sensors had persistence issues (values reset on HA restart). Home Assistant's Utility Meter is the recommended, battle-tested solution that:
- ✅ Survives Home Assistant restarts
- ✅ Allows custom reset times
- ✅ Supports tariff tracking (peak/off-peak)
- ✅ Requires no integration code maintenance

### Migration Guide
After updating, set up Utility Meter helpers:
1. Go to **Settings** → **Devices & Services** → **Helpers**
2. Click **+ Create Helper** → **Utility Meter**
3. Select `sensor.energy_total` as input
4. Choose cycle: Daily/Weekly/Monthly/Yearly

Or via YAML:
```yaml
utility_meter:
  wallbox_energy_daily:
    source: sensor.energy_total
    cycle: daily
```

## [1.1.2] - 2024-12-09

### Fixed
- **Lint Configuration** - Fixed TOML parse error by moving `exclude` field to correct section in pyproject.toml
- Code formatting issues (whitespace on blank lines, import sorting)
- Added appropriate lint rule exceptions for common patterns (unused test fixtures, OCPP-specific naming conventions)
- Unused variable warnings in test files

## [1.1.1] - 2024-12-08

### Fixed
- **Energy Period Sensors Bug** - Fixed critical issue where daily, weekly, monthly, and yearly energy sensors were all showing the same value (total energy) instead of their respective period consumption
- Period sensors now correctly track energy consumed in their specific time periods
- Removed incorrect addition of current session energy to period counters

### Added
- **Comprehensive Linting Setup** - Added Ruff, MyPy, and pre-commit hooks following Home Assistant best practices
- **Development Tools** - Added Makefile with quick commands (`make lint`, `make format`, `make test`)
- **Code Quality Enforcement** - CI now fails on formatting issues
- **Contributing Guide** - Added CONTRIBUTING.md with development guidelines
- **Pre-commit Hooks** - Automatic code formatting and validation on commit
- Automated trailing whitespace and blank line cleanup

### Changed
- Improved GitHub Actions workflows with separate lint workflow
- Enhanced release workflow to continue on HACS validation errors
- Cleaned up all trailing whitespace and blank lines across codebase
- Updated pyproject.toml with comprehensive tool configurations

### Documentation
- Added .ruff-format-on-save.md guide for editor integration
- Added .github/DEVELOPMENT.md quick reference
- Updated all development documentation

### Technical
- All Python files now have exactly 1 trailing newline (PEP 8 compliant)
- Ruff configured with Home Assistant-compatible rules
- MyPy strict type checking enabled
- Pre-commit hooks for automated quality checks

## [1.1.0] - 2024-12-08

### Added
- **Energy Daily Sensor** - Automatically resets at midnight for daily consumption tracking
- **Energy Weekly Sensor** - Automatically resets every Monday for weekly consumption tracking
- **Energy Monthly Sensor** - Automatically resets on 1st of month for monthly billing cycles
- **Energy Yearly Sensor** - Automatically resets on January 1st for annual consumption tracking
- Period-based energy sensors with automatic time-based resets
- `last_reset` attribute on all period sensors showing when counter was last reset
- Comprehensive energy sensor documentation (ENERGY_SENSORS.md)

### Fixed
- **Energy Total Sensor** - Now properly accumulates energy across ALL charging sessions
- Session end detection to prevent energy loss between charging sessions
- Energy Dashboard integration - sensor no longer resets with each session
- Cumulative energy tracking across wallbox restarts

### Changed
- Energy Total sensor now uses true cumulative tracking (never resets)
- Period sensors include current session energy for real-time updates
- Improved energy measurement accuracy with 0.1 kWh session detection threshold

### Technical
- Added `_check_and_reset_period_counters()` method for automatic period resets
- Session end detection based on energy value drops
- New coordinator data fields: `energy_cumulative`, `last_session_energy`, period counters
- Reset timestamps tracked for each period (daily/weekly/monthly/yearly)
- All period sensors use `state_class: TOTAL_INCREASING` for proper HA statistics

### Documentation
- Updated ENTITIES.md with energy sensor details and examples
- Updated DATA_SCHEMAS.md with new cumulative tracking fields
- Updated CONSTANTS.md with new sensor constants
- Updated COORDINATOR.md with reset logic documentation
- Added comprehensive ENERGY_SENSORS.md guide with:
  - Detailed usage instructions for each sensor
  - Energy Dashboard setup guide
  - Example automations and Lovelace cards
  - Advanced use cases (solar optimization, dynamic pricing, load balancing)
  - Troubleshooting section
  - Migration guide

### Tests
- Added comprehensive test coverage for all new energy sensors
- Tests verify period calculations with and without active sessions
- Tests verify last_reset attribute formatting
- All existing tests continue to pass

[1.1.0]: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases/tag/v1.1.0

## [1.0.1] - 2024-12-07

### Added
- Release process documentation (RELEASES.md)
- Repository description and topics for better discoverability
- HACS validation workflow for continuous integration

### Fixed
- Manifest.json key ordering to pass Hassfest validation
- HACS.json now at repository root as required by HACS
- Repository metadata for HACS compliance

### Documentation
- Comprehensive guide for creating new releases
- Improved README with CI/CD badges
- Better project structure and organization

[1.0.1]: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases/tag/v1.0.1

## [1.0.0] - 2024-12-07

### Added
- Initial public release
- OCPP 2.0.1 protocol support for BMW-branded wallboxes
- 37 comprehensive sensors for monitoring
- Real-time power, energy, current, and voltage monitoring
- Per-phase measurements (L1, L2, L3) for 3-phase installations
- Smart charging controls (start/stop, current limiting)
- Binary sensors for charging and connection status
- Start/Stop charging buttons
- Current limit control (0-32A)
- Energy Dashboard integration
- WebSocket Secure (WSS) connection
- SSL/TLS certificate support
- HACS installation support
- Config flow for easy setup
- Comprehensive documentation
- Test suite with pytest
- English translations

### Features
- **Smart Start/Stop**: EVCC-style charging control without stuck transactions
- **Dynamic Current Limiting**: Adjust charging current in real-time
- **Transaction Management**: Proper handling of OCPP charging sessions
- **Connection Monitoring**: Heartbeat and status tracking
- **Meter Values**: Real-time and periodic energy measurements
- **Status Notifications**: Connector and charging state updates
- **Boot Notification**: Device info and firmware tracking

### Technical
- Acts as OCPP 2.0.1 Central System (server)
- Supports OCPP messages: BootNotification, StatusNotification, Heartbeat, TransactionEvent, NotifyReport
- Outgoing commands: RequestStartTransaction, RequestStopTransaction, SetChargingProfile, Reset
- Local-only operation (no cloud required)
- Async/await architecture for performance
- Proper error handling and logging

### Documentation
- Complete README with installation and usage
- Architecture documentation
- OCPP handler documentation
- Testing guide
- Troubleshooting guide
- Example automations for solar charging and dynamic limiting

[1.0.0]: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases/tag/v1.0.0
