"""Read-only diagnostic information from actual parameters."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.entity import EntityCategory

from .domain.protocol import PARAMETER_HEADER_BYTES, ParameterId
from .entity import FlameEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities(
        [
            FlameSensor(c, key, parameter)
            for c in entry.runtime_data.coordinators
            for key, parameter in [
                ("temperature", ParameterId.MODE),
                ("errors", ParameterId.ERRORS),
                ("firmware", ParameterId.FIRMWARE),
            ]
        ]
    )


class FlameSensor(FlameEntity, SensorEntity):
    def __init__(self, coordinator, key, parameter) -> None:
        super().__init__(coordinator, key, parameter)
        self.key = key
        self._attr_entity_registry_enabled_default = False
        if key == "temperature":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            # Keep the existing unique ID, but retire the unverified reading.
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        return self.key != "temperature" and super().available

    @property
    def native_unit_of_measurement(self):
        return self.coordinator.unit if self.key == "temperature" else None

    @property
    def native_value(self):
        if self.key == "temperature":
            # Parameter 321 contains a setpoint, not a measured temperature.
            return None
        data = self.coordinator.data
        if not data or self.required_parameter not in data.parameters:
            return None
        parameter = data.parameters[self.required_parameter]
        # Firmware and error layouts vary by model; report exact payload bytes
        # as hex rather than inventing semantic firmware versions or messages.
        return parameter.raw[PARAMETER_HEADER_BYTES:].hex(" ")
