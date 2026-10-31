"""Discrete settings reflect wire enums instead of invented RGB/brightness."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity import EntityCategory

from .const import CONF_EXPERIMENTAL, DOMAIN
from .domain.parameters import color_labels
from .domain.protocol import FlameBrightness, FlamePalette, ParameterId, TemperatureScale
from .entity import FlameEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    entities = []
    for c in entry.runtime_data.coordinators:
        if c.features.get("FlameDimming"):
            entities.append(
                FlameSelect(
                    c,
                    "brightness",
                    ParameterId.FLAME_EFFECT,
                    "brightness",
                    [value.name.lower() for value in FlameBrightness],
                )
            )
        if entry.options.get(CONF_EXPERIMENTAL):
            if c.features.get("RgbFlameAccent") or c.features.get("FlameAmber"):
                entities.append(
                    FlameSelect(
                        c,
                        "color",
                        ParameterId.FLAME_EFFECT,
                        "color",
                        [
                            label.lower().replace(" + ", "_")
                            for label in color_labels(
                                c.features.get("FlamePresetOptions", FlamePalette.YELLOW_RED_BLUE)
                            )
                        ],
                    )
                )
            entities.append(
                FlameSelect(
                    c,
                    "temperature_scale",
                    ParameterId.TEMPERATURE_UNIT,
                    "unit",
                    [value.name.lower() for value in TemperatureScale],
                )
            )
    async_add_entities(entities)


class FlameSelect(FlameEntity, SelectEntity):
    def __init__(self, coordinator, key, parameter, field, options) -> None:
        super().__init__(coordinator, key, parameter)
        self.key, self.setting = key, field
        self._attr_options = options
        self._attr_entity_registry_enabled_default = key == "brightness"
        if key == "temperature_scale":
            self._attr_entity_category = EntityCategory.CONFIG

    @property
    def current_option(self):
        index = self.field(self.required_parameter, self.setting)
        return self.options[index] if index is not None and 0 <= index < len(self.options) else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        await self.coordinator.edit(self.required_parameter, **{self.setting: self.options.index(option)})
