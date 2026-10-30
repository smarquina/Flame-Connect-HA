"""Outbound capabilities are owned by the application, never by infrastructure."""

from typing import Any, Protocol

from ..domain.parameters import FireState, Parameter


class FireplacePort(Protocol):
    async def fires(self) -> list[dict[str, Any]]: ...
    async def overview(self, fire_id: str) -> FireState: ...
    async def write(self, fire_id: str, parameters: list[Parameter]) -> None: ...


class RefreshPort(Protocol):
    async def refresh(self, refresh_token: str) -> dict[str, Any]: ...


class TokenStorePort(Protocol):
    async def __call__(self, tokens: dict[str, Any]) -> None: ...
