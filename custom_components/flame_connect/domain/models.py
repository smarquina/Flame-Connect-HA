"""Normalized fireplace identity and immutable capabilities."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .capabilities import Capability
from .protocol import DEFAULT_TARGET_MAX_CELSIUS, OPTIFLAME_TARGET_MAX_CELSIUS, FlamePalette


@dataclass(frozen=True)
class FireCapabilities:
    """Only declared, typed capabilities cross the cloud boundary."""

    values: Mapping[Capability, bool | int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", MappingProxyType(dict(self.values)))

    def enabled(self, name: Capability) -> bool:
        return self.values.get(name) is True

    @property
    def flame_palette(self) -> int:
        return self.values.get(Capability.FLAME_PRESET_OPTIONS, FlamePalette.YELLOW_RED_BLUE)


@dataclass(frozen=True)
class Fireplace:
    """Stable device identity, independent of API field names."""

    fire_id: str
    name: str | None = None
    brand: str | None = None
    model: str | None = None
    product_type: str | None = None
    is_iot: bool = False
    with_heat: bool = False
    capabilities: FireCapabilities = field(default_factory=FireCapabilities)

    @property
    def supports_heating(self) -> bool:
        return self.with_heat or any(
            self.capabilities.enabled(name) for name in (Capability.ADVANCED_HEAT, Capability.SIMPLE_HEAT)
        )

    @property
    def target_max_celsius(self) -> float:
        if self.product_type in ("Optiflame V2", "Optiflame V3", "Optiflame V4") or "OLF" in (self.model or ""):
            return OPTIFLAME_TARGET_MAX_CELSIUS
        return DEFAULT_TARGET_MAX_CELSIUS
