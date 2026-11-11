# Technical reference

## Runtime

`flame-connect-card.js` is an ES2022 module registering `flame-connect-card` and its visual editor. The card implements configuration, HA state updates, card sizing and sections-grid sizing. It uses Lit with Shadow DOM and HA theme variables. Its dependency on Flame Connect HA is through entity contracts; no Python code or cloud SDK is bundled.

## Boundaries

- `domain`: immutable state types, availability-aware commands, visual-state selection and temperature conversion. No browser or HA imports.
- `application`: command validation and confirmation lifecycle, depending on an action port.
- `adapters/home-assistant`: registry discovery, state mapping and exact service calls targeting entity IDs.
- `presentation`: Lit card, visual editor, styles and localization.
- `composition`: constructs the application controller and HA action adapter.

The architecture check parses TypeScript syntax and checks resolved relative dependency boundaries for imports, re-exports, import types, dynamic imports and CommonJS calls. Nonliteral module loads are rejected in the core; comments and string content do not count as imports or browser access. Coverage checks require 100% of lines, statements, branches and functions across the TypeScript source and validation scripts, without coverage-ignore annotations. Browser tests separately verify the complete rendered interface and visual editor. SonarQube consumes the LCOV report.

Home Assistant entity domains, discovery suffixes and editor labels share one boundary contract. Detail-control bindings share a domain-level registry for visibility and layout decisions. Card styles, reusable sliders and effect-state presentation are isolated from view and command orchestration. The embedded default artwork URL is prepared once; entity-state mapping is reused across presentation updates and refreshed on Home Assistant notifications or reconfiguration. Commands still validate against a fresh state mapping.

## Actions and state

| Operation                  | Service                              | Data                      |
| -------------------------- | ------------------------------------ | ------------------------- |
| Whole-device on/off        | `switch.turn_on` / `switch.turn_off` | None                      |
| Flame on/off               | `light.turn_on` / `light.turn_off`   | None                      |
| Heating/ventilation on/off | `climate.set_hvac_mode`              | `hvac_mode: heat` / `off` |
| Flame speed                | `number.set_value`                   | `value`                   |
| Target                     | `climate.set_temperature`            | `temperature`             |
| Preset                     | `climate.set_preset_mode`            | `preset_mode`             |
| Color or brightness        | `select.select_option`               | `option`                  |

Every call targets the configured entity ID. The card sends no whole-device power action implicitly. Commands are serialized within each card and are never replayed automatically. An already satisfied command requires no call. Pending operations end on matching state, service failure, removal/reconfiguration or a 45-second deadline. Service acceptance alone does not settle a command. Raw provider errors are not displayed.

Incoming target temperature and speed values obey the same finite-range and step rules as outgoing commands. Invalid readings are unavailable instead of displaying a value inconsistent with a native slider. Effective effect state consistently applies confirmed standby to status icons, buttons and command confirmation; retained raw effect flags cannot confirm enabling an effect while power is off.

The backend remains responsible for its cloud read/modify/write serialization and the physical device's semantics. A configured power switch in standby takes precedence over retained effect flags in the illustration. Without that entity, effects-off is not interpreted as whole-device standby.

## Layout lifecycle

Compact and expanded presentations share one controller and one Home Assistant snapshot per render. Switching layouts updates local presentation state only. It does not reconfigure the card, dispose the controller, send a service call or replay a pending command. Expansion is instance-local rather than an entity or shared browser preference. Sections sizing uses automatic rows; masonry estimates distinguish compact and expanded views and count only mapped, globally visible compact controls, plus the optional visible thumbnail.

Chip mode opens a native HTML dialog in the browser top layer by default. It shares the controller and rendered controls with the expanded view, preserving command serialization and readback. Browser-managed modality handles background interaction and focus containment. Closing by Escape, backdrop or the close button restores focus; reconfiguration and disconnection close the dialog. Dashboard sizing remains compact while it is open. `chip_expansion: inline` selects the earlier inline behavior. The standalone card needs no external popup integration. A Mushroom summary plus Browser Mod popup can still host the existing expanded card; that dashboard composition is separate from the built-in layouts.

## Security and packaging

The card uses Home Assistant's authenticated frontend context. It neither stores nor obtains Flame Connect passwords, access tokens or refresh tokens. Entity data and names are rendered as escaped text. Configuration image overrides are same-origin paths. Default artwork is embedded in the self-contained bundle, with no CDN dependency or runtime discovery request for images.

Distribution validation checks the filename, self-contained imports, artwork presence and a 2.5 MB size ceiling. The integration package contains the compiled module under `custom_components/flame_connect/www/`. CI rebuilds it and verifies that it matches the committed file.

## Quality and compatibility

The project uses TypeScript strict checks, ESLint, formatting checks, dependency auditing, unit/contract tests, browser tests, automated accessibility checks, HACS validation and SonarQube Cloud. Applicable principles of HA's quality scale guide design; this frontend plugin does not claim an official integration-quality tier. Hassfest is a Python integration validator and does not validate this dashboard card.

Documentation and build requirements are independent of runtime HA compatibility. A successful simulated test does not prove account access, physical heat output or every model-specific color option.

Numeric target readings include their validated bounds and step, like flame speed. Target bounds and step have a single source in the target setting; unavailable targets use a disabled placeholder slider. Slider labels account for the minimum offset and fractional steps, including scientific notation. Temperature confirmation tolerance is capped below half a step. Static card and editor translation keys use the typed translation entry point; external provider options retain flexible lookup.

Discovery requests expire after 15 seconds, allowing explicit retry without accepting late responses. Heating actions require climate availability even when whole-device standby supplies the effective off state. Distribution checks parse JavaScript imports and re-exports, rejecting external module dependencies independently of their path.

Removing the editor clears its discovery deadline and invalidates pending results.

Discovery prefers the climate label over the flame label and sorts devices by name and ID, independently of registry order. Configuration errors expose a stable code and field; the editor displays its localized error heading and the affected field without raw parser details. Architecture checks resolve local symbols to distinguish browser globals from local declarations and data properties.

The optional chip presentation reuses the same controller, effect-state rules and action handlers. Its summary expansion button and effect buttons are sibling controls, avoiding nested interactive elements. Chip sizing estimates two masonry rows; detail controls and whole-device power remain in expanded view.

The optional `card_mod` configuration is retained as supplied through normalization and visual-editor updates. Styling and template evaluation are delegated to card-mod, which can target the card shadow root and its `ha-card` elements. The card does not interpret or inject the supplied CSS.

Action button backgrounds derive a translucent neutral surface from the card's `--primary-text-color` by default. Card-mod can set `--chip-background` or `--fireplace-action-background` and state-specific action variables on `ha-card` or on a button selected by `data-action`. Button rules use low-specificity selectors so normal card-mod selectors can override them. The main fireplace icon has a separate background variable and active color.
