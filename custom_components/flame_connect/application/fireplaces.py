"""Read/modify/write use case shared by all incoming entity adapters."""

import asyncio
from collections.abc import Callable

from ..domain.parameters import FireState, Parameter
from .ports import FireplacePort


class FireplaceService:
    """Serializes reads and commands for one physical device across platforms."""

    def __init__(self, gateway: FireplacePort, fire_id: str) -> None:
        self.gateway, self.fire_id = gateway, fire_id
        self.lock = asyncio.Lock()

    async def read(self) -> FireState:
        async with self.lock:
            return await self.gateway.overview(self.fire_id)

    async def execute(self, build: Callable[[FireState], list[Parameter]]) -> FireState:
        async with self.lock:
            before = await self.gateway.overview(self.fire_id)
            await self.gateway.write(self.fire_id, build(before))
            return await self.gateway.overview(self.fire_id)
