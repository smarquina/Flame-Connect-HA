import type { Bindings } from '../../domain/model';
import type { HomeAssistant, RegistryEntry } from './types';

import { ENTITY_CONTRACTS, ENTITY_ROLES } from '../../configuration/entity-contracts';

export interface DiscoveredFireplace {
  id: string;
  name: string;
  entities: Bindings;
}

export async function discover(hass: HomeAssistant): Promise<DiscoveredFireplace[]> {
  const entries = await hass.callWS<RegistryEntry[]>({ type: 'config/entity_registry/list' });
  const devices = new Map<string, DiscoveredFireplace>();
  for (const entry of [...entries].sort((left, right) =>
    left.entity_id.localeCompare(right.entity_id, 'en'),
  )) {
    if (entry.platform !== 'flame_connect' || !entry.device_id || entry.disabled_by) continue;
    const role = ENTITY_ROLES.find((key) => {
      const { suffix, domain } = ENTITY_CONTRACTS[key];
      return (
        suffix !== null &&
        entry.unique_id.endsWith(suffix) &&
        entry.entity_id.startsWith(domain + '.')
      );
    });
    if (!role) continue;
    const device = devices.get(entry.device_id) ?? {
      id: entry.device_id,
      name: entry.name ?? entry.original_name ?? entry.device_id,
      entities: {},
    };
    device.entities[role] = entry.entity_id;
    if (role === 'climate' || (role === 'flame' && !device.entities.climate)) {
      const name = hass.states[entry.entity_id]?.attributes.friendly_name;
      if (typeof name === 'string') device.name = name;
    }
    devices.set(entry.device_id, device);
  }
  return [...devices.values()]
    .filter((device) => device.entities.flame || device.entities.climate)
    .sort(
      (left, right) =>
        left.name.localeCompare(right.name, 'en') || left.id.localeCompare(right.id, 'en'),
    );
}
