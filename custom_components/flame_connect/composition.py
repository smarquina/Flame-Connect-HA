"""Explicit composition root for cloud adapters and application use cases."""

import aiohttp

from .adapters.cloud.api import FlameClient
from .adapters.cloud.auth import B2C, create_transaction
from .adapters.cloud.credential_login import CredentialLogin
from .adapters.cloud.tokens import decode_tokens, encode_tokens
from .application.accounts import AccountLinker
from .application.credentials import TokenSet
from .application.ports import CredentialAuthorizationPort, TokenStorePort
from .application.tokens import TokenManager

__all__ = [
    "create_client",
    "create_credential_login",
    "create_linker",
    "create_transaction",
    "decode_tokens",
    "encode_tokens",
]


def create_credential_login() -> CredentialAuthorizationPort:
    return CredentialLogin()


def create_client(session: aiohttp.ClientSession, tokens: TokenSet, save: TokenStorePort) -> FlameClient:
    return FlameClient(session, TokenManager(B2C(session, tokens.policy), tokens, save))


def create_linker(session: aiohttp.ClientSession, policy: str, save: TokenStorePort) -> AccountLinker:
    return AccountLinker(B2C(session, policy), lambda tokens, persist: create_client(session, tokens, persist), save)
