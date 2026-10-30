from unittest.mock import AsyncMock, patch

import pytest

from custom_components.flame_connect.adapters.cloud.api import ORIGIN, FlameClient
from custom_components.flame_connect.domain.errors import (
    AccessDenied,
    AuthenticationError,
    CommandError,
    DeviceUnavailable,
    ProtocolError,
)
from custom_components.flame_connect.domain.parameters import Parameter


@pytest.fixture
def api():
    manager = AsyncMock()
    manager.get.return_value = "jwt-fixture"
    return FlameClient(AsyncMock(), manager)


async def test_reads(api, fire, overview):
    with patch(
        "custom_components.flame_connect.adapters.cloud.api.json_request",
        AsyncMock(side_effect=[(200, [fire]), (200, overview)]),
    ) as send:
        assert await api.fires() == [fire]
        state = await api.overview("fixture-fire")
        assert state.fire_id == "fixture-fire"
        assert send.call_args.args[2] == ORIGIN + "/api/Fires/GetFireOverview"
        assert send.call_args.kwargs["params"] == {"FireId": "fixture-fire"}
        assert send.call_args.kwargs["headers"]["Authorization"] == "Bearer jwt-fixture"


@pytest.mark.parametrize("value", [None, {}, [{}], [{"FireId": 1}], [{"FireId": "a"}, {"FireId": "a"}]])
async def test_invalid_list(api, value):
    with patch("custom_components.flame_connect.adapters.cloud.api.json_request", AsyncMock(return_value=(200, value))):
        with pytest.raises(ProtocolError):
            await api.fires()


@pytest.mark.parametrize(
    "value,error",
    [
        (None, ProtocolError),
        ({}, ProtocolError),
        ({"ResultCode": True}, ProtocolError),
        ({"ResultCode": 1}, DeviceUnavailable),
    ],
)
async def test_overview_errors(api, value, error):
    with patch("custom_components.flame_connect.adapters.cloud.api.json_request", AsyncMock(return_value=(200, value))):
        with pytest.raises(error):
            await api.overview("a")


@pytest.mark.parametrize(
    "status,error",
    [
        (401, AuthenticationError),
        (403, AccessDenied),
        (410, DeviceUnavailable),
        (400, CommandError),
        (302, CommandError),
    ],
)
async def test_statuses(api, status, error):
    with patch(
        "custom_components.flame_connect.adapters.cloud.api.json_request", AsyncMock(return_value=(status, None))
    ) as send:
        with pytest.raises(error):
            await api.fires()
        assert send.await_count == (2 if status == 401 else 1)


async def test_retry_read(api):
    with patch(
        "custom_components.flame_connect.adapters.cloud.api.json_request",
        AsyncMock(side_effect=[(401, None), (200, [])]),
    ) as send:
        assert await api.fires() == []
        assert send.await_count == 2


async def test_write_no_replay(api):
    param = Parameter(236, b"\xec\x00\x01\x01")
    with patch(
        "custom_components.flame_connect.adapters.cloud.api.json_request", AsyncMock(return_value=(401, None))
    ) as send:
        with pytest.raises(CommandError, match="not repeated"):
            await api.write("a", [param])
        send.assert_awaited_once()
    with patch(
        "custom_components.flame_connect.adapters.cloud.api.json_request",
        AsyncMock(return_value=(200, {"FireId": "a", "IsException": False})),
    ):
        await api.write("a", [param])
    for value in [None, {}, {"FireId": "b", "IsException": False}, {"FireId": "a", "IsException": True}]:
        with patch(
            "custom_components.flame_connect.adapters.cloud.api.json_request", AsyncMock(return_value=(200, value))
        ):
            with pytest.raises(CommandError):
                await api.write("a", [param])
    for parameters in [[], [Parameter(64541, b"")]]:
        with pytest.raises(ProtocolError):
            await api.write("a", parameters)
