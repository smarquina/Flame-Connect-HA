import type { FireplaceState } from '../domain/model';
import type { IconName } from './icons';
import { effectiveEffect } from '../domain/state';

interface EffectPresentation {
  value: boolean | null;
  label: 'flame' | 'heating' | 'ventilation';
  status: 'on' | 'off' | 'not_available';
  state: 'on' | 'off' | 'unknown';
  icon: IconName;
}
export function effectPresentation(
  state: FireplaceState,
  kind: 'flame' | 'heating',
): EffectPresentation {
  const value = effectiveEffect(state, kind);
  const label = kind === 'heating' && state.mode === 'fan_only' ? 'ventilation' : kind;
  let status: 'on' | 'off' | 'not_available' = 'not_available';
  if (value !== null) status = value ? 'on' : 'off';
  const stateLabel = status === 'not_available' ? 'unknown' : status;
  const effectIcon = label === 'ventilation' ? 'mode' : kind;
  return {
    value,
    label,
    status,
    state: stateLabel,
    icon: value === null ? ('unavailable' as const) : effectIcon,
  };
}
