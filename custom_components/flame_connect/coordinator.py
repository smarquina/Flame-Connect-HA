"""One snapshot and cross-platform command lock per fireplace."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .application.fireplaces import FireplaceService
from .application.ports import FireplacePort
from .const import CONF_TEMPERATURE_UNIT, DEFAULT_INTERVAL, DOMAIN
from .domain.errors import AuthenticationError, FlameError
from .domain.parameters import FireState, Parameter

_LOGGER = logging.getLogger(__name__)


class FireCoordinator(DataUpdateCoordinator[FireState]):
    """A failed fireplace never marks siblings unavailable."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: FireplacePort, fire: dict[str, Any]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {fire.get('FriendlyName', 'fireplace')}",
            update_interval=timedelta(seconds=DEFAULT_INTERVAL),
            always_update=False,
        )
        self.client, self.fire, self.entry = client, fire, entry
        self.fire_id = fire["FireId"]
        self.service = FireplaceService(client, self.fire_id)

    async def _async_update_data(self) -> FireState:
        try:
            return await self.service.read()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="invalid_auth") from err
        except FlameError as err:
            raise UpdateFailed("Fireplace state unavailable") from err

    @property
    def features(self) -> dict[str, Any]:
        return self.fire.get("FireFeature") or {}

    @property
    def unit(self) -> str | None:
        configured = self.entry.options.get(CONF_TEMPERATURE_UNIT, "auto")
        if configured in ("C", "F"):
            return "°C" if configured == "C" else "°F"
        if self.data and (parameter := self.data.parameters.get(236)):
            value = parameter.field("unit")
            return {0: "°F", 1: "°C"}.get(value)
        return "°C"

    async def command(self, build: Callable[[FireState], list[Parameter]]) -> None:
        """Always read inside the lock; never replay commands on errors."""
        try:
            confirmed = await self.service.execute(build)
        except AuthenticationError as err:
            self.entry.async_start_reauth(self.hass)
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="invalid_auth") from err
        except FlameError as err:
            self.async_set_update_error(UpdateFailed("Unable to confirm fireplace state"))
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="command_failed") from err
        self.async_set_updated_data(confirmed)

    async def edit(self, ident: int, **changes: int | float) -> None:
        await self.command(lambda state: [state.require(ident).edit(**changes)])
