import en from './en.json';
import es from './es.json';
export type TranslationKey = keyof typeof en;
export function translate(language: string, key: TranslationKey): string {
  return localize(language, key);
}
export function localize(language: string, key: string): string {
  const dictionary: Record<string, string> = language.toLowerCase().startsWith('es') ? es : en;
  const lookup = (entry: string) =>
    Object.hasOwn(dictionary, entry) ? dictionary[entry] : undefined;
  return (
    lookup(key) ??
    key
      .split('_')
      .map((part) => lookup(part) ?? part)
      .join(' + ')
  );
}
export function numberText(language: string, value: number, precision = 1): string {
  try {
    return new Intl.NumberFormat(language, { maximumFractionDigits: precision }).format(value);
  } catch {
    return new Intl.NumberFormat('en', { maximumFractionDigits: precision }).format(value);
  }
}

export function sliderPrecision(minimum: number, step: number): number {
  const decimalPlaces = (value: number): number => {
    const [mantissa, exponent = '0'] = String(value).split('e');
    return Math.max(0, (mantissa!.split('.')[1]?.length ?? 0) - Number(exponent));
  };
  return Math.min(20, Math.max(1, decimalPlaces(minimum), decimalPlaces(step)));
}
