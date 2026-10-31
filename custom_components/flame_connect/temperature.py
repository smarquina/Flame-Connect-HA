"""Shared Home Assistant presentation and validation for target temperatures."""

from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN
from .domain.protocol import (
    DEFAULT_TARGET_MAX_CELSIUS,
    OPTIFLAME_TARGET_MAX_CELSIUS,
    TARGET_MIN_CELSIUS,
    TEMPERATURE_DECIMAL_PLACES,
)


def supports_heating(coordinator) -> bool:
    return any(
        value is True
        for value in (
            coordinator.fire.get("WithHeat"),
            coordinator.features.get("AdvancedHeat"),
            coordinator.features.get("SimpleHeat"),
        )
    )


def temperature_unit(coordinator) -> str:
    return coordinator.unit or UnitOfTemperature.CELSIUS


def display_temperature(coordinator, celsius: float) -> float:
    return TemperatureConverter.convert(celsius, UnitOfTemperature.CELSIUS, temperature_unit(coordinator))


def temperature_limits(coordinator) -> tuple[float, float]:
    fire = coordinator.fire
    maximum = (
        OPTIFLAME_TARGET_MAX_CELSIUS
        if fire.get("ProductType") in ("Optiflame V2", "Optiflame V3", "Optiflame V4")
        or "OLF" in (fire.get("ProductModel") or "")
        else DEFAULT_TARGET_MAX_CELSIUS
    )
    return display_temperature(coordinator, TARGET_MIN_CELSIUS), display_temperature(coordinator, maximum)


def target_celsius(coordinator, value: float) -> float:
    minimum, maximum = temperature_limits(coordinator)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
    return round(
        TemperatureConverter.convert(value, temperature_unit(coordinator), UnitOfTemperature.CELSIUS),
        TEMPERATURE_DECIMAL_PLACES,
    )
