"""The decorative flame is an on/off light; presets are separate selectors."""

from homeassistant.components.light import ColorMode, LightEntity

from .entity import FlameEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([FlameLight(c) for c in entry.runtime_data.coordinators])


class FlameLight(FlameEntity, LightEntity):
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "flame", 322)

    @property
    def is_on(self):
        value = self.field(322, "flame")
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.edit(322, flame=1)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.edit(322, flame=0)
