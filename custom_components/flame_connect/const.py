"""Constants for the unofficial Flame Connect integration."""

from homeassistant.const import Platform

DOMAIN = "flame_connect"
NAME = "Flame Connect (unofficial)"
PLATFORMS = [
    Platform.CLIMATE,
    Platform.LIGHT,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
CONF_FIRES = "fires"
CONF_TEMPERATURE_UNIT = "temperature_unit"
CONF_EXPERIMENTAL = "experimental_controls"
DEFAULT_INTERVAL = 30
DEFAULT_OPTIONS = {CONF_TEMPERATURE_UNIT: "auto", CONF_EXPERIMENTAL: False}
