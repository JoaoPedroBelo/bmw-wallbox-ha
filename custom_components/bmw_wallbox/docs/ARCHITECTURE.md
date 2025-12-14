# BMW Wallbox Integration - System Architecture

## Component Overview

```mermaid
flowchart TB
    subgraph HA["HOME ASSISTANT"]
        subgraph Integration["BMW Wallbox Integration"]
            CF["Config Flow<br/>config_flow.py"]
            CE["Config Entry"]
            
            subgraph Coord["Coordinator (coordinator.py)"]
                BWC["BMWWallboxCoordinator<br/>- data: dict[str, Any]<br/>- charge_point: WallboxChargePoint<br/>- current_transaction_id: str<br/>- device_info: dict"]
                BWC_Methods["Methods:<br/>- async_start_server()<br/>- async_start_charging()<br/>- async_pause_charging()<br/>- async_set_current_limit()"]
                
                WCP["WallboxChargePoint<br/>(extends ocpp.v201.ChargePoint)<br/><br/>Handlers:<br/>- @on('BootNotification')<br/>- @on('StatusNotification')<br/>- @on('Heartbeat')<br/>- @on('TransactionEvent')<br/>- @on('NotifyReport')"]
            end
            
            subgraph Entities["Entity Platforms"]
                Sensors["Sensors<br/>sensor.py<br/>15 entities"]
                BinSensors["Binary Sensors<br/>binary_sensor.py<br/>2 entities"]
                Buttons["Buttons<br/>button.py<br/>2 entities"]
                Numbers["Numbers<br/>number.py<br/>2 entities"]
                Switches["Switches<br/>switch.py<br/>1 entity"]
            end
        end
    end
    
    Wallbox["BMW Wallbox<br/>(Client)"]
    
    CF -->|creates| CE
    CE --> BWC
    BWC --> BWC_Methods
    BWC -->|contains| WCP
    WCP <-->|"WebSocket (wss://)<br/>OCPP 2.0.1"| Wallbox
    
    Coord --> Sensors
    Coord --> BinSensors
    Coord --> Buttons
    Coord --> Numbers
    Coord --> Switches
```

---

## Class Hierarchy

```mermaid
classDiagram
    direction TB
    
    class DataUpdateCoordinator {
        <<Home Assistant>>
    }
    class BMWWallboxCoordinator {
        +data: dict
        +charge_point: WallboxChargePoint
    }
    class WallboxChargePoint {
        +id: str
        +coordinator: BMWWallboxCoordinator
    }
    class ChargePoint {
        <<ocpp.v201>>
    }
    
    DataUpdateCoordinator <|-- BMWWallboxCoordinator
    BMWWallboxCoordinator *-- WallboxChargePoint
    ChargePoint <|-- WallboxChargePoint
    
    class CoordinatorEntity {
        <<Home Assistant>>
    }
    class SensorEntity
    class BinarySensorEntity
    class ButtonEntity
    class NumberEntity
    class SwitchEntity
    
    class BMWWallboxSensorBase
    class BMWWallboxStatusSensor
    class BMWWallboxPowerSensor
    class BMWWallboxEnergyTotalSensor
    class BMWWallboxCurrentSensor
    class BMWWallboxVoltageSensor
    
    class BMWWallboxBinarySensorBase
    class BMWWallboxChargingBinarySensor
    class BMWWallboxConnectedBinarySensor
    
    class BMWWallboxButtonBase
    class BMWWallboxStartButton
    class BMWWallboxStopButton
    
    class BMWWallboxCurrentLimitNumber
    class BMWWallboxLEDBrightnessNumber
    
    class BMWWallboxChargingSwitch
    
    CoordinatorEntity <|-- SensorEntity
    CoordinatorEntity <|-- BinarySensorEntity
    CoordinatorEntity <|-- ButtonEntity
    CoordinatorEntity <|-- NumberEntity
    CoordinatorEntity <|-- SwitchEntity
    
    SensorEntity <|-- BMWWallboxSensorBase
    BMWWallboxSensorBase <|-- BMWWallboxStatusSensor
    BMWWallboxSensorBase <|-- BMWWallboxPowerSensor
    BMWWallboxSensorBase <|-- BMWWallboxEnergyTotalSensor
    BMWWallboxSensorBase <|-- BMWWallboxCurrentSensor
    BMWWallboxSensorBase <|-- BMWWallboxVoltageSensor
    
    BinarySensorEntity <|-- BMWWallboxBinarySensorBase
    BMWWallboxBinarySensorBase <|-- BMWWallboxChargingBinarySensor
    BMWWallboxBinarySensorBase <|-- BMWWallboxConnectedBinarySensor
    
    ButtonEntity <|-- BMWWallboxButtonBase
    BMWWallboxButtonBase <|-- BMWWallboxStartButton
    BMWWallboxButtonBase <|-- BMWWallboxStopButton
    
    NumberEntity <|-- BMWWallboxCurrentLimitNumber
    NumberEntity <|-- BMWWallboxLEDBrightnessNumber
    
    SwitchEntity <|-- BMWWallboxChargingSwitch
```

---

## Data Flow

### 1. Incoming Data (Wallbox → Home Assistant)

```mermaid
sequenceDiagram
    participant Wallbox
    participant WCP as WallboxChargePoint<br/>on_transaction_event
    participant Data as BMWWallboxCoordinator<br/>.data dict
    participant Entities as All Entities<br/>(CoordinatorEntity pattern)
    
    Wallbox->>WCP: OCPP TransactionEvent
    Note over WCP: Extract meter values
    WCP->>Data: Update coordinator.data
    Note over Data: power: 7200.0<br/>current: 32.0<br/>voltage: 230.0<br/>charging_state: ...
    Data->>Entities: async_set_updated_data()
    Note over Entities: Automatically notified<br/>sensor.power.native_value<br/>→ coordinator.data["power"]
```

