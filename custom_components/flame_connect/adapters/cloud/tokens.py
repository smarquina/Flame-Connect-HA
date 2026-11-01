"""Map persisted token records without changing existing config entries."""

from collections.abc import Mapping
from math import isfinite
from typing import TypedDict

from ...application.credentials import TokenSet
from ...domain.errors import AuthenticationError
from .const import POLICIES


class StoredTokens(TypedDict):
    access_token: str
    refresh_token: str | None
    expires_at: float
    account_id: str
    policy: str


def decode_tokens(value: object) -> TokenSet:
    if not isinstance(value, Mapping):
        raise AuthenticationError("Invalid saved tokens; link the account again")
    access, refresh = value.get("access_token"), value.get("refresh_token")
    expires, account, policy = value.get("expires_at", 0), value.get("account_id"), value.get("policy", "normal")
    if (
        not isinstance(access, str)
        or not access
        or (refresh is not None and (not isinstance(refresh, str) or not refresh))
        or isinstance(expires, bool)
        or not isinstance(expires, (int, float))
        or not isfinite(expires)
        or not isinstance(account, str)
        or not account
        or not isinstance(policy, str)
        or policy not in POLICIES
    ):
        raise AuthenticationError("Invalid saved tokens; link the account again")
    return TokenSet(access, refresh, float(expires), account, policy)


def encode_tokens(tokens: TokenSet) -> StoredTokens:
    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "expires_at": tokens.expires_at,
        "account_id": tokens.account_id,
        "policy": tokens.policy,
    }
