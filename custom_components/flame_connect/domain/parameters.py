"""Lossless TLV decoding and edits. Offsets include the three-byte header."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

from .errors import ProtocolError
from .protocol import (
    BOOST_CLEARED_MINUTES,
    BYTE_MAX,
    COUNTDOWN_DURATION_BYTES,
    COUNTDOWN_DURATION_OFFSET,
    COUNTDOWN_MAX_MINUTES,
    COUNTDOWN_MIN_MINUTES,
    FIELDS,
    HEAT_TEMPERATURE_OFFSET,
    MODE_TEMPERATURE_OFFSET,
    PARAMETER_HEADER_BYTES,
    PARAMETER_ID_BYTES,
    PARAMETER_LENGTH_OFFSET,
    PARAMETER_PAYLOAD_SIZES,
    TEMPERATURE_DECIMAL_FACTOR,
    TEMPERATURE_FRACTION_RELATIVE_OFFSET,
    WIRE_TEMPERATURE_MIN_CELSIUS,
    FlamePalette,
    HeatMode,
    ParameterId,
    SwitchState,
)


@dataclass(frozen=True)
class Parameter:
    """A validated packet; edits preserve all untouched bytes."""

    id: int
    raw: bytes

    def __post_init__(self) -> None:
        if (
            (type(self.id) is not int and not isinstance(self.id, ParameterId))
            or not isinstance(self.raw, bytes)
            or len(self.raw) < PARAMETER_HEADER_BYTES
            or int.from_bytes(self.raw[:PARAMETER_ID_BYTES], "little") != self.id
            or self.raw[PARAMETER_LENGTH_OFFSET] != len(self.raw) - PARAMETER_HEADER_BYTES
            or (
                self.id in PARAMETER_PAYLOAD_SIZES
                and self.raw[PARAMETER_LENGTH_OFFSET] != PARAMETER_PAYLOAD_SIZES[self.id]
            )
        ):
            raise ProtocolError("Invalid parameter envelope")

    def field(self, name: str) -> int:
        """Read a known field."""
        if name not in FIELDS.get(self.id, {}):
            raise ProtocolError("Unsupported parameter field")
        spec = FIELDS[self.id][name]
        return self.raw[spec.offset] + spec.display_offset

    def _setpoint(self, expected: ParameterId, offset: int) -> float:
        if self.id != expected:
            raise ProtocolError("Unsupported setpoint parameter")
        return float(f"{self.raw[offset]}.{self.raw[offset + TEMPERATURE_FRACTION_RELATIVE_OFFSET]}")

    @property
    def mode_setpoint(self) -> float:
        """MODE echoes the selected setpoint; it is not a room measurement."""
        return self._setpoint(ParameterId.MODE, MODE_TEMPERATURE_OFFSET)

    @property
    def target_temperature(self) -> float:
        """Confirmed heat setpoint in Celsius."""
        return self._setpoint(ParameterId.HEAT_SETTINGS, HEAT_TEMPERATURE_OFFSET)

    def with_target_temperature(self, celsius: float) -> Parameter:
        """Edit a heat setpoint while retaining every unrelated byte."""
        return self.edit(target_temperature=celsius)

    @property
    def duration(self) -> int:
        """Countdown minutes."""
        if self.id != ParameterId.COUNTDOWN:
            raise ProtocolError("Unsupported countdown parameter")
        return int.from_bytes(
            self.raw[COUNTDOWN_DURATION_OFFSET : COUNTDOWN_DURATION_OFFSET + COUNTDOWN_DURATION_BYTES], "little"
        )

    def edit(self, **changes: int | float) -> Parameter:
        """Modify known fields, rejecting silent truncation and unknown writes."""
        raw = bytearray(self.raw)
        for name, value in changes.items():
            if name == "target_temperature" and self.id == ParameterId.HEAT_SETTINGS:
                try:
                    number = Decimal(str(value))
                    if (
                        not number.is_finite()
                        or not WIRE_TEMPERATURE_MIN_CELSIUS <= number <= BYTE_MAX
                        or number * TEMPERATURE_DECIMAL_FACTOR
                        != (number * TEMPERATURE_DECIMAL_FACTOR).to_integral_value()
                    ):
                        raise ValueError
                    raw[HEAT_TEMPERATURE_OFFSET] = int(number)
                    raw[HEAT_TEMPERATURE_OFFSET + TEMPERATURE_FRACTION_RELATIVE_OFFSET] = (
                        int(number * TEMPERATURE_DECIMAL_FACTOR) % TEMPERATURE_DECIMAL_FACTOR
                    )
                except (InvalidOperation, ValueError) as err:
                    raise ProtocolError("Invalid target temperature") from err
            elif name == "duration" and self.id == ParameterId.COUNTDOWN:
                if type(value) is not int or not COUNTDOWN_MIN_MINUTES <= value <= COUNTDOWN_MAX_MINUTES:
                    raise ProtocolError("Invalid countdown duration")
                raw[COUNTDOWN_DURATION_OFFSET : COUNTDOWN_DURATION_OFFSET + COUNTDOWN_DURATION_BYTES] = value.to_bytes(
                    COUNTDOWN_DURATION_BYTES, "little"
                )
            elif name in FIELDS.get(self.id, {}):
                spec = FIELDS[self.id][name]
                if type(value) is not int or not spec.minimum <= value <= spec.maximum:
                    raise ProtocolError("Invalid parameter value")
                raw[spec.offset] = value - spec.display_offset
            else:
                raise ProtocolError("Unsupported parameter edit")
        return Parameter(self.id, bytes(raw))


@dataclass(frozen=True)
class FireState:
    """State belongs to exactly one fireplace."""

    fire_id: str
    parameters: Mapping[int, Parameter]

    def __post_init__(self) -> None:
        snapshot = dict(self.parameters)
        if any(key != parameter.id for key, parameter in snapshot.items()):
            raise ProtocolError("Parameter identity mismatch")
        object.__setattr__(self, "parameters", MappingProxyType(snapshot))

    def require(self, ident: int) -> Parameter:
        """A missing parameter must not produce invented default bytes."""
        if ident not in self.parameters:
            raise ProtocolError("Device did not return required parameter")
        return self.parameters[ident]

    def power(self, on: bool) -> list[Parameter]:
        """Mirror the application power action, preserving optional fields."""
        params = [self.require(ParameterId.MODE).edit(mode=int(on))]
        if ParameterId.HEAT_SETTINGS in self.parameters:
            changes = (
                {"heat": SwitchState.ON.value}
                if on
                else {
                    "heat": SwitchState.OFF.value,
                    "heat_mode": HeatMode.NORMAL.value,
                    "boost": BOOST_CLEARED_MINUTES,
                }
            )
            params.append(self.parameters[ParameterId.HEAT_SETTINGS].edit(**changes))
        if ParameterId.FLAME_EFFECT in self.parameters:
            params.append(self.parameters[ParameterId.FLAME_EFFECT].edit(flame=int(on)))
        return params


def color_labels(preset: int) -> list[str]:
    """Model palettes share numeric codes but use different visible colors."""
    palettes: dict[int, tuple[str, str, str]] = {
        FlamePalette.YELLOW_RED_BLUE: ("Yellow", "Red", "Blue"),
        FlamePalette.YELLOW_ORANGE_BLUE: ("Yellow", "Orange", "Blue"),
        FlamePalette.AMBER_ORANGE_YELLOW: ("Amber", "Orange", "Yellow"),
    }
    a, b, c = palettes.get(preset, ("Yellow", "Red", "Blue"))
    return [f"{a} + {b} + {c}", f"{a} + {b}", f"{a} + {c}", c, b, a, f"{c} + {b}"]
