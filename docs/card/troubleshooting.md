# Troubleshooting

| Symptom                                 | Check                                                                                                                                             |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Custom element does not exist           | Verify the installed resource URL, JavaScript-module type, browser console and frontend cache. Avoid duplicate resources.                         |
| No fireplace in discovery               | Confirm the backend is installed and its entities are enabled. If registry access is denied, choose entities manually.                            |
| Color is absent                         | Enable experimental controls in Flame Connect HA, enable the color entity and bind it in the card. The model must support a palette.              |
| Temperature unavailable                 | Verify the external sensor has `device_class: temperature`, a finite value and °C/°F units. Target and room temperature are separate.             |
| Flame-on disabled in standby            | The card will not silently activate whole-device power, which can enable heating too. Start the fireplace explicitly and then choose its effects. |
| Target change rejected                  | Use the climate entity's minimum, maximum and step. Target changes do not turn heating on.                                                        |
| A command is unconfirmed                | Check the backend entities and original app before repeating it. The card does not automatically retry.                                           |
| Illustration and physical output differ | Images represent configured effects. Thermostat cycling, actual heat output, brightness and color are not measured by the illustration.           |
| Old UI after update                     | Refresh Companion/browser clients. For manual resources, update the version query.                                                                |

A clock icon indicates a command awaiting confirmation. A warning icon indicates a failed or invalid action; hover it to read the message. Both expose their messages to screen readers. A dash in the room-temperature reading means the sensor is unavailable.

The power button requires `entities.power`. It appears by default when mapped unless `show_power: false` is configured. A start triangle offers power-on; a power symbol offers shutdown.

If flame speed is missing, check that the model exposes its Flame speed Number entity, enable that entity if needed, map it in the card and enable **Show flame speed**. The card reads its numeric range and step from Home Assistant; it does not synthesize speed controls for unsupported devices.

If a control is missing only in compact view, select it under **Controls in compact view**. Its entity binding and global visibility must also be enabled. Expanding intentionally does not restore controls hidden under **Visible elements**. Each card keeps its own expansion state; a reload returns to its configured initial view.

If automatic discovery failed temporarily, use **Refresh fireplaces** in the visual editor. A successful retry clears the discovery warning. The editor does not retry continuously in the background. Manual entity selection remains available.

If a slider becomes unavailable despite a numeric entity value, check its minimum, maximum and step. Incoming off-step or out-of-range values are intentionally rejected.

Report card version, backend version, HA version, browser, fireplace model and the affected entity domains. Include a minimal redacted card configuration only when needed. Do not post credentials, JWTs, native callback URLs or full HA state exports.

## Chip opens inside the dashboard

Update the card resource and reload the frontend, then select **Chip expansion → Dialog** in the visual editor. The default is `chip_expansion: modal`; remove an explicit `inline` value to use the default. A chip opens its own modal without Browser Mod. The standard compact layout continues to expand in the dashboard.
