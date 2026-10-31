"""Numeric settings with explicit protocol ranges and optional controls."""

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.exceptions import ServiceValidationError

from .const import CONF_EXPERIMENTAL, DOMAIN
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


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    entities = []
    for c in entry.runtime_data.coordinators:
        if supports_heating(c):
            entities.append(FlameTargetTemperature(c))
            if c.features.get("PowerBoost") is True:
                entities.append(
                    FlameNumber(
                        c, "boost_duration", ParameterId.HEAT_SETTINGS, BOOST_MIN_MINUTES, BOOST_MAX_MINUTES, "min"
                    )
                )
        if c.features.get("FlameFanSpeed"):
            entities.append(FlameNumber(c, "speed", ParameterId.FLAME_EFFECT, FLAME_SPEED_MIN, FLAME_SPEED_MAX))
        if entry.options.get(CONF_EXPERIMENTAL):
            if c.features.get("CountDownTimer"):
                entities.append(
                    FlameNumber(
                        c, "duration", ParameterId.COUNTDOWN, COUNTDOWN_MIN_MINUTES, COUNTDOWN_MAX_MINUTES, "min"
                    )
                )
            if c.features.get("Sound"):
                entities.extend(
                    [
                        FlameNumber(c, "volume", ParameterId.SOUND, BYTE_MIN, BYTE_MAX),
                        FlameNumber(c, "sound_file", ParameterId.SOUND, BYTE_MIN, BYTE_MAX),
                    ]
                )
    async_add_entities(entities)


class FlameTargetTemperature(FlameEntity, NumberEntity):
    """Editable setpoint, independent of the read-only reported temperature."""

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
            self.coordinator, self.coordinator.data.require(ParameterId.HEAT_SETTINGS).temperature
        )

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.edit(ParameterId.HEAT_SETTINGS, temperature=target_celsius(self.coordinator, value))


class FlameNumber(FlameEntity, NumberEntity):
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, key, parameter, minimum, maximum, unit=None) -> None:
        super().__init__(coordinator, key, parameter)
        self.key = key
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_registry_enabled_default = key in ("speed", "boost_duration")

    @property
    def native_value(self):
        if self.key == "duration":
            data = self.coordinator.data
            return (
                data.parameters[ParameterId.COUNTDOWN].duration
                if data and ParameterId.COUNTDOWN in data.parameters
                else None
            )
        return self.field(self.required_parameter, "boost" if self.key == "boost_duration" else self.key)

    async def async_set_native_value(self, value: float) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not self.native_min_value <= value <= self.native_max_value
            or int(value) != value
        ):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_value")
        setting = "boost" if self.key == "boost_duration" else self.key
        await self.coordinator.edit(self.required_parameter, **{setting: int(value)})
