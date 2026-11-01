import asyncio
import json
import time
from dataclasses import replace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import aiohttp
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from custom_components.flame_connect.adapters.cloud.auth import (
    B2C,
    CLIENT_ID,
    HOST,
    ISSUER,
    REDIRECT_URI,
)
from custom_components.flame_connect.adapters.cloud.auth import (
    create_transaction as Transaction,
)
from custom_components.flame_connect.adapters.cloud.http import json_request
from custom_components.flame_connect.adapters.cloud.tokens import decode_tokens
from custom_components.flame_connect.application.tokens import TokenManager
from custom_components.flame_connect.domain.errors import AuthenticationError, ConnectionError, ProtocolError


@pytest.fixture
def signing():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key())), "kid": "test", "alg": "RS256"}

    def token(**claims):
        return jwt.encode(
            {"iss": ISSUER, "exp": int(time.time()) + 3600, "oid": "account", **claims},
            private,
            algorithm="RS256",
            headers={"kid": "test"},
        )

    return token, key


@pytest.fixture
def provider(signing):
    token, key = signing
    provider = B2C(AsyncMock())
    provider.metadata = {
        "issuer": ISSUER,
        "token_endpoint": f"https://{HOST}/token",
        "jwks_uri": f"https://{HOST}/keys",
    }
    provider.keys = [key]
    return provider


def test_transaction():
    tx = Transaction()
    query = parse_qs(urlsplit(tx.url).query)
    assert query["code_challenge_method"] == ["S256"]
    assert tx.verifier not in tx.url
    assert query["redirect_uri"] == [REDIRECT_URI]
    callback = REDIRECT_URI + "/?code=one&state=" + tx.state
    assert tx.consume(callback) == "one"
    with pytest.raises(AuthenticationError):
        tx.consume(callback)
    assert tx.verifier not in repr(tx)


@pytest.mark.parametrize(
    "kind", ["host", "path", "scheme", "fragment", "state", "duplicate", "error", "no_code", "expired", "long"]
)
def test_bad_return(kind):
    tx = Transaction()
    raw = REDIRECT_URI + "?code=one&state=" + tx.state
    raw = {
        "host": raw.replace("://auth", "://evil"),
        "path": raw.replace("?", "/bad?"),
        "scheme": raw.replace("msal", "https"),
        "fragment": raw + "#bad",
        "state": raw + "bad",
        "duplicate": raw + "&code=two",
        "error": raw + "&error=denied",
        "no_code": REDIRECT_URI + "?state=" + tx.state,
        "long": raw + "&pad=" + "a" * 32000,
    }.get(kind, raw)
    if kind == "expired":
        tx.created -= 601
    with pytest.raises(AuthenticationError):
        tx.consume(raw)


async def test_discovery(signing):
    _, key = signing
    p = B2C(AsyncMock())
    metadata = {"issuer": ISSUER, "token_endpoint": f"https://{HOST}/token", "jwks_uri": f"https://{HOST}/keys"}
    with patch(
        "custom_components.flame_connect.adapters.cloud.auth.json_request",
        AsyncMock(side_effect=[(200, metadata), (200, {"keys": [key]})]),
    ):
        await p.discover()
    assert p.keys == [key]
    with pytest.raises(AuthenticationError):
        B2C(AsyncMock(), "bad")
    for url in ["http://evil", f"https://user@{HOST}/", f"https://{HOST}:443/", "https://evil", None, ":bad"]:
        assert not p._trusted(url)


@pytest.mark.parametrize(
    "payload",
    [(200, {}), (200, {"issuer": ISSUER, "token_endpoint": "https://evil", "jwks_uri": "https://evil"}), (400, None)],
)
async def test_discovery_bad(payload):
    with patch("custom_components.flame_connect.adapters.cloud.auth.json_request", AsyncMock(return_value=payload)):
        with pytest.raises(ProtocolError):
            await B2C(AsyncMock()).discover()


async def test_bad_jwks():
    data = {
        "issuer": ISSUER,
        "token_endpoint": "https://HOST/token".replace("HOST", HOST),
        "jwks_uri": f"https://{HOST}/keys",
    }
    with patch(
        "custom_components.flame_connect.adapters.cloud.auth.json_request",
        AsyncMock(side_effect=[(200, data), (200, {})]),
    ):
        with pytest.raises(ProtocolError):
            await B2C(AsyncMock()).discover()


async def test_verify(provider, signing):
    token, _ = signing
    assert (await provider.verify(token()))["oid"] == "account"
    assert (await provider.verify(token(aud=CLIENT_ID, nonce="n"), identity=True, nonce="n"))["nonce"] == "n"
    for bad in [
        token(iss="other"),
        token(exp=1),
        token(nbf=time.time() + 3600),
        token(tfp="bad"),
        token()[:-1] + "!",
        "bad",
        "a" * 20001,
        None,
    ]:
        with pytest.raises(AuthenticationError):
            await provider.verify(bad)
    with pytest.raises(AuthenticationError):
        await provider.verify(token(aud="bad"), identity=True)
    with pytest.raises(AuthenticationError):
        await provider.verify(token(aud=CLIENT_ID, nonce="bad"), identity=True, nonce="n")
    with pytest.raises(AuthenticationError):
        await provider.verify(jwt.encode({"exp": time.time() + 3600}, "s" * 32, algorithm="HS256"))
    with patch.object(provider, "discover", AsyncMock()):
        provider.keys = []
        with pytest.raises(AuthenticationError):
            await provider.verify(token())


