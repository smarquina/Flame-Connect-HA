"""Tests for the bundled card resource lifecycle."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from homeassistant.components.lovelace import LOVELACE_DATA, MODE_STORAGE
from homeassistant.components.lovelace.resources import ResourceStorageCollection

from custom_components.flame_connect import async_setup, frontend


def test_card_version_matches_package_and_documentation():
    version = json.loads(Path("frontend/package.json").read_text())["version"]
    assert frontend.CARD_URL.endswith(f"?v={version}")
    assert frontend.CARD_URL in Path("docs/card/installation.md").read_text()


async def test_concurrent_registration_and_retry(hass, monkeypatch, caplog):
    resources = ResourceStorageCollection(hass, SimpleNamespace(async_load=AsyncMock(return_value={})))
    register = AsyncMock(side_effect=[RuntimeError("failed"), None])
    hass.http = SimpleNamespace(async_register_static_paths=register)
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)
    monkeypatch.setattr(frontend, "async_setup_component", AsyncMock(return_value=True))
    await asyncio.gather(frontend.async_setup_card(hass), frontend.async_setup_card(hass))
    assert register.await_count == 2
    assert len(resources.async_items()) == 1
    assert "will be retried" in caplog.text


async def test_legacy_and_bundled_resources_in_either_order(monkeypatch, caplog):
    resources = MagicMock(spec=ResourceStorageCollection)
    resources.async_get_info = AsyncMock()
    resources.async_update_item = AsyncMock()
    resources.async_create_item = AsyncMock()
    hass = SimpleNamespace(
        http=SimpleNamespace(async_register_static_paths=AsyncMock()),
        data={LOVELACE_DATA: SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)},
    )
    monkeypatch.setattr(frontend, "async_setup_component", AsyncMock(return_value=True))
    bundled = {"id": "bundled", "url": frontend.CARD_PATH + "?v=old"}
    legacy = {"id": "legacy", "url": "/hacsfiles/flame-connect-card/flame-connect-card.js"}
    for items in ([bundled, legacy], [legacy, bundled]):
        resources.async_items.return_value = items
        await frontend.async_setup_card(hass)
    assert resources.async_update_item.await_count == 2
    resources.async_create_item.assert_not_awaited()
    assert "Multiple Flame Connect Card resources" in caplog.text


async def test_register_and_update_resource(monkeypatch):
    resources = MagicMock(spec=ResourceStorageCollection)
    resources.async_get_info = AsyncMock()
    resources.async_create_item = AsyncMock()
    resources.async_update_item = AsyncMock()
    resources.async_items.return_value = []
    http = SimpleNamespace(async_register_static_paths=AsyncMock())
    hass = SimpleNamespace(
        http=http, data={LOVELACE_DATA: SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)}
    )
    monkeypatch.setattr(frontend, "async_setup_component", AsyncMock(return_value=True))

    assert await async_setup(hass, {})
    resources.async_create_item.assert_awaited_once_with({"res_type": "module", "url": frontend.CARD_URL})
    resources.async_items.return_value = [{"id": "one", "url": frontend.CARD_PATH + "?v=old"}]
    await frontend.async_setup_card(hass)
    http.async_register_static_paths.assert_awaited_once()
    resources.async_update_item.assert_awaited_once_with("one", {"url": frontend.CARD_URL})
    resources.async_items.return_value = [{"id": "one", "url": frontend.CARD_URL}]
    await frontend.async_setup_card(hass)
    resources.async_update_item.assert_awaited_once()


async def test_legacy_yaml_and_unavailable(monkeypatch, caplog):
    hass = SimpleNamespace(http=None, data={})
    await frontend.async_setup_card(hass)
    assert "HTTP is unavailable" in caplog.text
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
    setup = AsyncMock(return_value=False)
    monkeypatch.setattr(frontend, "async_setup_component", setup)
    await frontend.async_setup_card(hass)
    assert "Unable to set up Lovelace" in caplog.text
    setup.return_value = True
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode="yaml", resources=None)
    await frontend.async_setup_card(hass)
    assert "Lovelace YAML resources" in caplog.text
    resources = MagicMock(spec=ResourceStorageCollection)
    resources.async_get_info = AsyncMock()
    resources.async_create_item = AsyncMock()
    resources.async_items.return_value = [
        {"id": "old", "url": "/hacsfiles/flame-connect-card/flame-connect-card.js?v=1"}
    ]
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)
    await frontend.async_setup_card(hass)
    resources.async_create_item.assert_not_awaited()
    assert "Remove the separately installed" in caplog.text


async def test_real_lovelace_collection(hass, monkeypatch):
    """Register a module in Home Assistant's actual resource collection."""
    resources = ResourceStorageCollection(hass, SimpleNamespace(async_load=AsyncMock(return_value={})))
    hass.http = SimpleNamespace(async_register_static_paths=AsyncMock())
    hass.data[LOVELACE_DATA] = SimpleNamespace(resource_mode=MODE_STORAGE, resources=resources)
    monkeypatch.setattr(frontend, "async_setup_component", AsyncMock(return_value=True))
    await frontend.async_setup_card(hass)
    items = resources.async_items()
    assert len(items) == 1
    assert items[0]["url"] == frontend.CARD_URL
    assert items[0]["type"] == "module"
    await frontend.async_setup_card(hass)
    assert len(resources.async_items()) == 1
