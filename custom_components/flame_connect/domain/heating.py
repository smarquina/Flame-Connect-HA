"""Heating capabilities and preset edits, independent of Home Assistant."""

from .capabilities import Capability
from .errors import ProtocolError
from .models import FireCapabilities
from .parameters import FireState, Parameter
from .protocol import BOOST_DEFAULT_MINUTES, BOOST_MAX_MINUTES, BOOST_MIN_MINUTES, HeatMode, ParameterId

HEAT_MODES = {mode.name.lower(): mode for mode in HeatMode}


def supported_modes(features: FireCapabilities) -> list[str]:
    """Do not advertise optional modes unless explicitly declared."""
    requirements = {
        "boost": Capability.POWER_BOOST,
        "eco": Capability.ADVANCED_HEAT,
        "fan_only": Capability.FAN_ONLY,
        "schedule": Capability.SEVEN_DAY_TIMER,
    }
    return ["normal", *(mode for mode, capability in requirements.items() if features.enabled(capability))]


def preset_parameter(state: FireState, features: FireCapabilities, preset: str) -> Parameter:
    """Selecting a preset never changes power, heat status or setpoint."""
    if preset not in supported_modes(features):
        raise ProtocolError("Unsupported heating preset")
    parameter = state.require(ParameterId.HEAT_SETTINGS)
    changes = {"heat_mode": HEAT_MODES[preset].value}
    if preset == "boost":
        duration = parameter.field("boost")
        changes["boost"] = duration if BOOST_MIN_MINUTES <= duration <= BOOST_MAX_MINUTES else BOOST_DEFAULT_MINUTES
    return parameter.edit(**changes)
