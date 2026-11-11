"""Register the bundled Lovelace card."""

from __future__ import annotations

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


async def async_setup_card(hass: HomeAssistant) -> None:
    """Publish the card and register its resource once per HA process."""
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
    for item in resources.async_items():
        path = item["url"].split("?", 1)[0]
        if path == CARD_PATH:
            if item["url"] != CARD_URL:
                await resources.async_update_item(item["id"], {"url": CARD_URL})
            return
        if path.endswith("/flame-connect-card/flame-connect-card.js"):
            _LOGGER.warning("Remove the separately installed Flame Connect Card resource, then reload the integration")
            return
    await resources.async_create_item({"res_type": "module", "url": CARD_URL})
