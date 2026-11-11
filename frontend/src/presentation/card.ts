import { LitElement, html, nothing } from 'lit';
import { styleMap } from 'lit/directives/style-map.js';
import scene from '../assets/fireplaces.png?inline';
import { parseConfig } from '../configuration/config';
import {
  CARD_TYPE,
  ControlError,
  type CardConfig,
  type Command,
  type FireplaceState,
  type EntityRole,
  type DetailControl,
  type VisibilityOption,
  type ErrorCode,
} from '../domain/model';
import { visualState, visibleModes } from '../domain/state';
import { mapState } from '../adapters/home-assistant/state-mapper';
import type { HomeAssistant } from '../adapters/home-assistant/types';
import { localize, numberText, translate, type TranslationKey } from '../localization/localize';
import { composeController } from '../composition';
import type { FireplaceController } from '../application/controller';
import { visibleControl } from '../domain/controls';
import { cardStyles } from './card-styles';
import { sharedStyles } from './styles';
import { icon } from './icons';
import { renderSlider } from './slider';
import { effectPresentation } from './effect-state';
import { renderChip, chipStyles } from './chip';
import './editor';
const CHIP_EFFECT_ICONS = {
  flame: 'mdi:fire',
  heating: 'mdi:radiator',
  ventilation: 'mdi:fan',
} as const;
const EXPANDED_ROWS = 8;
const COMPACT_BASE_ROWS = 3;
const CHIP_ROWS = 2;
const DETAIL_ROWS = 2;
const THUMBNAIL_ROWS = 2;
const DEFAULT_SCENE_IMAGE = 'url(' + JSON.stringify(scene) + ')';

export class FlameConnectCard extends LitElement {
  static readonly properties = { preview: { type: Boolean } };
  static readonly styles = [sharedStyles, cardStyles, chipStyles];
  preview = false;
  private config?: CardConfig;
  private currentHass?: HomeAssistant;
  private mappedState?: FireplaceState;
  private controller?: FireplaceController;
  private error: ErrorCode | '' = '';
  private generation = 0;
  private expanded = true;
  private modalOpen = false;

