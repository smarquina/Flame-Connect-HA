"""Outbound capabilities are owned by the application, never by infrastructure."""

from typing import Protocol

from ..domain.models import Fireplace
from ..domain.parameters import FireState, Parameter
from .credentials import TokenSet
from .linking import Transaction


class FireplacePort(Protocol):
    async def fires(self) -> list[Fireplace]: ...
    async def overview(self, fire_id: str) -> FireState: ...
    async def write(self, fire_id: str, parameters: list[Parameter]) -> None: ...


class RefreshPort(Protocol):
    async def refresh(self, refresh_token: str) -> TokenSet: ...


class AuthorizationPort(Protocol):
    async def exchange(self, *, transaction: Transaction, callback: str) -> TokenSet: ...


class TokenStorePort(Protocol):
    async def __call__(self, tokens: TokenSet, /) -> None: ...
