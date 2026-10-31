# Technical operation

An unofficial integration for the Flame Connect cloud API. The complete account contract is provided in [openapi.json](openapi.json); this integration's client exposes only inventory, state, and writes to known parameters.

## Servers and headers

API: `https://mobileapi.gdhv-iot.com`. Requests send a Bearer access token, `Accept: application/json`, JSON Content-Type for writes, and the client headers recovered from the app: `app_name`, `api_version`, `app_version`, `app_device_os`, `device_version`, `device_manufacturer`, `device_model`, `lang_code`, `country`, and `logging_required_flag`.

Their presence reproduces the known client; individual headers have not all been proven mandatory. Options do not accept alternative servers or arbitrary headers. The API's client language header is independent of Home Assistant's interface translations.

## Authentication

Azure B2C public client, authorization code with PKCE S256 and `offline_access`, without a client secret. The registered return URI is native. The verifier and nonce remain in Home Assistant's in-memory transaction; the desktop assistant receives only the public authorization URL and captures the return.

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

Tests enforce inward dependency direction. Automated checks require more than 95% executed statements in each integration module and full configuration-flow coverage, including branches. Coverage is exported to SonarQube Cloud for reliability, security, and maintainability analysis. A configured scanner alone is not evidence of a passing Quality Gate; the remote analysis must complete successfully.
