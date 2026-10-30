"""Read-only diagnostic information from actual parameters."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.unit_conversion import TemperatureConverter

from .entity import FlameEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities(
        [
            FlameSensor(c, key, parameter)
            for c in entry.runtime_data.coordinators
            for key, parameter in [("temperature", 321), ("errors", 329), ("firmware", 327)]
        ]
    )


class FlameSensor(FlameEntity, SensorEntity):
    def __init__(self, coordinator, key, parameter) -> None:
        super().__init__(coordinator, key, parameter)
        self.key = key
        if key == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False

    @property
    def available(self) -> bool:
        return super().available and (self.key != "temperature" or self.coordinator.unit is not None)

    @property
    def native_unit_of_measurement(self):
        return self.coordinator.unit if self.key == "temperature" else None

    @property
    def native_value(self):
        data = self.coordinator.data
        if not data or self.required_parameter not in data.parameters:
            return None
        parameter = data.parameters[self.required_parameter]
        if self.key == "temperature":
            return TemperatureConverter.convert(parameter.temperature, "°C", self.coordinator.unit)
        # Firmware and error layouts vary by model; report exact payload bytes
        # as hex rather than inventing semantic firmware versions or messages.
        return parameter.raw[3:].hex(" ")
