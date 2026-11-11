import { html, css, nothing, type TemplateResult } from 'lit';
import type { FireplaceState } from '../domain/model';
import { effectiveEffect } from '../domain/state';

export function renderChip(
  state: FireplaceState,
  name: string,
  status: string,
  expandLabel: string,
  expand: () => void,
  actions: TemplateResult,
  popup: boolean,
) {
  const flame = effectiveEffect(state, 'flame');
  const heat = effectiveEffect(state, 'heating');
  const active = flame === true || heat === true;
  const unknown = flame === null || heat === null;
  return html`<div class="chip">
    <button
      class="chip-summary"
      type="button"
      aria-expanded=${popup ? nothing : 'false'}
      aria-haspopup=${popup ? 'dialog' : nothing}
      @click=${expand}
    >
      <span class="sr-only">${expandLabel}: </span>
      <span class="chip-icon" data-active=${String(active)}
        ><ha-icon icon="mdi:fireplace"></ha-icon
      ></span>
      <span class="chip-text"><strong>${name}</strong> <span>${status}</span></span>
      ${unknown ? html`<span class="chip-warning"><ha-icon icon="mdi:alert-circle-outline"></ha-icon></span>` : ''}
    </button>
    ${actions}
  </div>`;
}
export const chipStyles = css`
  ha-card[data-view='chip'] {
    border-radius: var(--ha-card-border-radius, 12px);
  }
  .chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px;
  }
  .chip-summary {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 10px;
    border: 0;
    background: transparent;
    text-align: start;
    padding: 0;
    min-height: 36px;
  }
  .chip-icon {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(
      --fireplace-icon-background,
      var(--chip-background, color-mix(in srgb, var(--primary-text-color, #202020) 6%, transparent))
    );
    color: var(--secondary-text-color, #777);
  }
  .chip-icon[data-active='true'] {
    color: var(--state-climate-heat-color, #e87500);
  }
  .chip-text {
    display: grid;
    min-width: 0;
    gap: 0;
  }
  .chip-text strong {
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
  }
  .chip ha-icon {
    --mdc-icon-size: 20px;
    width: 20px;
    height: 20px;
  }
  dialog {
    padding: 0;
    border: 0;
    background: transparent;
    width: calc(100% - 32px);
    max-width: 600px;
    max-height: calc(100dvh - 32px);
    overflow: auto;
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 45%);
  }
  .chip-text strong,
  .chip-text > span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .chip-text > span {
    font-size: 12px;
    font-weight: 400;
    line-height: 16px;
    color: var(--secondary-text-color, #555);
  }
  .chip .toggles {
    flex-shrink: 0;
    gap: 6px;
  }
  .chip .toggles button {
    width: 36px;
    min-height: 36px;
    height: 36px;
    border-radius: 12px;
  }
  :where(.chip .toggles) button:where([aria-pressed='true']) {
    color: var(
      --fireplace-action-active-color,
      var(--fireplace-action-color, var(--primary-color, var(--state-climate-heat-color, #e87500)))
    );
  }
  .chip-warning {
    color: var(--error-color, #a72020);
  }
  .chip-feedback:empty {
    display: none;
  }
`;
