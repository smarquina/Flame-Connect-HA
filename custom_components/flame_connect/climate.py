"""Heating remains independent of the decorative flame."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import DOMAIN
from .entity import FlameEntity

PARALLEL_UPDATES = 1
PRESETS = ["normal", "boost", "eco", "fan", "schedule"]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    # The official app uses heat capabilities; WithHeat may be absent or false.
    async_add_entities(
        [
            FlameClimate(c)
            for c in entry.runtime_data.coordinators
            if c.fire.get("WithHeat") is True
            or c.features.get("AdvancedHeat") is True
            or c.features.get("SimpleHeat") is True
        ]
    )


class FlameClimate(FlameEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 0.1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "heating", 323)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.unit is not None

    def _display(self, value):
        return TemperatureConverter.convert(value, UnitOfTemperature.CELSIUS, self._unit())

    def _unit(self):
        return self.coordinator.unit or "°C"

    def _current(self):
        data = self.coordinator.data
        return self._display(data.parameters[321].temperature) if data and 321 in data.parameters else None

    def _target(self):
        data = self.coordinator.data
        return self._display(data.parameters[323].temperature) if data and 323 in data.parameters else None

    # HA 2026.11 renamed the native properties. Do not implement deprecated
    # aliases on newer versions or apply Home Assistant's conversion twice.
    if hasattr(ClimateEntity, "native_temperature_unit"):
        native_temperature_unit = property(_unit)
        native_current_temperature = property(_current)
        native_target_temperature = property(_target)
    else:
        temperature_unit = property(_unit)
        current_temperature = property(_current)
        target_temperature = property(_target)

    @property
    def min_temp(self) -> float:
        return self._display(15)

    @property
    def max_temp(self) -> float:
        fire = self.coordinator.fire
        maximum = (
            30.6
            if fire.get("ProductType") in ("Optiflame V2", "Optiflame V3", "Optiflame V4")
            or "OLF" in (fire.get("ProductModel") or "")
            else 32.9
        )
        return self._display(maximum)

    @property
    def hvac_mode(self) -> HVACMode | None:
        heat = self.field(323, "heat")
        return None if heat is None else HVACMode.HEAT if heat else HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self.hvac_modes:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")

        def build(state):
            params = [state.require(323).edit(heat=int(hvac_mode == HVACMode.HEAT))]
            if hvac_mode == HVACMode.HEAT:
                params.append(state.require(321).edit(mode=1))
            return params

        await self.coordinator.command(build)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        value = kwargs.get(ATTR_TEMPERATURE)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not self.min_temp <= value <= self.max_temp
        ):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        await self.coordinator.edit(
            323, temperature=round(TemperatureConverter.convert(value, self._unit(), UnitOfTemperature.CELSIUS), 1)
        )
