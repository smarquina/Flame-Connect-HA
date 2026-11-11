import type { HomeAssistant } from '../../src/adapters/home-assistant/types';
import { CARD_TYPE } from '../../src/domain/model';
import { parseConfig } from '../../src/configuration/config';
export const config = parseConfig({
  type: CARD_TYPE,
  name: 'Living room',
  show_power: true,
  entities: {
    power: 'switch.fire_power',
    flame: 'light.fire_flame',
    climate: 'climate.fire_heating',
    color: 'select.fire_color',
    brightness: 'select.fire_brightness',
    ambient: 'sensor.room_temperature',
  },
});
export function fakeHass(): HomeAssistant {
  return {
    language: 'en',
    config: { unit_system: { temperature: '°C' } },
    states: {
      'switch.fire_power': {
        entity_id: 'switch.fire_power',
        state: 'on',
        attributes: { friendly_name: 'Power' },
      },
      'light.fire_flame': {
        entity_id: 'light.fire_flame',
        state: 'on',
        attributes: { friendly_name: 'Living room flame' },
      },
      'climate.fire_heating': {
        entity_id: 'climate.fire_heating',
        state: 'heat',
        attributes: {
          friendly_name: 'Living room heating',
          hvac_modes: ['off', 'heat'],
          temperature: 22,
          current_temperature: null,
          min_temp: 15,
          max_temp: 30,
          target_temp_step: 0.5,
          temperature_unit: '°C',
          preset_modes: ['normal', 'eco', 'fan_only', 'boost'],
          preset_mode: 'normal',
        },
      },
      'select.fire_color': {
        entity_id: 'select.fire_color',
        state: 'yellow_red_blue',
        attributes: { options: ['yellow_red_blue', 'blue', 'red'] },
      },
      'select.fire_brightness': {
        entity_id: 'select.fire_brightness',
        state: 'high',
        attributes: { options: ['high', 'low', 'flicker_high', 'flicker_low'] },
      },
      'number.fire_speed': {
        entity_id: 'number.fire_speed',
        state: '3',
        attributes: { friendly_name: 'Flame speed', min: 1, max: 5, step: 1 },
      },
      'sensor.room_temperature': {
        entity_id: 'sensor.room_temperature',
        state: '19.5',
        attributes: { device_class: 'temperature', unit_of_measurement: '°C' },
      },
    },
    callService: async () => undefined,
    callWS: async <T>() => [] as T,
  };
}
