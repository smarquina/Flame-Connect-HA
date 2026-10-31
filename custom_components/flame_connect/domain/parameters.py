"""Lossless TLV decoding and edits. Offsets include the three-byte header."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

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

    def field(self, name: str) -> int:
        """Read a known field."""
        spec = FIELDS[self.id][name]
        return self.raw[spec.offset] + spec.display_offset

    @property
    def temperature(self) -> float:
        """Read the app's decimal-text fraction, not a fraction of 256."""
        offset = MODE_TEMPERATURE_OFFSET if self.id == ParameterId.MODE else HEAT_TEMPERATURE_OFFSET
        if self.id not in (ParameterId.MODE, ParameterId.HEAT_SETTINGS):
            raise ProtocolError("Invalid temperature encoding")
        return float(f"{self.raw[offset]}.{self.raw[offset + TEMPERATURE_FRACTION_RELATIVE_OFFSET]}")

    @property
    def duration(self) -> int:
        """Countdown minutes."""
        return int.from_bytes(
            self.raw[COUNTDOWN_DURATION_OFFSET : COUNTDOWN_DURATION_OFFSET + COUNTDOWN_DURATION_BYTES], "little"
        )

    def edit(self, **changes: int | float) -> Parameter:
        """Modify known fields, rejecting silent truncation and unknown writes."""
        raw = bytearray(self.raw)
        for name, value in changes.items():
            if name == "temperature" and self.id == ParameterId.HEAT_SETTINGS:
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
    parameters: dict[int, Parameter]

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
    a, b, c = {
        FlamePalette.YELLOW_RED_BLUE: ("Yellow", "Red", "Blue"),
        FlamePalette.YELLOW_ORANGE_BLUE: ("Yellow", "Orange", "Blue"),
        FlamePalette.AMBER_ORANGE_YELLOW: ("Amber", "Orange", "Yellow"),
    }.get(preset, ("Yellow", "Red", "Blue"))
    return [f"{a} + {b} + {c}", f"{a} + {b}", f"{a} + {c}", c, b, a, f"{c} + {b}"]
