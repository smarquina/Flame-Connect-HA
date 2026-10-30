"""Stable identity, device grouping and shared snapshot access."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FireCoordinator


class FlameEntity(CoordinatorEntity[FireCoordinator]):
    _attr_has_entity_name = True
    required_parameter: int | None = None

    def __init__(self, coordinator: FireCoordinator, key: str, parameter: int | None = None) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.fire_id}_{key}"
        self._attr_translation_key = key
        self.required_parameter = parameter
        fire = coordinator.fire
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.fire_id)},
            name=fire.get("FriendlyName") or "Fireplace",
            manufacturer=fire.get("Brand") or "Glen Dimplex",
            model=fire.get("ProductModel"),
            configuration_url="https://www.flame-connect.com/",
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and (self.required_parameter is None or self.required_parameter in self.coordinator.data.parameters)
        )

    def field(self, parameter: int, key: str) -> int | None:
        if self.coordinator.data and (value := self.coordinator.data.parameters.get(parameter)):
            return value.field(key)
        return None
