# Flame Connect for Home Assistant — unofficial

[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=smarquina_Flame-Connect-HA&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=smarquina_Flame-Connect-HA)

<img src="custom_components/flame_connect/brand/icon.png" width="112" alt="Flame Connect icon">

A community integration for controlling **Flame Connect** compatible Wi-Fi electric fireplaces from Home Assistant. Each fireplace appears as a device with its own controls and sensors.

**This project is unofficial and is not affiliated with, approved by, or supported by Glen Dimplex or the fireplace manufacturers.** Product information and support for the original application are available at [flame-connect.com](https://www.flame-connect.com/).

Communication uses the Flame Connect cloud and requires Internet access and an account with access to the fireplace. Local Bluetooth and LAN control are not supported.

## Requirements and installation

**1. Add the repository and install a published version.** On Home Assistant **2026.11 or later**, open it in the Marketplace:

[![Open Flame Connect in your Home Assistant Marketplace](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=smarquina&repository=Flame-Connect-HA&category=integration)

For an existing HACS installation, use the legacy repository shortcut or the manual instructions below:

[![Open Flame Connect in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=smarquina&repository=Flame-Connect-HA&category=integration)

**2. Restart Home Assistant when prompted, then add the integration:**

[![Add the Flame Connect integration to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=flame_connect)

These buttons open your own Home Assistant through [My Home Assistant](https://my.home-assistant.io/). Choose your instance if asked. The repository button opens its installation page; it does not install files automatically. The integration button requires the component to be installed and loaded first. If a shortcut is unavailable on your version, follow the manual steps below.

- Home Assistant **2026.10.4 or later**, subject to the tested versions listed in each release.
- The built-in Marketplace on **2026.11 or later**, or HACS on **2026.10.4**. A **Wi-Fi/IoT** fireplace registered in the original app; Bluetooth-only models are not supported.
- Email/password accounts can link directly in Home Assistant. Browser linking remains available for phone sign-in, external providers, additional verification, or sign-in failures; that alternative requires a computer with Chrome, Chromium, or Edge and Node.js 22.15 or later. **Home Assistant does not need a browser or Node.js**.

On **Home Assistant 2026.11 or later**, open **Settings → Marketplace → Add from link**. Enter `https://github.com/smarquina/Flame-Connect-HA`, connect GitHub when prompted, and confirm. If asked for a type, select **Integration**. Open the repository and select **Install**, following any restart instructions. The Marketplace may open configuration afterwards; you can also add **Flame Connect (unofficial)** under **Settings → Devices & services → Add integration**.

On **Home Assistant 2026.10.4**, use **HACS → Custom repositories**, add the same URL with type **Integration**, download the version, and restart before adding the integration.

See the [installation and account-linking guide](docs/installation.md), including pre-release instructions. As explained in the [official HACS documentation](https://hacs.xyz/docs/marketplace/), upgrading to 2026.11 migrates installations and custom repositories to the Marketplace; do not reinstall HACS. This migration does not establish that Flame Connect has been tested on that Home Assistant version.

This project is **beta**. This README describes the code in the branch you are viewing; a published release may contain fewer features. Check the [release notes](https://github.com/smarquina/Flame-Connect-HA/releases) before installing. A draft PR is not an installable release. Direct sign-in and the new heating modes still need validation with your account and fireplace; see [compatibility and validation](docs/compatibility.md).

For manual installation without a store, follow the [manual installation instructions](docs/installation.md#manual-installation).

## Account setup and options

After adding **Flame Connect (unofficial)**, choose **Email and password** for an email account or **Browser with desktop assistant** for phone sign-in, external providers, or additional verification. Select the same account type used in the original app. On the direct sign-in form you can switch to browser linking without entering credentials. Select at least one Wi-Fi fireplace and finish setup.

The [setup field reference](docs/installation.md#configuration-parameters) explains every field and where to obtain its value. After setup, open **Settings → Devices & services → Flame Connect (unofficial) → Configure** to change:

| Option | Default | Effect |
|---|---|---|
| Preferred temperature unit: auto / C / F | Automatic | Follows the fireplace display preference or selects Celsius/Fahrenheit for native values; Home Assistant applies its display conversions. Does not change the physical scale. |
| Create experimental controls | Off | Creates supported color, countdown, sound, and physical-scale controls disabled by default. Enable each entity separately to test it. |

Changing options reloads the integration and sends no device commands. Use the entry menu's **Reconfigure** action to change the selected fireplaces. Reauthentication links the same account while retaining device identifiers and selection.

## Devices and features

Fireplace names come from your account. Their identifiers remain stable if you rename them.

| Entity | Function |
|---|---|
| Heating | Thermostat with heating on/off and an adjustable target temperature |
| Target temperature | Editable heating setpoint, shared with the Heating thermostat |
| Heating presets | Normal; Eco, Boost, Fan only, and Existing weekly schedule when declared by the model |
| Heating boost duration | 1–20 minutes, where PowerBoost is supported |
| Fireplace power | Turn on as the app does, or put the fireplace in standby |
| Flame | Turn the decorative effect on or off independently |
| Flame brightness | High, Low, Flicker high, and Flicker low, where supported |
| Flame speed | 1–5, where supported |
| Reported temperature | Read-only temperature field returned by the fireplace API |
| Connection | Whether the last state read succeeded |
| Firmware and error bytes | Exact technical data; disabled by default |

See the [control guide](docs/controls.md) for entity types, heating presets, Boost, experimental controls, and stable automation values. Each fireplace is a separate device; functions are created according to its declared capabilities.

**Turning on fireplace power activates manual mode and the available heating and flame parameters, matching the app's power button.** For decoration only, use Flame and keep Heating off. Turning Heating off does not put the entire fireplace in standby.

Use **Target temperature** to change the heating setpoint directly from the device page, or adjust it in **Heating**. Both show the same confirmed setpoint. Changing the target alone does not turn on heating or fireplace power. **Reported temperature** is a separate, read-only value; its correspondence to an independent room-temperature measurement still needs physical validation.

Manufacturer and model are shown when supplied by the API. Available functions depend on model capabilities; missing parameters are not replaced with invented values.

### Heating presets and Boost

Select a preset in **Heating**. Eco requires `AdvancedHeat`, Boost requires `PowerBoost`, Fan only requires `FanOnly`, and Existing weekly schedule requires `SevenDayTimer`. The schedule preset activates a schedule already configured in the original app; it does not create or edit that schedule.

Set **Heating boost duration** before selecting Boost. Both actions preserve heating status, fireplace power, flame, and target temperature. If heating is off, turn it on separately. To cancel Boost, select Normal. A duration can also be changed during Boost; this may restart its period on the device. Selecting Boost uses the reported duration when it is 1–20 minutes, otherwise an explicit default of 15 minutes. There is no countdown or remaining-time sensor yet. These additional modes still require physical validation on each model.

### Experimental controls

Enable **Create experimental controls** in the integration options to create these entities. They start disabled; enable each entity you want to test:

- Flame color presets from the model's palette.
- Countdown activation and duration.
- Sound volume and sound file.
- Device temperature scale.

These writes still require physical validation. The sound range 0–255 is the byte's capacity, **not a guarantee of supported volume levels**. Sound controls are not created unless the model declares that capability.

## Language

The integration provides **English and Spanish** for setup, options, entity names, selectable values, and errors. Home Assistant chooses interface translations from the user's profile language; no integration language setting is required. Backend-generated entity names follow Home Assistant's configured system language. Custom names and fireplace names from your account are preserved.

Change your interface language in your Home Assistant profile. Automation states remain stable language-independent keys; translated labels are for display. Documentation and the desktop linking assistant use English.

## Celsius and Fahrenheit

The API transmits temperatures and target temperatures in **Celsius**, even when the fireplace displays Fahrenheit. The integration converts values once at the presentation boundary.

**Preferred temperature unit** accepts `auto`, `C`, or `F`. Automatic follows the device's display preference, falling back to Celsius when missing. This option does not write to the fireplace.

Climate cards respect Home Assistant's unit system. Choosing Fahrenheit in the integration does not override the global unit system for a climate card. Changing the physical display scale is a separate experimental control.

Target limits follow the app: minimum 15 °C; maximum 30.6 °C for recognized Optiflame/OLF families, or 32.9 °C otherwise. Limits are converted where needed and may require adjustment for other models.

## Updates and availability

- One shared state read per fireplace every 30 seconds while entities are listening.
- A fresh read before each command and another afterwards to confirm the state.
- Inventory and capabilities are refreshed when the integration loads or reloads. Use **Reconfigure** to select additional fireplaces.
- An offline fireplace does not interrupt the others. Its controls become unavailable and Connection reports the failed read.
- An unconfirmed command raises an error and is not retried automatically. Read the state before trying again.

Changing options reloads the integration without restarting Home Assistant. For file updates, use **Settings → Updates** in the Marketplace and restart Home Assistant to apply the update; with HACS, follow its restart instructions.

## Authentication and renewal

Choose **Email and password** for direct sign-in from Home Assistant. Credentials are sent only to the official Microsoft/B2C service over HTTPS using an isolated cookie session, and are not saved. Browser linking lets you enter credentials on the official hosted page instead and remains necessary for phone sign-in, external providers, or additional verification. The integration stores access and refresh tokens in Home Assistant's configuration, persists rotated refresh tokens, and retains access across restarts. It does not store your password.

Tokens are renewed before expiry or after an access token is rejected. If renewal is no longer valid, Home Assistant requests **reauthentication**. Link the same account to preserve devices and entities.

The integration adds no custom actions, conditions, or triggers: use standard Home Assistant entity actions and state changes.

## Quality and support

The integration is checked against the applicable **Bronze and Silver technical criteria** of the [Home Assistant Integration Quality Scale](https://contributors.home-assistant.io/core/quality-scale/rules/). The [technical compliance reference](docs/technical.md#bronze-and-silver-criteria) maps every criterion to its implementation or documented exemption. Branding is supplied locally for this custom integration; this is not publication in Home Assistant Core or its central brands repository.

Configuration uses the UI, validates account access, prevents duplicates, and supports same-account reauthentication and unloading. Devices recover independently after failures, commands raise translated errors, and updates are serialized per fireplace. CI enforces more than 95% statement coverage in every integration module and 100% configuration-flow line/branch coverage. HACS validation, Hassfest, and the SonarCloud Quality Gate run on pull requests; the badge above links to the main project's quality status.

These checks do **not** constitute official Bronze/Silver certification or prove every function on every fireplace. The manifest remains `quality_scale: custom`. [Physical validation and limitations](docs/compatibility.md) are listed separately. The maintainer is [@smarquina](https://github.com/smarquina); report problems through the [issue tracker](https://github.com/smarquina/Flame-Connect-HA/issues) with reviewed diagnostics and version/model details, following the [troubleshooting guide](docs/troubleshooting.md). Do not include credentials, tokens, native callback URLs, or unreviewed HAR files.

## Help and technical documentation

- [Installation and account linking](docs/installation.md).
- [Controls, heating presets, and Boost](docs/controls.md).
- [Operation, authentication, and API](docs/technical.md).
- [Troubleshooting and diagnostics](docs/troubleshooting.md).
- [Device API OpenAPI contract](docs/openapi.json) and [Azure B2C contract](docs/b2c.openapi.json).
- [Compatibility and limitations](docs/compatibility.md).

## Removing the integration

Remove the configuration entry under **Settings → Devices & services**, then uninstall the repository from the Marketplace or HACS if no longer needed. Restart when prompted. This removes the integration's local configuration; it does not delete your account or remove the fireplace from the original app.

## Branding and license

The icon belongs to the Flame Connect application and was supplied by the user for identification. Trademarks and artwork belong to their respective owners and are not covered by the MIT license for this project's original code. Their use does not imply manufacturer affiliation or endorsement.
