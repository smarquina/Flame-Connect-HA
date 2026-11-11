"""Register the bundled Lovelace card."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/flame_connect/flame-connect-card.js"
CARD_URL = f"{CARD_PATH}?v=0.5.2"
REGISTERED = "flame_connect_card_registered"
LOCK = "flame_connect_card_lock"


async def async_setup_card(hass: HomeAssistant) -> None:
    """Publish the card and register its resource once per HA process."""
    lock = hass.data.setdefault(LOCK, asyncio.Lock())
    async with lock:
        try:
            await _async_setup_card(hass)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unable to register the Flame Connect card; it will be retried on integration reload")


async def _async_setup_card(hass: HomeAssistant) -> None:
    """Reconcile the resource while holding the registration lock."""
    if hass.http is None:
        _LOGGER.warning("HTTP is unavailable; the Flame Connect card cannot be registered")
        return
    if not hass.data.get(REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_PATH, str(Path(__file__).parent / "www" / "flame-connect-card.js"), False)]
        )
        hass.data[REGISTERED] = True
    if not await async_setup_component(hass, "lovelace", {}):
        _LOGGER.warning("Unable to set up Lovelace for the Flame Connect card")
        return
    lovelace = hass.data[LOVELACE_DATA]
    if lovelace.resource_mode != MODE_STORAGE or not isinstance(lovelace.resources, ResourceStorageCollection):
        _LOGGER.warning("Add %s as a module to your Lovelace YAML resources", CARD_URL)
        return
    resources = lovelace.resources
    await resources.async_get_info()
    items = resources.async_items()
    bundled = [item for item in items if item["url"].split("?", 1)[0] == CARD_PATH]
    legacy = [
        item for item in items if item["url"].split("?", 1)[0].endswith("/flame-connect-card/flame-connect-card.js")
    ]
    if legacy:
        _LOGGER.warning("Remove the separately installed Flame Connect Card resource, then reload the integration")
    if bundled:
        if bundled[0]["url"] != CARD_URL:
            await resources.async_update_item(bundled[0]["id"], {"url": CARD_URL})
        if len(bundled) > 1 or legacy:
            _LOGGER.warning("Multiple Flame Connect Card resources are registered; remove the duplicate resources")
        return
    if legacy:
        return
    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
