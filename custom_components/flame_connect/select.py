"""Discrete settings reflect wire enums instead of invented RGB/brightness."""

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_EXPERIMENTAL, DOMAIN
from .domain.capabilities import Capability
from .domain.parameters import color_labels
from .domain.protocol import FlameBrightness, ParameterId, TemperatureScale
from .entity import FlameEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class FlameSelectDescription(SelectEntityDescription):
    parameter: ParameterId
    setting: str
    capabilities: tuple[Capability, ...] = ()
    experimental: bool = False


SELECTS = {
    description.key: description
    for description in (
        FlameSelectDescription(
            key="brightness",
            parameter=ParameterId.FLAME_EFFECT,
            setting="brightness",
            capabilities=(Capability.FLAME_DIMMING,),
            options=[value.name.lower() for value in FlameBrightness],
        ),
        FlameSelectDescription(
            key="color",
            parameter=ParameterId.FLAME_EFFECT,
            setting="color",
            capabilities=(Capability.RGB_FLAME_ACCENT, Capability.FLAME_AMBER),
            experimental=True,
            entity_registry_enabled_default=False,
        ),
        FlameSelectDescription(
            key="temperature_scale",
            parameter=ParameterId.TEMPERATURE_UNIT,
            setting="unit",
            experimental=True,
            options=[value.name.lower() for value in TemperatureScale],
            entity_category=EntityCategory.CONFIG,
            entity_registry_enabled_default=False,
        ),
    )
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    entities = []
    for coordinator in entry.runtime_data.coordinators:
        for description in SELECTS.values():
            if description.experimental and not entry.options.get(CONF_EXPERIMENTAL):
                continue
            if description.capabilities and not any(
                coordinator.features.enabled(key) for key in description.capabilities
            ):
                continue
            entities.append(FlameSelect(coordinator, description))
    async_add_entities(entities)


class FlameSelect(FlameEntity, SelectEntity):
    entity_description: FlameSelectDescription

    def __init__(self, coordinator, description: FlameSelectDescription) -> None:
        super().__init__(coordinator, description.key, description.parameter)
        self.entity_description = description
        if description.key == "color":
            self._attr_options = [
                label.lower().replace(" + ", "_") for label in color_labels(coordinator.features.flame_palette)
            ]

    @property
    def current_option(self):
        index = self.field(self.entity_description.parameter, self.entity_description.setting)
        return self.options[index] if index is not None and 0 <= index < len(self.options) else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        await self.coordinator.edit(
            self.entity_description.parameter, **{self.entity_description.setting: self.options.index(option)}
        )
