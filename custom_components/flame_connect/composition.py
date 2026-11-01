"""Explicit composition root for cloud adapters and application use cases."""

import aiohttp

from .adapters.cloud.api import FlameClient
from .adapters.cloud.auth import B2C
from .application.accounts import AccountLinker
from .application.credentials import TokenSet
from .application.ports import TokenStorePort
from .application.tokens import TokenManager


def create_client(session: aiohttp.ClientSession, tokens: TokenSet, save: TokenStorePort) -> FlameClient:
    return FlameClient(session, TokenManager(B2C(session, tokens.policy), tokens, save))


def create_linker(session: aiohttp.ClientSession, policy: str, save: TokenStorePort) -> AccountLinker:
    return AccountLinker(B2C(session, policy), lambda tokens, persist: create_client(session, tokens, persist), save)
