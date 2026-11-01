"""UI account linking via the official B2C native return."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .adapters.cloud.auth import create_transaction
from .adapters.cloud.credential_login import CredentialLogin
from .adapters.cloud.tokens import decode_tokens, encode_tokens
from .application.credentials import TokenSet
from .application.linking import Transaction
from .composition import create_client, create_linker
from .const import CONF_EXPERIMENTAL, CONF_FIRES, CONF_TEMPERATURE_UNIT, DEFAULT_OPTIONS, DOMAIN, NAME
from .domain.errors import AuthenticationError, ConnectionError, FlameError
from .domain.models import Fireplace


def temperature_selector() -> selector.SelectSelector:
    """Keep stored C/F values while translating the automatic preference."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["auto", "C", "F"],
            translation_key="temperature_unit",
        )
    )


class FlameConnectFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Keep verifier and nonce in memory; persist tokens only after validation."""

    VERSION = 1

    def __init__(self) -> None:
        self.transaction: Transaction | None = None
        self.tokens: TokenSet | None = None
        self.fires: list[Fireplace] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> FlameOptionsFlow:
        return FlameOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self.transaction = create_transaction(policy=user_input["policy"])
            if user_input["policy"] == "normal" and user_input.get("login_method") == "credentials":
                return await self.async_step_credentials()
            return await self.async_step_link()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("login_method", default="credentials"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=["credentials", "browser"], translation_key="login_method"
                        )
                    ),
                    vol.Required("policy", default="normal"): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=["normal", "social"], translation_key="policy")
                    ),
                }
            ),
        )

    async def async_step_credentials(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors = {}
        if user_input is not None:
            if user_input.get("use_browser"):
                self.transaction = create_transaction()
                return await self.async_step_link()
            self.transaction = create_transaction()
            try:
                native_return = await CredentialLogin().authorize(
                    self.transaction, user_input["email"].strip(), user_input["password"]
                )
            except AuthenticationError:
                errors["base"] = "credentials_rejected"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except FlameError:
                errors["base"] = "invalid_response"
            else:
                return await self.async_step_link({"callback_url": native_return})
        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(
                {
                    vol.Optional("email", default=""): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
                    ),
                    vol.Optional("password", default=""): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    ),
                    vol.Optional("use_browser", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors = {}
        if self.transaction is None:
            self.transaction = create_transaction()
        if user_input is not None:
            try:
                account = await create_linker(
                    async_get_clientsession(self.hass), self.transaction.policy, self._store_tokens
                ).link(self.transaction, user_input["callback_url"].strip())
                self.tokens, self.fires = account.tokens, list(account.fires)
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except FlameError:
                errors["base"] = "invalid_response"
            else:
                await self.async_set_unique_id(self.tokens.account_id)
                if self.source == config_entries.SOURCE_REAUTH:
                    self._abort_if_unique_id_mismatch()
                    entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(
                        entry, data_updates={"tokens": encode_tokens(self.tokens)}
                    )
                self._abort_if_unique_id_configured()
                return await self.async_step_devices()
            # A redeemed/expired code cannot be reused after any error.
            self.transaction = create_transaction(policy=self.transaction.policy)
        return self.async_show_form(
            step_id="link",
            data_schema=vol.Schema(
                {
                    vol.Required("callback_url"): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={
                "authorize_url": self.transaction.url,
                "installation_url": "https://github.com/smarquina/Flame-Connect-HA/blob/main/docs/installation.md",
            },
        )

    async def async_step_devices(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if not self.fires:
            return self.async_abort(reason="no_devices")
        choices = {fire.fire_id: fire.name or fire.model or "Fireplace" for fire in self.fires if fire.is_iot}
        if not choices:
            return self.async_abort(reason="no_wifi_devices")
        if user_input is not None:
            selected = user_input[CONF_FIRES]
            if selected and set(selected) <= choices.keys():
                if self.source == config_entries.SOURCE_RECONFIGURE:
                    entry = self._get_reconfigure_entry()
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_FIRES: selected},
                        options={**entry.options, CONF_TEMPERATURE_UNIT: user_input[CONF_TEMPERATURE_UNIT]},
                    )
                return self.async_create_entry(
                    title=NAME,
                    data={"tokens": encode_tokens(self.tokens), CONF_FIRES: selected},
                    options={**DEFAULT_OPTIONS, CONF_TEMPERATURE_UNIT: user_input[CONF_TEMPERATURE_UNIT]},
                )
        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_FIRES, default=list(choices)): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[selector.SelectOptionDict(value=k, label=v) for k, v in choices.items()],
                            multiple=True,
                        )
                    ),
                    vol.Required(CONF_TEMPERATURE_UNIT, default="auto"): temperature_selector(),
                }
            ),
            errors={"base": "select_device"} if user_input is not None else {},
        )

    async def _store_tokens(self, tokens: TokenSet) -> None:
        self.tokens = tokens
        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, "tokens": encode_tokens(tokens)})

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        try:
            self.tokens = decode_tokens(entry.data["tokens"])
            client = create_client(async_get_clientsession(self.hass), self.tokens, self._store_tokens)
            self.fires = await client.fires()
        except AuthenticationError:
            entry.async_start_reauth(self.hass)
            return self.async_abort(reason="reauthentication_required")
        except ConnectionError, FlameError:
            return self.async_show_form(
                step_id="reconfigure", data_schema=vol.Schema({}), errors={"base": "cannot_connect"}
            )
        return await self.async_step_devices()

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        self.transaction = create_transaction(policy=entry_data["tokens"].get("policy", "normal"))
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return await self.async_step_user()
        return self.async_show_form(step_id="reauth_confirm", data_schema=vol.Schema({}))


class FlameOptionsFlow(config_entries.OptionsFlow):
    """Options affect interpretation and optional controls, never send commands."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TEMPERATURE_UNIT, default=self.config_entry.options.get(CONF_TEMPERATURE_UNIT, "auto")
                    ): temperature_selector(),
                    vol.Required(
                        CONF_EXPERIMENTAL, default=self.config_entry.options.get(CONF_EXPERIMENTAL, False)
                    ): bool,
                }
            ),
        )
