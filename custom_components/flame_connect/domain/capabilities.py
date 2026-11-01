"""Known device capabilities; values preserve public diagnostic field names."""

from enum import StrEnum


class Capability(StrEnum):
    ADVANCED_HEAT = "AdvancedHeat"
    APPLY_FLAME_ONLY_FIRST = "ApplyFlameOnlyFirst"
    CHECK_IF_REMOTE_WAS_USED = "CheckIfRemoteWasUsed"
    COUNT_DOWN_TIMER = "CountDownTimer"
    FAN_ONLY = "FanOnly"
    FLAME_AMBER = "FlameAmber"
    FLAME_DIMMING = "FlameDimming"
    FLAME_FAN_SPEED = "FlameFanSpeed"
    FLAME_HEIGHT = "FlameHeight"
    FLAME_PRESET_OPTIONS = "FlamePresetOptions"
    FRONT_LIGHT_AMBER = "FrontLightAmber"
    FUEL_BED_DIMMING = "FuelBedDimming"
    LGT1_TO5 = "Lgt1To5"
    MEDIA_ACCENT = "MediaAccent"
    MOODS = "Moods"
    PIR_TOGGLE_SMART_SENSE = "PirToggleSmartSense"
    POWER_BOOST = "PowerBoost"
    PRESET_OPTIONS = "PresetOptions"
    REQUIRES_WARM_UP = "RequiresWarmUp"
    RGB_BACK_LIGHT = "RgbBackLight"
    RGB_FLAME_ACCENT = "RgbFlameAccent"
    RGB_FUEL_BED = "RgbFuelBed"
    RGB_LOG_EFFECT = "RgbLogEffect"
    SEVEN_DAY_TIMER = "SevenDayTimer"
    SIMPLE_HEAT = "SimpleHeat"
    SOUND = "Sound"


CAPABILITY_PRESETS = frozenset({Capability.PRESET_OPTIONS, Capability.FLAME_PRESET_OPTIONS})
CAPABILITY_FLAGS = frozenset(Capability) - CAPABILITY_PRESETS
