import { html } from 'lit';
import { styleMap } from 'lit/directives/style-map.js';
import { numberText, sliderPrecision } from '../localization/localize';
import { icon } from './icons';

interface SliderOptions {
  kind: 'target' | 'speed';
  confirmed: number | null;
  lower: number | null;
  upper: number | null;
  step: number | null;
  unit: string;
  language: string;
  label: string;
  disabled: boolean;
  commit: (value: number) => void;
}
function sliderFill(value: number, minimum: number, maximum: number): string {
  const fraction = maximum > minimum ? (value - minimum) / (maximum - minimum) : 0;
  return `${Math.max(0, Math.min(1, fraction)) * 100}%`;
}

export function renderSlider({
  kind,
  confirmed,
  lower,
  upper,
  step,
  unit,
  language,
  label,
  disabled,
  commit,
}: SliderOptions) {
  const enabled =
    confirmed !== null && lower !== null && upper !== null && step !== null && upper > lower;
  const minimum = lower ?? 0;
  const maximum = upper ?? minimum;
  const value = confirmed ?? minimum;
  const fill = sliderFill(value, minimum, maximum);
  const format = (number: number) =>
    numberText(language, number, sliderPrecision(minimum, step ?? 1)) + (unit ? ' ' + unit : '');
  const reading = confirmed === null ? '—' : format(confirmed);
  return html`<div class="slider-row">
    <label class="slider-label" for=${kind} title=${label}>
      ${icon(kind)}<span class="sr-only">${label}</span>
      <span class="slider-value ${kind}-value">${reading}</span>
    </label>
    <input
      id=${kind}
      type="range"
      aria-label=${label}
      aria-valuetext=${reading}
      .value=${String(value)}
      min=${minimum}
      max=${maximum}
      step=${step ?? 1}
      style=${styleMap({ '--fill': fill })}
      ?disabled=${disabled || !enabled}
      @input=${(event: Event) => {
        const input = event.currentTarget as HTMLInputElement;
        input.style.setProperty('--fill', sliderFill(input.valueAsNumber, minimum, maximum));
        input.setAttribute('aria-valuetext', format(input.valueAsNumber));
      }}
      @change=${(event: Event) => {
        const input = event.currentTarget as HTMLInputElement;
        commit(input.valueAsNumber);
        input.value = String(value);
        input.style.setProperty('--fill', fill);
        input.setAttribute('aria-valuetext', reading);
      }}
    />
  </div>`;
}
