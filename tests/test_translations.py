"""Exercise locale resources through Home Assistant, without cloud or device access."""

import json
import re
from pathlib import Path

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations, async_translate_state

from custom_components.flame_connect.const import DOMAIN
from custom_components.flame_connect.domain.parameters import color_labels

COMPONENT = Path(__file__).parents[1] / "custom_components" / DOMAIN


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, path))
        else:
            result[path] = item
    return result


def test_locale_keys_placeholders_and_english_source_match():
    source = json.loads((COMPONENT / "strings.json").read_text())
    english = json.loads((COMPONENT / "translations/en.json").read_text())
    spanish = json.loads((COMPONENT / "translations/es.json").read_text())
    assert source == english
    base, translated = flatten(source), flatten(spanish)
    assert base.keys() == translated.keys()
    for key, text in base.items():
        assert isinstance(translated[key], str) and translated[key].strip(), key
        assert sorted(re.findall(r"\{\w+\}", text)) == sorted(re.findall(r"\{\w+\}", translated[key])), key
    for preset in (0, 1, 2):
        for label in color_labels(preset):
            key = label.lower().replace(" + ", "_")
            assert key in english["entity"]["select"]["color"]["state"]
            assert key in spanish["entity"]["select"]["color"]["state"]


@pytest.mark.parametrize(
    "language,heating,brightness,color,policy,automatic,invalid_auth",
    [
        ("en", "Heating", "Low", "Blue", "Phone or email", "Automatic", "Link the Flame Connect account again."),
        (
            "es",
            "Calefacción",
            "Bajo",
            "Azul",
            "Teléfono o correo",
            "Automática",
            "Vuelve a vincular tu cuenta de Flame Connect.",
        ),
    ],
)
async def test_home_assistant_resolves_language(
    hass, entry, api_client, language, heating, brightness, color, policy, automatic, invalid_auth
):
    hass.config.language = language
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # The actual backend generates entity names in the configured system language.
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    climate = next(entity for entity in entities if entity.translation_key == "heating")
    assert climate.original_name == heating
    assert hass.states.get(climate.entity_id).attributes["friendly_name"] == f"Living room {heating}"
    target = next(entity for entity in entities if entity.translation_key == "target_temperature")
    reported = next(entity for entity in entities if entity.translation_key == "temperature")
    assert target.original_name == ("Temperatura objetivo" if language == "es" else "Target temperature")
    assert reported.original_name == ("Temperatura informada" if language == "es" else "Reported temperature")

    # The frontend requests these same resources using the user's profile language.
    for category in ("config", "options", "entity", "selector", "exceptions"):
        resources = await async_get_translations(hass, language, category, {DOMAIN})
        expected = flatten(json.loads((COMPONENT / f"translations/{language}.json").read_text())[category])
        for key, text in expected.items():
            assert resources[f"component.{DOMAIN}.{category}.{key}"] == text

    assert async_translate_state(hass, "low", "select", DOMAIN, "brightness", None) == brightness
    assert async_translate_state(hass, "blue", "select", DOMAIN, "color", None) == color
    selectors = await async_get_translations(hass, language, "selector", {DOMAIN})
    assert selectors[f"component.{DOMAIN}.selector.policy.options.normal"] == policy
    assert selectors[f"component.{DOMAIN}.selector.temperature_unit.options.auto"] == automatic
    errors = await async_get_translations(hass, language, "exceptions", {DOMAIN})
    assert errors[f"component.{DOMAIN}.exceptions.invalid_auth.message"] == invalid_auth
    # Changing display language never changes API enums or entity identifiers.
    brightness_entity = next(entity for entity in entities if entity.translation_key == "brightness")
    assert hass.states.get(brightness_entity.entity_id).attributes["options"] == [
        "high",
        "low",
        "flicker_high",
        "flicker_low",
    ]
    assert brightness_entity.unique_id == "fixture-fire_brightness"
