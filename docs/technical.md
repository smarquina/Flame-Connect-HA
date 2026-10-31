# Technical operation

An unofficial integration for the Flame Connect cloud API. The complete account contract is provided in [openapi.json](openapi.json); this integration's client exposes only inventory, state, and writes to known parameters.

## Servers and headers

API: `https://mobileapi.gdhv-iot.com`. Requests send a Bearer access token, `Accept: application/json`, JSON Content-Type for writes, and the client headers recovered from the app: `app_name`, `api_version`, `app_version`, `app_device_os`, `device_version`, `device_manufacturer`, `device_model`, `lang_code`, `country`, and `logging_required_flag`.

Their presence reproduces the known client; individual headers have not all been proven mandatory. Options do not accept alternative servers or arbitrary headers. The API's client language header is independent of Home Assistant's interface translations.

## Authentication

Azure B2C public client, authorization code with PKCE S256 and `offline_access`, without a client secret. The registered return URI is native. The verifier and nonce remain in Home Assistant's in-memory transaction; the desktop assistant receives only the public authorization URL and captures the return.

Direct email/password sign-in follows the same authorization-code flow, not a password grant. A separate cookie session reads the hosted page's CSRF and transaction values, submits `request_type=RESPONSE`, `email`, and `password` to the normal policy's `SelfAsserted` endpoint, then follows `api/CombinedSigninAndSignup/confirmed` to the native return. The form sends `Origin`, `Referer`, `X-CSRF-TOKEN`, `X-Requested-With`, Accept, and form Content-Type headers. Cookie quoting is disabled to preserve B2C base64 cookie values. Cookies set by each response stay in this isolated session and are discarded on exit.

Only HTTPS destinations on the configured B2C host are followed, with no custom ports or embedded credentials. Redirects are handled manually and bounded to 20 hops per phase, response bodies to 2 MiB, requests to 30 seconds, and sign-in to 60 seconds overall. Provider bodies, credentials, cookies, and callback URLs are not logged. The captured native return is redeemed by the existing state/PKCE/token-validation path. Passwords are not persisted or retried. External identity providers and interactive challenges use the existing browser alternative.

RS256 signatures, provider public keys, issuer, and expiry are verified. ID token audience and nonce are also checked. The remote API additionally validates the access token's resource authorization. Errors and logs do not expose tokens or keys. Metadata and keys are accepted only from the known B2C host, without following redirects.

Persistent tokens are stored through ConfigEntry and survive restarts. An account-level lock coordinates renewal and persists rotated refresh tokens before using the new credentials. Temporary network errors are not treated as incorrect credentials.

## State and commands

- `GetFires`: inventory and capabilities.
- `GetFireOverview?FireId=...`: state and `WifiFireOverview.Parameters`.
- `WriteWifiParameters`: parameter packets to modify.

HTTP 200 alone is insufficient: ResultCode, IsException, and the device identifier are checked. Unrecognized results are rejected. Each fireplace shares a state snapshot and command lock across its entity platforms.

State is always read before constructing a write and again afterwards. Writes are never retried automatically, and old states are not restored at startup. Following a 401, a read may be retried once after token renewal; a write reports failure and requires manual review.

## Binary packets

`Value` is a Base64 packet: uint16 little-endian ID, uint8 length, and payload. ID, packet size, and length are validated before accessing offsets. Edits preserve the other bytes of the received packet.

| ID | Payload | Purpose |
|---|---:|---|
| 236 | 1 byte | Device Celsius/Fahrenheit preference |
| 321 | 3 | Mode and Celsius temperature |
| 322 | 20 | Flame effect, speed, brightness, and colors |
| 323 | 5 | Heating, mode, Celsius target, and boost |
| 326 | 3 | Countdown and little-endian duration |
| 327 | 9 | Firmware bytes, without unverified version interpretation |
| 329 | 4 | Error bytes, without unverified interpretation |
| 369 | 2 | Volume and sound file |

Flame color occupies absolute byte 19, payload offset 16 of parameter 322. Codes 0..6 are presets with palette labels determined by FlamePresetOptions; they are not arbitrary RGB values.

The app converts Fahrenheit targets to Celsius before writing. The integration follows the same rule; parameter 236 does not change the packet's temperature meaning. Limits come from the client UI: 15 °C to 30.6/32.9 °C depending on family, and may need adjustment for other models.

