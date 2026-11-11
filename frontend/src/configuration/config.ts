import {
  CARD_TYPE,
  DETAIL_CONTROLS,
  LEGACY_DETAIL_CONTROLS,
  type DetailControl,
  SCHEMA_VERSION,
  VISIBILITY_OPTIONS,
  type CardConfig,
  type EntityRole,
} from '../domain/model';

import { ENTITY_CONTRACTS } from './entity-contracts';

export class ConfigurationError extends Error {
  readonly code = 'invalid_config';
  readonly field: string;
  constructor(readonly detail: string) {
    super(detail);
    this.field = detail.split(':')[0]!;
  }
}

const RECORD = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);

export function validateImage(value: unknown): string {
  if (typeof value !== 'string')
    throw new ConfigurationError(
      'images: use a same-origin absolute path, e.g. /local/fireplace.png',
    );
  const url = new URL(value, 'https://home-assistant.invalid');
  if (url.origin !== 'https://home-assistant.invalid')
    throw new ConfigurationError(
      'images: external URLs are not supported; use a same-origin absolute path',
    );
  if (!/^\/(?!\/)[^\s\\]*$/.test(value))
    throw new ConfigurationError(
      'images: use a same-origin absolute path, e.g. /local/fireplace.png',
    );
  return value;
}

function parseEntities(value: unknown): CardConfig['entities'] {
  if (!RECORD(value)) throw new ConfigurationError('entities: select a flame or climate entity');
  const entities: CardConfig['entities'] = {};
  for (const [key, entry] of Object.entries(value)) {
    if (!Object.hasOwn(ENTITY_CONTRACTS, key))
      throw new ConfigurationError(`entities.${key}: unsupported role`);
    const role = key as EntityRole;
    if (
      typeof entry !== 'string' ||
      !new RegExp(`^${ENTITY_CONTRACTS[role].domain}\\.[a-z0-9_]+$`).test(entry)
    )
      throw new ConfigurationError(
        `entities.${key}: expected a ${ENTITY_CONTRACTS[role].domain} entity`,
      );
    entities[role] = entry;
  }
  if (!entities.flame && !entities.climate)
    throw new ConfigurationError('entities: select a flame or climate entity');
  return entities;
}

function parseImages(value: unknown): CardConfig['images'] {
  const images: CardConfig['images'] = {};
  if (value === undefined) return images;
  if (!RECORD(value)) throw new ConfigurationError('images: expected an object');
  for (const [key, image] of Object.entries(value)) {
    if (!['off', 'flame', 'heat', 'both'].includes(key))
      throw new ConfigurationError(`images.${key}: unsupported state`);
    images[key as keyof typeof images] = validateImage(image);
  }
  return images;
}

export function parseControlOrder(value: unknown): DetailControl[] {
  if (value === undefined) return [...DETAIL_CONTROLS];
  if (!Array.isArray(value)) throw new ConfigurationError('control_order: expected an array');
  const legacy = value.length === LEGACY_DETAIL_CONTROLS.length && !value.includes('speed');
  const length = legacy ? LEGACY_DETAIL_CONTROLS.length : DETAIL_CONTROLS.length;
  if (
    value.length !== length ||
    new Set(value).size !== length ||
    !value.every((entry) => DETAIL_CONTROLS.includes(entry))
  )
    throw new ConfigurationError(
      'control_order: include ambient, target, mode, color, brightness and speed exactly once',
    );
  return legacy ? [...value, 'speed'] : [...value];
}

export function parseImageBackground(value: unknown): string {
  if (value === undefined) return '#000000';
  const presets: Record<string, string> = {
    none: 'transparent',
    transparent: 'transparent',
    black: '#000000',
    white: '#ffffff',
  };
  if (typeof value === 'string') {
    if (Object.hasOwn(presets, value)) return presets[value]!;
    if (/^#[0-9a-f]{6}$/i.test(value)) return value.toLowerCase();
  }
  throw new ConfigurationError(
    'image_background: use none, transparent, black, white or a six-digit hex color',
  );
}

export function parseCompactControls(value: unknown): DetailControl[] {
  if (value === undefined) return [];
  if (
    !Array.isArray(value) ||
    new Set(value).size !== value.length ||
    !value.every((entry) => DETAIL_CONTROLS.includes(entry))
  )
    throw new ConfigurationError('compact_controls: use unique supported control names');
  return [...value];
}

function parseCompactStyle(value: unknown): CardConfig['compact_style'] {
  if (value !== undefined && value !== 'standard' && value !== 'chip')
    throw new ConfigurationError('compact_style: expected standard or chip');
  return value === 'chip' ? 'chip' : 'standard';
}

function parseChipExpansion(value: unknown): CardConfig['chip_expansion'] {
  if (value !== undefined && value !== 'modal' && value !== 'inline')
    throw new ConfigurationError('chip_expansion: expected modal or inline');
  return value === 'inline' ? 'inline' : 'modal';
}

function cardModConfig(value: Record<string, unknown>): Pick<CardConfig, 'card_mod'> {
  return Object.hasOwn(value, 'card_mod') ? { card_mod: value.card_mod } : {};
}

export function parseConfig(value: unknown): CardConfig {
  if (!RECORD(value) || value.type !== CARD_TYPE)
    throw new ConfigurationError(`type: expected ${CARD_TYPE}`);
  if (value.version !== undefined && value.version !== SCHEMA_VERSION)
    throw new ConfigurationError('version: unsupported configuration version');
  if (
    value.initial_view !== undefined &&
    (typeof value.initial_view !== 'string' ||
      !['compact', 'expanded'].includes(value.initial_view))
  )
    throw new ConfigurationError('initial_view: expected compact or expanded');
  if (value.compact_image !== undefined && typeof value.compact_image !== 'boolean')
    throw new ConfigurationError('compact_image: expected a boolean');
  const compactStyle = parseCompactStyle(value.compact_style);
  const entities = parseEntities(value.entities);
  if (value.name !== undefined && (typeof value.name !== 'string' || !value.name.trim()))
    throw new ConfigurationError('name: expected a non-empty string');
  for (const key of VISIBILITY_OPTIONS) {
    if (value[key] !== undefined && typeof value[key] !== 'boolean')
      throw new ConfigurationError(`${key}: expected a boolean`);
  }
  return {
    type: CARD_TYPE,
    ...cardModConfig(value),
    version: SCHEMA_VERSION,
    entities,
    initial_view: value.initial_view === 'compact' ? 'compact' : 'expanded',
    compact_style: compactStyle,
    chip_expansion: parseChipExpansion(value.chip_expansion),
    compact_image: value.compact_image === true,
    compact_controls: parseCompactControls(value.compact_controls),
    control_order: parseControlOrder(value.control_order),
    images: parseImages(value.images),
    image_background: parseImageBackground(value.image_background),
    show_power: value.show_power !== false,
    show_image: value.show_image !== false,
    show_flame: value.show_flame !== false,
    show_heating: value.show_heating !== false,
    show_target: value.show_target !== false,
    show_ambient: value.show_ambient !== false,
    show_mode: value.show_mode !== false,
    show_color: value.show_color !== false,
    show_brightness: value.show_brightness !== false,
    show_speed: value.show_speed !== false,
    ...(typeof value.name === 'string' ? { name: value.name } : {}),
  };
}
