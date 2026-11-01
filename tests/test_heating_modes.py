"""Capability-filtered heating controls preserve unrelated device settings."""

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.flame_connect.climate import FlameClimate
from custom_components.flame_connect.domain.capabilities import Capability
from custom_components.flame_connect.domain.errors import ProtocolError
from custom_components.flame_connect.domain.heating import HEAT_MODES, preset_parameter, supported_modes
from custom_components.flame_connect.domain.models import FireCapabilities
from custom_components.flame_connect.domain.parameters import FireState
from custom_components.flame_connect.number import NUMBERS, FlameNumber


def test_optional_modes_require_explicit_capabilities():
    assert supported_modes(FireCapabilities()) == ["normal"]
    assert supported_modes(FireCapabilities({Capability.ADVANCED_HEAT: True})) == ["normal", "eco"]
    assert supported_modes(FireCapabilities({Capability.ADVANCED_HEAT: 1, Capability.FAN_ONLY: False})) == ["normal"]
    assert supported_modes(FireCapabilities({Capability.SEVEN_DAY_TIMER: True})) == ["normal", "schedule"]


@pytest.mark.parametrize("mode", HEAT_MODES)
async def test_presets_are_confirmed_without_changing_power(hass, entry, api_client, fire, mode):
    fire["FireFeature"].update(AdvancedHeat=True, PowerBoost=True, FanOnly=True, SevenDayTimer=True)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = entry.runtime_data.coordinators[0]
    climate = FlameClimate(coordinator)
    assert set(climate.preset_modes) == set(HEAT_MODES)
    state = coordinator.data
    before = state.require(323).edit(boost=10)
    state = FireState(state.fire_id, {**state.parameters, 323: before})
    changed = preset_parameter(state, coordinator.features, mode)
    api_client.overview.side_effect = [state, FireState(state.fire_id, {**state.parameters, 323: changed})]
    await climate.async_set_preset_mode(mode)
    written = api_client.write.call_args.args[1]
    assert written == [changed]
    assert written[0].raw[3] == before.raw[3]
    assert written[0].raw[5:] == before.raw[5:]
    assert climate.preset_mode == mode
    registry = er.async_get(hass)
    entity = next(
        e for e in er.async_entries_for_config_entry(registry, entry.entry_id) if e.translation_key == "boost_duration"
    )
    assert entity.disabled_by is None
    with pytest.raises(ServiceValidationError):
        await climate.async_set_preset_mode("unknown")


async def test_boost_default_and_duration_validation(hass, entry, api_client, fire):
    fire["FireFeature"]["PowerBoost"] = True
    assert await hass.config_entries.async_setup(entry.entry_id)
    c = entry.runtime_data.coordinators[0]
    state = c.data
    invalid_duration = state.require(323).edit(boost=0)
    before = FireState(state.fire_id, {**state.parameters, 323: invalid_duration})
    assert preset_parameter(before, c.features, "boost").field("boost") == 15
    number = FlameNumber(c, NUMBERS["boost_duration"])
    assert number.native_value == state.require(323).field("boost")
    await number.async_set_native_value(20)
    written = api_client.write.call_args.args[1][0]
    assert written.field("boost") == 20
    assert written.raw[:7] == state.require(323).raw[:7]
    for value in (0, 21, 1.5, True):
        with pytest.raises(ServiceValidationError):
            await number.async_set_native_value(value)
    with pytest.raises(ProtocolError):
        preset_parameter(before, FireCapabilities(), "boost")


async def test_unsupported_presets_and_unknown_readback(hass, entry, api_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    c = entry.runtime_data.coordinators[0]
    climate = FlameClimate(c)
    assert climate.preset_modes == ["normal"]
    for mode in ("boost", "eco", "fan_only", "schedule"):
        with pytest.raises(ServiceValidationError):
            await climate.async_set_preset_mode(mode)
    api_client.write.assert_not_called()
    before = c.data.require(323)
    from custom_components.flame_connect.domain.parameters import Parameter

    c.async_set_updated_data(FireState(c.fire_id, {323: Parameter(323, before.raw[:4] + b"\xff" + before.raw[5:])}))
    assert climate.preset_mode is None
