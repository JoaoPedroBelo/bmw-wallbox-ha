# BMW Wallbox (Delta Electronics) — Full Capability Report

Results from a full OCPP 2.0.1 `GetBaseReport(FullInventory)` dump performed on 2026-04-11.

**Charge Point ID:** `DE*BMW*EXXXXXXXXXXXXXXXXX`
**Firmware:** `01.20.06.71`
**Connection:** WiFi, OCPP 2.0.1 over WSS, Security Profile 2

---

## Measurands Available

The wallbox only supports **4 measurands** via `SampledDataCtrlr`:

| Measurand | Supported |
|---|---|
| `Current.Import` | Yes |
| `Energy.Active.Import.Register` | Yes |
| `Power.Active.Import` | Yes |
| `Voltage` | Yes |
| `SoC` | **No** |
| `Frequency` | **No** |
| `Temperature` | **No** |
| `Power.Factor` | **No** |
| `Power.Active.Export` | **No** |
| `Power.Reactive.*` | **No** |
| `Energy.Active.Export.*` | **No** |
| `Energy.Reactive.*` | **No** |
| `Current.Export` | **No** |
| `Current.Offered` | **No** |

All other measurands defined in OCPP 2.0.1 `MeasurandEnumType` are not available on this hardware.

## ISO 15118 Support

Minimal. The `ISO15118Ctrlr` component exists but only exposes one variable:

| Variable | Status | Value |
|---|---|---|
| `CentralContractValidationAllowed` | Accepted | `false` |
| `PnCEnabled` | UnknownVariable | — |
| `V2GCertificateInstallationEnabled` | UnknownVariable | — |
| `ContractValidationOffline` | UnknownVariable | — |
| `ContractCertificateInstallationEnabled` | UnknownVariable | — |
| `RequestMeteringReceipt` | UnknownVariable | — |
| `ISO15118EvseId` | UnknownVariable | — |
| `CountryName` | UnknownVariable | — |
| `OrganizationName` | UnknownVariable | — |
| `MaxScheduleTuples` | UnknownVariable | — |

**Conclusion:** No Plug & Charge, no ISO 15118 vehicle communication. The wallbox cannot receive vehicle data (brand, model, battery capacity, SoC) from the car. AC charging uses basic IEC 61851 pilot signal only.

### Why Public Chargers Show Battery %

Public chargers that display SoC typically use:
1. **DC (CCS/CHAdeMO)** — mandatory PLC communication where the car sends battery data
2. **Backend/app** — the user's account has the car registered (brand, model, license plate)
3. **ISO 15118 Plug & Charge** — certificate exchange identifies the contract, not the car itself

This BMW Wallbox (AC, no PnC) has no mechanism to receive car data via the cable. For vehicle info (SoC, model, battery), use the **BMW Connected Drive** integration or similar cloud APIs.

## Full Inventory

### ChargingStation

| Variable | Value | Mutability |
|---|---|---|
| Available | `true` | ReadOnly |
| AvailabilityState | `Occupied` | ReadOnly |
| SupplyPhases | `1` | ReadOnly |
| Power | `6584 W` (max 7360 W) | ReadOnly |
| ACCurrent | `30 A` (max 32 A) | ReadOnly |
| ACVoltage | `216 V` (max 230 V) | ReadOnly |
| FirmwareVersion | `01.20.06.71` | ReadOnly |
| GridType | `TN` (options: TN, TT, IT) | ReadOnly |
| GMIstatus | `true` | ReadOnly |
| MaxCurrent | `32 A` | ReadOnly |
| Country | `PT` | ReadWrite |
| InstallationComplete | `true` | ReadOnly |

### EVSE (id=1)

| Variable | Value | Mutability |
|---|---|---|
| Available | `true` | ReadOnly |
| AvailabilityState | `Occupied` | ReadOnly |
| SupplyPhases | `1` | ReadOnly |
| Power | `6548 W` (max 7360 W) | ReadOnly |
| ACVoltage | `215 V` (max 230 V) | ReadWrite |
| ACCurrent | `30 A` (max 32 A) | ReadWrite |

