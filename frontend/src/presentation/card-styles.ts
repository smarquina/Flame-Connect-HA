import { css } from 'lit';
export const cardStyles = css`
  ha-card {
    display: block;
    overflow: hidden;
    border: 1px solid var(--ha-card-border-color, var(--divider-color, #ddd));
    border-radius: var(--ha-card-border-radius, 16px);
    background: var(--ha-card-background, var(--card-background-color, #fff));
  }
  header {
    padding: 18px 20px 12px;
    display: flex;
    gap: 12px;
    justify-content: space-between;
    align-items: center;
  }
  h2 {
    font-size: 1.15rem;
    margin: 0 0 4px;
    font-weight: 600;
  }
  .status-icons {
    display: flex;
    gap: 8px;
    color: var(--secondary-text-color, #555);
  }
  .status-icons [data-state='on'] {
    color: var(--primary-color, #007a91);
  }
  .status-icons [data-state='unknown'] {
    color: var(--error-color, #a72020);
  }
  .view-toggle {
    display: grid;
    place-items: center;
    min-width: 44px;
  }
  ha-card[data-view='compact'] .body {
    padding-top: 8px;
    gap: 12px;
  }
  ha-card[data-view='compact'] .scene {
    width: min(100%, 220px);
    margin-inline: auto;
  }
  .scene {
    aspect-ratio: 2.05;
    background-color: #000;
    background-size: 200% 200%;
    background-repeat: no-repeat;
  }
  .scene.unknown {
    background-image: none !important;
    display: grid;
    place-items: center;
    color: #ddd;
  }
  .body {
    display: grid;
    gap: 18px;
    padding: 18px 20px;
  }
  .toggles:empty,
  .settings:empty {
    display: none;
  }
  .toggles {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: center;
  }
  :where(.toggles) button {
    width: 56px;
    height: 56px;
    display: grid;
    place-items: center;
    padding: 0;
    border: none;
    border-radius: 16px;
    --_fireplace-action-background: var(
      --fireplace-action-background,
      var(--chip-background, color-mix(in srgb, var(--primary-text-color, #202020) 6%, transparent))
    );
    background: var(--_fireplace-action-background);
    color: var(--fireplace-action-color, inherit);
  }
  :where(.toggles) button:where([aria-pressed='true']) {
    background: var(--fireplace-action-active-background, var(--_fireplace-action-background));
    color: var(
      --fireplace-action-active-color,
      var(--fireplace-action-color, var(--primary-color, #007a91))
    );
    box-shadow: inset 0 0 0 2px currentColor;
  }
  svg {
    width: 24px;
    height: 24px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
    flex-shrink: 0;
  }
  .control-label {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  :where(.control-label) select,
  button:where(.view-toggle) {
    background: var(
      --fireplace-control-background,
      color-mix(in srgb, var(--primary-text-color, #202020) 6%, transparent)
    );
    color: var(--fireplace-control-color, inherit);
    border-color: var(
      --fireplace-control-border-color,
      color-mix(in srgb, var(--primary-text-color, #202020) 20%, transparent)
    );
  }
  :where(.control-label) option {
    background-color: var(--fireplace-option-background, Canvas);
    color: var(--fireplace-option-color, CanvasText);
  }
  .feedback {
    display: flex;
    justify-content: center;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
    border: 0;
  }
  .settings {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 14px;
    align-items: center;
  }
  .settings > div {
    min-width: 0;
  }
  .reading-label {
    display: inline-flex;
    color: var(--secondary-text-color, #555);
  }
  .reading {
    font-size: 1.7rem;
    font-weight: 600;
    margin-top: 6px;
  }
  .settings > [data-control='target'],
  .settings > [data-control='speed'] {
    grid-column: 1 / -1;
  }
  .slider-row {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 12px;
    border: 1px solid var(--divider-color, #ddd);
    border-radius: 18px;
  }
  .slider-label {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  .slider-label > svg {
    box-sizing: content-box;
    padding: 10px;
    border-radius: 50%;
    background: var(
      --fireplace-control-background,
      color-mix(in srgb, var(--primary-text-color, #202020) 6%, transparent)
    );
  }
  .slider-value {
    font-size: 1.1rem;
    font-weight: 600;
    white-space: nowrap;
  }
  input[type='range'] {
    appearance: none;
    -webkit-appearance: none;
    min-width: 0;
    width: 100%;
    height: 48px;
    min-height: 48px;
    margin: 0;
    padding: 0 9px;
    border: 0;
    border-radius: 16px;
    background: linear-gradient(
      to right,
      var(--state-climate-heat-color, #ffab56) var(--fill),
      var(--secondary-background-color, #eee) var(--fill)
    );
    cursor: pointer;
  }
  input[type='range']:disabled {
    cursor: default;
  }
  input[type='range']::-webkit-slider-runnable-track {
    height: 28px;
    background: transparent;
  }
  input[type='range']::-webkit-slider-thumb {
    appearance: none;
    -webkit-appearance: none;
    width: 5px;
    height: 28px;
    border: 0;
    border-radius: 4px;
    background: #fff;
    box-shadow: 0 0 0 1px #888;
  }
  input[type='range']::-moz-range-track {
    height: 28px;
    background: transparent;
  }
  input[type='range']::-moz-range-thumb {
    width: 5px;
    height: 28px;
    border: 0;
    border-radius: 4px;
    background: #fff;
    box-shadow: 0 0 0 1px #888;
  }
  @media (max-width: 360px) {
    header {
      padding: 14px;
    }
    .body {
      padding: 14px;
    }
    .settings {
      grid-template-columns: 1fr;
    }
  }
`;
