# BMW Wallbox Integration - Energy Sensors Guide

## Overview

The integration provides 6 energy sensors for comprehensive tracking and monitoring:

| Sensor | Unit | Reset Behavior | Primary Use |
|--------|------|---------------|-------------|
| **Energy Total** | kWh | Never (cumulative) | Home Assistant Energy Dashboard |
| **Energy Session** | Wh | Per charging session | Current charge monitoring |
| **Energy Daily** | kWh | Midnight | Daily consumption patterns |
| **Energy Weekly** | kWh | Monday midnight | Weekly trends |
| **Energy Monthly** | kWh | 1st of month | Billing cycles |
| **Energy Yearly** | kWh | January 1st | Annual tracking |

---

## Energy Total Sensor

### Purpose

**Main sensor for Home Assistant Energy Dashboard** - tracks lifetime cumulative energy consumption.

### Technical Details

- **Entity ID:** `sensor.bmw_wallbox_energy_total`
- **Device Class:** `energy`
- **State Class:** `total_increasing`
- **Unit:** kWh
- **Precision:** 2 decimal places

### How It Works

1. **Cumulative Tracking**: Accumulates energy across ALL charging sessions
2. **Session Detection**: Monitors for energy drops > 0.1 kWh
3. **When Session Ends**: Adds last session's final value to cumulative total
4. **Calculation**: `energy_total = energy_cumulative + current_session_energy`

### Why This Matters

The wallbox's OCPP energy register (`Energy.Active.Import.Register`) resets to 0 at each charging session. This sensor solves that problem by maintaining a true cumulative total.

**Before Fix (Old Behavior):**
```
Session 1: 0 → 25 kWh → ends
Session 2: 0 → 15 kWh (total lost: 25 kWh!)
```

**After Fix (Current Behavior):**
```
Session 1: 0 → 25 kWh → ends → cumulative = 25 kWh
Session 2: 0 → 15 kWh → total shows 40 kWh ✓
```

### Energy Dashboard Setup

1. Go to **Settings** → **Dashboards** → **Energy**
2. Click **Add Consumption**
3. Select `sensor.bmw_wallbox_energy_total`
4. Done! Energy will now be tracked correctly

### Example Lovelace Card

```yaml
type: energy-date-selection
```

Or detailed stats:

```yaml
type: statistics-graph
entities:
  - sensor.bmw_wallbox_energy_total
chart_type: line
period: day
stat_types:
  - change
```

---

## Energy Session Sensor

### Purpose

Track energy consumed in the **current charging session only**.

### Technical Details

- **Entity ID:** `sensor.bmw_wallbox_energy_session`
- **Device Class:** `energy`
- **State Class:** `total_increasing`
- **Unit:** Wh (not kWh, for precision)
- **Precision:** 0 decimal places

### Behavior

- Starts at 0 when charging begins
- Increases throughout the session
- Resets to 0 when a new session starts
- Useful for "how much did this charge cost?" calculations

### Example Automation

```yaml
automation:
  - alias: "Notify When Charge Complete"
    trigger:
      - platform: state
        entity_id: sensor.bmw_wallbox_state
        from: "Charging"
        to: "Ready"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Charging complete! 
            Energy used: {{ states('sensor.bmw_wallbox_energy_session') }} Wh
            Cost: €{{ (states('sensor.bmw_wallbox_energy_session') | float / 1000 * 0.25) | round(2) }}
```

---

## Period-Based Energy Sensors

### Energy Daily

**Resets:** Every day at midnight

**Use Cases:**
- Track daily consumption patterns
- Compare weekday vs weekend usage
- Monitor "did I charge today?"
- Daily cost calculations

**Example Dashboard:**

```yaml
type: custom:mini-graph-card
entities:
  - entity: sensor.bmw_wallbox_energy_daily
    name: Today
hours_to_show: 24
line_width: 2
points_per_hour: 4
```

**Automation Example:**

```yaml
automation:
  - alias: "Daily Energy Report"
    trigger:
      - platform: time
        at: "23:55:00"
    action:
      - service: notify.mobile_app
        data:
          message: >
            Today's charging: {{ states('sensor.bmw_wallbox_energy_daily') }} kWh
            Cost: €{{ (states('sensor.bmw_wallbox_energy_daily') | float * 0.25) | round(2) }}
```

---

### Energy Weekly

**Resets:** Every Monday at midnight

