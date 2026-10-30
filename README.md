# Flame Connect for Home Assistant — unofficial

[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=smarquina_Flame-Connect-HA&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=smarquina_Flame-Connect-HA)

<img src="custom_components/flame_connect/brand/icon.png" width="112" alt="Flame Connect icon">

A community integration for controlling **Flame Connect** compatible Wi-Fi electric fireplaces from Home Assistant. Each fireplace appears as a device with its own controls and sensors.

**This project is unofficial and is not affiliated with, approved by, or supported by Glen Dimplex or the fireplace manufacturers.** Product information and support for the original application are available at [flame-connect.com](https://www.flame-connect.com/).

Communication uses the Flame Connect cloud and requires Internet access and an account with access to the fireplace. Local Bluetooth and LAN control are not supported.

## Requirements and installation

- Home Assistant **2026.10.4 or later**, subject to the tested versions listed in each release.
- The built-in Marketplace on **2026.11 or later**, or HACS on **2026.10.4**. A **Wi-Fi/IoT** fireplace registered in the original app; Bluetooth-only models are not supported.
- For account linking: a computer with Chrome, Chromium, or Edge and Node.js 22.15 or later. **Home Assistant does not need a browser or Node.js**.

On **Home Assistant 2026.11 or later**, open **Settings → Marketplace → Add from link**. Enter `https://github.com/smarquina/Flame-Connect-HA`, connect GitHub when prompted, and confirm. If asked for a type, select **Integration**. Open the repository and select **Install**, following any restart instructions. The Marketplace may open configuration afterwards; you can also add **Flame Connect (unofficial)** under **Settings → Devices & services → Add integration**.

On **Home Assistant 2026.10.4**, use **HACS → Custom repositories**, add the same URL with type **Integration**, download the version, and restart before adding the integration.

See the [installation and account-linking guide](docs/installation.md), including pre-release instructions. As explained in the [official HACS documentation](https://hacs.xyz/docs/marketplace/), upgrading to 2026.11 migrates installations and custom repositories to the Marketplace; do not reinstall HACS. This migration does not establish that Flame Connect has been tested on that Home Assistant version.

This release is **beta**. Full authentication through the component still needs validation in your installation. Native login was verified in the earlier laboratory, which is not a complete integration test.

## Devices and features

Fireplace names come from your account. Their identifiers remain stable if you rename them.

| Entity | Function |
|---|---|
| Heating | Independent heating control, temperature, and target temperature |
| Fireplace power | Turn on as the app does, or put the fireplace in standby |
| Flame | Turn the decorative effect on or off independently |
| Flame brightness | High, Low, Flicker high, and Flicker low, where supported |
| Flame speed | 1–5, where supported |
| Temperature | Reading returned by the fireplace |
| Connection | Whether the last state read succeeded |
| Firmware and error bytes | Exact technical data; disabled by default |

**Turning on fireplace power activates manual mode and the available heating and flame parameters, matching the app's power button.** For decoration only, use Flame and keep Heating off. Turning Heating off does not put the entire fireplace in standby.

Manufacturer and model are shown when supplied by the API. Available functions depend on model capabilities; missing parameters are not replaced with invented values.

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

Enter your password only on the official Microsoft/B2C website. The integration stores access and refresh tokens in Home Assistant's configuration, persists rotated refresh tokens, and retains access across restarts. It does not store your password.

Tokens are renewed before expiry or after an access token is rejected. If renewal is no longer valid, Home Assistant requests **reauthentication**. Link the same account to preserve devices and entities.

The integration adds no custom actions, conditions, or triggers: use standard Home Assistant entity actions and state changes.

## Help and technical documentation

- [Installation and account linking](docs/installation.md).
- [Operation, authentication, and API](docs/technical.md).
- [Troubleshooting and diagnostics](docs/troubleshooting.md).
- [Device API OpenAPI contract](docs/openapi.json) and [Azure B2C contract](docs/b2c.openapi.json).
- [Compatibility and limitations](docs/compatibility.md).

## Removing the integration

Remove the configuration entry under **Settings → Devices & services**, then uninstall the repository from the Marketplace or HACS if no longer needed. Restart when prompted. This removes the integration's local configuration; it does not delete your account or remove the fireplace from the original app.

## Branding and license

The icon belongs to the Flame Connect application and was supplied by the user for identification. Trademarks and artwork belong to their respective owners and are not covered by the MIT license for this project's original code. Their use does not imply manufacturer affiliation or endorsement.
