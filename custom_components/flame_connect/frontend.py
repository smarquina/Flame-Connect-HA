"""Register the bundled Lovelace card."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HassJob, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.setup import async_setup_component

_LOGGER = logging.getLogger(__name__)
CARD_PATH = "/flame_connect/flame-connect-card.js"
CARD_HASH = "4510a0d2966145ce07111fbcf17b837d9b3d0bbd232f8376a432e5937778669e"
CARD_URL = f"{CARD_PATH}?v={CARD_HASH}"
REGISTERED = "flame_connect_card_registered"
LOCK = "flame_connect_card_lock"
RETRY = "flame_connect_card_retry"
STOP_LISTENER = "flame_connect_card_stop_listener"
RETRY_SECONDS = 60


async def async_setup_card(hass: HomeAssistant) -> None:
    """Publish the card and register its resource once per HA process."""
    lock = hass.data.setdefault(LOCK, asyncio.Lock())
    async with lock:
        try:
            ready = await _async_setup_card(hass)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unable to register the Flame Connect card; retrying automatically")
            ready = False
        if ready:
            if cancel := hass.data.pop(RETRY, None):
                cancel()
        elif RETRY not in hass.data:
            if STOP_LISTENER not in hass.data:

                @callback
                def cancel_retry(_event: Event) -> None:
                    if cancel := hass.data.pop(RETRY, None):
                        cancel()
                    hass.data.pop(STOP_LISTENER, None)

                hass.data[STOP_LISTENER] = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, cancel_retry)

            async def retry(_now: datetime) -> None:
                hass.data.pop(RETRY, None)
                await async_setup_card(hass)

            hass.data[RETRY] = async_call_later(hass, RETRY_SECONDS, HassJob(retry, cancel_on_shutdown=True))


async def _async_setup_card(hass: HomeAssistant) -> bool:
    """Reconcile the resource while holding the registration lock."""
    if hass.http is None:
        _LOGGER.warning("HTTP is unavailable; the Flame Connect card cannot be registered")
        return False
    if not hass.data.get(REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_PATH, str(Path(__file__).parent / "www" / "flame-connect-card.js"), False)]
        )
        hass.data[REGISTERED] = True
    if not await async_setup_component(hass, "lovelace", {}):
        _LOGGER.warning("Unable to set up Lovelace for the Flame Connect card")
        return False
    lovelace = hass.data[LOVELACE_DATA]
    if lovelace.resource_mode != MODE_STORAGE or not isinstance(lovelace.resources, ResourceStorageCollection):
        _LOGGER.warning("Add %s as a module to your Lovelace YAML resources", CARD_URL)
        return True
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
        return True
    if legacy:
        return True
    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
    return True