**Use Cases:**
- Track weekly consumption trends
- Work week vs weekend comparison
- Weekly budget monitoring
- Compare week-over-week usage

**Example Template Sensor:**

```yaml
template:
  - sensor:
      - name: "Wallbox Weekly Cost"
        unit_of_measurement: "EUR"
        state: >
          {{ (states('sensor.bmw_wallbox_energy_weekly') | float * 0.25) | round(2) }}
```

**History Stats:**

```yaml
sensor:
  - platform: history_stats
    name: "Wallbox Charging Days This Week"
    entity_id: binary_sensor.bmw_wallbox_charging
    state: "on"
    type: count
    start: >
      {{ as_timestamp(now()) - (now().weekday() * 86400) }}
    end: "{{ now() }}"
```

---

### Energy Monthly

**Resets:** 1st of every month at midnight

**Use Cases:**
- Monthly billing calculations
- Track against monthly budgets
- Electricity bill verification
- Month-over-month comparison

**Example Dashboard Card:**

```yaml
type: entities
entities:
  - entity: sensor.bmw_wallbox_energy_monthly
    name: This Month
    icon: mdi:calendar-month
  - type: attribute
    entity: sensor.bmw_wallbox_energy_monthly
    attribute: last_reset
    name: Since
  - type: custom:bar-card
    entity: sensor.bmw_wallbox_energy_monthly
    max: 500
    positions:
      value: inside
    unit_of_measurement: "kWh"
```

**Cost Tracking:**

```yaml
template:
  - sensor:
      - name: "Wallbox Monthly Cost"
        unit_of_measurement: "EUR"
        state: >
          {{ (states('sensor.bmw_wallbox_energy_monthly') | float * 0.25) | round(2) }}
        attributes:
          budget: 125
          remaining: >
            {{ (125 - (states('sensor.bmw_wallbox_energy_monthly') | float * 0.25)) | round(2) }}
```

---

### Energy Yearly

**Resets:** January 1st at midnight

**Use Cases:**
- Annual consumption tracking
- Year-over-year comparison
- Carbon footprint calculations
- Long-term trend analysis

**Example Carbon Footprint:**

```yaml
template:
  - sensor:
      - name: "Wallbox CO2 Saved Yearly"
        unit_of_measurement: "kg"
        icon: mdi:leaf
        state: >
          {# Assume 150g CO2/km for gas car, 20 kWh/100km for EV #}
          {% set energy_kwh = states('sensor.bmw_wallbox_energy_yearly') | float %}
          {% set km_driven = energy_kwh / 0.20 %}
          {% set co2_saved = km_driven * 0.150 %}
          {{ co2_saved | round(0) }}
```

---

## Sensor Attributes

All period-based sensors include a `last_reset` attribute:

```yaml
sensor.bmw_wallbox_energy_daily:
  state: 15.5
  attributes:
    last_reset: "2025-12-08T00:00:00"
    unit_of_measurement: "kWh"
    device_class: "energy"
    state_class: "total_increasing"
    friendly_name: "Energy Daily"
    icon: "mdi:calendar-today"
```

**Accessing in Templates:**

```yaml
{{ state_attr('sensor.bmw_wallbox_energy_daily', 'last_reset') }}
```

---

## Advanced Use Cases

### Solar Charging Optimization

Track how much solar energy is used for charging:

```yaml
template:
  - sensor:
      - name: "Wallbox Solar Percentage Today"
        unit_of_measurement: "%"
        state: >
          {% set wallbox = states('sensor.bmw_wallbox_energy_daily') | float %}
          {% set solar = states('sensor.solar_production_daily') | float %}
          {% if wallbox > 0 %}
            {{ (min(solar, wallbox) / wallbox * 100) | round(1) }}
          {% else %}
            0
          {% endif %}
```

### Dynamic Pricing Integration

Calculate actual cost based on time-of-use pricing:

```yaml
automation:
  - alias: "Calculate Daily Charging Cost"
    trigger:
      - platform: time
        at: "23:59:00"
    action:
      - service: input_number.set_value
        target:
          entity_id: input_number.daily_charging_cost
        data:
          value: >
            {% set energy = states('sensor.bmw_wallbox_energy_daily') | float %}
            {% set peak_hours = states('sensor.charging_peak_hours_today') | float %}
            {% set off_peak_hours = energy - peak_hours %}
            {{ (peak_hours * 0.35 + off_peak_hours * 0.15) | round(2) }}
```

### Load Balancing Statistics

