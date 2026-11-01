"""Isolated, bounded B2C form login; no credential, cookie or response logging."""

from __future__ import annotations

import asyncio
import json
import re
from http import HTTPStatus
from urllib.parse import urlencode, urljoin, urlsplit

import aiohttp

from ...application.linking import Transaction
from ...domain.errors import AuthenticationError, ConnectionError, ProtocolError
from .const import (
    HOST,
    HTTP_REQUEST_TIMEOUT_SECONDS,
    LOGIN_EMAIL_MAX_CHARS,
    LOGIN_FIELD_MAX_CHARS,
    LOGIN_MAX_REDIRECTS,
    LOGIN_PASSWORD_MAX_CHARS,
    LOGIN_TIMEOUT_SECONDS,
    POLICIES,
    TENANT,
)
from .http import read_body

ORIGIN = f"https://{HOST}"
BASE = f"{ORIGIN}/{TENANT}/{POLICIES['normal']}/"
REDIRECTS = (
    HTTPStatus.MOVED_PERMANENTLY,
    HTTPStatus.FOUND,
    HTTPStatus.SEE_OTHER,
    HTTPStatus.TEMPORARY_REDIRECT,
    HTTPStatus.PERMANENT_REDIRECT,
)


def trusted_url(url: str) -> bool:
    """Never follow a redirect carrying credentials or cookies off the tenant."""
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
    except ValueError:
        return False


def login_fields(page: str) -> tuple[str, str]:
    """Read only the two JSON string values needed by the hosted B2C form."""
    values = []
    for field in ("csrf", "transId"):
        match = re.search(r'"' + field + r'"\s*:\s*("(?:[^"\\]|\\.)*")', page)
        if match is None:
            raise ProtocolError("Unsupported sign-in page; use browser linking")
        value = json.loads(match[1])
        if not value or len(value) > LOGIN_FIELD_MAX_CHARS or any(char in value for char in "\r\n"):
            raise ProtocolError("Invalid sign-in page")
        values.append(value)
    return values[0], values[1]


async def request(session, method: str, url: str, **kwargs) -> tuple[int, str, str]:
    """Disable automatic redirects; discard provider error bodies and URLs."""
    if not trusted_url(url):
        raise AuthenticationError("Unexpected sign-in destination; use browser linking")
    async with session.request(method, url, allow_redirects=False, **kwargs) as response:
        raw = await read_body(response)
        return response.status, raw.decode("utf-8", errors="replace"), response.headers.get("Location", "")


async def follow(session, url: str, redirect_uri: str | None = None) -> tuple[str, str]:
    """Follow only tenant redirects, stopping before the native callback."""
    for _ in range(LOGIN_MAX_REDIRECTS):
        status, body, location = await request(session, "GET", url)
        if status == HTTPStatus.OK:
            return url, body
        if status not in REDIRECTS or not location:
            raise AuthenticationError("Sign-in requires browser linking")
        next_url = urljoin(url, location)
        if redirect_uri and next_url.startswith(redirect_uri + "?"):
            return next_url, ""
        url = next_url
    raise AuthenticationError("Too many sign-in redirects")


class CredentialLogin:
    """Obtain a one-use callback; the existing PKCE adapter validates and redeems it."""

    async def authorize(self, transaction: Transaction, email: str, password: str) -> str:
        if (
            transaction.policy != "normal"
            or not email
            or not password
            or len(email) > LOGIN_EMAIL_MAX_CHARS
            or len(password) > LOGIN_PASSWORD_MAX_CHARS
        ):
            raise AuthenticationError("Use an email account or browser linking")
        try:
            # A separate jar is necessary: shared HA sessions disable cookies.
            # Unquoted values preserve B2C cookies containing base64 punctuation.
            async with (
                asyncio.timeout(LOGIN_TIMEOUT_SECONDS),
                aiohttp.ClientSession(
                    cookie_jar=aiohttp.CookieJar(quote_cookie=False),
                    timeout=aiohttp.ClientTimeout(total=HTTP_REQUEST_TIMEOUT_SECONDS),
                ) as session,
            ):
                return await self._authorize(session, transaction, email, password)
        except aiohttp.ClientError, TimeoutError:
            raise ConnectionError("Cannot reach the sign-in service") from None
        except ValueError, UnicodeError:
            raise ProtocolError("Unsupported sign-in response; use browser linking") from None

    async def _authorize(self, session, transaction: Transaction, email: str, password: str) -> str:
        page_url, page = await follow(session, transaction.url)
        csrf, tx = login_fields(page)
        query = urlencode({"tx": tx, "p": POLICIES["normal"]})
        status, body, _ = await request(
            session,
            "POST",
            BASE + "SelfAsserted?" + query,
            data={"request_type": "RESPONSE", "email": email, "password": password},
            headers={
                "Origin": ORIGIN,
                "Referer": page_url,
                "X-CSRF-TOKEN": csrf,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        if status != HTTPStatus.OK:
            raise AuthenticationError("Sign-in rejected; check credentials or use browser linking")
        data = json.loads(body)
        if not isinstance(data, dict) or str(data.get("status")) != str(HTTPStatus.OK.value):
            raise AuthenticationError("Sign-in rejected; check credentials or use browser linking")
        confirmed = (
            BASE
            + "api/CombinedSigninAndSignup/confirmed?"
            + urlencode({"rememberMe": "false", "csrf_token": csrf, "tx": tx, "p": POLICIES["normal"]})
        )
        callback, _ = await follow(session, confirmed, transaction.settings.redirect_uri)
        if not callback.startswith(transaction.settings.redirect_uri + "?"):
            raise AuthenticationError("Sign-in requires browser linking")
        return callback
