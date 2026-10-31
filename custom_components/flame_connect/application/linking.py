"""PKCE transaction use case: no framework or transport dependencies."""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlencode, urlsplit

from ..domain.errors import AuthenticationError

PKCE_VERIFIER_ENTROPY_BYTES = 48
OAUTH_STATE_NONCE_ENTROPY_BYTES = 32
AUTHORIZATION_LIFETIME_SECONDS = 600
MAX_CALLBACK_URL_CHARS = 32000


@dataclass(frozen=True)
class OAuthSettings:
    """Authorization details injected by an identity-provider adapter."""

    client_id: str
    redirect_uri: str
    authorize_endpoint: str
    scope: str
    policy: str


@dataclass(repr=False)
class Transaction:
    """A single use transaction owned by a config flow, not persisted."""

    settings: OAuthSettings
    verifier: str = field(default_factory=lambda: secrets.token_urlsafe(PKCE_VERIFIER_ENTROPY_BYTES))
    state: str = field(default_factory=lambda: secrets.token_urlsafe(OAUTH_STATE_NONCE_ENTROPY_BYTES))
    nonce: str = field(default_factory=lambda: secrets.token_urlsafe(OAUTH_STATE_NONCE_ENTROPY_BYTES))
    created: float = field(default_factory=time.time)
    consumed: bool = False

    @property
    def policy(self) -> str:
        return self.settings.policy

    @property
    def url(self) -> str:
        """Open the official hosted page, never a custom password form."""
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).decode().rstrip("=")
        return (
            self.settings.authorize_endpoint
            + "?"
            + urlencode(
                {
                    "client_id": self.settings.client_id,
                    "response_type": "code",
                    "response_mode": "query",
                    "redirect_uri": self.settings.redirect_uri,
                    "scope": self.settings.scope,
                    "state": self.state,
                    "nonce": self.nonce,
                    "code_challenge": challenge,
                    "code_challenge_method": "S256",
                    "ui_locales": "es",
                }
            )
        )

    def consume(self, callback: str) -> str:
        """Validate scheme, state, timeout and duplicates before consuming."""
        try:
            if not isinstance(callback, str) or len(callback) > MAX_CALLBACK_URL_CHARS:
                raise ValueError
            url = urlsplit(callback)
            expected = urlsplit(self.settings.redirect_uri)
            query = parse_qs(url.query, keep_blank_values=True, strict_parsing=True)
            if (
                url.scheme != expected.scheme
                or url.netloc != expected.netloc
                or url.path.rstrip("/") != expected.path.rstrip("/")
                or url.fragment
            ):
                raise ValueError
            if (
                self.consumed
                or time.time() - self.created > AUTHORIZATION_LIFETIME_SECONDS
                or any(len(v) != 1 for v in query.values())
            ):
                raise ValueError
            if not secrets.compare_digest(query.get("state", [""])[0], self.state):
                raise ValueError
            code = query.get("code", [""])[0]
            if not code or "error" in query:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as err:
            raise AuthenticationError("Invalid or expired authorization return; start again") from err
        self.consumed = True
        return code
