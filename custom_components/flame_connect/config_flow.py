"""UI account linking via the official B2C native return."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .adapters.cloud.api import FlameClient
from .adapters.cloud.auth import B2C, create_transaction
from .application.linking import Transaction
from .application.tokens import TokenManager
from .const import CONF_EXPERIMENTAL, CONF_FIRES, CONF_TEMPERATURE_UNIT, DEFAULT_OPTIONS, DOMAIN, NAME
from .domain.errors import AuthenticationError, ConnectionError, FlameError


class FlameConnectFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Keep verifier and nonce in memory; persist tokens only after validation."""

    VERSION = 1

    def __init__(self) -> None:
        self.transaction: Transaction | None = None
        self.tokens: dict[str, Any] = {}
        self.fires: list[dict[str, Any]] = []

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> FlameOptionsFlow:
        return FlameOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            self.transaction = create_transaction(policy=user_input["policy"])
            return await self.async_step_link()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("policy", default="normal"): vol.In(["normal", "social"])}),
        )

    async def async_step_link(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors = {}
        if self.transaction is None:
            self.transaction = create_transaction()
        if user_input is not None:
            try:
                provider = B2C(async_get_clientsession(self.hass), self.transaction.policy)
                self.tokens = await provider.exchange(
                    transaction=self.transaction, callback=user_input["callback_url"].strip()
                )
                if not self.tokens.get("refresh_token"):
                    raise AuthenticationError("Missing refresh token")

                client = FlameClient(
                    async_get_clientsession(self.hass), TokenManager(provider, self.tokens, self._store_tokens)
                )
                self.fires = await client.fires()
            except AuthenticationError:
                errors["base"] = "invalid_auth"
            except ConnectionError:
                errors["base"] = "cannot_connect"
            except FlameError:
                errors["base"] = "invalid_response"
            else:
                await self.async_set_unique_id(self.tokens["account_id"])
                if self.source == config_entries.SOURCE_REAUTH:
                    self._abort_if_unique_id_mismatch()
                    entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(entry, data_updates={"tokens": self.tokens})
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
        choices = {
            fire["FireId"]: fire.get("FriendlyName") or fire.get("ProductModel") or "Fireplace"
            for fire in self.fires
            if fire.get("IsIotFire") is True
        }
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
                    data={"tokens": self.tokens, CONF_FIRES: selected},
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
                    vol.Required(CONF_TEMPERATURE_UNIT, default="auto"): vol.In(["auto", "C", "F"]),
                }
            ),
            errors={"base": "select_device"} if user_input is not None else {},
        )

    async def _store_tokens(self, tokens: dict[str, Any]) -> None:
        self.tokens = tokens
        if self.source == config_entries.SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, "tokens": tokens})

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        self.tokens = dict(entry.data["tokens"])
        provider = B2C(async_get_clientsession(self.hass), self.tokens.get("policy", "normal"))
        client = FlameClient(
            async_get_clientsession(self.hass), TokenManager(provider, self.tokens, self._store_tokens)
        )
        try:
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
            return await self.async_step_link()
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
                    ): vol.In(["auto", "C", "F"]),
                    vol.Required(
                        CONF_EXPERIMENTAL, default=self.config_entry.options.get(CONF_EXPERIMENTAL, False)
                    ): bool,
                }
            ),
        )
