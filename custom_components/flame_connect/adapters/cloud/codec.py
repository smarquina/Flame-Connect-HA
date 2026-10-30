"""Map external JSON/Base64 to domain value objects without leaking HTTP inward."""

import base64
import binascii
from typing import Any

from ...domain.errors import ProtocolError
from ...domain.parameters import SIZES, FireState, Parameter


def decode_parameter(value: dict[str, Any]) -> Parameter:
    try:
        ident, encoded = value["ParameterId"], value["Value"]
        if type(ident) is not int or not isinstance(encoded, str) or len(encoded) > 1024:
            raise ValueError
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) < 3 or int.from_bytes(raw[:2], "little") != ident or raw[2] != len(raw) - 3:
            raise ValueError
        if ident in SIZES and raw[2] != SIZES[ident]:
            raise ValueError
    except (KeyError, TypeError, ValueError, binascii.Error) as err:
        raise ProtocolError("Invalid parameter envelope") from err
    return Parameter(ident, raw)


def encode_parameter(value: Parameter) -> dict[str, Any]:
    return {"ParameterId": value.id, "Value": base64.b64encode(value.raw).decode()}


def decode_state(fire_id: str, body: Any) -> FireState:
    if not isinstance(body, dict):
        raise ProtocolError("Invalid overview")
    overview = body.get("WifiFireOverview", body.get("WiFiFireOverview"))
    if (
        not isinstance(overview, dict)
        or overview.get("FireId") != fire_id
        or not isinstance(overview.get("Parameters"), list)
    ):
        raise ProtocolError("Overview does not match fireplace")
    parameters = {}
    for item in overview["Parameters"]:
        if not isinstance(item, dict):
            raise ProtocolError("Invalid parameter")
        parameter = decode_parameter(item)
        if parameter.id in parameters:
            raise ProtocolError("Duplicate parameter")
        parameters[parameter.id] = parameter
    return FireState(fire_id, parameters)
