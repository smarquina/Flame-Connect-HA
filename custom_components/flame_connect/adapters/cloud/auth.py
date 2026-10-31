"""Azure B2C public-client PKCE; secrets never enter logs or reprs."""

from __future__ import annotations

import asyncio
import secrets
from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

import aiohttp
import jwt

from ...application.linking import OAuthSettings, Transaction
from ...domain.errors import AuthenticationError, ConnectionError, ProtocolError
from .const import (
    CLIENT_ID,
    HOST,
    HTTP_MAX_RESPONSE_BYTES,
    HTTP_REQUEST_TIMEOUT_SECONDS,
    HTTP_RESPONSE_CHUNK_BYTES,
    ISSUER,
    POLICIES,
    REDIRECT_URI,
    SCOPE,
    TENANT,
    TOKEN_MAX_CHARS,
)


def create_transaction(policy: str = "normal") -> Transaction:
    """Supply B2C-specific settings to the pure PKCE use case."""
    if policy not in POLICIES:
        raise AuthenticationError("Unknown policy")
    settings = OAuthSettings(
        CLIENT_ID, REDIRECT_URI, f"https://{HOST}/{TENANT}/{POLICIES[policy]}/oauth2/v2.0/authorize", SCOPE, policy
    )
    return Transaction(settings)


async def json_request(session: aiohttp.ClientSession, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:
    """Fixed-host callers only. Bound responses and suppress sensitive upstream errors."""
    try:
        async with session.request(
            method,
            url,
            allow_redirects=False,
            timeout=aiohttp.ClientTimeout(total=HTTP_REQUEST_TIMEOUT_SECONDS),
            **kwargs,
        ) as response:
            raw = bytearray()
            async for chunk in response.content.iter_chunked(HTTP_RESPONSE_CHUNK_BYTES):
                raw.extend(chunk)
                if len(raw) > HTTP_MAX_RESPONSE_BYTES:
                    raise ProtocolError("Response too large")
            if response.status >= HTTPStatus.INTERNAL_SERVER_ERROR or response.status == HTTPStatus.TOO_MANY_REQUESTS:
                raise ConnectionError("Service temporarily unavailable")
            if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                return response.status, None
            import json

            try:
                data = json.loads(raw) if raw else None
            except (ValueError, UnicodeDecodeError) as err:
                raise ProtocolError("Invalid JSON response") from err
            return response.status, data
    except (aiohttp.ClientError, TimeoutError) as err:
        raise ConnectionError("Cannot reach Flame Connect") from err


class B2C:
    """OIDC metadata, keys and token exchange bound to the known tenant."""

    def __init__(self, session: aiohttp.ClientSession, policy: str = "normal") -> None:
        if policy not in POLICIES:
            raise AuthenticationError("Unknown policy")
        self.session = session
        self.policy = policy
        self.metadata: dict[str, Any] | None = None
        self.keys: list[dict[str, Any]] = []

    def _trusted(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            return (
                parsed.scheme == "https"
                and parsed.hostname == HOST
                and parsed.port is None
                and not parsed.username
                and not parsed.password
                and not parsed.fragment
            )
        except TypeError, ValueError:
            return False

    async def discover(self) -> None:
        """Reject redirected or substituted token/JWKS hosts."""
        status, data = await json_request(
            self.session,
            "GET",
            f"https://{HOST}/{TENANT}/{POLICIES[self.policy]}/v2.0/.well-known/openid-configuration",
        )
        if (
            status != HTTPStatus.OK
            or not isinstance(data, dict)
            or data.get("issuer") != ISSUER
            or not all(isinstance(data.get(k), str) and self._trusted(data[k]) for k in ("token_endpoint", "jwks_uri"))
        ):
            raise ProtocolError("Invalid identity metadata")
        status, keys = await json_request(self.session, "GET", data["jwks_uri"])
        if status != HTTPStatus.OK or not isinstance(keys, dict) or not isinstance(keys.get("keys"), list):
            raise ProtocolError("Invalid identity keys")
        self.metadata, self.keys = data, keys["keys"]

    async def verify(self, token: str, *, identity: bool = False, nonce: str | None = None) -> dict[str, Any]:
        """Validate signature, issuer, time and identity nonce/audience."""
        if not isinstance(token, str) or len(token) > TOKEN_MAX_CHARS:
            raise AuthenticationError("Invalid token")
        if self.metadata is None:
            await self.discover()
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                raise ValueError
            key = next((k for k in self.keys if k.get("kid") == header.get("kid") and k.get("kty") == "RSA"), None)
            if key is None:
                await self.discover()
                key = next((k for k in self.keys if k.get("kid") == header.get("kid") and k.get("kty") == "RSA"), None)
            if key is None:
                raise ValueError

            def decode() -> dict[str, Any]:
                public = jwt.PyJWK.from_dict(key).key
                return jwt.decode(
                    token,
                    public,
                    algorithms=["RS256"],
                    issuer=ISSUER,
                    audience=CLIENT_ID if identity else None,
                    options={"verify_aud": identity, "require": ["exp", "iss"]},
                )

            claims = await asyncio.to_thread(decode)
            if claims.get("tfp", claims.get("acr", POLICIES[self.policy])).lower() != POLICIES[self.policy].lower():
                raise ValueError
            if nonce is not None and (
                not isinstance(claims.get("nonce"), str) or not secrets.compare_digest(claims["nonce"], nonce)
            ):
                raise ValueError
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, KeyError, AttributeError) as err:
            raise AuthenticationError("Token validation failed") from err

    async def exchange(
        self, *, transaction: Transaction | None = None, callback: str = "", refresh_token: str | None = None
    ) -> dict[str, Any]:
        """Redeem once or refresh; preserve old refresh token if not rotated."""
        form = {"client_id": CLIENT_ID, "scope": SCOPE}
        if transaction is not None:
            form.update(
                grant_type="authorization_code",
                code=transaction.consume(callback),
                redirect_uri=REDIRECT_URI,
                code_verifier=transaction.verifier,
            )
        elif refresh_token:
            form.update(grant_type="refresh_token", refresh_token=refresh_token)
        else:
            raise AuthenticationError("Missing authorization")
        if self.metadata is None:
            await self.discover()
        status, data = await json_request(
            self.session, "POST", self.metadata["token_endpoint"], data=form, headers={"Accept": "application/json"}
        )
        if status != HTTPStatus.OK or not isinstance(data, dict) or not isinstance(data.get("access_token"), str):
            raise AuthenticationError("Authorization rejected; link the account again")
        claims = await self.verify(data["access_token"])
        identity = {}
        if data.get("id_token"):
            identity = await self.verify(
                data["id_token"], identity=True, nonce=transaction.nonce if transaction else None
            )
        account = claims.get("oid") or claims.get("sub") or identity.get("oid") or identity.get("sub")
        if not isinstance(account, str) or not account:
            raise AuthenticationError("Token has no stable account identifier")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token") or refresh_token,
            "expires_at": claims["exp"],
            "account_id": account,
            "policy": self.policy,
        }

    async def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Implement the application token-refresh port."""
        return await self.exchange(refresh_token=refresh_token)
