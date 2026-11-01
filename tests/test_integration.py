from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.flame_connect.coordinator import FireCoordinator
from custom_components.flame_connect.diagnostics import async_get_config_entry_diagnostics
from custom_components.flame_connect.domain.errors import (
    AuthenticationError,
    CommandError,
    ConnectionError,
)
from custom_components.flame_connect.domain.parameters import FireState, Parameter


async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_devices_states_unload(hass, entry, api_client):
    await setup(hass, entry)
    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert {e.domain for e in entities} >= {"climate", "light", "switch", "sensor", "binary_sensor", "select", "number"}
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1 and devices[0].model == "OLF"
    assert len({e.device_id for e in entities}) == 1
    assert all(e.unique_id.startswith("fixture-fire_") for e in entities)
    for e in entities:
        if e.disabled_by is None:
            assert hass.states.get(e.entity_id).state != STATE_UNAVAILABLE
    data = await async_get_config_entry_diagnostics(hass, entry)
    text = str(data)
    assert "fake-access" not in text and "fixture-fire" not in text and "Living room" not in text
    assert data["devices"][0]["parameters"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "error,expected",
    [(AuthenticationError(), ConfigEntryState.SETUP_ERROR), (ConnectionError(), ConfigEntryState.SETUP_RETRY)],
)
async def test_account_setup_errors(hass, entry, api_client, error, expected):
    api_client.fires.side_effect = error
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == expected


