"""Link an identity and discover its devices through application-owned ports."""

from collections.abc import Callable
from dataclasses import dataclass

from ..domain.errors import AuthenticationError
from ..domain.models import Fireplace
from .credentials import TokenSet
from .linking import Transaction
from .ports import AuthorizationPort, FireplacePort, TokenStorePort


@dataclass(frozen=True, repr=False)
class LinkedAccount:
    tokens: TokenSet
    fires: tuple[Fireplace, ...]


class AccountLinker:
    def __init__(
        self,
        provider: AuthorizationPort,
        connect: Callable[[TokenSet, TokenStorePort], FireplacePort],
        save: TokenStorePort,
    ) -> None:
        self.provider, self.connect, self.save = provider, connect, save

    async def link(self, transaction: Transaction, callback: str) -> LinkedAccount:
        tokens = await self.provider.exchange(transaction=transaction, callback=callback)
        if not tokens.refresh_token:
            raise AuthenticationError("Missing refresh token")

        async def rotated(updated: TokenSet) -> None:
            nonlocal tokens
            await self.save(updated)
            tokens = updated

        fires = await self.connect(tokens, rotated).fires()
        return LinkedAccount(tokens, tuple(fires))
