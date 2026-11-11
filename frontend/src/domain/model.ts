export const CARD_TYPE = 'custom:flame-connect-card';
export const SCHEMA_VERSION = 1;
export const COMMAND_TIMEOUT_MS = 45_000;
export const NUMERIC_STEP_TOLERANCE = 0.001;
export const TEMPERATURE_CONFIRMATION_TOLERANCE = 0.01;
export const SUPPORTED_PRESETS = ['normal', 'eco', 'fan_only'] as const;
export const VISUAL_STATES = ['off', 'flame', 'heat', 'both', 'unknown'] as const;
export type VisualState = (typeof VISUAL_STATES)[number];
export type EntityRole =
  'power' | 'flame' | 'climate' | 'color' | 'brightness' | 'ambient' | 'speed';
export type Bindings = Partial<Record<EntityRole, string>>;
export const VISIBILITY_OPTIONS = [
  'show_power',
  'show_flame',
  'show_heating',
  'show_image',
  'show_target',
  'show_ambient',
  'show_mode',
  'show_color',
  'show_brightness',
  'show_speed',
] as const;
export const LEGACY_DETAIL_CONTROLS = ['ambient', 'target', 'mode', 'color', 'brightness'] as const;
export const DETAIL_CONTROLS = [...LEGACY_DETAIL_CONTROLS, 'speed'] as const;
export type DetailControl = (typeof DETAIL_CONTROLS)[number];
export type VisibilityOption = (typeof VISIBILITY_OPTIONS)[number];
export interface CardConfig extends Record<VisibilityOption, boolean> {
  type: typeof CARD_TYPE;
  card_mod?: unknown;
  version: number;
  name?: string;
  entities: Bindings;
  control_order: DetailControl[];
  image_background: string;
  initial_view: 'compact' | 'expanded';
  compact_style: 'standard' | 'chip';
  chip_expansion: 'modal' | 'inline';
  compact_image: boolean;
  compact_controls: DetailControl[];
  images: Partial<Record<Exclude<VisualState, 'unknown'>, string>>;
}
export interface Choice {
  available: boolean;
  value: string | null;
  options: readonly string[];
}
export interface Temperature {
  value: number;
  unit: '°C' | '°F';
}
export interface NumericSetting {
  value: number;
  minimum: number;
  maximum: number;
  step: number;
}
export interface FireplaceState {
  speed: NumericSetting | null;
  name: string;
  power: boolean | null;
  flame: boolean | null;
  heating: boolean | null;
  climateAvailable: boolean;
  mode: string | null;
  modes: readonly string[];
  target: (Temperature & NumericSetting) | null;
  ambient: Temperature | null;
  color: Choice;
  brightness: Choice;
}
export type Command =
  | { kind: 'power' | 'flame' | 'heating'; value: boolean }
  | { kind: 'temperature' | 'speed'; value: number }
  | { kind: 'mode' | 'color' | 'brightness'; value: string };
export type ErrorCode = 'unavailable' | 'invalid_value' | 'standby' | 'busy' | 'timeout' | 'failed';
export class ControlError extends Error {
  constructor(readonly code: ErrorCode) {
    super(code);
  }
}