@pytest.mark.parametrize("with_heat", [False, None])
@pytest.mark.parametrize("capability", ["AdvancedHeat", "SimpleHeat"])
async def test_heat_capabilities_create_thermostat_without_with_heat(
    hass, entry, api_client, fire, with_heat, capability
):
    from homeassistant.components.climate import ClimateEntityFeature

    fire["WithHeat"] = with_heat
    fire["FireFeature"][capability] = True
    api_client.fires.return_value = [fire]
    await setup(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    entity = next(entity for entity in entities if entity.domain == "climate")
    state = hass.states.get(entity.entity_id)
    assert entity.unique_id == "fixture-fire_heating"
    assert state.state != STATE_UNAVAILABLE
    assert state.attributes["temperature"] == api_client.overview.return_value.require(323).temperature
    assert state.attributes["supported_features"] & ClimateEntityFeature.TARGET_TEMPERATURE
    api_client.write.assert_not_called()


async def test_offline_recovers(hass, entry, api_client):
    state = api_client.overview.return_value
    api_client.overview.side_effect = ConnectionError()
    await setup(hass, entry)
    coordinator = entry.runtime_data.coordinators[0]
    assert not coordinator.last_update_success
    api_client.overview.side_effect = None
    api_client.overview.return_value = state
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coordinator.last_update_success
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_command_lock_and_failures(hass, entry, client, fire):
    c = FireCoordinator(hass, entry, client, fire)
    await c.async_refresh()
    original = c.data
    await c.edit(322, color=3)
    assert client.write.call_args.args[1][0].raw[19] == 3
    assert original.require(322).raw == client.overview.return_value.require(322).raw
    client.write.side_effect = CommandError()
    with pytest.raises(HomeAssistantError):
        await c.edit(322, flame=1)
    assert not c.last_update_success
    client.write.side_effect = None
    with pytest.raises(HomeAssistantError):
        await c.edit(322, color=7)
    with patch.object(entry, "async_start_reauth") as reauth:
        client.overview.side_effect = AuthenticationError()
        with pytest.raises(HomeAssistantError):
            await c.edit(322, flame=1)
        reauth.assert_called_once()
        with pytest.raises(ConfigEntryAuthFailed):
            await c._async_update_data()
    client.overview.side_effect = ConnectionError()
    await c.async_refresh()
    assert not c.last_update_success


async def test_units_and_preferences(hass, entry, client, fire):
    c = FireCoordinator(hass, entry, client, fire)
    assert c.unit == "°C"
    await c.async_refresh()
    for option, expected in [("F", "°F"), ("C", "°C"), ("auto", "°C")]:
        hass.config_entries.async_update_entry(entry, options={"temperature_unit": option})
        if option == "auto":
            c.async_set_updated_data(FireState(c.fire_id, {236: Parameter(236, b"\xec\x00\x01\x01")}))
        assert c.unit == expected
    c.async_set_updated_data(FireState(c.fire_id, {236: Parameter(236, b"\xec\x00\x01\x00")}))
    assert c.unit == "°F"


async def test_platform_actions(hass, entry, api_client):
    await setup(hass, entry)
    registry = er.async_get(hass)
    lookup = {e.translation_key: e.entity_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}
    for domain, service, key, data in [
        ("switch", "turn_on", "power", {}),
        ("switch", "turn_off", "power", {}),
        ("light", "turn_on", "flame", {}),
        ("light", "turn_off", "flame", {}),
        ("climate", "set_hvac_mode", "heating", {"hvac_mode": "heat"}),
        ("climate", "set_hvac_mode", "heating", {"hvac_mode": "off"}),
        ("climate", "set_temperature", "heating", {"temperature": 22}),
        ("select", "select_option", "brightness", {"option": "low"}),
        ("number", "set_value", "speed", {"value": 4}),
    ]:
        await hass.services.async_call(domain, service, {"entity_id": lookup[key], **data}, blocking=True)
    assert api_client.write.await_count == 9
    c = entry.runtime_data.coordinators[0]
    c.async_set_update_error(ConnectionError())
    await hass.async_block_till_done()
    assert hass.states.get(lookup["heating"]).state == STATE_UNAVAILABLE
    assert hass.states.get(lookup["connectivity"]).state == "off"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_experimental_entities(hass, entry, api_client):
    hass.config_entries.async_update_entry(entry, options={"experimental_controls": True})
    await setup(hass, entry)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    keys = {e.translation_key for e in entities}
    assert {"timer", "duration", "volume", "sound_file", "color", "temperature_scale"} <= keys
    assert all(
        e.disabled_by is not None
        for e in entities
        if e.translation_key in {"timer", "duration", "volume", "sound_file", "color", "temperature_scale"}
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_options_reload(hass, entry, api_client):
    await setup(hass, entry)
    with patch.object(hass.config_entries, "async_reload", AsyncMock(return_value=True)) as reload:
        hass.config_entries.async_update_entry(entry, options={"temperature_unit": "F"})
        await hass.async_block_till_done()
        reload.assert_awaited_once_with(entry.entry_id)
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_token_persistence(hass, entry, api_client, tokens):
    with patch("custom_components.flame_connect.TokenManager") as manager:
        await setup(hass, entry)
        save = manager.call_args.args[2]
        await save({**tokens, "refresh_token": "rotated"})
        assert entry.data["tokens"]["refresh_token"] == "rotated"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_experimental_actions_and_diagnostics(hass, entry, api_client):
    from custom_components.flame_connect import climate as climate_module
    from custom_components.flame_connect.number import FlameNumber
    from custom_components.flame_connect.select import FlameSelect

    hass.config_entries.async_update_entry(entry, options={"experimental_controls": True, "temperature_unit": "F"})
    state = api_client.overview.return_value
    parameters = {**state.parameters, 369: Parameter(369, b"\x71\x01\x02\x00\x00")}
    api_client.overview.return_value = FireState(state.fire_id, parameters)
    await setup(hass, entry)
    registry = er.async_get(hass)
    for e in er.async_entries_for_config_entry(registry, entry.entry_id):
        registry.async_update_entity(e.entity_id, disabled_by=None)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    lookup = {e.translation_key: e.entity_id for e in er.async_entries_for_config_entry(registry, entry.entry_id)}
    for key in ["firmware", "errors"]:
        assert hass.states.get(lookup[key]).state not in ("unknown", STATE_UNAVAILABLE)
    for domain, service, key, data in [
        ("switch", "turn_on", "timer", {}),
        ("switch", "turn_off", "timer", {}),
        ("number", "set_value", "duration", {"value": 45}),
        ("number", "set_value", "volume", {"value": 5}),
        ("number", "set_value", "sound_file", {"value": 1}),
        ("select", "select_option", "color", {"option": "blue"}),
        ("select", "select_option", "temperature_scale", {"option": "celsius"}),
    ]:
        await hass.services.async_call(domain, service, {"entity_id": lookup[key], **data}, blocking=True)
    c = entry.runtime_data.coordinators[0]
    climate = climate_module.FlameClimate(c)
    assert climate.min_temp == 59
    assert climate.max_temp == pytest.approx(87.08)
    assert climate._target() == pytest.approx(state.require(323).temperature * 1.8 + 32)
    await climate.async_set_temperature(temperature=71.6)
    written = api_client.write.call_args.args[1][0]
    assert written.temperature == 22
    for invalid in ["cool", "auto"]:
        with pytest.raises(ServiceValidationError):
            await climate.async_set_hvac_mode(invalid)
    for invalid in [True, None, 1000]:
        with pytest.raises(ServiceValidationError):
            await climate.async_set_temperature(temperature=invalid)
    with pytest.raises(ServiceValidationError):
        await FlameNumber(c, "speed", 322, 1, 5).async_set_native_value(2.5)
    with pytest.raises(ServiceValidationError):
        await FlameSelect(c, "color", 322, "color", ["Blue"]).async_select_option("invalid")
    # Missing parameters expose unknown/unavailable rather than stale values.
    c.async_set_updated_data(FireState(c.fire_id, {}))
    assert climate.field(322, "flame") is None
    await hass.async_block_till_done()
    for key in ["flame", "temperature", "volume", "duration"]:
        assert hass.states.get(lookup[key]).state == STATE_UNAVAILABLE
    assert FlameNumber(c, "duration", 326, 0, 32767).native_value is None
    from custom_components.flame_connect.sensor import FlameSensor

    assert FlameSensor(c, "firmware", 327).native_value is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_minimal_capabilities_and_native_api(hass, entry, client, fire):
    import importlib

    from homeassistant.components.climate import ClimateEntity

    from custom_components.flame_connect import FlameRuntime, climate, number, select
    from custom_components.flame_connect import climate as climate_module

    fire = {**fire, "WithHeat": False, "ProductType": "other", "ProductModel": "other", "FireFeature": {}}
    c = FireCoordinator(hass, entry, client, fire)
    await c.async_refresh()
    entry.runtime_data = FlameRuntime(client, [c])
    added = []
    for platform in [number, select, climate]:
        await platform.async_setup_entry(hass, entry, added.extend)
    assert added == []
    entity = climate_module.FlameClimate(c)
    assert entity.max_temp == 32.9
    with patch.object(ClimateEntity, "native_temperature_unit", property(lambda _: "°C"), create=True):
        importlib.reload(climate_module)
        native = climate_module.FlameClimate(c)
        assert native.native_temperature_unit == c.unit
        assert native.native_current_temperature is None
        assert native.native_target_temperature == c.data.require(323).temperature
    importlib.reload(climate_module)


async def test_diagnostics_allowlist(hass, entry, api_client):
    hass.config_entries.async_update_entry(entry, options={"temperature_unit": "auto", "unexpected_secret": "secret"})
    await setup(hass, entry)
    coordinator = entry.runtime_data.coordinators[0]
    coordinator.fire["FireFeature"] = {
        "Sound": True,
        "FlamePresetOptions": 0,
        "AccessCode": "private-pin",
        "Unknown": 1,
        "FlameDimming": "private-value",
    }
    coordinator.async_set_updated_data(None)
    data = await async_get_config_entry_diagnostics(hass, entry)
    assert data["options"] == {"temperature_unit": "auto"}
    assert data["devices"][0]["features"] == {"Sound": True, "FlamePresetOptions": 0}
    assert data["devices"][0]["parameters"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)
