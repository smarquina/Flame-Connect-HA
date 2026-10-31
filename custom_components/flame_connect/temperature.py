"""Shared Home Assistant presentation and validation for target temperatures."""

from homeassistant.const import UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN


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
        30.6
        if fire.get("ProductType") in ("Optiflame V2", "Optiflame V3", "Optiflame V4")
        or "OLF" in (fire.get("ProductModel") or "")
        else 32.9
    )
    return display_temperature(coordinator, 15), display_temperature(coordinator, maximum)


def target_celsius(coordinator, value: float) -> float:
    minimum, maximum = temperature_limits(coordinator)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
    return round(TemperatureConverter.convert(value, temperature_unit(coordinator), UnitOfTemperature.CELSIUS), 1)
