import { LitElement, css, html, nothing } from 'lit';
import {
  CARD_TYPE,
  DETAIL_CONTROLS,
  type DetailControl,
  SCHEMA_VERSION,
  VISIBILITY_OPTIONS,
  type CardConfig,
  type EntityRole,
} from '../domain/model';
import {
  ConfigurationError,
  parseConfig,
  parseControlOrder,
  parseImageBackground,
} from '../configuration/config';
import { discover, type DiscoveredFireplace } from '../adapters/home-assistant/discovery';
import type { HomeAssistant } from '../adapters/home-assistant/types';
import { translate, type TranslationKey } from '../localization/localize';
import { sharedStyles } from './styles';

import { ENTITY_CONTRACTS, ENTITY_ROLES } from '../configuration/entity-contracts';

export const DISCOVERY_TIMEOUT_MS = 15_000;

export class FlameConnectCardEditor extends LitElement {
  static readonly styles = [
    sharedStyles,
    css`
      .editor {
        display: grid;
        gap: 16px;
        padding: 12px 0;
      }
      .entities {
        display: grid;
        gap: 12px;
      }
      .order-row {
        display: grid;
        grid-template-columns: 1fr auto auto;
        align-items: center;
        gap: 8px;
      }
      .check {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      input[type='checkbox'] {
        width: 22px;
        min-height: 22px;
      }
      details {
        padding: 12px;
        border: 1px solid var(--divider-color, #777);
        border-radius: 10px;
      }
      summary {
        cursor: pointer;
        padding: 4px;
      }
    `,
  ];
  private currentHass?: HomeAssistant;
  private config: Record<string, unknown> = {
    type: CARD_TYPE,
    version: SCHEMA_VERSION,
    entities: {},
  };
  private fireplaces: DiscoveredFireplace[] = [];
  private discoveryState: 'idle' | 'loading' | 'ready' | 'error' = 'idle';
  private discoveryGeneration = 0;
  private discoveryTimer?: ReturnType<typeof setTimeout>;
  private error = '';
  set hass(value: HomeAssistant) {
    this.currentHass = value;
    if (this.discoveryState === 'idle') void this.refreshDiscovery();
    this.requestUpdate();
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.discoveryGeneration++;
    clearTimeout(this.discoveryTimer);
    this.discoveryTimer = undefined;
    this.discoveryState = 'idle';
  }
  private async refreshDiscovery(): Promise<void> {
    if (!this.currentHass || this.discoveryState === 'loading') return;
    const generation = ++this.discoveryGeneration;
    this.discoveryState = 'loading';
    this.requestUpdate();
    try {
      let timer: ReturnType<typeof setTimeout> | undefined;
      const devices = await Promise.race([
        discover(this.currentHass),
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => reject(new Error('Discovery timeout')), DISCOVERY_TIMEOUT_MS);
          this.discoveryTimer = timer;
        }),
      ]).finally(() => clearTimeout(timer));
      if (generation !== this.discoveryGeneration) return;
      this.fireplaces = devices;
      this.discoveryState = 'ready';
    } catch {
      if (generation === this.discoveryGeneration) this.discoveryState = 'error';
    } finally {
      if (generation === this.discoveryGeneration) {
        this.discoveryTimer = undefined;
        this.requestUpdate();
      }
    }
  }
  setConfig(value: unknown): void {
    if (value && typeof value === 'object' && !Array.isArray(value))
      this.config = structuredClone(value as Record<string, unknown>);
    this.requestUpdate();
  }
  private t(key: TranslationKey): string {
    return translate(this.currentHass?.locale?.language ?? this.currentHass?.language ?? 'en', key);
  }
  private bindings(): CardConfig['entities'] {
    return (this.config.entities as CardConfig['entities']) ?? {};
  }
  private emit(): void {
    try {
      const config = parseConfig(this.config);
      this.error = '';
      this.dispatchEvent(
        new CustomEvent('config-changed', { detail: { config }, bubbles: true, composed: true }),
      );
    } catch (error) {
      this.error = error instanceof ConfigurationError ? error.field : 'configuration';
    }
    this.requestUpdate();
  }
  private entity(role: EntityRole, event: Event): void {
    const value = (event.currentTarget as HTMLSelectElement).value;
    const entities = { ...this.bindings() };
    if (value) entities[role] = value;
    else delete entities[role];
    this.config = { ...this.config, entities };
    this.emit();
  }
  private selectDevice(event: Event): void {
    const device = this.fireplaces.find(
      (entry) => entry.id === (event.currentTarget as HTMLSelectElement).value,
    );
    if (!device) return;
    const ambient = this.bindings().ambient;
    this.config = {
      ...this.config,
      entities: { ...device.entities, ...(ambient ? { ambient } : {}) },
    };
    this.emit();
  }
  private options(role: EntityRole): string[] {
    return Object.keys(this.currentHass?.states ?? {})
      .filter((entity) => {
        if (!entity.startsWith(ENTITY_CONTRACTS[role].domain + '.')) return false;
        return (
          role !== 'ambient' ||
          this.currentHass?.states[entity]?.attributes.device_class === 'temperature'
        );
      })
      .sort((left, right) => left.localeCompare(right, 'en'));
  }
  private controlOrder(): DetailControl[] {
    try {
      return parseControlOrder(this.config.control_order);
    } catch {
      return [...DETAIL_CONTROLS];
    }
  }
  private moveControl(index: number, direction: -1 | 1): void {
    const order = this.controlOrder();
    const next = index + direction;
    if (next < 0 || next >= order.length) return;
    [order[index], order[next]] = [order[next]!, order[index]!];
    this.config = { ...this.config, control_order: order };
    this.emit();
  }
  private orderControls() {
    const order = this.controlOrder();
    return html`<fieldset class="entities">
      <legend>${this.t('control_order')}</legend>
      ${order.map(
        (kind, index) =>
          html`<div class="order-row" data-order-control=${kind}>
            <span>${this.t(kind)}</span>
            <button
              aria-label=${this.t('move_up') + ': ' + this.t(kind)}
              title=${this.t('move_up') + ': ' + this.t(kind)}
              ?disabled=${index === 0}
              @click=${() => this.moveControl(index, -1)}
            >
              ↑
            </button>
            <button
              aria-label=${this.t('move_down') + ': ' + this.t(kind)}
              title=${this.t('move_down') + ': ' + this.t(kind)}
              ?disabled=${index === order.length - 1}
              @click=${() => this.moveControl(index, 1)}
            >
              ↓
            </button>
          </div>`,
      )}
    </fieldset>`;
  }
  private backgroundControl() {
    let background: string;
    try {
      background = parseImageBackground(this.config.image_background);
    } catch {
      background = '#000000';
    }
    const transparent = background === 'transparent';
    return html`<fieldset class="entities">
      <legend>${this.t('image_background')}</legend>
      <label
        >${this.t('background_style')}<select
          aria-label=${this.t('background_style')}
          .value=${transparent ? 'none' : 'color'}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              image_background:
                (event.currentTarget as HTMLSelectElement).value === 'none'
                  ? 'transparent'
                  : '#000000',
            };
            this.emit();
          }}
        >
          <option value="none" ?selected=${transparent}>${this.t('background_none')}</option>
          <option value="color" ?selected=${!transparent}>${this.t('background_color')}</option>
        </select></label
      >
      <label
        >${this.t('background_color')}<input
          type="color"
          aria-label=${this.t('background_color')}
          .value=${transparent ? '#000000' : background}
          ?disabled=${transparent}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              image_background: (event.currentTarget as HTMLInputElement).value,
            };
            this.emit();
          }}
      /></label>
    </fieldset>`;
  }
  private compactControls() {
    const selected = Array.isArray(this.config.compact_controls)
      ? this.config.compact_controls
      : [];
    return html`<fieldset class="entities">
      <legend>${this.t('compact_controls')}</legend>
      ${DETAIL_CONTROLS.map(
        (kind) =>
          html`<label class="check"
            ><input
              type="checkbox"
              aria-label=${this.t('compact') + ': ' + this.t(kind)}
              .checked=${selected.includes(kind)}
              @change=${(event: Event) => {
                const enabled = (event.currentTarget as HTMLInputElement).checked;
                const controls = selected.filter((entry) => entry !== kind);
                this.config = {
                  ...this.config,
                  compact_controls: enabled ? [...controls, kind] : controls,
                };
                this.emit();
              }}
            />${this.t(kind)}</label
          >`,
      )}
    </fieldset>`;
  }
  protected render() {
    const bindings = this.bindings();
    const options = new Map(ENTITY_ROLES.map((role) => [role, this.options(role)]));
    const images = this.config.images as CardConfig['images'] | undefined;
    return html`<div class="editor">
      <p class="hint">${this.t('editor_description')}</p>
      <label
        >${this.t('discovery')}<select
          aria-label=${this.t('discovery')}
          @change=${(event: Event) => this.selectDevice(event)}
        >
          <option value="">${this.t('select')}</option>
          ${this.fireplaces.map((device) => html`<option value=${device.id}>${device.name}</option>`)}
        </select></label
      >
      <button
        type="button"
        ?disabled=${!this.currentHass || this.discoveryState === 'loading'}
        @click=${() => this.refreshDiscovery()}
      >
        ${this.t('refresh_discovery')}
      </button>
      ${this.discoveryState === 'error' ? html`<p class="hint" role="status">${this.t('discovery_failed')}</p>` : nothing}
      <label
        >${this.t('name')}<input
          aria-label=${this.t('name')}
          .value=${String(this.config.name ?? '')}
          @change=${(event: Event) => {
            const name = (event.currentTarget as HTMLInputElement).value.trim();
            this.config = { ...this.config };
            if (name) this.config.name = name;
            else delete this.config.name;
            this.emit();
          }}
      /></label>
      <div class="entities">
        ${ENTITY_ROLES.map(
          (role) =>
            html` <label
              >${this.t(ENTITY_CONTRACTS[role].label)}<select
                aria-label=${this.t(ENTITY_CONTRACTS[role].label)}
                .value=${bindings[role] ?? ''}
                @change=${(event: Event) => this.entity(role, event)}
              >
                <option value="">—</option>
                ${bindings[role] && !options.get(role)!.includes(bindings[role]!) ? html`<option value=${bindings[role]!} selected>${bindings[role]} (${this.t('not_available')})</option>` : nothing}
                ${options.get(role)!.map((entity) => html`<option value=${entity} ?selected=${bindings[role] === entity}>${this.currentHass?.states[entity]?.attributes.friendly_name ?? entity} (${entity})</option>`)}
              </select></label
            >`,
        )}
      </div>
      <p class="hint">${this.t('entity_hint')}</p>
      <p class="hint">${this.t('sensor_hint')}</p>
      <fieldset class="entities">
        <legend>${this.t('visibility')}</legend>
        ${VISIBILITY_OPTIONS.map(
          (key) =>
            html`<label class="check"
              ><input
                type="checkbox"
                .checked=${this.config[key] !== false}
                @change=${(event: Event) => {
                  this.config = {
                    ...this.config,
                    [key]: (event.currentTarget as HTMLInputElement).checked,
                  };
                  this.emit();
                }}
              />${this.t(key)}</label
            >`,
        )}
      </fieldset>
      <label
        >${this.t('initial_view')}<select
          aria-label=${this.t('initial_view')}
          .value=${String(this.config.initial_view ?? 'expanded')}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              initial_view: (event.currentTarget as HTMLSelectElement).value,
            };
            this.emit();
          }}
        >
          <option value="compact">${this.t('compact')}</option>
          <option value="expanded">${this.t('expanded')}</option>
        </select></label
      >
      <label class="check"
        ><input
          type="checkbox"
          .checked=${this.config.compact_image === true}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              compact_image: (event.currentTarget as HTMLInputElement).checked,
            };
            this.emit();
          }}
        />${this.t('compact_image')}</label
      >
      <label
        >${this.t('compact_style')}<select
          aria-label=${this.t('compact_style')}
          .value=${String(this.config.compact_style ?? 'standard')}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              compact_style: (event.currentTarget as HTMLSelectElement).value,
            };
            this.emit();
          }}
        >
          <option value="standard">${this.t('standard')}</option>
          <option value="chip">${this.t('chip')}</option>
        </select></label
      >
      <label
        >${this.t('chip_expansion')}<select
          aria-label=${this.t('chip_expansion')}
          .value=${String(this.config.chip_expansion ?? 'modal')}
          @change=${(event: Event) => {
            this.config = {
              ...this.config,
              chip_expansion: (event.currentTarget as HTMLSelectElement).value,
            };
            this.emit();
          }}
        >
          <option value="modal">${this.t('modal')}</option>
          <option value="inline">${this.t('inline')}</option>
        </select></label
      >
      ${this.compactControls()} ${this.orderControls()} ${this.backgroundControl()}
      <p class="hint">${this.t('power_hint')}</p>
      <details>
        <summary>${this.t('show_image')}</summary>
        <div class="entities">
          ${(['off', 'flame', 'heat', 'both'] as const).map(
            (key) =>
              html`<label
                >${this.t(`image_${key}`)}<input
                  aria-label=${this.t(`image_${key}`)}
                  placeholder=${this.t('image_path')}
                  .value=${images?.[key] ?? ''}
                  @change=${(event: Event) => {
                    const value = (event.currentTarget as HTMLInputElement).value;
                    const next = { ...images };
                    if (value) next[key] = value;
                    else delete next[key];
                    this.config = { ...this.config, images: next };
                    this.emit();
                  }}
              /></label>`,
          )}
        </div>
      </details>
      ${this.error ? html`<p role="alert" class="error">${this.t('invalid_config')}: ${this.error}</p>` : nothing}
    </div>`;
  }
}
if (!customElements.get('flame-connect-card-editor'))
  customElements.define('flame-connect-card-editor', FlameConnectCardEditor);
