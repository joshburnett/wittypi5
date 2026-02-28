# Change Log

## [Unreleased]

### Added

- Properties: firmware_id, firmware_version, missed_heartbeats, action_reason_startup, action_reason_shutdown (ActionReason enum), month, day, year
- ActionReason enum for decoded action reason (startup + shutdown nibbles)
- sync_rtc_with_local() method to set RTC from datetime.now()

- Project layout changed to src layout (src/wittypi5/)

- Initial Witty Pi 5 Python module
  - `wittypi5/registers.py`: `Register` enum with all I2C virtual register addresses (0-103)
  - `wittypi5/device.py`: `WittyPi5` class with:
    - `open()` / `close()` for I2C bus connection
    - `read_register(reg)` / `write_register(reg, value)` taking `Register` enum
    - Decoded value properties: `v_usb`, `v_in`, `v_out` (V), `i_out` (A); `temp_c`, `temp_f`; `hour`, `minute`, `second`, `date`, `time`, `datetime`
    - Config properties (`config_*`) for all configuration registers (17-54)
  - I2C via smbus2, default bus 1, address 0x51
