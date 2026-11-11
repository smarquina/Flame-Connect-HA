import type { CardConfig, DetailControl, EntityRole } from './model';

export const CONTROL_ROLES = {
  ambient: 'ambient',
  target: 'climate',
  mode: 'climate',
  color: 'color',
  brightness: 'brightness',
  speed: 'speed',
} as const satisfies Record<DetailControl, EntityRole>;
export function visibleControl(config: CardConfig, kind: DetailControl): boolean {
  return config[`show_${kind}`] && Boolean(config.entities[CONTROL_ROLES[kind]]);
}