The **Target temperature** number entity and **Heating** climate entity both edit only the target in parameter 323. They share validation, unit conversion, and the per-device coordinator, so both update from the same post-command readback. A target change preserves the remaining bytes, including heating status, mode, and boost; it does not power on the fireplace. Home Assistant handles the final conversion to its configured display unit. The **Reported temperature** sensor remains read-only and uses the separate field in parameter 321.

Heating preset wire values are Normal=0, Boost=1, Eco=2, Fan only=3, Schedule=4 (parameter 323, absolute byte 4). Optional presets require the corresponding `PowerBoost`, `AdvancedHeat`, `FanOnly`, or `SevenDayTimer` capability to be explicitly true. Schedule activates the device's existing weekly program; editing its periods is not implemented. Duration edits use byte 7, in minutes, limited to 1–20, preserving status, mode and setpoint. Boost selection reuses a valid reported duration or writes a documented 15-minute default. The app's Wi-Fi picker writes durations 5, 10, 15, and 20 directly; no zero-based conversion is applied. Preset and duration writes share the same read/modify/write/read lock as temperature controls and do not implicitly turn on heating or power.

## Availability and diagnostics

Each fireplace has its own coordinator. A failure makes its controls unavailable without blocking other devices. The account is checked during setup; individual offline fireplaces can load as unavailable and recover later.

Downloadable diagnostics include model, capabilities, options, and parameter IDs. They exclude personal device names, PINs, account and device identifiers, tokens, and passwords. Logs report loss and recovery without repeating the same error on every poll.

## Language and stable values

`strings.json` is the English source; `translations/en.json` and `translations/es.json` provide complete runtime resources. Home Assistant resolves setup, options, selectors, entity labels and states, and translated exceptions using its native translation system. Interface translations follow the user's profile; backend-generated entity names follow the system language. Names supplied by the account or user are preserved.

Select entity values use lowercase keys such as `high`, `flicker_low`, and `blue`, while translated display labels depend on language. Temperature configuration values remain `auto`, `C`, and `F`; B2C policy values remain `normal` and `social`. No translated label is sent to the cloud. The desktop assistant uses English and does not read Home Assistant's language preference.

If you tested an earlier beta using display labels in automations, update select values: `Low` becomes `low`, `Flicker high` becomes `flicker_high`, `Blue` becomes `blue`, and `Celsius` becomes `celsius`. Color combinations use underscores, for example `yellow_red_blue`. Entity unique IDs and stored temperature preferences are unchanged.

## Home Assistant compatibility

The tested baseline is Home Assistant 2026.10.4 and Python 3.14. The native climate property change announced for 2026.11 is handled, but compatibility must also be verified against its released version. Each release will state the versions actually tested.

## Architecture and quality control

The domain contains device parameters and invariants without importing Home Assistant, HTTP, or JWT libraries. Account linking, renewal, and read/modify/write use cases depend on application-layer ports. Cloud adapters implement those ports; entities and coordinators are Home Assistant input adapters. Token persistence is injected through a port rather than performed by the domain.

`domain/protocol.py` is the source of wire identifiers (`ParameterId`), modes and state enums, packet sizes and offsets, field ranges, and device-control limits. Field specifications name their offset, minimum, maximum, and any display adjustment; the flame-speed zero-based encoding is explicit. Cloud timeout/response/login limits live in `adapters/cloud/const.py`, HTTP statuses use the standard `HTTPStatus` enum, and PKCE transaction/refresh bounds remain in the application layer. These names do not change JSON values, packet bytes, UI keys, or accepted ranges.

Tests enforce inward dependency direction. Automated checks require more than 95% executed statements in each integration module and full configuration-flow coverage, including branches. Coverage is exported to SonarQube Cloud for reliability, security, and maintainability analysis. A configured scanner alone is not evidence of a passing Quality Gate; the remote analysis must complete successfully.

### Bronze and Silver criteria

