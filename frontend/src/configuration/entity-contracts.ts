import type { EntityRole } from '../domain/model';

// Home Assistant boundary metadata; the domain itself does not depend on HA domains.
export const ENTITY_CONTRACTS = {
  climate: { domain: 'climate', suffix: '_heating', label: 'heating' },
  flame: { domain: 'light', suffix: '_flame', label: 'flame' },
  power: { domain: 'switch', suffix: '_power', label: 'power' },
  ambient: { domain: 'sensor', suffix: null, label: 'ambient' },
  color: { domain: 'select', suffix: '_color', label: 'color' },
  brightness: { domain: 'select', suffix: '_brightness', label: 'brightness' },
  speed: { domain: 'number', suffix: '_speed', label: 'speed' },
} as const satisfies Record<EntityRole, { domain: string; suffix: string | null; label: string }>;
export const ENTITY_ROLES = Object.keys(ENTITY_CONTRACTS) as EntityRole[];
