"""Allowlisted diagnostics contain no identifiers, PINs, names or tokens."""

from homeassistant.core import HomeAssistant

from . import FlameConfigEntry
from .const import CONF_EXPERIMENTAL, CONF_TEMPERATURE_UNIT

SAFE_FEATURES = frozenset(
    {
        "Sound",
        "SimpleHeat",
        "AdvancedHeat",
        "SevenDayTimer",
        "CountDownTimer",
        "Moods",
        "FlameHeight",
        "RgbFlameAccent",
        "FlameDimming",
        "RgbFuelBed",
        "FuelBedDimming",
        "FlameFanSpeed",
        "RgbBackLight",
        "FrontLightAmber",
        "PirToggleSmartSense",
        "Lgt1To5",
        "RequiresWarmUp",
        "PresetOptions",
        "ApplyFlameOnlyFirst",
        "FlameAmber",
        "CheckIfRemoteWasUsed",
        "MediaAccent",
        "PowerBoost",
        "FanOnly",
        "RgbLogEffect",
        "FlamePresetOptions",
    }
)


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: FlameConfigEntry) -> dict:
    return {
        "integration": "Flame Connect (unofficial)",
        "options": {
            key: entry.options[key] for key in (CONF_TEMPERATURE_UNIT, CONF_EXPERIMENTAL) if key in entry.options
        },
        "devices": [
            {
                "model": c.fire.get("ProductModel"),
                "features": {
                    key: value
                    for key, value in c.features.items()
                    if key in SAFE_FEATURES and type(value) in (bool, int)
                },
                "available": c.last_update_success,
                "parameters": sorted(c.data.parameters) if c.data else [],
            }
            for c in entry.runtime_data.coordinators
        ],
    }
