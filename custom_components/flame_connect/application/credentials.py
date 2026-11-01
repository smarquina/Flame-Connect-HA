"""Token values passed through ports; never include credentials in representations."""

from dataclasses import dataclass


@dataclass(frozen=True, repr=False)
class TokenSet:
    access_token: str
    refresh_token: str | None
    expires_at: float
    account_id: str
    policy: str = "normal"
