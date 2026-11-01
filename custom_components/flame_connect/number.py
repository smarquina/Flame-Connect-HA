"""Numeric settings with explicit protocol ranges and optional controls."""

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.exceptions import ServiceValidationError

from .const import CONF_EXPERIMENTAL, DOMAIN
from .domain.capabilities import Capability
from .domain.protocol import (
    BOOST_MAX_MINUTES,
    BOOST_MIN_MINUTES,
    BYTE_MAX,
    BYTE_MIN,
    COUNTDOWN_MAX_MINUTES,
    COUNTDOWN_MIN_MINUTES,
    FLAME_SPEED_MAX,
    FLAME_SPEED_MIN,
    TEMPERATURE_STEP,
    ParameterId,
)
from .entity import FlameEntity
from .temperature import display_temperature, supports_heating, target_celsius, temperature_limits

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class FlameNumberDescription(NumberEntityDescription):
    parameter: ParameterId
    setting: str
    capability: Capability
    experimental: bool = False
    requires_heating: bool = False


NUMBERS = {
    description.key: description
    for description in (
        FlameNumberDescription(
            key="boost_duration",
            parameter=ParameterId.HEAT_SETTINGS,
            setting="boost",
            capability=Capability.POWER_BOOST,
            requires_heating=True,
            native_min_value=BOOST_MIN_MINUTES,
            native_max_value=BOOST_MAX_MINUTES,
            native_unit_of_measurement="min",
        ),
        FlameNumberDescription(
            key="speed",
            parameter=ParameterId.FLAME_EFFECT,
            setting="speed",
            capability=Capability.FLAME_FAN_SPEED,
            native_min_value=FLAME_SPEED_MIN,
            native_max_value=FLAME_SPEED_MAX,
        ),
        FlameNumberDescription(
            key="duration",
            parameter=ParameterId.COUNTDOWN,
            setting="duration",
            capability=Capability.COUNT_DOWN_TIMER,
            experimental=True,
            native_min_value=COUNTDOWN_MIN_MINUTES,
            native_max_value=COUNTDOWN_MAX_MINUTES,
            native_unit_of_measurement="min",
            entity_registry_enabled_default=False,
        ),
        FlameNumberDescription(
            key="volume",
            parameter=ParameterId.SOUND,
            setting="volume",
            capability=Capability.SOUND,
            experimental=True,
            native_min_value=BYTE_MIN,
            native_max_value=BYTE_MAX,
            entity_registry_enabled_default=False,
        ),
        FlameNumberDescription(
            key="sound_file",
            parameter=ParameterId.SOUND,
            setting="sound_file",
            capability=Capability.SOUND,
            experimental=True,
            native_min_value=BYTE_MIN,
            native_max_value=BYTE_MAX,
            entity_registry_enabled_default=False,
        ),
    )
}


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    entities = []
    for coordinator in entry.runtime_data.coordinators:
        if supports_heating(coordinator):
            entities.append(FlameTargetTemperature(coordinator))
        for description in NUMBERS.values():
            if description.requires_heating and not supports_heating(coordinator):
                continue
            if description.experimental and not entry.options.get(CONF_EXPERIMENTAL):
                continue
            if coordinator.features.enabled(description.capability):
                entities.append(FlameNumber(coordinator, description))
    async_add_entities(entities)


class FlameTargetTemperature(FlameEntity, NumberEntity):
    """Editable heat setpoint; no room measurement is inferred."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_step = TEMPERATURE_STEP
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "target_temperature", ParameterId.HEAT_SETTINGS)

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.unit is not None

    @property
    def native_unit_of_measurement(self):
        return self.coordinator.unit

    @property
    def native_min_value(self):
        return temperature_limits(self.coordinator)[0]

    @property
    def native_max_value(self):
        return temperature_limits(self.coordinator)[1]

    @property
    def native_value(self):
        if not self.available:
            return None
        return display_temperature(
            self.coordinator, self.coordinator.data.require(ParameterId.HEAT_SETTINGS).target_temperature
        )

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.set_target_temperature(target_celsius(self.coordinator, value))


class FlameNumber(FlameEntity, NumberEntity):
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    entity_description: FlameNumberDescription

    def __init__(self, coordinator, description: FlameNumberDescription) -> None:
        super().__init__(coordinator, description.key, description.parameter)
        self.entity_description = description

    @property
    def native_value(self):
        if self.entity_description.setting == "duration":
            data = self.coordinator.data
            return (
                data.parameters[ParameterId.COUNTDOWN].duration
                if data and ParameterId.COUNTDOWN in data.parameters
                else None
            )
        return self.field(self.entity_description.parameter, self.entity_description.setting)

    async def async_set_native_value(self, value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not self.native_min_value <= value <= self.native_max_value
            or int(value) != value
        ):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        await self.coordinator.edit(self.entity_description.parameter, **{self.entity_description.setting: int(value)})
