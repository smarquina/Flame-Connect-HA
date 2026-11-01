"""Independent boundary contracts: malformed input, immutable snapshots and persistence."""

from dataclasses import FrozenInstanceError, replace
from unittest.mock import AsyncMock

import pytest

from custom_components.flame_connect.adapters.cloud.auth import create_transaction
from custom_components.flame_connect.adapters.cloud.codec import decode_fireplace, decode_parameter, encode_parameter
from custom_components.flame_connect.adapters.cloud.tokens import decode_tokens, encode_tokens
from custom_components.flame_connect.application.accounts import AccountLinker
from custom_components.flame_connect.domain.capabilities import Capability
from custom_components.flame_connect.domain.errors import AuthenticationError, ConnectionError, ProtocolError
from custom_components.flame_connect.domain.parameters import FireState, Parameter
from custom_components.flame_connect.domain.protocol import ParameterId


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {},
        {"access_token": "x"},
        {"access_token": "x", "account_id": "a", "expires_at": float("nan")},
        {"access_token": "x", "account_id": "a", "expires_at": True},
        {"access_token": "x", "account_id": "a", "policy": "unsupported"},
        {"access_token": "x", "account_id": "a", "refresh_token": 123},
    ],
)
def test_invalid_saved_tokens_require_reauthentication(value):
    with pytest.raises(AuthenticationError):
        decode_tokens(value)


def test_tokens_roundtrip_without_disclosing_secrets(tokens):
    value = decode_tokens(tokens)
    assert encode_tokens(value) == tokens
    assert tokens["access_token"] not in repr(value)
    assert tokens["refresh_token"] not in repr(value)
    with pytest.raises(FrozenInstanceError):
        value.expires_at = 1
    legacy = {key: item for key, item in tokens.items() if key != "policy"}
    assert decode_tokens(legacy).policy == "normal"


@pytest.mark.parametrize(
    "changed",
    [
        {"FriendlyName": 1},
        {"WithHeat": 1},
        {"FireFeature": []},
        {"FireFeature": {"Sound": "true"}},
        {"FireFeature": {"FlamePresetOptions": True}},
        {"FireFeature": {"FlamePresetOptions": -1}},
    ],
)
def test_invalid_inventory_fields_are_rejected(fire, changed):
    with pytest.raises(ProtocolError):
        decode_fireplace({**fire, **changed})


def test_capabilities_are_a_detached_allowlisted_snapshot(fire):
    fire["FireFeature"]["AccessCode"] = "private"
    device = decode_fireplace(fire)
    fire["FireFeature"]["Sound"] = False
    assert device.capabilities.enabled(Capability.SOUND)
    assert "AccessCode" not in device.capabilities.values
    with pytest.raises(TypeError):
        device.capabilities.values[Capability.SOUND] = False
    assert not decode_fireplace({"FireId": "minimal"}).supports_heating


def test_state_copies_input_and_rejects_inconsistent_identity():
    packet = Parameter(ParameterId.TEMPERATURE_UNIT, b"\xec\x00\x01\x01")
    source = {packet.id: packet}
    state = FireState("fire", source)
    source.clear()
    assert state.require(packet.id) == packet
    with pytest.raises(TypeError):
        state.parameters[packet.id] = packet
    with pytest.raises(ProtocolError):
        FireState("fire", {ParameterId.MODE: packet})
    with pytest.raises(ProtocolError):
        packet.field("mode")
    with pytest.raises(ProtocolError):
        _ = packet.duration
    with pytest.raises(ProtocolError):
        _ = packet.target_temperature


@pytest.mark.parametrize(
    "ident,raw",
    [(321, b""), (True, b"\x01\x00\x00"), (321, b"\x41\x01\x00"), (321, bytearray(b"\x41\x01\x03\x01\x15\x00"))],
)
def test_direct_parameter_construction_cannot_bypass_validation(ident, raw):
    with pytest.raises(ProtocolError):
        Parameter(ident, raw)


def test_unknown_parameter_roundtrip_is_lossless():
    packet = Parameter(600, b"\x58\x02\x03\x10\x20\xff")
    assert decode_parameter(encode_parameter(packet)) == packet


async def test_account_linker_preserves_rotated_credentials_before_return(tokens, fire):
    provider, gateway, save = AsyncMock(), AsyncMock(), AsyncMock()
    initial = decode_tokens(tokens)
    rotated = replace(initial, refresh_token="rotated")
    provider.exchange.return_value = initial

    def connect(received, persist):
        assert received == initial

        async def inventory():
            await persist(rotated)
            save.assert_awaited_once_with(rotated)
            return [decode_fireplace(fire)]

        gateway.fires.side_effect = inventory
        return gateway

    result = await AccountLinker(provider, connect, save).link(create_transaction(), "fixture-return")
    assert result.tokens == rotated
    assert result.fires[0].fire_id == fire["FireId"]
    assert rotated.refresh_token not in repr(result)


async def test_failed_token_persistence_never_uses_rotated_access(tokens):
    from custom_components.flame_connect.application.tokens import TokenManager

    provider, save = AsyncMock(), AsyncMock(side_effect=ConnectionError("storage failed"))
    original = replace(decode_tokens(tokens), expires_at=0)
    provider.refresh.return_value = replace(original, access_token="new", refresh_token="rotated")
    manager = TokenManager(provider, original, save)
    with pytest.raises(ConnectionError):
        await manager.get()
    assert manager.tokens == original
