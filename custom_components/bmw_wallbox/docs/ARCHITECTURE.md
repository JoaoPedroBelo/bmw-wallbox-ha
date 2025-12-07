# BMW Wallbox Integration - System Architecture

## Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            HOME ASSISTANT                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     BMW Wallbox Integration                          │    │
│  │                                                                      │    │
│  │  ┌──────────────┐    ┌─────────────────────────────────────────┐    │    │
│  │  │ Config Flow  │    │           Coordinator                    │    │    │
│  │  │ config_flow  │    │         coordinator.py                   │    │    │
│  │  │    .py       │    │                                          │    │    │
│  │  └──────┬───────┘    │  ┌────────────────────────────────────┐ │    │    │
│  │         │            │  │     BMWWallboxCoordinator           │ │    │    │
│  │         │ creates    │  │  - data: dict[str, Any]             │ │    │    │
│  │         ▼            │  │  - charge_point: WallboxChargePoint │ │    │    │
│  │  ┌──────────────┐    │  │  - current_transaction_id: str      │ │    │    │
│  │  │ Config Entry │────┼──│  - device_info: dict                │ │    │    │
│  │  └──────────────┘    │  │                                      │ │    │    │
│  │                      │  │  Methods:                            │ │    │    │
│  │                      │  │  - async_start_server()              │ │    │    │
│  │                      │  │  - async_start_charging()            │ │    │    │
│  │                      │  │  - async_pause_charging()            │ │    │    │
│  │                      │  │  - async_set_current_limit()         │ │    │    │
│  │                      │  └────────────────────────────────────┘ │    │    │
│  │                      │                    │                     │    │    │
│  │                      │                    │ contains            │    │    │
│  │                      │                    ▼                     │    │    │
│  │                      │  ┌────────────────────────────────────┐ │    │    │
│  │                      │  │     WallboxChargePoint              │ │    │    │
│  │                      │  │  (extends ocpp.v201.ChargePoint)    │ │    │    │
│  │                      │  │                                      │ │    │    │
│  │                      │  │  Handlers:                          │ │    │    │
│  │                      │  │  - @on("BootNotification")          │ │    │    │
│  │                      │  │  - @on("StatusNotification")        │ │    │    │
│  │                      │  │  - @on("Heartbeat")                 │ │    │    │
│  │                      │  │  - @on("TransactionEvent")          │ │    │    │
│  │                      │  │  - @on("NotifyReport")              │ │    │    │
│  │                      │  └────────────────────────────────────┘ │    │    │
│  │                      └──────────────────┬──────────────────────┘    │    │
│  │                                         │                           │    │
│  │         ┌───────────────────────────────┼───────────────────────┐   │    │
│  │         │                               │                       │   │    │
│  │         ▼                               ▼                       ▼   │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────┐  ┌────────┐  ┌──────┐│    │
│  │  │   Sensors   │  │Binary Sensor│  │ Buttons │  │ Number │  │Switch││    │
│  │  │ sensor.py   │  │binary_sensor│  │button.py│  │number  │  │switch││    │
│  │  │             │  │    .py      │  │         │  │  .py   │  │ .py  ││    │
│  │  │ 15 entities │  │ 2 entities  │  │2 entities│ │2 entity│  │1 ent ││    │
│  │  └─────────────┘  └─────────────┘  └─────────┘  └────────┘  └──────┘│    │
│  │                                                                      │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                         ▲                                     │
└─────────────────────────────────────────┼─────────────────────────────────────┘
                                          │
                                          │ WebSocket (wss://)
                                          │ OCPP 2.0.1
                                          │
                                    ┌─────┴─────┐
                                    │    BMW    │
                                    │  Wallbox  │
                                    │ (Client)  │
                                    └───────────┘
```

---

## Class Hierarchy

```
DataUpdateCoordinator (Home Assistant)
    └── BMWWallboxCoordinator
            │
            └── contains: WallboxChargePoint
                              │
                              └── extends: ocpp.v201.ChargePoint


CoordinatorEntity (Home Assistant)
    │
    ├── SensorEntity
    │       └── BMWWallboxSensorBase
    │               ├── BMWWallboxStatusSensor
    │               ├── BMWWallboxPowerSensor
    │               ├── BMWWallboxEnergyTotalSensor
    │               ├── BMWWallboxCurrentSensor
    │               ├── BMWWallboxVoltageSensor
    │               └── ... (15 total sensors)
    │
    ├── BinarySensorEntity
    │       └── BMWWallboxBinarySensorBase
    │               ├── BMWWallboxChargingBinarySensor
    │               └── BMWWallboxConnectedBinarySensor
    │
    ├── ButtonEntity
    │       └── BMWWallboxButtonBase
    │               ├── BMWWallboxStartButton
    │               └── BMWWallboxStopButton
    │
    ├── NumberEntity
    │       ├── BMWWallboxCurrentLimitNumber
    │       └── BMWWallboxLEDBrightnessNumber
    │
    └── SwitchEntity
            └── BMWWallboxChargingSwitch
```

---

## Data Flow

### 1. Incoming Data (Wallbox → Home Assistant)

```
┌──────────────┐     OCPP Message      ┌──────────────────────┐
│   Wallbox    │ ───────────────────►  │  WallboxChargePoint  │
│              │   TransactionEvent    │  on_transaction_event│
└──────────────┘                       └──────────┬───────────┘
                                                  │
                                                  │ Extract meter values
                                                  │ Update coordinator.data
                                                  ▼
                                       ┌──────────────────────┐
                                       │ BMWWallboxCoordinator│
                                       │      .data dict      │
                                       │                      │
                                       │ power: 7200.0        │
                                       │ current: 32.0        │
                                       │ voltage: 230.0       │
                                       │ charging_state: ...  │
                                       └──────────┬───────────┘
                                                  │
                                                  │ async_set_updated_data()
                                                  ▼
                               ┌──────────────────────────────────┐
                               │         All Entities             │
                               │  (automatically notified via     │
                               │   CoordinatorEntity pattern)     │
                               │                                  │
                               │  sensor.power.native_value       │
                               │    → coordinator.data["power"]   │
                               └──────────────────────────────────┘
```

### 2. Outgoing Commands (Home Assistant → Wallbox)

```
┌──────────────┐     User presses      ┌──────────────────────┐
│  HA Frontend │ ───────────────────►  │  BMWWallboxStartBtn  │
│              │   Start Charging      │   async_press()      │
└──────────────┘                       └──────────┬───────────┘
                                                  │
                                                  │ Calls coordinator method
                                                  ▼
                                       ┌──────────────────────┐
                                       │ BMWWallboxCoordinator│
                                       │ async_start_charging │
                                       └──────────┬───────────┘
                                                  │
                                                  │ Checks state, chooses action
                                                  ▼
                                       ┌──────────────────────┐
                                       │  WallboxChargePoint  │
                                       │      .call()         │
                                       └──────────┬───────────┘
                                                  │
                                                  │ OCPP Command
                                                  ▼
                                       ┌──────────────────────┐
                                       │      Wallbox         │
                                       │  Executes command    │
                                       └──────────────────────┘
```

---

## Charging State Machine

```
                              ┌─────────────────┐
                              │                 │
                              │      Idle       │◄──────────────────────┐
                              │   (No cable)    │                       │
                              │                 │                       │
                              └────────┬────────┘                       │
                                       │                                │
                                       │ Cable plugged in               │
                                       ▼                                │
                              ┌─────────────────┐                       │
                              │                 │                       │
                              │  EVConnected    │                       │
                              │  (Cable ready)  │                       │
                              │                 │                       │
                              └────────┬────────┘                       │
                                       │                                │
                                       │ RequestStartTransaction        │
                                       │ or Auto-start                  │
                                       ▼                                │
                              ┌─────────────────┐                       │
              SetChargingProfile(32A)  │                 │                       │
             ┌────────────────│    Charging     │───────────────────────┤
             │                │  (Power > 0W)   │  Cable unplugged      │
             │                │                 │                       │
             │                └────────┬────────┘                       │
             │                         │                                │
             │                         │ SetChargingProfile(0A)         │
             │                         │ or Car pauses                  │
             │                         ▼                                │
             │                ┌─────────────────┐                       │
             │                │                 │                       │
             └───────────────►│ SuspendedEVSE   │───────────────────────┘
                              │  (Paused by us) │  Cable unplugged
                              │  Power = 0W     │
                              │                 │
                              └─────────────────┘

                              ┌─────────────────┐
                              │                 │
                              │  SuspendedEV    │  (Car decided to pause)
                              │  (Paused by car)│  (Battery full, temp limit)
                              │                 │
                              └─────────────────┘
```

---

## OCPP Message Flow

### Normal Charging Session

```
Timeline    Wallbox                          Home Assistant
─────────────────────────────────────────────────────────────────────
   │
   │        ──── WebSocket Connect ────►
   │
   │        ──── BootNotification ─────►
   │        ◄─── BootNotificationResp ──     (stores device_info)
   │
   │        ──── StatusNotification ───►     connector_status = Available
   │        ◄─── StatusNotificationResp ─
   │
   │        ──── Heartbeat ────────────►     connected = True
   │        ◄─── HeartbeatResponse ─────
   │
   │        ... (Heartbeat every 10s) ...
   │
   │        [Cable plugged in]
   │
   │        ──── StatusNotification ───►     connector_status = Occupied
   │        ◄─── StatusNotificationResp ─
   │
   │        ──── TransactionEvent ─────►     event_type = Started
   │        ◄─── TransactionEventResp ──     transaction_id = "abc-123"
   │                                         charging_state = EVConnected
   │
   │        [Charging starts]
   │
   │        ──── TransactionEvent ─────►     event_type = Updated
   │        ◄─── TransactionEventResp ──     power = 7200W
   │                                         current = 32A
   │                                         energy_total = 1.5kWh
   │
   │        ... (TransactionEvent every 60s with meter values) ...
   │
   │        [User presses Stop]
   │
   │        ◄─── SetChargingProfile ────     limit = 0A (pause)
   │        ──── SetChargingProfileResp►     status = Accepted
   │
   │        ──── TransactionEvent ─────►     charging_state = SuspendedEVSE
   │        ◄─── TransactionEventResp ──     power = 0W
   │
   │        [User presses Start]
   │
   │        ◄─── SetChargingProfile ────     limit = 32A (resume)
   │        ──── SetChargingProfileResp►     status = Accepted
   │
   │        ──── TransactionEvent ─────►     charging_state = Charging
   │        ◄─── TransactionEventResp ──     power = 7200W
   │
   │        [Cable unplugged]
   │
   │        ──── TransactionEvent ─────►     event_type = Ended
   │        ◄─── TransactionEventResp ──     stopped_reason = EVDisconnected
   │
   │        ──── StatusNotification ───►     connector_status = Available
   │        ◄─── StatusNotificationResp ─
   │
   ▼
```

---

## Async Model

### WebSocket Server

```python
# coordinator.py - async_start_server()

# 1. Create SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain(cert_path, key_path)

# 2. Start WebSocket server (runs in background)
self.server = await websockets.serve(
    on_connect,           # Handler for new connections
    "0.0.0.0",            # Listen on all interfaces
    self.config["port"],  # Default: 9000
    subprotocols=["ocpp2.0.1"],
    ssl=ssl_context,
)

# 3. on_connect creates WallboxChargePoint and starts message loop
async def on_connect(websocket):
    self.charge_point = WallboxChargePoint(id, websocket, self)
    await self.charge_point.start()  # Blocks, processes messages
```

### Entity Updates

```python
# Entities extend CoordinatorEntity which handles automatic updates

class BMWWallboxPowerSensor(CoordinatorEntity, SensorEntity):
    @property
    def native_value(self) -> float | None:
        # Called automatically when coordinator.data updates
        return self.coordinator.data.get("power")

# In coordinator, after processing OCPP message:
self.data["power"] = new_value
self.async_set_updated_data(self.data)  # Triggers all entity updates
```

---

## File Dependencies

```
__init__.py
    ├── imports: const.py (DOMAIN)
    ├── imports: coordinator.py (BMWWallboxCoordinator)
    └── loads: sensor.py, binary_sensor.py, button.py, number.py, switch.py

coordinator.py
    ├── imports: const.py (DOMAIN, UPDATE_INTERVAL)
    ├── imports: ocpp library
    └── imports: websockets library

sensor.py
    ├── imports: const.py (DOMAIN)
    └── imports: coordinator.py (BMWWallboxCoordinator)

binary_sensor.py
    ├── imports: const.py (DOMAIN, BINARY_SENSOR_*)
    └── imports: coordinator.py (BMWWallboxCoordinator)

button.py
    ├── imports: const.py (DOMAIN, BUTTON_*)
    └── imports: coordinator.py (BMWWallboxCoordinator)

number.py
    ├── imports: const.py (DOMAIN, NUMBER_*)
    └── imports: coordinator.py (BMWWallboxCoordinator)

switch.py
    ├── imports: const.py (DOMAIN, SWITCH_*)
    └── imports: coordinator.py (BMWWallboxCoordinator)

config_flow.py
    └── imports: const.py (all CONF_*, DEFAULT_*, DOMAIN)
```