async def test_exchange(provider, signing):
    token, _ = signing
    tx = Transaction()
    raw = REDIRECT_URI + "?code=one&state=" + tx.state
    response = {"access_token": token(), "id_token": token(aud=CLIENT_ID, nonce=tx.nonce), "refresh_token": "new"}
    with patch(
        "custom_components.flame_connect.adapters.cloud.auth.json_request", AsyncMock(return_value=(200, response))
    ) as request:
        result = await provider.exchange(transaction=tx, callback=raw)
        assert result.account_id == "account"
        form = request.call_args.kwargs["data"]
        assert form["code_verifier"] == tx.verifier and "client_secret" not in form
    with patch(
        "custom_components.flame_connect.adapters.cloud.auth.json_request",
        AsyncMock(return_value=(200, {"access_token": token()})),
    ):
        assert (await provider.exchange(refresh_token="old")).refresh_token == "old"
    with pytest.raises(AuthenticationError):
        await provider.exchange()
    for response in [
        (400, {"error_description": "secret"}),
        (200, {}),
        (200, {"access_token": token(oid=None, sub=None)}),
    ]:
        with patch(
            "custom_components.flame_connect.adapters.cloud.auth.json_request", AsyncMock(return_value=response)
        ):
            with pytest.raises(AuthenticationError) as err:
                await provider.exchange(refresh_token="old")
            assert "secret" not in str(err.value)


async def test_manager(tokens):
    provider = AsyncMock()
    save = AsyncMock()
    new = {**tokens, "access_token": "new", "refresh_token": "rotated"}
    provider.refresh.return_value = decode_tokens(new)
    manager = TokenManager(provider, decode_tokens(tokens), save)
    assert await manager.get() == tokens["access_token"]
    assert await manager.get(rejected="old") == tokens["access_token"]
    manager.tokens = replace(manager.tokens, expires_at=1)
    results = await asyncio.gather(*[manager.get() for _ in range(5)])
    assert results == ["new"] * 5
    provider.refresh.assert_awaited_once()
    save.assert_awaited_once_with(decode_tokens(new))
    manager.tokens = replace(manager.tokens, expires_at=1)
    provider.refresh.return_value = decode_tokens({**new, "account_id": "other"})
    with pytest.raises(AuthenticationError):
        await manager.get()
    manager.tokens = replace(manager.tokens, refresh_token=None)
    with pytest.raises(AuthenticationError):
        await manager.get()


class Content:
    def __init__(self, raw):
        self.raw = raw

    async def iter_chunked(self, size):
        yield self.raw


class Response:
    def __init__(self, status, raw):
        self.status = status
        self.content = Content(raw)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.parametrize(
    "status,raw,expected", [(200, b'{"x":1}', {"x": 1}), (200, b"", None), (401, b"bad", None), (403, b"bad", None)]
)
async def test_json_request(status, raw, expected):
    from unittest.mock import Mock

    session = Mock()
    session.request.return_value = Response(status, raw)
    assert await json_request(session, "GET", f"https://{HOST}/") == (status, expected)
    assert session.request.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "status,raw,error",
    [
        (500, b"", ConnectionError),
        (429, b"", ConnectionError),
        (200, b"bad", ProtocolError),
        (200, b"x" * (2 * 1024 * 1024 + 1), ProtocolError),
    ],
)
async def test_json_failure(status, raw, error):
    from unittest.mock import Mock

    session = Mock()
    session.request.return_value = Response(status, raw)
    with pytest.raises(error):
        await json_request(session, "GET", f"https://{HOST}/")


async def test_network_failure():
    from unittest.mock import Mock

    session = Mock()
    session.request.side_effect = aiohttp.ClientError("secret")
    with pytest.raises(ConnectionError, match="Cannot reach"):
        await json_request(session, "GET", f"https://{HOST}/")


async def test_cold_start_refresh_adapter(provider, signing):
    token, _ = signing
    provider.metadata = None

    async def discover():
        provider.metadata = {"token_endpoint": f"https://{HOST}/token"}

    with (
        patch.object(provider, "discover", AsyncMock(side_effect=discover)),
        patch(
            "custom_components.flame_connect.adapters.cloud.auth.json_request",
            AsyncMock(return_value=(200, {"access_token": token()})),
        ),
    ):
        result = await provider.refresh("old")
        assert result.account_id == "account"
        assert result.refresh_token == "old"
    provider.metadata = None
    with patch.object(provider, "discover", AsyncMock(side_effect=discover)):
        assert (await provider.verify(token()))["oid"] == "account"
    assert not provider._trusted(f"https://{HOST}:invalid/")
    with patch(
        "custom_components.flame_connect.adapters.cloud.auth.json_request",
        AsyncMock(return_value=(200, {"access_token": token(oid=123)})),
    ):
        with pytest.raises(AuthenticationError, match="stable account"):
            await provider.refresh("old")


def test_unknown_policy_cannot_build_transaction():
    with pytest.raises(AuthenticationError):
        Transaction("unsupported")
