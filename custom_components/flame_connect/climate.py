"""Heating remains independent of the decorative flame."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN
from .domain.heating import HEAT_MODES, preset_parameter, supported_modes
from .entity import FlameEntity
from .temperature import display_temperature, supports_heating, target_celsius, temperature_limits, temperature_unit

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    # The official app uses heat capabilities; WithHeat may be absent or false.
    async_add_entities([FlameClimate(c) for c in entry.runtime_data.coordinators if supports_heating(c)])


class FlameClimate(FlameEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_target_temperature_step = 0.1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "heating", 323)
        self._attr_preset_modes = supported_modes(coordinator.features)

    @property
    def preset_mode(self) -> str | None:
        mode = self.field(323, "heat_mode")
        return next((key for key, value in HEAT_MODES.items() if value == mode), None)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in self.preset_modes:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        await self.coordinator.command(lambda state: [preset_parameter(state, self.coordinator.features, preset_mode)])

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.unit is not None

    def _display(self, value):
        return display_temperature(self.coordinator, value)

    def _unit(self):
        return temperature_unit(self.coordinator)

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
        return temperature_limits(self.coordinator)[0]

    @property
    def max_temp(self) -> float:
        return temperature_limits(self.coordinator)[1]

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
        await self.coordinator.edit(323, temperature=target_celsius(self.coordinator, kwargs.get(ATTR_TEMPERATURE)))