### Connector (EVSE 1, Connector 1)

| Variable | Value | Mutability |
|---|---|---|
| Available | `true` | ReadOnly |
| AvailabilityState | `Occupied` | ReadOnly |

### AuthCtrlr

| Variable | Value | Mutability |
|---|---|---|
| Enabled | `false` | ReadWrite |
| OfflineTxForUnknownIdEnabled | `false` | ReadWrite |
| AuthorizeRemoteStart | `false` | ReadWrite |
| LocalAuthorizeOffline | `true` | ReadWrite |
| LocalPreAuthorize | `false` | ReadWrite |

### AuthCtrlr (MBA instance)

| Variable | Value | Mutability |
|---|---|---|
| Enabled | `true` | ReadWrite |

### LocalAuthListCtrlr

| Variable | Value | Mutability |
|---|---|---|
| Enabled | `false` | ReadWrite |
| Entries | `0` (max 32) | ReadOnly |
| ItemsPerMessage | `8` | ReadOnly |
| BytesPerMessage | `2048` | ReadOnly |
| Storage | `8192` | ReadOnly |
| SetupCardIdToken | `(redacted)` | ReadWrite |
| ListContent | `(redacted)` | ReadWrite |

### TxCtrlr

| Variable | Value | Mutability |
|---|---|---|
| EVConnectionTimeOut | `60 s` | ReadWrite |
| StopTxOnEVSideDisconnect | `true` | ReadOnly |
| TxBeforeAcceptedEnabled | `true` | ReadWrite |
| TxStartPoint | `EVConnected,Authorized,EnergyTransfer` | ReadWrite |
| TxStopPoint | `PowerPathClosed` | ReadWrite |
| StopTxOnInvalidId | `true` | ReadWrite |

### SampledDataCtrlr

| Variable | Value | Mutability |
|---|---|---|
| TxEndedMeasurands | `Energy.Active.Import.Register` | ReadWrite |
| TxEndedInterval | `0 s` | ReadWrite |
| TxStartedMeasurands | `Energy.Active.Import.Register` | ReadWrite |
| TxUpdatedMeasurands | `Energy.Active.Import.Register` | ReadWrite |
| TxUpdatedInterval | `0 s` | ReadWrite |

**Available measurands:** `Current.Import, Energy.Active.Import.Register, Power.Active.Import, Voltage`

### AlignedDataCtrlr

| Variable | Value | Mutability |
|---|---|---|
| Enabled | `false` | ReadWrite |
| Available | `false` | ReadOnly |
| SendDuringIdle | `true` | ReadWrite |
| SignReadings | `false` | ReadWrite |

### SmartChargingCtrlr

| Variable | Value | Mutability |
|---|---|---|
| Enabled | `true` | ReadWrite |
| ACPhaseSwitchingSupported | `false` | ReadOnly |
| ProfileStackLevel | `5` | ReadOnly |
| RateUnit | `A, W` | ReadOnly |
| PeriodsPerSchedule | `33` | ReadOnly |
| ExternalControlSignalsEnabled | `false` | ReadOnly |
| NotifyChargingLimitWithSchedules | `false` | ReadWrite |
| Phases3to1 | `false` | ReadOnly |
| Entries (ChargingProfiles) | `15` | ReadOnly |
| LimitChangeSignificance | `0.0` | ReadWrite |

### LocalSmartChargingCtrlr

| Instance | Variable | Value | Mutability |
|---|---|---|---|
| — | ChargingPowerLimited | `false` | ReadWrite |
| DLC | MinTimeOff | `1 min` (1-30) | ReadWrite |
| DLC | CurrentSafeLLM | `0 A` (0-10) | ReadWrite |
| DLC | CurrentSafeSLM | `0 A` (0-20) | ReadWrite |
| DLC | Enabled | `false` | ReadWrite |
| PV | ChargingMode | `direct` (direct/manual/strict) | ReadWrite |
| PV | MinimumCurrent | `6 A` (6-32) | ReadWrite |
| PV | Enabled | `false` | ReadWrite |
| PeakShifting | MinTimeOff | `1 min` (1-30) | ReadWrite |
| PeakShifting | Enabled | `true` | ReadWrite |
| ScheduledCharging | Enabled | `true` | ReadWrite |