```yaml
sensor:
  - platform: statistics
    name: "Wallbox Average Daily Energy"
    entity_id: sensor.bmw_wallbox_energy_daily
    state_characteristic: mean
    sampling_size: 30
    max_age:
      days: 30
```

### Budget Alerts

```yaml
automation:
  - alias: "Monthly Energy Budget Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.bmw_wallbox_energy_monthly
        above: 400  # kWh
    condition:
      - condition: template
        value_template: >
          {{ now().day < 28 }}  # Not end of month yet
    action:
      - service: notify.mobile_app
        data:
          message: >
            ⚠️ Monthly charging budget exceeded!
            Used: {{ states('sensor.bmw_wallbox_energy_monthly') }} kWh
            Days remaining: {{ (now().replace(month=now().month+1, day=1) - now()).days }}
```

---

## Troubleshooting

### Energy Total Not Increasing

**Symptoms:** Energy Total stays at 0 or doesn't increase

**Causes:**
1. No charging sessions completed yet
2. Wallbox not sending energy measurements

**Solution:**
```bash
# Check coordinator data
# In Home Assistant Developer Tools > States
# Look for sensor.bmw_wallbox_energy_total
# Check attributes for last_session_energy and energy_cumulative
```

### Period Sensors Not Resetting

**Symptoms:** Daily/weekly/monthly sensors don't reset at expected time

**Causes:**
1. No charging activity after reset time
2. Home Assistant restarted during reset window

**Solution:**
- Reset logic runs on every TransactionEvent
- Charge the car at least once after the reset time
- Check logs for "energy counter reset" messages

### Session Detection Issues

**Symptoms:** Energy jumps unexpectedly or sessions not detected

**Causes:**
1. Energy values fluctuating around detection threshold
2. Wallbox sending unusual energy patterns

**Solution:**
- Detection threshold is 0.1 kWh to avoid false positives
- Check coordinator logs for "New session detected" messages
- Monitor `sensor.bmw_wallbox_energy_session` for drops

---

## Technical Implementation

### Session End Detection Logic

```python
# In coordinator.py on_transaction_event()
last_session = coordinator.data.get("last_session_energy", 0.0)
current_session = session_energy_kwh

if current_session < last_session - 0.1:  # Energy dropped
    # New session detected!
    coordinator.data["energy_cumulative"] += last_session
    coordinator.data["energy_daily"] += last_session
    coordinator.data["energy_weekly"] += last_session
    coordinator.data["energy_monthly"] += last_session
    coordinator.data["energy_yearly"] += last_session
```

### Reset Logic

```python
# In coordinator.py _check_and_reset_period_counters()
now = datetime.now()

# Daily reset
if now.date() > last_reset_daily.date():
    coordinator.data["energy_daily"] = 0.0
    coordinator.data["last_reset_daily"] = now
```

### Sensor Value Calculation

```python
# In sensor.py period sensor classes
@property
def native_value(self) -> float | None:
    # Base accumulated from completed sessions
    base = self.coordinator.data.get("energy_daily", 0.0)
    # Plus current ongoing session
    current = self.coordinator.data.get("last_session_energy", 0.0)
    return base + current
```

---

## Migration from Previous Versions

If you were using the integration before these sensors were added:

1. **Energy Total** will start from 0
2. **Period sensors** will start tracking from first use
3. **Historical data** is not back-filled
4. **Energy Dashboard** will show data from first connection

To preserve historical data:
```yaml
# Use utility_meter to track periods yourself
utility_meter:
  wallbox_daily:
    source: sensor.bmw_wallbox_energy_total
    cycle: daily
```

---

## Best Practices

1. **Always use Energy Total for Energy Dashboard** - it's the only one that never resets
2. **Monitor session sensor** during charging to see real-time progress
3. **Use period sensors for budgets and alerts** - they reset automatically
4. **Check last_reset attribute** to understand when period counters were reset
5. **Create template sensors for costs** - multiply by your electricity rate
6. **Use statistics platform** for long-term trends and averages
7. **Set up alerts early** to catch unusual consumption patterns

---

## Related Documentation

- [ENTITIES.md](ENTITIES.md) - Complete entity reference
- [DATA_SCHEMAS.md](DATA_SCHEMAS.md) - Data structure details
- [COORDINATOR.md](COORDINATOR.md) - Coordinator API reference
- [Home Assistant Energy Dashboard](https://www.home-assistant.io/docs/energy/)


