"""Shared Home Assistant presentation and validation for target temperatures."""

from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN
from .domain.protocol import (
    TARGET_MIN_CELSIUS,
    TEMPERATURE_DECIMAL_PLACES,
)


def supports_heating(coordinator) -> bool:
    return coordinator.fire.supports_heating


def temperature_unit(coordinator) -> str:
    return coordinator.unit or UnitOfTemperature.CELSIUS


def display_temperature(coordinator, celsius: float) -> float:
    return TemperatureConverter.convert(celsius, UnitOfTemperature.CELSIUS, temperature_unit(coordinator))


def temperature_limits(coordinator) -> tuple[float, float]:
    return display_temperature(coordinator, TARGET_MIN_CELSIUS), display_temperature(
        coordinator, coordinator.fire.target_max_celsius
    )


def target_celsius(coordinator, value: float) -> float:
    minimum, maximum = temperature_limits(coordinator)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
    return round(
        TemperatureConverter.convert(value, temperature_unit(coordinator), UnitOfTemperature.CELSIUS),
        TEMPERATURE_DECIMAL_PLACES,
    )
