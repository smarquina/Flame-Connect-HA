"""Lossless TLV decoding and edits. Offsets include the three-byte header."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .errors import ProtocolError

SIZES = {236: 1, 321: 3, 322: 20, 323: 5, 325: 1, 326: 3, 327: 9, 329: 4, 369: 2, 370: 8}
FIELDS = {
    236: {"unit": (3, 0, 1)},
    321: {"mode": (3, 0, 1)},
    322: {"flame": (3, 0, 1), "speed": (4, 1, 5), "brightness": (5, 0, 3), "color": (19, 0, 6)},
    323: {"heat": (3, 0, 1), "heat_mode": (4, 0, 4), "boost": (7, 0, 255)},
    326: {"timer": (3, 0, 1)},
    369: {"volume": (3, 0, 255), "sound_file": (4, 0, 255)},
}


@dataclass(frozen=True)
class Parameter:
    """A validated packet; edits preserve all untouched bytes."""

    id: int
    raw: bytes

    def field(self, name: str) -> int:
        """Read a known field."""
        offset = FIELDS[self.id][name][0]
        return self.raw[offset] + (1 if name == "speed" else 0)

    @property
    def temperature(self) -> float:
        """Read the app's decimal-text fraction, not a fraction of 256."""
        offset = 4 if self.id == 321 else 5
        if self.id not in (321, 323):
            raise ProtocolError("Invalid temperature encoding")
        return float(f"{self.raw[offset]}.{self.raw[offset + 1]}")

    @property
    def duration(self) -> int:
        """Countdown minutes."""
        return int.from_bytes(self.raw[4:6], "little")

    def edit(self, **changes: int | float) -> Parameter:
        """Modify known fields, rejecting silent truncation and unknown writes."""
        raw = bytearray(self.raw)
        for name, value in changes.items():
            if name == "temperature" and self.id == 323:
                try:
                    number = Decimal(str(value))
                    if (
                        not number.is_finite()
                        or not 7 <= number <= 255
                        or number * 10 != (number * 10).to_integral_value()
                    ):
                        raise ValueError
                    raw[5], raw[6] = int(number), int(number * 10) % 10
                except (InvalidOperation, ValueError) as err:
                    raise ProtocolError("Invalid target temperature") from err
            elif name == "duration" and self.id == 326:
                if type(value) is not int or not 0 <= value <= 32767:
                    raise ProtocolError("Invalid countdown duration")
                raw[4:6] = value.to_bytes(2, "little")
            elif name in FIELDS.get(self.id, {}):
                offset, low, high = FIELDS[self.id][name]
                if type(value) is not int or not low <= value <= high:
                    raise ProtocolError("Invalid parameter value")
                raw[offset] = value - (1 if name == "speed" else 0)
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
        params = [self.require(321).edit(mode=int(on))]
        if 323 in self.parameters:
            params.append(self.parameters[323].edit(**({"heat": 1} if on else {"heat": 0, "heat_mode": 0, "boost": 0})))
        if 322 in self.parameters:
            params.append(self.parameters[322].edit(flame=int(on)))
        return params


def color_labels(preset: int) -> list[str]:
    """Model palettes share numeric codes but use different visible colors."""
    a, b, c = {0: ("Yellow", "Red", "Blue"), 1: ("Yellow", "Orange", "Blue"), 2: ("Amber", "Orange", "Yellow")}.get(
        preset, ("Yellow", "Red", "Blue")
    )
    return [f"{a} + {b} + {c}", f"{a} + {b}", f"{a} + {c}", c, b, a, f"{c} + {b}"]
