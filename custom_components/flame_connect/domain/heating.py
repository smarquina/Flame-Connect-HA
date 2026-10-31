"""Heating capabilities and preset edits, independent of Home Assistant."""

from .errors import ProtocolError
from .parameters import FireState, Parameter
from .protocol import BOOST_DEFAULT_MINUTES, BOOST_MAX_MINUTES, BOOST_MIN_MINUTES, HeatMode, ParameterId

HEAT_MODES = {mode.name.lower(): mode for mode in HeatMode}


def supported_modes(features: dict) -> list[str]:
    """Do not advertise optional modes unless explicitly declared."""
    requirements = {"boost": "PowerBoost", "eco": "AdvancedHeat", "fan_only": "FanOnly", "schedule": "SevenDayTimer"}
    return ["normal", *(mode for mode, capability in requirements.items() if features.get(capability) is True)]


def preset_parameter(state: FireState, features: dict, preset: str) -> Parameter:
    """Selecting a preset never changes power, heat status or setpoint."""
    if preset not in supported_modes(features):
        raise ProtocolError("Unsupported heating preset")
    parameter = state.require(ParameterId.HEAT_SETTINGS)
    changes = {"heat_mode": HEAT_MODES[preset].value}
    if preset == "boost":
        duration = parameter.field("boost")
        changes["boost"] = duration if BOOST_MIN_MINUTES <= duration <= BOOST_MAX_MINUTES else BOOST_DEFAULT_MINUTES
    return parameter.edit(**changes)