### 2. Outgoing Commands (Home Assistant → Wallbox)

```mermaid
sequenceDiagram
    participant UI as HA Frontend
    participant Btn as BMWWallboxStartBtn<br/>async_press()
    participant Coord as BMWWallboxCoordinator<br/>async_start_charging
    participant WCP as WallboxChargePoint<br/>.call()
    participant Wallbox
    
    UI->>Btn: User presses Start Charging
    Btn->>Coord: Calls coordinator method
    Note over Coord: Checks state<br/>chooses action
    Coord->>WCP: OCPP Command
    WCP->>Wallbox: SetChargingProfile(32A)
    Wallbox-->>WCP: Response
```

---

## Charging State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle: Initial state
    
    Idle: No cable connected
    EVConnected: Cable ready
    Charging: Power > 0W
    SuspendedEVSE: Paused by us<br/>Power = 0W
    SuspendedEV: Paused by car<br/>(Battery full, temp limit)
    
    Idle --> EVConnected: Cable plugged in
    EVConnected --> Charging: RequestStartTransaction<br/>or Auto-start
    Charging --> SuspendedEVSE: SetChargingProfile(0A)<br/>or Car pauses
    SuspendedEVSE --> Charging: SetChargingProfile(32A)
    Charging --> Idle: Cable unplugged
    SuspendedEVSE --> Idle: Cable unplugged
    EVConnected --> Idle: Cable unplugged
    SuspendedEV --> Idle: Cable unplugged
    Charging --> SuspendedEV: Car decides to pause
    SuspendedEV --> Charging: Car resumes
```

---

## OCPP Message Flow

### Normal Charging Session

```mermaid
sequenceDiagram
    participant Wallbox
    participant HA as Home Assistant
    
    Note over Wallbox,HA: Connection Established
    Wallbox->>HA: WebSocket Connect
    
    Wallbox->>HA: BootNotification
    HA-->>Wallbox: BootNotificationResp
    Note right of HA: stores device_info
    
    Wallbox->>HA: StatusNotification
    HA-->>Wallbox: StatusNotificationResp
    Note right of HA: connector_status = Available
    
    Wallbox->>HA: Heartbeat
    HA-->>Wallbox: HeartbeatResponse
    Note right of HA: connected = True
    
    Note over Wallbox,HA: ... Heartbeat every 10s ...
    
    Note over Wallbox: Cable plugged in
    
    Wallbox->>HA: StatusNotification
    HA-->>Wallbox: StatusNotificationResp
    Note right of HA: connector_status = Occupied
    
    Wallbox->>HA: TransactionEvent (Started)
    HA-->>Wallbox: TransactionEventResp
    Note right of HA: transaction_id = "abc-123"<br/>charging_state = EVConnected
    
    Note over Wallbox: Charging starts
    
    Wallbox->>HA: TransactionEvent (Updated)
    HA-->>Wallbox: TransactionEventResp
    Note right of HA: power = 7200W<br/>current = 32A<br/>energy_total = 1.5kWh
    
    Note over Wallbox,HA: ... TransactionEvent every 60s with meter values ...
    
    Note over HA: User presses Stop
    
    HA->>Wallbox: SetChargingProfile (0A)
    Wallbox-->>HA: SetChargingProfileResp (Accepted)
    
    Wallbox->>HA: TransactionEvent
    HA-->>Wallbox: TransactionEventResp
    Note right of HA: charging_state = SuspendedEVSE<br/>power = 0W
    
    Note over HA: User presses Start
    
    HA->>Wallbox: SetChargingProfile (32A)
    Wallbox-->>HA: SetChargingProfileResp (Accepted)
    
    Wallbox->>HA: TransactionEvent
    HA-->>Wallbox: TransactionEventResp
    Note right of HA: charging_state = Charging<br/>power = 7200W
    
    Note over Wallbox: Cable unplugged
    
    Wallbox->>HA: TransactionEvent (Ended)
    HA-->>Wallbox: TransactionEventResp
    Note right of HA: stopped_reason = EVDisconnected
    
    Wallbox->>HA: StatusNotification
    HA-->>Wallbox: StatusNotificationResp
    Note right of HA: connector_status = Available
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

```mermaid
flowchart TB
    subgraph Core["Core Files"]
        init["__init__.py"]
        const["const.py"]
        coord["coordinator.py"]
    end
    
    subgraph Platforms["Entity Platforms"]
        sensor["sensor.py"]
        binary["binary_sensor.py"]
        button["button.py"]
        number["number.py"]
        switch["switch.py"]
    end
    
    subgraph Config["Configuration"]
        config["config_flow.py"]
    end
    
    subgraph External["External Libraries"]
        ocpp["ocpp library"]
        ws["websockets library"]
    end
    
    init -->|imports| const
    init -->|imports| coord
    init -->|loads| sensor
    init -->|loads| binary
    init -->|loads| button
    init -->|loads| number
    init -->|loads| switch
    
    coord -->|imports| const
    coord -->|imports| ocpp
    coord -->|imports| ws
    
    sensor -->|imports| const
    sensor -->|imports| coord
    
    binary -->|imports| const
    binary -->|imports| coord
    
    button -->|imports| const
    button -->|imports| coord
    
    number -->|imports| const
    number -->|imports| coord
    
    switch -->|imports| const
    switch -->|imports| coord
    
    config -->|imports| const
```
