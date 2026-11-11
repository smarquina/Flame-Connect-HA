import type { CardConfig, Choice, FireplaceState, Temperature } from '../../domain/model';
import { convertTemperature, validNumericValue } from '../../domain/state';
import type { HassEntity, HomeAssistant } from './types';

const UNAVAILABLE = new Set(['unavailable', 'unknown']);
export const available = (entity: HassEntity | undefined): entity is HassEntity =>
  entity !== undefined && !UNAVAILABLE.has(entity.state);
const numeric = (value: unknown): number | null =>
  typeof value === 'number' && Number.isFinite(value) ? value : null;
const unit = (value: unknown): Temperature['unit'] | null =>
  value === '°C' || value === '°F' ? value : null;
const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === 'string') : [];
const onOff = (entity: HassEntity | undefined): boolean | null =>
  available(entity) && ['on', 'off'].includes(entity.state) ? entity.state === 'on' : null;

function choice(entity: HassEntity | undefined): Choice {
  const options = strings(entity?.attributes.options);
  return {
    available: available(entity) && options.includes(entity.state),
    value: available(entity) && options.includes(entity.state) ? entity.state : null,
    options,
  };
}

function ambientReading(
  entity: HassEntity | undefined,
  nativeUnit: Temperature['unit'] | null,
): Temperature | null {
  const ambientUnit = unit(entity?.attributes.unit_of_measurement);
  if (
    !available(entity) ||
    entity.attributes.device_class !== 'temperature' ||
    entity.state.trim() === ''
  )
    return null;
  const value = Number(entity.state);
  const displayUnit = nativeUnit ?? ambientUnit;
  if (!Number.isFinite(value) || !ambientUnit || !displayUnit) return null;
  return { value: convertTemperature(value, ambientUnit, displayUnit), unit: displayUnit };
}

function heatingState(
  entity: HassEntity | undefined,
  configured: boolean,
  enabled: boolean,
): boolean | null {
  if (!configured) return false;
  if (!enabled || !entity || !['off', 'heat'].includes(entity.state)) return null;
  return entity.state === 'heat';
}

function limits(attr: Record<string, unknown>) {
  const minimum = numeric(attr.min_temp);
  const maximum = numeric(attr.max_temp);
  const valid = minimum !== null && maximum !== null && minimum <= maximum;
  const step = numeric(attr.target_temp_step);
  return {
    minimum: valid ? minimum : null,
    maximum: valid ? maximum : null,
    step: step !== null && step > 0 ? step : null,
  };
}

function speedSetting(entity: HassEntity | undefined): FireplaceState['speed'] {
  if (!available(entity) || entity.state.trim() === '') return null;
  const value = Number(entity.state);
  const minimum = numeric(entity.attributes.min);
  const maximum = numeric(entity.attributes.max);
  const step = numeric(entity.attributes.step);
  if (
    minimum === null ||
    maximum === null ||
    step === null ||
    !validNumericValue(value, minimum, maximum, step)
  )
    return null;
  return { value, minimum, maximum, step };
}

export function mapState(config: CardConfig, hass: HomeAssistant): FireplaceState {
  const get = (role: keyof CardConfig['entities']) => hass.states[config.entities[role] ?? ''];
  const climate = get('climate');
  const flame = get('flame');
  const attr = climate?.attributes ?? {};
  const climateAvailable =
    available(climate) &&
    strings(attr.hvac_modes).includes('heat') &&
    strings(attr.hvac_modes).includes('off');
  const nativeUnit = unit(attr.temperature_unit) ?? unit(hass.config?.unit_system?.temperature);
  const targetValue = numeric(attr.temperature);
  const range = limits(attr);
  const validTarget =
    targetValue !== null &&
    range.minimum !== null &&
    range.maximum !== null &&
    range.step !== null &&
    validNumericValue(targetValue, range.minimum, range.maximum, range.step);
  const friendlyName = climate?.attributes.friendly_name ?? flame?.attributes.friendly_name;
  return {
    speed: speedSetting(get('speed')),
    name: config.name ?? (typeof friendlyName === 'string' ? friendlyName : 'Fireplace'),
    power: onOff(get('power')),
    flame: config.entities.flame ? onOff(flame) : false,
    heating: heatingState(climate, Boolean(config.entities.climate), climateAvailable),
    climateAvailable,
    mode: available(climate) && typeof attr.preset_mode === 'string' ? attr.preset_mode : null,
    modes: strings(attr.preset_modes),
    target:
      climateAvailable && validTarget && targetValue !== null && nativeUnit
        ? {
            value: targetValue,
            unit: nativeUnit,
            minimum: range.minimum!,
            maximum: range.maximum!,
            step: range.step!,
          }
        : null,
    ambient: ambientReading(get('ambient'), nativeUnit),
    color: choice(get('color')),
    brightness: choice(get('brightness')),
  };
}
