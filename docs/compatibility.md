# Compatibility and limitations

This project is unofficial. [Flame Connect](https://www.flame-connect.com/) describes the original app and its commercial compatibility; those capabilities do not guarantee support in this integration.

## Scope

Only Wi-Fi/IoT fireplaces returned by the account are supported. There is no local BLE control, LAN discovery, or offline operation.

Model names and capabilities come from the API. Universal support for every fireplace from a manufacturer is not claimed. Initial reference family: Optiflame/OLF; this integration still requires validation on the actual device.

## Functional validation

| Function | Current evidence |
|---|---|
| Official login and JWT retrieval | User-validated in the earlier laboratory |
| Inventory and state | User-validated in the earlier laboratory |
| Power/standby, heating, and flame | User-validated in the earlier laboratory |
| Token renewal and errors | Automated tests with a simulated provider |
| Direct email/password sign-in | Synthetic B2C responses and configuration-flow tests; real-account validation pending |
| Heating presets and Boost duration | Original app protocol and automated tests; physical validation pending |
| Complete Home Assistant integration | Pending user validation |
| English and Spanish resources | Checked with Home Assistant's translation loader and entity setup |
| Flame color | Pending physical validation; experimental |
| Countdown | Pending physical validation; experimental |
| Sound | Pending; may be unavailable or unsuitable on some models |
| Device display scale | Pending physical validation; experimental |

Laboratory tests are not presented as physical validation of the complete integration. Automated tests do not operate real fireplaces.

## Functions not exposed

Guests, ownership transfer, editing weekly schedules, favorites, firmware updates, and factory reset. Activating an existing weekly heating schedule is supported only when the device declares `SevenDayTimer`. Firmware/error bytes are read-only technical data and do not imply update support or interpreted diagnostics.

The quality scale is a technical target, not official Home Assistant, Marketplace, or HACS certification. This custom integration does not claim official Silver certification.
