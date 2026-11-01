"""Network-free tests using the real Home Assistant framework."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.flame_connect.adapters.cloud.codec import decode_fireplace, decode_state
from custom_components.flame_connect.const import DOMAIN


@pytest.fixture(autouse=True)
def custom_components_enabled(enable_custom_integrations):
    yield


@pytest.fixture
def overview():
    return json.loads((Path(__file__).parent / "fixtures/overview.json").read_text())


@pytest.fixture
def fire():
    return {
        "FireId": "fixture-fire",
        "FriendlyName": "Living room",
        "Brand": "Dimplex",
        "ProductModel": "OLF",
        "ProductType": "Optiflame V2",
        "IsIotFire": True,
        "WithHeat": True,
        "FireFeature": {
            "FlameFanSpeed": True,
            "FlameDimming": True,
            "RgbFlameAccent": True,
            "FlamePresetOptions": 0,
            "CountDownTimer": True,
            "Sound": True,
        },
    }


@pytest.fixture
def tokens():
    return {
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
        "expires_at": time.time() + 3600,
        "account_id": "fixture-account",
        "policy": "normal",
    }


@pytest.fixture
def entry(hass, tokens):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="fixture-account",
        title="Flame Connect",
        data={"tokens": tokens, "fires": ["fixture-fire"]},
        options={"temperature_unit": "auto", "experimental_controls": False},
        version=1,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def client(fire, overview):
    client = AsyncMock()
    client.fires.side_effect = lambda: [decode_fireplace(fire)]
    client.overview.return_value = decode_state(fire["FireId"], overview)
    return client


@pytest.fixture
def api_client(client):
    with patch("custom_components.flame_connect.composition.FlameClient", return_value=client):
        yield client
