import {
  ControlError,
  SUPPORTED_PRESETS,
  NUMERIC_STEP_TOLERANCE,
  TEMPERATURE_CONFIRMATION_TOLERANCE,
  type Command,
  type FireplaceState,
  type VisualState,
} from './model';

export function validNumericValue(
  value: number,
  minimum: number,
  maximum: number,
  step: number,
): boolean {
  const steps = (value - minimum) / step;
  return (
    Number.isFinite(value) &&
    Number.isFinite(minimum) &&
    Number.isFinite(maximum) &&
    Number.isFinite(step) &&
    step > 0 &&
    minimum <= maximum &&
    value >= minimum &&
    value <= maximum &&
    Math.abs(steps - Math.round(steps)) <= NUMERIC_STEP_TOLERANCE
  );
}

export function effectiveEffect(state: FireplaceState, kind: 'flame' | 'heating'): boolean | null {
  return state.power === false ? false : state[kind];
}

export function visualState(state: FireplaceState): VisualState {
  if (state.power === false) return 'off';
  if (state.flame === null || state.heating === null) return 'unknown';
  const heat = state.heating && state.mode !== 'fan_only';
  if (heat) return state.flame ? 'both' : 'heat';
  return state.flame ? 'flame' : 'off';
}

export function visibleModes(state: FireplaceState): string[] {
  return state.modes.filter((mode) => SUPPORTED_PRESETS.some((preset) => preset === mode));
}

function validateTemperature(state: FireplaceState, value: number): void {
  if (!state.climateAvailable || !state.target) throw new ControlError('unavailable');
  const { minimum, maximum, step } = state.target;
  if (!validNumericValue(value, minimum, maximum, step)) throw new ControlError('invalid_value');
}

function validateSpeed(state: FireplaceState, value: number): void {
  if (!state.speed) throw new ControlError('unavailable');
  const { minimum, maximum, step } = state.speed;
  if (!validNumericValue(value, minimum, maximum, step)) throw new ControlError('invalid_value');
}

function validateEffect(state: FireplaceState, kind: 'power' | 'flame', value: boolean): void {
  if (state[kind] === null) throw new ControlError('unavailable');
  if (kind === 'flame' && value && state.power === false) throw new ControlError('standby');
}

export function validateCommand(state: FireplaceState, command: Command): void {
  switch (command.kind) {
    case 'power':
    case 'flame':
      validateEffect(state, command.kind, command.value);
      break;
    case 'heating':
      if (!state.climateAvailable || state.heating === null) throw new ControlError('unavailable');
      break;
    case 'speed':
      validateSpeed(state, command.value);
      break;
    case 'temperature': {
      validateTemperature(state, command.value);
      break;
    }
    case 'mode':
      if (!state.climateAvailable) throw new ControlError('unavailable');
      if (!visibleModes(state).includes(command.value)) throw new ControlError('invalid_value');
      break;
    case 'color':
    case 'brightness':
      if (!state[command.kind].available) throw new ControlError('unavailable');
      if (!state[command.kind].options.includes(command.value))
        throw new ControlError('invalid_value');
  }
}

export function isConfirmed(state: FireplaceState, command: Command): boolean {
  switch (command.kind) {
    case 'speed':
      return state.speed !== null && state.speed.value === command.value;
    case 'temperature':
      return (
        state.target !== null &&
        Math.abs(state.target.value - command.value) <
          Math.min(TEMPERATURE_CONFIRMATION_TOLERANCE, state.target.step / 2)
      );
    case 'mode':
      return state.mode === command.value && state.climateAvailable;
    case 'color':
    case 'brightness':
      return state[command.kind].available && state[command.kind].value === command.value;
    case 'flame':
    case 'heating':
      return effectiveEffect(state, command.kind) === command.value;
    default:
      return state[command.kind] === command.value;
  }
}

export function convertTemperature(value: number, from: '°C' | '°F', to: '°C' | '°F'): number {
  if (from === to) return value;
  return to === '°C' ? ((value - 32) * 5) / 9 : (value * 9) / 5 + 32;
}
