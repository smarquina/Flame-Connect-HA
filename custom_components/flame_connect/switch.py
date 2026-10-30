"""Whole-fireplace power and opt-in unvalidated countdown control."""

from homeassistant.components.switch import SwitchEntity

from .const import CONF_EXPERIMENTAL
from .entity import FlameEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    entities = []
    for c in entry.runtime_data.coordinators:
        entities.append(FlameSwitch(c, "power", 321))
        if entry.options.get(CONF_EXPERIMENTAL) and c.features.get("CountDownTimer"):
            entities.append(FlameSwitch(c, "timer", 326))
    async_add_entities(entities)


class FlameSwitch(FlameEntity, SwitchEntity):
    def __init__(self, coordinator, key, parameter) -> None:
        super().__init__(coordinator, key, parameter)
        self.key = key
        self._attr_entity_registry_enabled_default = key == "power"

    @property
    def is_on(self):
        value = self.field(321, "mode") if self.key == "power" else self.field(326, "timer")
        return bool(value) if value is not None else None

    async def _set(self, on: bool) -> None:
        if self.key == "power":
            await self.coordinator.command(lambda state: state.power(on))
        else:
            await self.coordinator.edit(326, timer=int(on))

    async def async_turn_on(self, **kwargs) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set(False)
