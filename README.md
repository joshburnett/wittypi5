# Witty Pi 5 Python Driver

Python module for reading and writing Witty Pi 5 HAT+ registers via I2C on Raspberry Pi 5.

## Setup

1. Enable I2C on your Raspberry Pi (`raspi-config` → Interface Options → I2C).
2. Install from PyPI:

   ```bash
   uv pip install wittypi5
   ```

   Or with pip:

   ```bash
   pip install wittypi5
   ```

## Usage

```python
from wittypi5 import ActionReason, Register, WittyPi5

wp5 = WittyPi5()
wp5.open()
# Status readings
print(f"Firmware: {wp5.firmware_version}")
print(f"V_USB: {wp5.v_usb} V, V_IN: {wp5.v_in} V")
print(f"Last startup: {wp5.action_reason_startup.name}")
print(f"Last shutdown: {wp5.action_reason_shutdown.name}")

# RTC and temperature
print(f"RTC: {wp5.datetime}")
print(f"Temperature: {wp5.temp_c}°C ({wp5.temp_f}°F)")

# Sync RTC with system time
wp5.sync_rtc_with_local()

# Raw register access
state = wp5.read_register(Register.RASPBERRY_PI_STATE)

# Config (read/write)
wp5.config_led_on_time = 100  # LED on for 100 ms
wp5.close()


# Or, with context manager
with WittyPi5() as wp5:
    # Status readings
    print(f"Firmware: {wp5.firmware_version}")
    print(f"V_USB: {wp5.v_usb} V, V_IN: {wp5.v_in} V")
    print(f"Last startup: {wp5.action_reason_startup.name}")
    print(f"Last shutdown: {wp5.action_reason_shutdown.name}")

    # RTC and temperature
    print(f"RTC: {wp5.datetime}")
    print(f"Temperature: {wp5.temp_c}°C ({wp5.temp_f}°F)")

    # Sync RTC with system time
    wp5.sync_rtc_with_local()

    # Raw register access
    state = wp5.read_register(Register.RASPBERRY_PI_STATE)

    # Config (read/write)
    wp5.config_led_on_time = 100  # LED on for 100 ms
```

## Methods

| Method | Description |
|--------|-------------|
| `open()` | Open I2C connection |
| `close()` | Close I2C connection |
| `read_register(reg)` | Read byte from register |
| `write_register(reg, value)` | Write byte to register |
| `sync_rtc_with_local()` | Set RTC from `datetime.now()` |

## Custom I2C Bus or Address

```python
wp5 = WittyPi5(i2c_bus=1, i2c_address=0x51)
wp5.open()
# ...
wp5.close()
```

## Properties

### Status

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `firmware_id` | int | Read only | Firmware ID |
| `firmware_version` | str | Read only | Firmware version (e.g. `"1.02"`) |
| `missed_heartbeats` | int | Read only | Number of missed heartbeats |
| `action_reason_startup` | ActionReason | Read only | Latest startup action reason |
| `action_reason_shutdown` | ActionReason | Read only | Latest shutdown action reason |
| `v_usb` | float | Read only | V_USB voltage (V) |
| `v_in` | float | Read only | V_IN voltage (V) |
| `v_out` | float | Read only | V_OUT voltage (V) |
| `i_out` | float | Read only | I_OUT current (A) |

### RTC and Temperature

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `hour` | int | Read only | RTC hour (0-23) |
| `minute` | int | Read only | RTC minute (0-59) |
| `second` | int | Read only | RTC second (0-59) |
| `day` | int | Read only | RTC day of month (1-31) |
| `weekday` | int | Read only | RTC day of week (0=Mon, 6=Sun) |
| `month` | int | Read only | RTC month (1-12) |
| `year` | int | Read only | RTC year (full year) |
| `date` | datetime.date | Read only | RTC date |
| `time` | datetime.time | Read only | RTC time |
| `datetime` | datetime.datetime | Read only | RTC date and time |
| `temp_c` | float | Read only | Temperature (°C) |
| `temp_f` | float | Read only | Temperature (°F) |

### Config

| Property | Type | Access | Description |
|----------|------|--------|-------------|
| `config_i2c_address` | int | R/W | I2C slave address |
| `config_power_on_delay` | int | R/W | Delay before turning on Pi in seconds (0=immediate, 255=stay off) |
| `config_shutdown_delay` | int | R/W | Delay between Pi shutdown and power cut (seconds) |
| `config_pulse_interval` | int | R/W | Pulse interval for LED and dummy load (seconds) |
| `config_led_on_time` | int | R/W | White LED on time in ms (0=no blink) |
| `config_dummy_load_time` | int | R/W | Dummy load time in ms (0=off) |
| `config_low_voltage_threshold` | int | R/W | Low voltage threshold (×10 mV), 0=disabled |
| `config_recovery_voltage_threshold` | int | R/W | Recovery voltage threshold (×10 mV), 0=disabled |
| `config_power_source_priority` | int | R/W | 0=VUSB first, 1=VIN first |
| `config_v_usb_adjustment` | int | R/W | Adjustment for VUSB (×100), -128 to 127 |
| `config_v_in_adjustment` | int | R/W | Adjustment for VIN (×100), -128 to 127 |
| `config_v_out_adjustment` | int | R/W | Adjustment for VOUT (×100), -128 to 127 |
| `config_i_out_adjustment` | int | R/W | Adjustment for IOUT (×1000), -128 to 127 |
| `config_watchdog_heartbeat_limit` | int | R/W | Missed heartbeats before power cycle (0=disabled) |
| `config_log_to_file_enabled` | bool | R/W | Whether to write log to file |
| `config_startup_alarm_second` | int | R/W | Startup alarm second (0-59) |
| `config_startup_alarm_minute` | int | R/W | Startup alarm minute (0-59) |
| `config_startup_alarm_hour` | int | R/W | Startup alarm hour (0-23) |
| `config_startup_alarm_day` | int | R/W | Startup alarm day (day-of-week 1-7 or date 1-31) |
| `config_shutdown_alarm_second` | int | R/W | Shutdown alarm second (0-59) |
| `config_shutdown_alarm_minute` | int | R/W | Shutdown alarm minute (0-59) |
| `config_shutdown_alarm_hour` | int | R/W | Shutdown alarm hour (0-23) |
| `config_shutdown_alarm_day` | int | R/W | Shutdown alarm day (day-of-week 1-7 or date 1-31) |
| `config_factory_reset_enabled` | bool | R/W | Allow BOOTSEL + button for factory reset |
| `config_below_temp_action` | int | R/W | Action for below temp: 0=nothing, 1=startup, 2=shutdown |
| `config_below_temp_threshold` | int | R/W | Below temperature threshold (°C) |
| `config_over_temp_action` | int | R/W | Action for over temp: 0=nothing, 1=startup, 2=shutdown |
| `config_over_temp_threshold` | int | R/W | Over temperature threshold (°C) |
| `config_dst_mode_and_offset` | int | R/W | DST mode (bit7) and offset in minutes (bits 6-0), 0=disable |
| `config_dst_applied` | int | R/W | Whether DST has been applied |
| `config_system_clock_mhz` | int | R/W | System clock for RP2350 (MHz) |