  set hass(value: HomeAssistant) {
    this.currentHass = value;
    this.mappedState = this.config ? mapState(this.config, value) : undefined;
    if (this.mappedState) this.controller?.update(this.mappedState);
    this.requestUpdate();
  }
  setConfig(value: unknown): void {
    const config = parseConfig(value);
    this.closeModal();
    this.generation++;
    this.controller?.dispose();
    this.config = config;
    this.mappedState = this.currentHass ? mapState(config, this.currentHass) : undefined;
    this.expanded = config.initial_view === 'expanded';
    this.error = '';
    this.controller = composeController(
      () => this.currentHass,
      config.entities,
      () => this.requestUpdate(),
    );
    this.requestUpdate();
  }
  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.closeModal();
    this.generation++;
    this.controller?.dispose();
  }
  getCardSize(): number {
    if (this.modalOpen) return CHIP_ROWS;
    if (this.expanded) return EXPANDED_ROWS;
    const config = this.config!;
    if (config.compact_style === 'chip') return CHIP_ROWS;
    const details = config.compact_controls.filter((kind) => visibleControl(config, kind)).length;
    const thumbnail = config.compact_image && config.show_image ? THUMBNAIL_ROWS : 0;
    return COMPACT_BASE_ROWS + details * DETAIL_ROWS + thumbnail;
  }
  getGridOptions() {
    return { columns: 12, rows: 'auto', min_columns: 6 };
  }
  static getConfigElement(): HTMLElement {
    return document.createElement('flame-connect-card-editor');
  }
  static getStubConfig() {
    return { type: CARD_TYPE, entities: {} };
  }
  private get language(): string {
    return this.currentHass?.locale?.language ?? this.currentHass?.language ?? 'en';
  }
  private t(key: TranslationKey): string {
    return translate(this.language, key);
  }
  private get disabled(): boolean {
    return this.preview || this.controller?.busy === true;
  }
  private async run(command: Command): Promise<void> {
    if (!this.isConnected || this.disabled || !this.config || !this.currentHass || !this.controller)
      return;
    const generation = this.generation;
    this.error = '';
    try {
      await this.controller.execute(mapState(this.config, this.currentHass), command);
    } catch (error) {
      if (generation === this.generation)
        this.error = error instanceof ControlError ? error.code : 'failed';
    }
    this.requestUpdate();
  }
  private choose(
    kind: 'mode' | 'color' | 'brightness',
    event: Event,
    confirmed: string | null,
  ): void {
    const input = event.currentTarget as HTMLSelectElement;
    const value = input.value;
    void this.run({ kind, value });
    // The displayed selection follows confirmed state, not native optimistic selection.
    input.value = confirmed ?? '';
  }
  private snapshot(): FireplaceState | undefined {
    return this.mappedState;
  }
  private selectControl(state: FireplaceState, kind: 'mode' | 'color' | 'brightness') {
    const options = kind === 'mode' ? visibleModes(state) : state[kind].options;
    const current = kind === 'mode' ? state.mode : state[kind].value;
    const enabled = kind === 'mode' ? state.climateAvailable : state[kind].available;
    const placeholder = current ? localize(this.language, current) : this.t('select');
    return html`<label class="control-label" title=${this.t(kind)}
      >${icon(kind)}<span class="sr-only">${this.t(kind)}</span
      ><select
        aria-label=${this.t(kind)}
        .value=${current ?? ''}
        ?disabled=${this.disabled || !enabled}
        @change=${(event: Event) => this.choose(kind, event, current)}
      >
        ${!current || !options.includes(current) ? html`<option value=${current ?? ''}>${placeholder}</option>` : nothing}
        ${options.map((option) => html`<option value=${option} ?selected=${current === option}>${localize(this.language, option)}</option>`)}
      </select></label
    >`;
  }
  private status(state: FireplaceState): TranslationKey {
    if (state.power === false) return 'standby_label';
    const visual = visualState(state);
    if (visual === 'unknown') return 'state_unknown';
    if (state.heating && state.mode === 'fan_only') return 'fan_active';
    return `state_${visual}`;
  }
  private image(state: FireplaceState, config: CardConfig) {
    if (!config.show_image) return nothing;
    const visual = visualState(state);
    const customImage = visual !== 'unknown' ? config.images[visual] : undefined;
    const positions = {
      off: '0% 0%',
      flame: '100% 0%',
      heat: '0% 100%',
      both: '100% 100%',
      unknown: '0% 0%',
    };
    const label = this.t(this.status(state)) + '. ' + this.t('image_hint');
    const image = customImage ? 'url(' + JSON.stringify(customImage) + ')' : DEFAULT_SCENE_IMAGE;
    const unknown = visual === 'unknown';
    return html`<div
      class="scene ${unknown ? 'unknown' : ''}"
      role="img"
      aria-label=${label}
      style=${styleMap({ backgroundColor: config.image_background, backgroundImage: image, backgroundSize: customImage ? 'contain' : '200% 200%', backgroundPosition: customImage ? 'center' : positions[visual] })}
    >
      ${unknown ? icon('unavailable') : nothing}
    </div>`;
  }
  private toggle(state: FireplaceState, kind: 'flame' | 'heating', chip = false) {
    const effect = effectPresentation(state, kind);
    const { value } = effect;
    const chipIcon = value === null ? 'mdi:alert-circle-outline' : CHIP_EFFECT_ICONS[effect.label];
    const glyph = chip ? html`<ha-icon icon=${chipIcon}></ha-icon>` : icon(effect.icon);
    const unavailable = value === null;
    const text = this.t(effect.label) + ' · ' + this.t(effect.status);
    const standby = kind === 'flame' && state.power === false && !value;
    return html`<button
      data-action=${kind}
      aria-label=${text}
      title=${text}
      aria-pressed=${String(value === true)}
      ?disabled=${this.disabled || unavailable || standby || (kind === 'heating' && !state.climateAvailable)}
      @click=${() => this.run({ kind, value: !value })}
    >
      ${glyph}
    </button>`;
  }
  private targetControl(state: FireplaceState) {
    return this.sliderControl(
      'target',
      state.target?.value ?? null,
      state.target?.minimum ?? null,
      state.target?.maximum ?? null,
      state.target?.step ?? null,
      state.target?.unit ?? '',
    );
  }
  private speedControl(state: FireplaceState) {
    return this.sliderControl(
      'speed',
      state.speed?.value ?? null,
      state.speed?.minimum ?? null,
      state.speed?.maximum ?? null,
      state.speed?.step ?? null,
      '',
    );
  }
  private sliderControl(
    kind: 'target' | 'speed',
    confirmed: number | null,
    lower: number | null,
    upper: number | null,
    step: number | null,
    unit: string,
  ) {
    return renderSlider({
      kind,
      confirmed,
      lower,
      upper,
      step,
      unit,
      language: this.language,
      label: translate(this.language, kind),
      disabled: this.disabled,
      commit: (value) => {
        void this.run({ kind: kind === 'target' ? 'temperature' : 'speed', value });
      },
    });
  }
  private ambientControl(state: FireplaceState) {
    let reading = '—';
    if (state.ambient) {
      const language = this.language;
      reading = numberText(language, state.ambient.value) + ' ' + state.ambient.unit;
    }
    return html`<div>
      <div class="reading-label" title=${this.t('ambient')}>
        ${icon('ambient')}<span class="sr-only">${this.t('ambient')}</span>
      </div>
      <div class="reading">${reading}</div>
    </div>`;
  }
  private powerControl(state: FireplaceState, config: CardConfig) {
    if (!config.show_power || !config.entities.power) return nothing;
    return html`<button
      data-action="power"
      aria-label=${this.t(state.power ? 'power_off' : 'power_on')}
      aria-pressed=${String(state.power === true)}
      title=${this.t(state.power ? 'power_off' : 'power_on')}
      ?disabled=${this.disabled || state.power === null}
      @click=${() => this.run({ kind: 'power', value: !state.power })}
    >
      ${icon(state.power ? 'power_off' : 'power_on')}
    </button>`;
  }
  private isVisible(config: CardConfig, option: VisibilityOption, role: EntityRole): boolean {
    return config[option] && Boolean(config.entities[role]);
  }
  private detailControl(state: FireplaceState, config: CardConfig, kind: DetailControl) {
    if (!visibleControl(config, kind)) return nothing;
    const renderers = {
      ambient: () => this.ambientControl(state),
      target: () => this.targetControl(state),
      mode: () => this.selectControl(state, 'mode'),
      color: () => this.selectControl(state, 'color'),
      brightness: () => this.selectControl(state, 'brightness'),
      speed: () => this.speedControl(state),
    };
    return html`<div data-control=${kind}>${renderers[kind]()}</div>`;
  }
  private statusIcons(state: FireplaceState, config: CardConfig) {
    return html`<div class="status-icons" role="group" aria-label=${this.t('effect_status')}>
      ${(['flame', 'heating'] as const).map((kind) => {
        const role = kind === 'flame' ? 'flame' : 'climate';
        if (!config.entities[role]) return nothing;
        const effect = effectPresentation(state, kind);
        const text = this.t(effect.label) + ' · ' + this.t(effect.status);
        return html`<span
          role="status"
          data-status=${kind}
          data-state=${effect.state}
          aria-label=${text}
          title=${text}
          >${icon(effect.icon)}</span
        >`;
      })}
    </div>`;
  }
  private async changeView(): Promise<void> {
    if (this.modalOpen) {
      this.closeModal();
      return;
    }
    if (
      !this.expanded &&
      this.config!.compact_style === 'chip' &&
      this.config!.chip_expansion === 'modal'
    ) {
      this.modalOpen = true;
      this.expanded = true;
      this.requestUpdate();
      await this.updateComplete;
      if (this.modalOpen) this.renderRoot.querySelector<HTMLDialogElement>('dialog')!.showModal();
      return;
    }
    this.expanded = !this.expanded;
    this.requestUpdate();
    if (this.config!.compact_style === 'chip') {
      await this.updateComplete;
      this.renderRoot
        .querySelector<HTMLButtonElement>(this.expanded ? '.view-toggle' : '.chip-summary')!
        .focus();
    }
  }
  private closeModal(): void {
    if (!this.modalOpen) return;
    this.modalOpen = false;
    this.expanded = false;
    this.renderRoot.querySelector<HTMLDialogElement>('dialog')!.close();
    this.renderRoot.querySelector<HTMLButtonElement>('.chip-summary')!.focus();
    this.requestUpdate();
  }
  private backdrop(event: MouseEvent): void {
    const dialog = event.currentTarget as HTMLDialogElement;
    const rect = dialog.getBoundingClientRect();
    if (
      event.target === dialog &&
      (event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom)
    )
      this.closeModal();
  }
  private settings(state: FireplaceState, config: CardConfig) {
    const controls = config.control_order.filter(
      (kind) => this.expanded || config.compact_controls.includes(kind),
    );
    if (!controls.length) return nothing;
    return html`<div id="settings" class="settings">
      ${controls.map((kind) => this.detailControl(state, config, kind))}
    </div>`;
  }
  private feedback() {
    if (this.controller?.busy)
      return html`<div class="feedback" role="status" title=${this.t('pending')}>
        ${icon('pending')}<span class="sr-only">${this.t('pending')}</span>
      </div>`;
    if (this.error)
      return html`<div class="feedback error" role="alert" title=${this.t(this.error)}>
        ${icon('unavailable')}<span class="sr-only">${this.t(this.error)}</span>
      </div>`;
    return nothing;
  }
  private chip(state: FireplaceState, config: CardConfig) {
    const name = state.name === 'Fireplace' ? this.t('title') : state.name;
    const actions = html`<div class="toggles" role="group" aria-label=${this.t('controls')}>
      ${this.isVisible(config, 'show_flame', 'flame') ? this.toggle(state, 'flame', true) : nothing}
      ${this.isVisible(config, 'show_heating', 'climate') ? this.toggle(state, 'heating', true) : nothing}
    </div>`;
    return html`<ha-card data-view="chip" aria-label=${name}>
      ${renderChip(state, name, this.t(this.status(state)), this.t('expand'), () => this.changeView(), actions, config.chip_expansion === 'modal')}
      <div class="chip-feedback">${this.feedback()}</div>
    </ha-card>`;
  }
  protected render() {
    const state = this.snapshot();
    const config = this.config;
    if (!state || !config) return nothing;
    if (config.compact_style === 'chip' && (!this.expanded || this.modalOpen))
      return html` ${this.chip(state, config)}
        <dialog
          aria-label=${this.t('details')}
          @cancel=${(event: Event) => {
            event.preventDefault();
            this.closeModal();
          }}
          @click=${(event: MouseEvent) => this.backdrop(event)}
        >
          ${this.modalOpen ? this.details(state, config) : nothing}
        </dialog>`;
    return this.details(state, config);
  }
  private details(state: FireplaceState, config: CardConfig) {
    const layoutAction = this.expanded ? 'collapse' : 'expand';
    const viewAction = this.modalOpen ? 'close' : layoutAction;
    return html`<ha-card
      aria-label=${state.name}
      data-view=${this.expanded ? 'expanded' : 'compact'}
    >
      <header>
        <div>
          <h2>${state.name === 'Fireplace' ? this.t('title') : state.name}</h2>
          <p class="sr-only" role="status">${this.t(this.status(state))}</p>
          ${this.statusIcons(state, config)}
        </div>
        <button
          class="view-toggle"
          type="button"
          aria-label=${this.t(viewAction)}
          title=${this.t(viewAction)}
          aria-expanded=${String(this.expanded)}
          aria-controls="card-body"
          @click=${() => this.changeView()}
        >
          ${icon(viewAction)}
        </button>
      </header>
      ${this.expanded || config.compact_image ? this.image(state, config) : nothing}
      <div class="body" id="card-body">
        <div class="toggles" role="group" aria-label=${this.t('controls')}>
          ${this.powerControl(state, config)}${this.isVisible(config, 'show_flame', 'flame') ? this.toggle(state, 'flame') : nothing}${this.isVisible(config, 'show_heating', 'climate') ? this.toggle(state, 'heating') : nothing}
        </div>
        ${this.settings(state, config)} ${this.feedback()}
      </div>
    </ha-card>`;
  }
}
