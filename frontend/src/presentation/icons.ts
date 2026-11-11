import { html, svg } from 'lit';

const paths = {
  close: 'M6 6l12 12 M18 6L6 18',
  fireplace: 'M3 5h18v15H3z M3 8h18 M8 17c-2-3 2-4 3-7 3 3 6 5 3 7 M6 17h12',
  power_on: 'M8 5l11 7-11 7z',
  power_off: 'M12 3v9 M6.3 5.8a9 9 0 1 0 11.4 0',
  flame: 'M12 3c1 5 6 6 6 12a6 6 0 0 1-12 0c0-3 2-5 3-6 0 3 1 4 2 4 2-3 2-6 1-10z',
  heating: 'M6 21c5-6-5-10 0-18 M12 21c5-6-5-10 0-18 M18 21c5-6-5-10 0-18',
  ambient: 'M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0 M12 10v8',
  target:
    'M12 3v3 M12 18v3 M3 12h3 M18 12h3 M19 12a7 7 0 1 1-14 0 7 7 0 0 1 14 0 M14 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0',
  mode: 'M12 12c-5-9 7-12 6-5 0 3-3 4-6 5 M12 12c10 0 7 12 2 8-2-1-2-5-2-8 M12 12c-5 9-14 0-8-2 3-1 5 1 8 2',
  color:
    'M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-4 2 2 0 0 1 1-4h3c5 0 3-10-6-10 M7 9h.01 M10 6h.01 M15 6h.01 M18 9h.01',
  brightness:
    'M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1 1 M18 18l1 1 M5 19l1-1 M18 6l1-1 M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  speed: 'M4 18a9 9 0 1 1 16 0 M12 14l5-7 M6 11l1 1 M12 5v2 M18 11l-1 1',
  expand: 'M5 9l7 7 7-7',
  collapse: 'M5 15l7-7 7 7',
  pending: 'M12 8v4l3 2 M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0',
  unavailable: 'M12 3L2 21h20z M12 9v5 M12 17h.01',
} as const;

export type IconName = keyof typeof paths;

export function icon(name: IconName) {
  return html`<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    ${svg`<path d=${paths[name]} />`}
  </svg>`;
}