The tables map the current [Home Assistant quality rules](https://contributors.home-assistant.io/core/quality-scale/rules/) to this custom integration. **Implemented** means a criterion is covered by the implementation and its applicable checks; **Exempt** means the feature does not exist and the reason is stated. **Custom branding** is supplied in this repository rather than the central Core brands repository. The machine-readable checklist is [quality_scale.yaml](../custom_components/flame_connect/quality_scale.yaml).

This is a technical assessment for an unofficial custom integration, not an official tier assignment. Core publication, central branding acceptance, and official review are not claimed. The manifest deliberately keeps `quality_scale: custom`. Physical device/account validation is tracked separately in [compatibility](compatibility.md); passing automated checks does not establish it.

#### Bronze

| Rule | Assessment | Implementation / documentation |
|---|---|---|
| `action-setup` | Exempt | No custom integration actions are registered; standard entity actions are used. |
| `appropriate-polling` | Implemented | Shared 30-second coordinator per fireplace while entities listen; properties perform no network I/O. |
| `brands` | Custom branding | Local `brand/icon.png` and `brand/icon@2x.png`, matching the supplied app icon; no central Core brands publication. |
| `common-modules` | Implemented | Shared entity identity and device grouping in `entity.py`; shared state and commands in `coordinator.py`. |
| `config-flow` | Implemented | UI account sign-in, browser alternative, Wi-Fi fireplace selection, and unit preference. |
| `config-flow-test-coverage` | Implemented | Configuration-flow line and branch coverage must be 100%; sign-in errors, duplicates, selection, reauth, and reconfiguration are exercised. |
| `dependency-transparency` | Exempt | No additional runtime packages are installed; HTTP/JWT dependencies come from Home Assistant. Sources are available in this repository. |
| `docs-actions` | Exempt | No custom actions; [controls](controls.md) documents the native entity operations instead. |
| `docs-conditions` | Exempt | No integration-specific conditions; standard entity states are available. |
| `docs-high-level-description` | Implemented | README identifies the unofficial cloud integration, account requirements, and one device per fireplace. |
| `docs-installation-instructions` | Implemented | [Installation](installation.md) covers prerequisites, Marketplace/HACS, manual files, restart, and account linking. |
| `docs-removal-instructions` | Implemented | README and installation guide distinguish entry removal from uninstalling component files and preserving the manufacturer account. |
| `docs-triggers` | Exempt | No integration-specific triggers; standard state triggers are used. |
| `entity-event-setup` | Implemented | `CoordinatorEntity` handles update listeners through entity lifecycle methods. |
| `entity-unique-id` | Implemented | Stable fireplace ID plus functional key; identifiers survive renames and same-account reauthentication. |
| `has-entity-name` | Implemented | Shared base entity uses `has_entity_name`; names are translated and grouped under the device. |
| `runtime-data` | Implemented | Typed `FlameConfigEntry` stores runtime clients/coordinators in `ConfigEntry.runtime_data`. |
| `test-before-configure` | Implemented | Account inventory is successfully retrieved before the configuration entry is created. |
| `test-before-setup` | Implemented | Setup validates account access and reads device snapshots; individual offline fireplaces load unavailable and can recover. |
| `unique-config-entry` | Implemented | Verified stable account ID prevents duplicate entries. |

#### Silver

| Rule | Assessment | Implementation / documentation |
|---|---|---|
| `action-exceptions` | Implemented | Invalid values raise translated `ServiceValidationError`; failed/unconfirmed commands raise translated `HomeAssistantError`. |
| `config-entry-unloading` | Implemented | Platform unloading releases coordinator listeners and polling; options changes reload cleanly. |
| `docs-configuration-parameters` | Implemented | [Options after setup](installation.md#options-after-setup) lists every option, exact English label, accepted values, defaults, and effects. |
| `docs-installation-parameters` | Implemented | [Setup field reference](installation.md#configuration-parameters) explains every setup field, defaults, and where users obtain its value. |
| `entity-unavailable` | Implemented | Coordinator success, parameter presence, and known units determine availability; one fireplace's failure does not block others. |
| `integration-owner` | Implemented | `@smarquina` owns maintenance and is listed in the manifest; issues are linked from the README. |
| `log-when-unavailable` | Implemented | `DataUpdateCoordinator` logs failure/recovery transitions without repeating the same failure on every poll. |
| `parallel-updates` | Implemented | Every platform declares `PARALLEL_UPDATES`; a shared per-fireplace lock serializes read/modify/write/read operations. |
| `reauthentication-flow` | Implemented | Reauthentication verifies the same account, updates tokens, and preserves selected devices and identifiers. |
| `test-coverage` | Implemented | CI requires >95% statement coverage per integration module, plus full configuration-flow line/branch coverage. |

HACS repository validation, Hassfest, unit/integration tests, coverage checks, and the SonarCloud Quality Gate are separate automated checks. None grants an official Home Assistant quality tier. See the PR checks for the exact commit and the release notes for published functionality.
