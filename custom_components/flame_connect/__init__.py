"""Unofficial cloud integration for Flame Connect fireplaces."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .adapters.cloud.api import FlameClient
from .adapters.cloud.auth import B2C
from .application.tokens import TokenManager
from .const import CONF_FIRES, PLATFORMS
from .coordinator import FireCoordinator
from .domain.errors import AuthenticationError, FlameError


@dataclass
class FlameRuntime:
    client: FlameClient
    coordinators: list[FireCoordinator]


type FlameConfigEntry = ConfigEntry[FlameRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: FlameConfigEntry) -> bool:
    """Validate the account even if individual fireplaces are offline."""
    session = async_get_clientsession(hass)

    async def save(tokens: dict) -> None:
        hass.config_entries.async_update_entry(entry, data={**entry.data, "tokens": tokens})

    manager = TokenManager(B2C(session, entry.data["tokens"].get("policy", "normal")), entry.data["tokens"], save)
    client = FlameClient(session, manager)
    try:
        fires = await client.fires()
    except AuthenticationError as err:
        raise ConfigEntryAuthFailed from err
    except FlameError as err:
        raise ConfigEntryNotReady from err
    coordinators = []
    for fire in fires:
        if fire["FireId"] in entry.data[CONF_FIRES] and fire.get("IsIotFire") is True:
            coordinator = FireCoordinator(hass, entry, client, fire)
            # Account access has been checked. Offline individual devices may load
            # unavailable and recover independently without blocking siblings.
            await coordinator.async_refresh()
            coordinators.append(coordinator)
    entry.runtime_data = FlameRuntime(client, coordinators)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: FlameConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: FlameConfigEntry) -> bool:
    """Coordinator entities release listeners and polling when unloaded."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
