"""Heating capabilities and preset edits, independent of Home Assistant."""

from .errors import ProtocolError
from .parameters import FireState, Parameter

HEAT_MODES = {"normal": 0, "boost": 1, "eco": 2, "fan_only": 3, "schedule": 4}


def supported_modes(features: dict) -> list[str]:
    """Do not advertise optional modes unless explicitly declared."""
    requirements = {"boost": "PowerBoost", "eco": "AdvancedHeat", "fan_only": "FanOnly", "schedule": "SevenDayTimer"}
    return ["normal", *(mode for mode, capability in requirements.items() if features.get(capability) is True)]


def preset_parameter(state: FireState, features: dict, preset: str) -> Parameter:
    """Selecting a preset never changes power, heat status or setpoint."""
    if preset not in supported_modes(features):
        raise ProtocolError("Unsupported heating preset")
    parameter = state.require(323)
    changes = {"heat_mode": HEAT_MODES[preset]}
    if preset == "boost":
        duration = parameter.field("boost")
        changes["boost"] = duration if 1 <= duration <= 20 else 15
    return parameter.edit(**changes)
