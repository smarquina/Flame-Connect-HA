"""Map external JSON/Base64 to domain value objects without leaking HTTP inward."""

import base64
import binascii
from typing import Any

from ...domain.capabilities import CAPABILITY_FLAGS, CAPABILITY_PRESETS, Capability
from ...domain.errors import ProtocolError
from ...domain.models import FireCapabilities, Fireplace
from ...domain.parameters import FireState, Parameter

MAX_ENCODED_PARAMETER_CHARS = 1024


def decode_parameter(value: dict[str, Any]) -> Parameter:
    try:
        ident, encoded = value["ParameterId"], value["Value"]
        if type(ident) is not int or not isinstance(encoded, str) or len(encoded) > MAX_ENCODED_PARAMETER_CHARS:
            raise ValueError
        raw = base64.b64decode(encoded, validate=True)
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


def decode_fireplace(value: Any) -> Fireplace:
    """Validate known inventory fields and drop unrelated API metadata."""
    if not isinstance(value, dict) or not isinstance(value.get("FireId"), str) or not value["FireId"]:
        raise ProtocolError("Invalid fireplace identity")
    for key in ("FriendlyName", "Brand", "ProductModel", "ProductType"):
        if value.get(key) is not None and not isinstance(value[key], str):
            raise ProtocolError("Invalid fireplace description")
    for key in ("IsIotFire", "WithHeat"):
        if value.get(key) is not None and type(value[key]) is not bool:
            raise ProtocolError("Invalid fireplace capability")
    capabilities = decode_capabilities(value.get("FireFeature"))
    return Fireplace(
        fire_id=value["FireId"],
        name=value.get("FriendlyName"),
        brand=value.get("Brand"),
        model=value.get("ProductModel"),
        product_type=value.get("ProductType"),
        is_iot=value.get("IsIotFire") is True,
        with_heat=value.get("WithHeat") is True,
        capabilities=capabilities,
    )


def decode_capabilities(features: Any) -> FireCapabilities:
    """Unknown metadata never enters capability-dependent controls or diagnostics."""

    if features is None:
        features = {}
    if not isinstance(features, dict):
        raise ProtocolError("Invalid fireplace features")
    capabilities: dict[Capability, bool | int] = {}
    for key, item in features.items():
        if key in CAPABILITY_FLAGS:
            if type(item) is not bool:
                raise ProtocolError("Invalid feature flag")
            capabilities[Capability(key)] = item
        elif key in CAPABILITY_PRESETS:
            if type(item) is not int or item < 0:
                raise ProtocolError("Invalid feature preset")
            capabilities[Capability(key)] = item
    return FireCapabilities(capabilities)
