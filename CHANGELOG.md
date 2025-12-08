# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

