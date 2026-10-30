"""Fixed-endpoint cloud API. Writes are never automatically retried."""

from __future__ import annotations

from typing import Any

import aiohttp

from ...application.tokens import TokenManager
from ...domain.errors import AccessDenied, AuthenticationError, CommandError, DeviceUnavailable, ProtocolError
from ...domain.parameters import FireState, Parameter
from .auth import json_request
from .codec import decode_state, encode_parameter

ORIGIN = "https://mobileapi.gdhv-iot.com"
HEADERS = {
    "app_name": "FlameConnect",
    "api_version": "1.0",
    "app_version": "2.24.2",
    "app_device_os": "Android",
    "device_version": "Unknown",
    "device_manufacturer": "Unknown",
    "device_model": "Unknown",
    "lang_code": "es-ES",
    "country": "ES",
    "logging_required_flag": "0",
    "Accept": "application/json",
}


class FlameClient:
    """No arbitrary URLs, header overrides or generic command endpoints."""

    def __init__(self, session: aiohttp.ClientSession, tokens: TokenManager) -> None:
        self.session, self.tokens = session, tokens

    async def _request(
        self, path: str, *, body: dict[str, Any] | None = None, params: dict[str, str] | None = None
    ) -> Any:
        access = await self.tokens.get()

        async def send(token: str) -> tuple[int, Any]:
            kwargs: dict[str, Any] = {"headers": {**HEADERS, "Authorization": f"Bearer {token}"}}
            if body is not None:
                kwargs["json"] = body
            if params:
                kwargs["params"] = params
            return await json_request(self.session, "POST" if body is not None else "GET", ORIGIN + path, **kwargs)

        status, data = await send(access)
        if status == 401:
            access = await self.tokens.get(rejected=access)
            if body is not None:
                raise CommandError("Token renewed; command was not repeated. Read state and try again")
            status, data = await send(access)
        if status == 401:
            raise AuthenticationError("Link the account again")
        if status == 403:
            raise AccessDenied("Access denied to this fireplace")
        if status == 410:
            raise DeviceUnavailable("Fireplace no longer available")
        if status != 200:
            raise CommandError("Request rejected")
        return data

    async def fires(self) -> list[dict[str, Any]]:
        data = await self._request("/api/Fires/GetFires")
        if (
            not isinstance(data, list)
            or any(not isinstance(f, dict) or not isinstance(f.get("FireId"), str) or not f["FireId"] for f in data)
            or len({f["FireId"] for f in data}) != len(data)
        ):
            raise ProtocolError("Invalid fireplace list")
        return data

    async def overview(self, fire_id: str) -> FireState:
        data = await self._request("/api/Fires/GetFireOverview", params={"FireId": fire_id})
        if not isinstance(data, dict) or type(data.get("ResultCode")) is not int:
            raise ProtocolError("Invalid overview result")
        if data["ResultCode"] != 0:
            raise DeviceUnavailable("Fireplace is offline or busy")
        return decode_state(fire_id, data)

    async def write(self, fire_id: str, parameters: list[Parameter]) -> None:
        if not parameters or any(p.id not in (236, 321, 322, 323, 326, 369) for p in parameters):
            raise ProtocolError("Unsupported write")
        data = await self._request(
            "/api/Fires/WriteWifiParameters",
            body={"FireId": fire_id, "Parameters": [encode_parameter(p) for p in parameters]},
        )
        if not isinstance(data, dict) or data.get("FireId") != fire_id or data.get("IsException") is not False:
            raise CommandError("Device rejected the command or returned an invalid result")