### ExternalMeteringCtrlr (SmartMeter1)

| Variable | Value | Mutability |
|---|---|---|
| ModelName | `Janitza B23 312-10J` | ReadOnly |
| BaudRate | `19200` | ReadOnly |
| ParityCheck | `none` | ReadOnly |
| Address | `1` (Modbus) | ReadOnly |
| PhaseOrder | `L1SM-L1WB` | ReadOnly |
| Enabled | `false` | ReadOnly |
| PowerActive (Sum) | `0 W` | ReadOnly |
| ActiveEnergy (Total) | `0 Wh` | ReadOnly |
| SamplingRate | `1 s` | ReadWrite |
| NumSampleAvg | `1 s` | ReadWrite |

### MeteringCtrlr (Aggregation)

5-minute aggregated power data:

| Variable | Value |
|---|---|
| Period Length | `300 s` |
| Period Start | `2026-04-11T15:24:00Z` |
| Period End | `2026-04-11T15:29:00Z` |
| HouseholdPowerActive Avg | `0 W` |
| HouseholdPowerActive Min | `0 W` |
| HouseholdPowerActive Max | `0 W` |
| ChargerPowerActive Avg | `6506.5 W` |
| ChargerPowerActive Min | `6436.1 W` |
| ChargerPowerActive Max | `6586.5 W` |

### SecurityCtrlr

| Variable | Value | Mutability |
|---|---|---|
| BasicAuthPassword | *(WriteOnly)* | WriteOnly |
| SecurityProfile | `2` | ReadOnly |
| AdditionalRootCertificateCheck | `false` | ReadOnly |

### OCPPCommCtrlr

| Variable | Value | Mutability |
|---|---|---|
| MessageTimeout | `30 s` | ReadOnly |
| HeartbeatInterval | `10 s` | ReadWrite |
| NetworkConfigurationPriority | `0` | ReadWrite |
| NetworkProfileConnectionAttempts | `3` | ReadWrite |
| OfflineThreshold | `3600 s` | ReadWrite |
| QueueAllMessages | `true` | ReadWrite |
| MessageAttempts (TransactionEvent) | `3` | ReadWrite |
| MessageAttemptInterval (TransactionEvent) | `60 s` | ReadWrite |
| WebSocketPingInterval | `300 s` | ReadWrite |
| RetryBackOffRepeatTimes | `3` | ReadWrite |
| RetryBackOffRandomRange | `5 s` | ReadWrite |
| RetryBackOffWaitMinimum | `15 s` | ReadWrite |

### NetworkingCtrlr

| Variable | Value |
|---|---|
| ActiveConnection | `wifi` |
| LAN configured | `false` |
| WiFi configured | `true` |
| Mobile configured | `false` |

### Other

| Component | Variable | Value |
|---|---|---|
| MainCircuitBreaker | MaxCurrent | `100 A` |
| StatusLED | brightness | `30` |
| ClockCtrlr | TimeAdjustmentReportingThreshold | `20` |
| RandomDelayCtrlr | Min | `0 s` |
| RandomDelayCtrlr | Max | `0 s` |

### TriggerMessage Support

| Message | Status |
|---|---|
| BootNotification | **Rejected** |
| MeterValues | Accepted |
| StatusNotification | **Rejected** |
| TransactionEvent | Accepted |

## What Cannot Be Done

- **Get vehicle SoC** — not in measurands, no ISO 15118 communication
- **Get vehicle brand/model/battery** — no mechanism in OCPP or ISO 15118 on this hardware
- **Get frequency, temperature, power factor** — not supported by the meter
- **Phase switching** — ACPhaseSwitchingSupported = false (single phase only)
- **Trigger BootNotification/StatusNotification** — wallbox rejects these triggers
