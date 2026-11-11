import { render } from 'lit';
import { icon, type IconName } from '../../src/presentation/icons';
import { config, fakeHass } from './state';
import type { FlameConnectCard } from '../../src/presentation/card';
import type { HomeAssistant, RegistryEntry } from '../../src/adapters/home-assistant/types';

const cards: FlameConnectCard[] = [];
const hass = fakeHass();
const calls: unknown[] = [];
const entities = { ...config.entities, speed: 'number.fire_speed' };
const demo = { hass, calls, fail: false, defer: false, update, add };
declare global {
  interface Window {
    demo: typeof demo;
  }
}
window.demo = demo;
function update(): void {
  for (const card of cards) card.hass = { ...hass };
}
function add(name = 'Living room'): FlameConnectCard {
  const card = document.createElement('flame-connect-card') as FlameConnectCard;
  card.setConfig({ ...config, name, entities });
  card.hass = hass;
  cards.push(card);
  document.querySelector('main')!.append(card);
  return card;
}
hass.callWS = async <T>() => {
  const entries: RegistryEntry[] = Object.entries(entities)
    .filter(([role]) => role !== 'ambient')
    .map(([role, entity]) => ({
      entity_id: entity!,
      unique_id: `fire_${role === 'climate' ? 'heating' : role}`,
      platform: 'flame_connect',
      device_id: 'fire-device',
      disabled_by: null,
      original_name: 'Living room',
    }));
  return entries as T;
};
hass.callService = async (domain, service, data, target) => {
  calls.push({ domain, service, data, target });
  if (demo.fail) throw new Error('Synthetic service failure');
  if (demo.defer) return;
  const entity = hass.states[target.entity_id]!;
  if (service === 'turn_on' || service === 'turn_off')
    entity.state = service === 'turn_on' ? 'on' : 'off';
  if (service === 'set_hvac_mode') entity.state = String(data.hvac_mode);
  if (service === 'set_value') entity.state = String(data.value);
  if (service === 'set_temperature') entity.attributes.temperature = data.temperature;
  if (service === 'set_preset_mode') entity.attributes.preset_mode = data.preset_mode;
  if (service === 'select_option') entity.state = String(data.option);
  update();
};
add();
export type DemoHass = HomeAssistant;

// Render local stand-ins for HA's icon element in the standalone simulator.
if (!customElements.get('ha-icon'))
  customElements.define(
    'ha-icon',
    class extends HTMLElement {
      constructor() {
        super();
        this.attachShadow({ mode: 'open' });
      }
      static get observedAttributes() {
        return ['icon'];
      }
      connectedCallback() {
        this.attributeChangedCallback();
      }
      attributeChangedCallback() {
        const names: Record<string, IconName> = {
          'mdi:fireplace': 'fireplace',
          'mdi:fire': 'flame',
          'mdi:radiator': 'heating',
          'mdi:fan': 'mode',
          'mdi:alert-circle-outline': 'unavailable',
        };
        render(icon(names[this.getAttribute('icon') ?? ''] ?? 'unavailable'), this.shadowRoot!);
        const svg = this.shadowRoot!.querySelector('svg')!;
        svg.style.width = '20px';
        svg.style.height = '20px';
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
      }
    },
  );
