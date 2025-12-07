# BMW Wallbox Integration - Testing Checklist

## Automated Tests

Run with: `pytest tests/`

- [ ] Config flow tests pass
- [ ] Sensor tests pass
- [ ] Binary sensor tests pass
- [ ] Button tests pass
- [ ] Number tests pass
- [ ] Switch tests pass
- [ ] Coordinator tests pass
- [ ] Integration setup tests pass
- [ ] All tests achieve >80% code coverage

## Manual Integration Tests (Real Wallbox Required)

### Installation
- [ ] Integration installs without errors
- [ ] Config flow UI appears correctly
- [ ] All fields have correct default values
- [ ] Validation works (invalid port, missing SSL files)
- [ ] Integration creates entry successfully

### Initial Connection
- [ ] OCPP server starts on correct port
- [ ] SSL certificates are loaded correctly
- [ ] Wallbox connects successfully
- [ ] BootNotification is received
- [ ] Device info is populated correctly
- [ ] All entities are created

### Sensor Tests
- [ ] Power sensor shows 0W when idle
- [ ] Power sensor shows correct value when charging (e.g., ~7000W)
- [ ] Energy sensor increases during charging
- [ ] Energy sensor value persists after charging stops
- [ ] Charging state shows correct text (Charging/SuspendedEV/Idle)
- [ ] Transaction ID appears when charging starts
- [ ] Transaction ID clears when charging stops
- [ ] Current sensor shows correct amperage
- [ ] Voltage sensor shows correct voltage (~230V)

### Binary Sensor Tests
- [ ] Charging binary sensor ON when charging
- [ ] Charging binary sensor OFF when not charging
- [ ] Connected binary sensor ON when OCPP connected
- [ ] Connected binary sensor OFF after 30s without heartbeat

### Control Tests

#### Start Button
- [ ] Button appears in UI
- [ ] Button press sends RequestStartTransaction
- [ ] Charging starts after button press
- [ ] Transaction ID is captured
- [ ] Power sensor updates
- [ ] Charging binary sensor turns ON

#### Stop Button  
- [ ] Button appears in UI
- [ ] Button press sends RequestStopTransaction
- [ ] Charging stops after button press
- [ ] Power drops to 0W
- [ ] Charging binary sensor turns OFF

#### Charging Switch
- [ ] Switch shows OFF when not charging
- [ ] Switch shows ON when charging
- [ ] Turning switch ON starts charging
- [ ] Turning switch OFF stops charging
- [ ] Switch state reflects actual charging state

#### Current Limit Slider
- [ ] Slider shows current value
- [ ] Slider range is 0-32A
- [ ] Setting to 0A stops/limits charging
- [ ] Setting to 16A limits power to ~3.7kW
- [ ] Setting to 30A allows ~7kW charging
- [ ] Changes are applied immediately
- [ ] SetChargingProfile command is sent

### Reliability Tests

#### Home Assistant Restart
- [ ] Stop HA while wallbox idle - restarts OK
- [ ] Stop HA while charging - charging continues
- [ ] After restart, state is restored correctly
- [ ] After restart, controls still work

#### Wallbox Restart
- [ ] Restart wallbox while HA running
- [ ] Wallbox reconnects automatically
- [ ] State is updated after reconnection
- [ ] Transaction ID is restored (if charging)

#### Network Issues
- [ ] Disconnect network cable
- [ ] Connected binary sensor shows OFF
- [ ] Reconnect network cable
- [ ] Wallbox reconnects automatically
- [ ] All sensors update

#### Rapid Commands
- [ ] Send start 3 times quickly - no crashes
- [ ] Send stop 3 times quickly - no crashes
- [ ] Alternate start/stop rapidly - works correctly
- [ ] Change current limit rapidly - works correctly

#### Long-Running Test
- [ ] Run for 24 hours - no memory leaks
- [ ] Run for 24 hours - no crashes
- [ ] Multiple charge sessions - all tracked correctly

### Error Handling Tests

#### No Transaction
- [ ] Stop button when no transaction - shows error gracefully
- [ ] Current limit without transaction - shows warning

#### Wallbox Disconnected
- [ ] All controls show appropriate error
- [ ] Sensors show "unavailable"
- [ ] No crashes or exceptions

#### Invalid Commands
- [ ] Wallbox rejects command - error is logged
- [ ] Wallbox times out - timeout is handled
- [ ] Invalid response - handled gracefully

### Energy Dashboard Integration
- [ ] Integration appears in energy configuration
- [ ] Energy sensor can be selected
- [ ] Energy tracking works over multiple sessions
- [ ] Statistics are generated correctly
- [ ] Historical data is preserved
- [ ] Dashboard shows correct energy usage

### Device Page Tests
- [ ] Device page shows wallbox info
- [ ] Manufacturer shown correctly (BMW)
- [ ] Model shown correctly
- [ ] Firmware version displayed
- [ ] Serial number displayed
- [ ] All entities listed
- [ ] Entities grouped under device

### Logs Tests
- [ ] Debug logs show OCPP messages
- [ ] Errors are logged appropriately
- [ ] No excessive logging in INFO level
- [ ] Performance is acceptable

## Performance Benchmarks

- [ ] Server starts in < 5 seconds
- [ ] Wallbox connects in < 10 seconds
- [ ] Commands execute in < 2 seconds
- [ ] Sensor updates happen within 1 second of change
- [ ] Memory usage stable over 24 hours

## Documentation Tests

- [ ] README is accurate
- [ ] Installation guide works
- [ ] Example automations work
- [ ] Troubleshooting steps are helpful

## Edge Cases

- [ ] Multiple start commands - handled
- [ ] Multiple stop commands - handled
- [ ] Start while already charging - handled
- [ ] Stop while not charging - handled
- [ ] Current limit out of range - validated
- [ ] Missing SSL certificates - error shown
- [ ] Invalid charge point ID - handled
- [ ] Port already in use - error shown

## Sign-Off

- [ ] All automated tests pass
- [ ] All critical manual tests pass
- [ ] Documentation is complete
- [ ] No known critical bugs
- [ ] Ready for production use

**Tested by:** _______________  
**Date:** _______________  
**Version:** _______________

