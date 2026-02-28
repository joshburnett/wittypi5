"""Witty Pi 5 device driver for Raspberry Pi 5.

Communicates via I2C (SDA/SCL pins per HAT+ spec).
"""

from datetime import date, datetime, time
from enum import IntEnum

from wittypi5.registers import Register


class ActionReason(IntEnum):
    """Latest action reason (startup or shutdown).

    Higher 4 bits of register 14 = startup reason, lower 4 bits = shutdown reason.
    """

    UNKNOWN = 0
    STARTUP_ALARM = 1
    SHUTDOWN_ALARM = 2
    BUTTON_CLICK = 3
    VIN_DROPS = 4
    VIN_RECOVERS = 5
    OVER_TEMPERATURE = 6
    BELOW_TEMPERATURE = 7
    NEWLY_POWERED = 8
    REBOOT = 9
    MISSED_HEARTBEAT = 10
    EXTERNAL_SHUTDOWN = 11
    EXTERNAL_REBOOT = 12


def _bcd_to_int(bcd: int) -> int:
    """Convert BCD byte to integer."""
    return ((bcd >> 4) * 10) + (bcd & 0x0F)


def _int_to_bcd(value: int) -> int:
    """Convert integer to BCD byte."""
    return ((value // 10) << 4) | (value % 10)


def _decode_tmp112_temp(msb: int, lsb: int) -> float:
    """Decode TMP112 12-bit left-justified temperature to Celsius.

    Resolution: 0.0625°C per LSB.
    """
    raw = (msb << 8) | lsb
    temp_bits = raw >> 4
    if temp_bits >= 0x800:
        temp_bits -= 0x1000
    return temp_bits * 0.0625


class WittyPi5:
    """Witty Pi 5 HAT+ device with I2C communication."""

    DEFAULT_I2C_ADDRESS = 0x51
    DEFAULT_I2C_BUS = 1

    def __init__(
        self,
        *,
        i2c_bus: int = DEFAULT_I2C_BUS,
        i2c_address: int = DEFAULT_I2C_ADDRESS,
    ) -> None:
        self._i2c_bus = i2c_bus
        self._i2c_address = i2c_address
        self._smbus: object | None = None

    def open(self) -> None:
        """Open the I2C bus connection to the Witty Pi 5."""
        if self._smbus is not None:
            return

        try:
            from smbus2 import SMBus
        except ImportError as e:
            msg = "smbus2 required for I2C. Install with: uv pip install smbus2"
            raise ImportError(msg) from e

        self._smbus = SMBus(self._i2c_bus)

    def close(self) -> None:
        """Close the I2C bus connection."""
        if self._smbus is None:
            return
        self._smbus.close()
        self._smbus = None

    def __enter__(self) -> "WittyPi5":
        self.open()
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._smbus is None:
            raise RuntimeError("I2C connection not open. Call open() first.")

    def read_register(self, reg: Register) -> int:
        """Read a single byte from the given register."""
        self._ensure_open()
        return self._smbus.read_byte_data(self._i2c_address, reg)

    def write_register(self, reg: Register, value: int) -> None:
        """Write a single byte to the given register."""
        self._ensure_open()
        self._smbus.write_byte_data(self._i2c_address, reg, value & 0xFF)

    def read_word(self, reg_msb: Register) -> int:
        """Read a 16-bit value (MSB first) from consecutive registers."""
        msb = self.read_register(reg_msb)
        lsb = self.read_register(Register(reg_msb + 1))
        return (msb << 8) | lsb

    # --- Decoded value properties ---

    @property
    def firmware_id(self) -> int:
        """Firmware ID (read-only)."""
        return self.read_register(Register.FIRMWARE_ID)

    @property
    def firmware_version(self) -> str:
        """Firmware version as major.minor (e.g. '1.02')."""
        major = self.read_register(Register.FIRMWARE_VERSION_MAJOR)
        minor = self.read_register(Register.FIRMWARE_VERSION_MINOR)
        return f"{major}.{minor:02d}"

    @property
    def missed_heartbeats(self) -> int:
        """Number of missed heartbeats (watchdog)."""
        return self.read_register(Register.MISSED_HEARTBEATS)

    @property
    def action_reason_startup(self) -> ActionReason:
        """Latest startup action reason."""
        raw = self.read_register(Register.ACTION_REASON)
        startup = (raw >> 4) & 0x0F
        return ActionReason(startup) if startup <= 12 else ActionReason.UNKNOWN

    @property
    def action_reason_shutdown(self) -> ActionReason:
        """Latest shutdown action reason."""
        raw = self.read_register(Register.ACTION_REASON)
        shutdown = raw & 0x0F
        return ActionReason(shutdown) if shutdown <= 12 else ActionReason.UNKNOWN

    @property
    def month(self) -> int:
        """RTC month (1-12)."""
        return _bcd_to_int(self.read_register(Register.RTC_MONTH))

    @property
    def day(self) -> int:
        """RTC day of month (1-31)."""
        return _bcd_to_int(self.read_register(Register.RTC_DATE))

    @property
    def weekday(self) -> int:
        """RTC day of week (0=Monday, 6=Sunday, matches datetime.weekday())."""
        rtc_weekday = _bcd_to_int(self.read_register(Register.RTC_WEEKDAY))
        return (rtc_weekday + 6) % 7

    @property
    def year(self) -> int:
        """RTC year (full year, e.g. 2025)."""
        return _bcd_to_int(self.read_register(Register.RTC_YEAR)) + 2000

    @property
    def v_usb(self) -> float:
        """V_USB voltage in V."""
        return self.read_word(Register.V_USB_MSB) / 1000.0

    @property
    def v_in(self) -> float:
        """V_IN voltage in V."""
        return self.read_word(Register.V_IN_MSB) / 1000.0

    @property
    def v_out(self) -> float:
        """V_OUT voltage in V."""
        return self.read_word(Register.V_OUT_MSB) / 1000.0

    @property
    def i_out(self) -> float:
        """I_OUT current in A."""
        return self.read_word(Register.I_OUT_MSB) / 1000.0

    @property
    def temp_c(self) -> float:
        """Temperature sensor reading in Celsius."""
        msb = self.read_register(Register.TEMP_MSB)
        lsb = self.read_register(Register.TEMP_LSB)
        return _decode_tmp112_temp(msb, lsb)

    @property
    def temp_f(self) -> float:
        """Temperature sensor reading in Fahrenheit."""
        return self.temp_c * 9 / 5 + 32

    @property
    def hour(self) -> int:
        """RTC hour (0-23)."""
        return _bcd_to_int(self.read_register(Register.RTC_HOUR))

    @property
    def minute(self) -> int:
        """RTC minute (0-59)."""
        return _bcd_to_int(self.read_register(Register.RTC_MINUTE))

    @property
    def second(self) -> int:
        """RTC second (0-59)."""
        return _bcd_to_int(self.read_register(Register.RTC_SECOND))

    @property
    def date(self) -> date:
        """RTC date."""
        year = _bcd_to_int(self.read_register(Register.RTC_YEAR)) + 2000
        month = _bcd_to_int(self.read_register(Register.RTC_MONTH))
        day = _bcd_to_int(self.read_register(Register.RTC_DATE))
        return date(year, month, day)

    @property
    def time(self) -> time:
        """RTC time."""
        return time(
            self.hour,
            self.minute,
            self.second,
        )

    @property
    def datetime(self) -> datetime:
        """RTC date and time."""
        return datetime.combine(self.date, self.time)

    def sync_rtc_with_local(self) -> None:
        """Set RTC date and time from local system (datetime.now())."""
        dt = datetime.now()
        # RX8025T: 0=Sunday, 1=Monday, ..., 6=Saturday
        weekday_bcd = _int_to_bcd((dt.weekday() + 1) % 7)

        self.write_register(Register.RTC_SECOND, _int_to_bcd(dt.second))
        self.write_register(Register.RTC_MINUTE, _int_to_bcd(dt.minute))
        self.write_register(Register.RTC_HOUR, _int_to_bcd(dt.hour))
        self.write_register(Register.RTC_WEEKDAY, weekday_bcd)
        self.write_register(Register.RTC_DATE, _int_to_bcd(dt.day))
        self.write_register(Register.RTC_MONTH, _int_to_bcd(dt.month))
        self.write_register(Register.RTC_YEAR, _int_to_bcd(dt.year % 100))

    # --- Config properties ---

    @property
    def config_i2c_address(self) -> int:
        """I2C slave address."""
        return self.read_register(Register.I2C_SLAVE_ADDRESS)

    @config_i2c_address.setter
    def config_i2c_address(self, value: int) -> None:
        self.write_register(Register.I2C_SLAVE_ADDRESS, value)

    @property
    def config_power_on_delay(self) -> int:
        """Delay in seconds between power connection and turning on Pi (0=immediate, 255=stay off)."""
        return self.read_register(Register.POWER_ON_DELAY)

    @config_power_on_delay.setter
    def config_power_on_delay(self, value: int) -> None:
        self.write_register(Register.POWER_ON_DELAY, value & 0xFF)

    @property
    def config_shutdown_delay(self) -> int:
        """Delay in seconds between Pi shutdown and power cut."""
        return self.read_register(Register.SHUTDOWN_DELAY)

    @config_shutdown_delay.setter
    def config_shutdown_delay(self, value: int) -> None:
        self.write_register(Register.SHUTDOWN_DELAY, value & 0xFF)

    @property
    def config_pulse_interval(self) -> int:
        """Pulse interval in seconds for LED and dummy load."""
        return self.read_register(Register.PULSE_INTERVAL)

    @config_pulse_interval.setter
    def config_pulse_interval(self, value: int) -> None:
        self.write_register(Register.PULSE_INTERVAL, value & 0xFF)

    @property
    def config_led_on_time(self) -> int:
        """White LED on time in ms (0=no blink)."""
        return self.read_register(Register.LED_ON_TIME)

    @config_led_on_time.setter
    def config_led_on_time(self, value: int) -> None:
        self.write_register(Register.LED_ON_TIME, value & 0xFF)

    @property
    def config_dummy_load_time(self) -> int:
        """Dummy load application time in ms (0=off)."""
        return self.read_register(Register.DUMMY_LOAD_TIME)

    @config_dummy_load_time.setter
    def config_dummy_load_time(self, value: int) -> None:
        self.write_register(Register.DUMMY_LOAD_TIME, value & 0xFF)

    @property
    def config_low_voltage_threshold(self) -> int:
        """Low voltage threshold (x10 mV), 0=disabled."""
        return self.read_register(Register.LOW_VOLTAGE_THRESHOLD)

    @config_low_voltage_threshold.setter
    def config_low_voltage_threshold(self, value: int) -> None:
        self.write_register(Register.LOW_VOLTAGE_THRESHOLD, value & 0xFF)

    @property
    def config_recovery_voltage_threshold(self) -> int:
        """Recovery voltage threshold (x10 mV), 0=disabled."""
        return self.read_register(Register.RECOVERY_VOLTAGE_THRESHOLD)

    @config_recovery_voltage_threshold.setter
    def config_recovery_voltage_threshold(self, value: int) -> None:
        self.write_register(Register.RECOVERY_VOLTAGE_THRESHOLD, value & 0xFF)

    @property
    def config_power_source_priority(self) -> int:
        """Power source priority: 0=VUSB first, 1=VIN first."""
        return self.read_register(Register.POWER_SOURCE_PRIORITY)

    @config_power_source_priority.setter
    def config_power_source_priority(self, value: int) -> None:
        self.write_register(Register.POWER_SOURCE_PRIORITY, value & 0x01)

    @property
    def config_v_usb_adjustment(self) -> int:
        """Adjustment for measured VUSB (x100). Range: -128 to 127."""
        val = self.read_register(Register.V_USB_ADJUSTMENT)
        return val if val < 128 else val - 256

    @config_v_usb_adjustment.setter
    def config_v_usb_adjustment(self, value: int) -> None:
        self.write_register(Register.V_USB_ADJUSTMENT, value & 0xFF)

    @property
    def config_v_in_adjustment(self) -> int:
        """Adjustment for measured VIN (x100). Range: -128 to 127."""
        val = self.read_register(Register.V_IN_ADJUSTMENT)
        return val if val < 128 else val - 256

    @config_v_in_adjustment.setter
    def config_v_in_adjustment(self, value: int) -> None:
        self.write_register(Register.V_IN_ADJUSTMENT, value & 0xFF)

    @property
    def config_v_out_adjustment(self) -> int:
        """Adjustment for measured VOUT (x100). Range: -128 to 127."""
        val = self.read_register(Register.V_OUT_ADJUSTMENT)
        return val if val < 128 else val - 256

    @config_v_out_adjustment.setter
    def config_v_out_adjustment(self, value: int) -> None:
        self.write_register(Register.V_OUT_ADJUSTMENT, value & 0xFF)

    @property
    def config_i_out_adjustment(self) -> int:
        """Adjustment for measured IOUT (x1000). Range: -128 to 127."""
        val = self.read_register(Register.I_OUT_ADJUSTMENT)
        return val if val < 128 else val - 256

    @config_i_out_adjustment.setter
    def config_i_out_adjustment(self, value: int) -> None:
        self.write_register(Register.I_OUT_ADJUSTMENT, value & 0xFF)

    @property
    def config_watchdog_heartbeat_limit(self) -> int:
        """Allowed missed heartbeats before power cycle (0=watchdog disabled)."""
        return self.read_register(Register.WATCHDOG_HEARTBEAT_LIMIT)

    @config_watchdog_heartbeat_limit.setter
    def config_watchdog_heartbeat_limit(self, value: int) -> None:
        self.write_register(Register.WATCHDOG_HEARTBEAT_LIMIT, value & 0xFF)

    @property
    def config_log_to_file_enabled(self) -> bool:
        """Whether to write log to file (1=allowed, 0=not allowed)."""
        return bool(self.read_register(Register.LOG_TO_FILE_ENABLED))

    @config_log_to_file_enabled.setter
    def config_log_to_file_enabled(self, value: bool) -> None:
        self.write_register(Register.LOG_TO_FILE_ENABLED, int(value))

    @property
    def config_startup_alarm_second(self) -> int:
        """Startup alarm second (0-59)."""
        return _bcd_to_int(self.read_register(Register.STARTUP_ALARM_SECOND))

    @config_startup_alarm_second.setter
    def config_startup_alarm_second(self, value: int) -> None:
        self.write_register(Register.STARTUP_ALARM_SECOND, _int_to_bcd(value) & 0x7F)

    @property
    def config_startup_alarm_minute(self) -> int:
        """Startup alarm minute (0-59)."""
        return _bcd_to_int(self.read_register(Register.STARTUP_ALARM_MINUTE))

    @config_startup_alarm_minute.setter
    def config_startup_alarm_minute(self, value: int) -> None:
        self.write_register(Register.STARTUP_ALARM_MINUTE, _int_to_bcd(value) & 0x7F)

    @property
    def config_startup_alarm_hour(self) -> int:
        """Startup alarm hour (0-23)."""
        return _bcd_to_int(self.read_register(Register.STARTUP_ALARM_HOUR))

    @config_startup_alarm_hour.setter
    def config_startup_alarm_hour(self, value: int) -> None:
        self.write_register(Register.STARTUP_ALARM_HOUR, _int_to_bcd(value) & 0x3F)

    @property
    def config_startup_alarm_day(self) -> int:
        """Startup alarm day (day-of-week 1-7 or date 1-31 per RTC)."""
        return _bcd_to_int(self.read_register(Register.STARTUP_ALARM_DAY))

    @config_startup_alarm_day.setter
    def config_startup_alarm_day(self, value: int) -> None:
        self.write_register(Register.STARTUP_ALARM_DAY, _int_to_bcd(value) & 0xFF)

    @property
    def config_shutdown_alarm_second(self) -> int:
        """Shutdown alarm second (0-59)."""
        return _bcd_to_int(self.read_register(Register.SHUTDOWN_ALARM_SECOND))

    @config_shutdown_alarm_second.setter
    def config_shutdown_alarm_second(self, value: int) -> None:
        self.write_register(Register.SHUTDOWN_ALARM_SECOND, _int_to_bcd(value) & 0x7F)

    @property
    def config_shutdown_alarm_minute(self) -> int:
        """Shutdown alarm minute (0-59)."""
        return _bcd_to_int(self.read_register(Register.SHUTDOWN_ALARM_MINUTE))

    @config_shutdown_alarm_minute.setter
    def config_shutdown_alarm_minute(self, value: int) -> None:
        self.write_register(Register.SHUTDOWN_ALARM_MINUTE, _int_to_bcd(value) & 0x7F)

    @property
    def config_shutdown_alarm_hour(self) -> int:
        """Shutdown alarm hour (0-23)."""
        return _bcd_to_int(self.read_register(Register.SHUTDOWN_ALARM_HOUR))

    @config_shutdown_alarm_hour.setter
    def config_shutdown_alarm_hour(self, value: int) -> None:
        self.write_register(Register.SHUTDOWN_ALARM_HOUR, _int_to_bcd(value) & 0x3F)

    @property
    def config_shutdown_alarm_day(self) -> int:
        """Shutdown alarm day (day-of-week 1-7 or date 1-31 per RTC)."""
        return _bcd_to_int(self.read_register(Register.SHUTDOWN_ALARM_DAY))

    @config_shutdown_alarm_day.setter
    def config_shutdown_alarm_day(self, value: int) -> None:
        self.write_register(Register.SHUTDOWN_ALARM_DAY, _int_to_bcd(value) & 0xFF)

    @property
    def config_factory_reset_enabled(self) -> bool:
        """Allow long press BOOTSEL + button for factory reset."""
        return bool(self.read_register(Register.FACTORY_RESET_ENABLED))

    @config_factory_reset_enabled.setter
    def config_factory_reset_enabled(self, value: bool) -> None:
        self.write_register(Register.FACTORY_RESET_ENABLED, int(value))

    @property
    def config_below_temp_action(self) -> int:
        """Action for below temp: 0=nothing, 1=startup, 2=shutdown."""
        return self.read_register(Register.BELOW_TEMP_ACTION)

    @config_below_temp_action.setter
    def config_below_temp_action(self, value: int) -> None:
        self.write_register(Register.BELOW_TEMP_ACTION, value & 0x03)

    @property
    def config_below_temp_threshold(self) -> int:
        """Below temperature threshold (signed Celsius)."""
        val = self.read_register(Register.BELOW_TEMP_THRESHOLD)
        return val if val < 128 else val - 256

    @config_below_temp_threshold.setter
    def config_below_temp_threshold(self, value: int) -> None:
        self.write_register(Register.BELOW_TEMP_THRESHOLD, value & 0xFF)

    @property
    def config_over_temp_action(self) -> int:
        """Action for over temp: 0=nothing, 1=startup, 2=shutdown."""
        return self.read_register(Register.OVER_TEMP_ACTION)

    @config_over_temp_action.setter
    def config_over_temp_action(self, value: int) -> None:
        self.write_register(Register.OVER_TEMP_ACTION, value & 0x03)

    @property
    def config_dst_mode_and_offset(self) -> int:
        """DST: bit7=mode; bits 6-0=offset in minutes (0=disable)."""
        return self.read_register(Register.DST_MODE_AND_OFFSET)

    @config_dst_mode_and_offset.setter
    def config_dst_mode_and_offset(self, value: int) -> None:
        self.write_register(Register.DST_MODE_AND_OFFSET, value & 0xFF)

    @property
    def config_dst_applied(self) -> int:
        """Whether DST has been applied."""
        return self.read_register(Register.DST_APPLIED)

    @config_dst_applied.setter
    def config_dst_applied(self, value: int) -> None:
        self.write_register(Register.DST_APPLIED, value & 0xFF)

    @property
    def config_over_temp_threshold(self) -> int:
        """Over temperature threshold (signed Celsius)."""
        val = self.read_register(Register.OVER_TEMP_THRESHOLD)
        return val if val < 128 else val - 256

    @config_over_temp_threshold.setter
    def config_over_temp_threshold(self, value: int) -> None:
        self.write_register(Register.OVER_TEMP_THRESHOLD, value & 0xFF)

    @property
    def config_system_clock_mhz(self) -> int:
        """System clock for RP2350 in MHz."""
        return self.read_register(Register.SYSTEM_CLOCK_MHZ)

    @config_system_clock_mhz.setter
    def config_system_clock_mhz(self, value: int) -> None:
        self.write_register(Register.SYSTEM_CLOCK_MHZ, value & 0xFF)
