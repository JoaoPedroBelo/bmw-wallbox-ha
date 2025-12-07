# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

