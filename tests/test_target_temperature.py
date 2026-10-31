"""Exercise target controls without sending commands to a real fireplace."""

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.flame_connect.domain.parameters import FireState
from custom_components.flame_connect.number import FlameTargetTemperature


@pytest.mark.parametrize("unit", ["C", "F"])
async def test_target_controls_share_confirmed_state(hass, entry, api_client, unit):
    hass.config_entries.async_update_entry(entry, options={"temperature_unit": unit})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    number = next(entity for entity in entities if entity.translation_key == "target_temperature")
    climate = next(entity for entity in entities if entity.translation_key == "heating")
    assert number.disabled_by is None
    assert number.unique_id == "fixture-fire_target_temperature"
    api_client.write.assert_not_called()
    state = api_client.overview.return_value
    for domain, entity, service, key, value in (
        ("number", number, "set_value", "value", 22.5),
        ("climate", climate, "set_temperature", "temperature", 23.0),
    ):
        original = state.require(323)
        changed = original.edit(temperature=value)
        confirmed = FireState(state.fire_id, {**state.parameters, 323: changed})
        api_client.overview.side_effect = [state, confirmed]
        await hass.services.async_call(domain, service, {"entity_id": entity.entity_id, key: value}, blocking=True)
        await hass.async_block_till_done()
        written = api_client.write.call_args.args[1]
        assert len(written) == 1 and written[0] == changed
        assert changed.raw[:5] == original.raw[:5]
        assert changed.raw[7:] == original.raw[7:]
        assert float(hass.states.get(number.entity_id).state) == value
        assert hass.states.get(climate.entity_id).attributes["temperature"] == value
        state = confirmed
    assert api_client.write.call_count == 2


async def test_missing_target_is_unavailable(hass, entry, api_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = entry.runtime_data.coordinators[0]
    entity = FlameTargetTemperature(coordinator)
    coordinator.async_set_updated_data(FireState(coordinator.fire_id, {}))
    assert not entity.available
    assert entity.native_value is None


@pytest.mark.parametrize("value", [True, None, float("nan"), float("inf"), 14.9, 33.0])
async def test_invalid_target_never_writes(hass, entry, api_client, value):
    assert await hass.config_entries.async_setup(entry.entry_id)
    entity = FlameTargetTemperature(entry.runtime_data.coordinators[0])
    with pytest.raises(ServiceValidationError):
        await entity.async_set_native_value(value)
    api_client.write.assert_not_called()
