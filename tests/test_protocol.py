import base64

import pytest

from custom_components.flame_connect.adapters.cloud.codec import decode_parameter, decode_state, encode_parameter
from custom_components.flame_connect.domain.errors import ProtocolError
from custom_components.flame_connect.domain.parameters import FireState, color_labels


def packet(ident, payload):
    return decode_parameter(
        {
            "ParameterId": ident,
            "Value": base64.b64encode(ident.to_bytes(2, "little") + bytes([len(payload)]) + bytes(payload)).decode(),
        }
    )


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"ParameterId": True, "Value": ""},
        {"ParameterId": 321, "Value": "!"},
        {"ParameterId": 321, "Value": "AA=="},
        {"ParameterId": 321, "Value": "QQEAAQ=="},
        {"ParameterId": 321, "Value": 1},
        {"ParameterId": 321, "Value": "A" * 1025},
        {"ParameterId": 321, "Value": "QQEBAQ=="},
    ],
)
def test_invalid_envelopes(value):
    with pytest.raises(ProtocolError):
        decode_parameter(value)


def test_state_and_power(overview):
    state = decode_state("fixture-fire", overview)
    for parameter in state.parameters.values():
        assert decode_parameter(encode_parameter(parameter)) == parameter
    for on in [True, False]:
        params = state.power(on)
        assert params[0].field("mode") == int(on)
        assert params[1].field("heat") == int(on)
        assert params[2].field("flame") == int(on)
    assert state.require(321).mode_setpoint >= 0
    minimal = FireState("fixture-fire", {321: state.require(321)})
    assert len(minimal.power(True)) == 1
    with pytest.raises(ProtocolError):
        state.require(999)
    alternate = {"WiFiFireOverview": overview["WifiFireOverview"]}
    assert decode_state("fixture-fire", alternate) == state


@pytest.mark.parametrize(
    "body",
    [
        None,
        {},
        {"WifiFireOverview": {}},
        {"WifiFireOverview": {"FireId": "wrong", "Parameters": []}},
        {"WifiFireOverview": {"FireId": "fixture-fire", "Parameters": [1]}},
    ],
)
def test_invalid_state(body):
    with pytest.raises(ProtocolError):
        decode_state("fixture-fire", body)


def test_duplicate(overview):
    overview["WifiFireOverview"]["Parameters"].append(overview["WifiFireOverview"]["Parameters"][0])
    with pytest.raises(ProtocolError):
        decode_state("fixture-fire", overview)


@pytest.mark.parametrize("color", range(7))
def test_color_preserves_bytes(color):
    original = packet(322, list(range(20)))
    changed = original.edit(color=color)
    assert changed.raw[19] == color
    assert all(a == b for i, (a, b) in enumerate(zip(original.raw, changed.raw, strict=True)) if i != 19)


@pytest.mark.parametrize(
    "ident,payload,changes,field,value",
    [
        (322, [0] * 20, {"speed": 5}, "speed", 5),
        (323, [0, 0, 21, 0, 0], {"heat_mode": 2}, "heat_mode", 2),
        (236, [1], {"unit": 0}, "unit", 0),
        (369, [0, 0], {"volume": 10}, "volume", 10),
    ],
)
def test_edits(ident, payload, changes, field, value):
    assert packet(ident, payload).edit(**changes).field(field) == value


def test_temperature_timer():
    assert packet(323, [0, 0, 21, 0, 0]).with_target_temperature(23.5).target_temperature == 23.5
    assert packet(326, [0, 0, 0]).edit(duration=300).duration == 300
    assert packet(321, [1, 20, 10]).mode_setpoint == 20.1
    with pytest.raises(ProtocolError):
        _ = packet(236, [1]).target_temperature
    assert color_labels(0)[3] == "Blue"
    assert color_labels(1)[4] == "Orange"
    assert color_labels(2)[5] == "Amber"
    assert color_labels(99) == color_labels(0)


@pytest.mark.parametrize(
    "parameter,changes",
    [(packet(323, [0, 0, 21, 0, 0]), {"target_temperature": value}) for value in [6, 256, 23.55, "nan", "bad"]]
    + [(packet(326, [0, 0, 0]), {"duration": v}) for v in [-1, 32768, 1.5]]
    + [
        (packet(322, [0] * 20), {"color": 7}),
        (packet(322, [0] * 20), {"speed": True}),
        (packet(321, [0, 21, 0]), {"reset": 1}),
    ],
)
def test_invalid_edit(parameter, changes):
    with pytest.raises(ProtocolError):
        parameter.edit(**changes)
