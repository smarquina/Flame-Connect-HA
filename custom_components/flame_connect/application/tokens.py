"""Token lifecycle use case, depending only on abstract ports."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..domain.errors import AuthenticationError
from .ports import RefreshPort, TokenStorePort

TOKEN_REFRESH_MARGIN_SECONDS = 60


class TokenManager:
    """Single refresh in flight; persistence precedes use of rotated credentials."""

    def __init__(self, provider: RefreshPort, tokens: dict[str, Any], save: TokenStorePort) -> None:
        self.provider, self.tokens, self.save = provider, dict(tokens), save
        self.lock = asyncio.Lock()

    async def get(self, rejected: str | None = None) -> str:
        """Refresh shortly before expiration, or after a rejected access token."""
        async with self.lock:
            access = self.tokens.get("access_token")
            if (
                access
                and float(self.tokens.get("expires_at", 0)) > time.time() + TOKEN_REFRESH_MARGIN_SECONDS
                and (rejected is None or rejected != access)
            ):
                return access
            if not self.tokens.get("refresh_token"):
                raise AuthenticationError("Link the account again")
            tokens = await self.provider.refresh(self.tokens["refresh_token"])
            if tokens["account_id"] != self.tokens.get("account_id"):
                raise AuthenticationError("Refreshed account does not match")
            await self.save(tokens)
            self.tokens = tokens
            return tokens["access_token"]
