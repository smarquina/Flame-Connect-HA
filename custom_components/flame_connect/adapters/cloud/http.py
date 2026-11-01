"""Bounded HTTPS response transport; callers own destination and authentication policy."""

import json
from http import HTTPStatus
from typing import Any

import aiohttp

from ...domain.errors import ConnectionError, ProtocolError
from .const import HTTP_MAX_RESPONSE_BYTES, HTTP_REQUEST_TIMEOUT_SECONDS, HTTP_RESPONSE_CHUNK_BYTES


async def read_body(response: aiohttp.ClientResponse) -> bytes:
    raw = bytearray()
    async for chunk in response.content.iter_chunked(HTTP_RESPONSE_CHUNK_BYTES):
        raw.extend(chunk)
        if len(raw) > HTTP_MAX_RESPONSE_BYTES:
            raise ProtocolError("Response too large")
    if response.status >= HTTPStatus.INTERNAL_SERVER_ERROR or response.status == HTTPStatus.TOO_MANY_REQUESTS:
        raise ConnectionError("Service temporarily unavailable")
    return bytes(raw)


async def json_request(session: aiohttp.ClientSession, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:
    """Never follow redirects or expose sensitive provider response bodies."""
    try:
        async with session.request(
            method,
            url,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=HTTP_REQUEST_TIMEOUT_SECONDS),
            **kwargs,
        ) as response:
            raw = await read_body(response)
            if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                return response.status, None
            try:
                return response.status, json.loads(raw) if raw else None
            except (ValueError, UnicodeDecodeError) as err:
                raise ProtocolError("Invalid JSON response") from err
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ConnectionError("Cannot reach Flame Connect") from err
