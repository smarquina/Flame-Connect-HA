import { expect, it } from 'vitest';
import en from '../../src/localization/en.json';
import es from '../../src/localization/es.json';
import { localize, numberText, translate, sliderPrecision } from '../../src/localization/localize';
it('has complete, non-empty English and Spanish translations', () => {
  expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
  expect(Object.values(es).every((value) => value.trim().length > 0)).toBe(true);
  expect(localize('es-ES', 'target')).toBe('Temperatura objetivo');
  expect(localize('en', 'target')).toBe('Target temperature');
  expect(localize('fr', 'target')).toBe('Target temperature');
  expect(localize('es', 'yellow_red_blue')).toBe('Amarillo + Rojo + Azul');
  expect(localize('en', 'custom_palette')).toBe('custom + palette');
  expect(numberText('es', 22.5)).toBe('22,5');
  expect(numberText('en', 22.5)).toBe('22.5');
  expect(numberText('not a locale', 22.5)).toBe('22.5');
});

it('preserves explicitly requested numeric precision and typed labels', () => {
  expect(numberText('en', 20.25, 2)).toBe('20.25');
  expect(translate('es', 'target')).toBe('Temperatura objetivo');
});

it('preserves offset and scientific-notation slider precision', () => {
  expect(numberText('en', 20.15, sliderPrecision(20.05, 0.1))).toBe('20.15');
  expect(sliderPrecision(0, 1e-7)).toBe(7);
  expect(sliderPrecision(1.25e-7, 1e-7)).toBe(9);
  expect(sliderPrecision(0, 1e21)).toBe(1);
  expect(sliderPrecision(0, 1e-30)).toBe(20);
});
