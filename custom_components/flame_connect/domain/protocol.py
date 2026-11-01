"""Wire identifiers, layouts and limits; no transport or framework dependencies."""

from enum import IntEnum
from typing import NamedTuple


class ParameterId(IntEnum):
    TEMPERATURE_UNIT = 236
    MODE = 321
    FLAME_EFFECT = 322
    HEAT_SETTINGS = 323
    HEAT_CONTROL = 325
    COUNTDOWN = 326
    FIRMWARE = 327
    ERRORS = 329
    SOUND = 369
    LOG_EFFECT = 370


class HeatMode(IntEnum):
    NORMAL = 0
    BOOST = 1
    ECO = 2
    FAN_ONLY = 3
    SCHEDULE = 4


class FireMode(IntEnum):
    STANDBY = 0
    MANUAL = 1


class SwitchState(IntEnum):
    OFF = 0
    ON = 1


class TemperatureScale(IntEnum):
    FAHRENHEIT = 0
    CELSIUS = 1


class FlameBrightness(IntEnum):
    HIGH = 0
    LOW = 1
    FLICKER_HIGH = 2
    FLICKER_LOW = 3


class FlameColor(IntEnum):
    """Color positions depend on FlamePalette; they are not fixed RGB colors."""

    ALL = 0
    FIRST_SECOND = 1
    FIRST_THIRD = 2
    THIRD = 3
    SECOND = 4
    FIRST = 5
    THIRD_SECOND = 6


class FlamePalette(IntEnum):
    YELLOW_RED_BLUE = 0
    YELLOW_ORANGE_BLUE = 1
    AMBER_ORANGE_YELLOW = 2


class OverviewResult(IntEnum):
    SUCCESS = 0


PARAMETER_ID_BYTES = 2
PARAMETER_LENGTH_OFFSET = PARAMETER_ID_BYTES
PARAMETER_HEADER_BYTES = 3
MODE_TEMPERATURE_OFFSET = 4
HEAT_TEMPERATURE_OFFSET = 5
TEMPERATURE_FRACTION_RELATIVE_OFFSET = 1
TEMPERATURE_DECIMAL_FACTOR = 10
TEMPERATURE_DECIMAL_PLACES = 1
TEMPERATURE_STEP = 0.1
COUNTDOWN_DURATION_OFFSET = 4
COUNTDOWN_DURATION_BYTES = 2
FLAME_COLOR_OFFSET = 19
FLAME_SPEED_OFFSET = 4
FLAME_BRIGHTNESS_OFFSET = 5
HEAT_MODE_OFFSET = 4
SOUND_FILE_OFFSET = 4
BOOST_DURATION_OFFSET = 7

BYTE_MIN = 0
BYTE_MAX = 255
FLAME_SPEED_MIN = 1
FLAME_SPEED_MAX = 5
FLAME_SPEED_DISPLAY_ADJUSTMENT = 1
COUNTDOWN_MIN_MINUTES = 0
COUNTDOWN_MAX_MINUTES = 32767
BOOST_MIN_MINUTES = 1
BOOST_MAX_MINUTES = 20
BOOST_DEFAULT_MINUTES = 15
BOOST_CLEARED_MINUTES = 0
WIRE_TEMPERATURE_MIN_CELSIUS = 7
TARGET_MIN_CELSIUS = 15
OPTIFLAME_TARGET_MAX_CELSIUS = 30.6
DEFAULT_TARGET_MAX_CELSIUS = 32.9

# Payload byte lengths are declared once, indexed by the wire identifier.
PARAMETER_PAYLOAD_SIZES: dict[int, int] = {
    ParameterId.TEMPERATURE_UNIT: 1,
    ParameterId.MODE: 3,
    ParameterId.FLAME_EFFECT: 20,
    ParameterId.HEAT_SETTINGS: 5,
    ParameterId.HEAT_CONTROL: 1,
    ParameterId.COUNTDOWN: 3,
    ParameterId.FIRMWARE: 9,
    ParameterId.ERRORS: 4,
    ParameterId.SOUND: 2,
    ParameterId.LOG_EFFECT: 8,
}
WRITABLE_PARAMETERS = frozenset(
    {
        ParameterId.TEMPERATURE_UNIT,
        ParameterId.MODE,
        ParameterId.FLAME_EFFECT,
        ParameterId.HEAT_SETTINGS,
        ParameterId.COUNTDOWN,
        ParameterId.SOUND,
    }
)


class FieldSpec(NamedTuple):
    """Absolute byte position, user range and optional zero-based wire adjustment."""

    offset: int
    minimum: int
    maximum: int
    display_offset: int = 0


FIELDS: dict[int, dict[str, FieldSpec]] = {
    ParameterId.TEMPERATURE_UNIT: {
        "unit": FieldSpec(PARAMETER_HEADER_BYTES, TemperatureScale.FAHRENHEIT, TemperatureScale.CELSIUS)
    },
    ParameterId.MODE: {"mode": FieldSpec(PARAMETER_HEADER_BYTES, FireMode.STANDBY, FireMode.MANUAL)},
    ParameterId.FLAME_EFFECT: {
        "flame": FieldSpec(PARAMETER_HEADER_BYTES, SwitchState.OFF, SwitchState.ON),
        "speed": FieldSpec(FLAME_SPEED_OFFSET, FLAME_SPEED_MIN, FLAME_SPEED_MAX, FLAME_SPEED_DISPLAY_ADJUSTMENT),
        "brightness": FieldSpec(FLAME_BRIGHTNESS_OFFSET, FlameBrightness.HIGH, FlameBrightness.FLICKER_LOW),
        "color": FieldSpec(FLAME_COLOR_OFFSET, FlameColor.ALL, FlameColor.THIRD_SECOND),
    },
    ParameterId.HEAT_SETTINGS: {
        "heat": FieldSpec(PARAMETER_HEADER_BYTES, SwitchState.OFF, SwitchState.ON),
        "heat_mode": FieldSpec(HEAT_MODE_OFFSET, HeatMode.NORMAL, HeatMode.SCHEDULE),
        "boost": FieldSpec(BOOST_DURATION_OFFSET, BYTE_MIN, BYTE_MAX),
    },
    ParameterId.COUNTDOWN: {"timer": FieldSpec(PARAMETER_HEADER_BYTES, SwitchState.OFF, SwitchState.ON)},
    ParameterId.SOUND: {
        "volume": FieldSpec(PARAMETER_HEADER_BYTES, BYTE_MIN, BYTE_MAX),
        "sound_file": FieldSpec(SOUND_FILE_OFFSET, BYTE_MIN, BYTE_MAX),
    },
}
