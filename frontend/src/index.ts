import { FlameConnectCard } from './presentation/card';
if (!customElements.get('flame-connect-card'))
  customElements.define('flame-connect-card', FlameConnectCard);
const registry = window as unknown as {
  customCards?: { type: string; name: string; description: string; preview: boolean }[];
};
registry.customCards ??= [];
if (!registry.customCards.some((card) => card.type === 'flame-connect-card'))
  registry.customCards.push({
    type: 'flame-connect-card',
    name: 'Flame Connect Card',
    description: 'Unofficial fireplace control panel for Flame Connect HA.',
    preview: true,
  });
