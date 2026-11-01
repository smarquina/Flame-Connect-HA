# Fireplace controls

Each selected Wi-Fi fireplace appears as a separate Home Assistant device. Its name comes from Flame Connect. Controls share one confirmed state per fireplace; changes made with the app or remote normally appear after the next successful 30-second read. Missing or failed reads make the affected controls unavailable.

## Power, flame, and heating

| Control | Home Assistant entity | Behavior |
|---|---|---|
| Fireplace power | Switch | On selects manual mode and enables the available heating and flame parameters, matching the app's power action. Off puts the fireplace in standby and disables those effects. |
| Flame | Light with on/off support | Changes the decorative flame independently of heating. It does not offer arbitrary RGB or brightness sliders. |
| Heating | Climate | Turns heating on/off and exposes the target temperature and supported presets. Turning heating on also selects manual fireplace mode; turning it off does not put the entire fireplace in standby. |
| Target temperature | Number | Edits the same heating setpoint shown by Heating. Both update from the confirmed readback. A target change does not turn anything on. |
| Reported temperature (legacy) | Sensor | Unavailable; disabled by default for new installations. Its earlier source was a setpoint, not a measured room temperature. Existing entity identifiers are retained. |

For a decorative flame without heat, use **Flame** and keep **Heating** off. **Fireplace power** is the whole-device action and can enable heating.

In Spanish, the controls are **Calefacción** and **Temperatura objetivo**. The legacy sensor **Temperatura informada** is unavailable. The climate entity's current temperature is unknown because no independent room/probe measurement is exposed by the mapped API. Home Assistant translates the UI, while your custom entity names and the fireplace name are preserved.

Targets use Celsius on the wire. Native target limits are 15 °C to 30.6 °C for recognized Optiflame/OLF families, or 32.9 °C otherwise. Home Assistant handles display-unit conversions. The preferred unit option does not change the physical fireplace display.

## Heating presets

Choose a preset in the **Heating** climate entity. Normal is available with heating support; optional presets appear only when the model explicitly declares the corresponding capability. Preset selection preserves fireplace power, heating on/off, target temperature, and flame. If heating is off, enable it separately.

| English label | Spanish label | Stable automation value | Required capability | Function |
|---|---|---|---|---|
| Normal | Normal | `normal` | Heating support | Select normal operation; also cancels Boost. |
| Eco | Eco | `eco` | `AdvancedHeat` | Select the device's Eco heating mode. Savings or exact regulation behavior depend on the device. |
| Boost | Calefacción intensiva | `boost` | `PowerBoost` | Select the device's timed intensive heating mode. |
| Fan only | Solo ventilador | `fan_only` | `FanOnly` | Select ventilation without heat, as defined by the device. |
| Existing weekly schedule | Horario semanal existente | `schedule` | `SevenDayTimer` | Activate the weekly program already configured using the original app. Does not create or edit its periods. |

Use standard Home Assistant climate actions such as **Set preset mode** (`climate.set_preset_mode`). Automation values stay in English keys regardless of the interface language. Unsupported values raise an error without writing to the fireplace.

## Heating boost duration

The **Heating boost duration** number entity (**Duración de calefacción intensiva** in Spanish) is created and enabled by default only when the fireplace supports heating and declares `PowerBoost`. It is independent of the experimental option.

1. Set a whole-minute duration from **1 to 20**. The duration setting alone does not activate Boost or switch heating on.
2. Select **Boost** in Heating. It uses the reported duration if within that range; otherwise the integration explicitly sets **15 minutes**.
3. If heating was off, turn it on separately. Check the app and device when validating this beta.
4. Select **Normal** to cancel Boost before it finishes.

Changing duration during Boost may restart its period on the fireplace. The duration is a reported setting, not a countdown, remaining-time measurement, or guaranteed completion timestamp. No Boost-end sensor is exposed. New preset behavior and duration changes still need physical validation per model.

## Flame settings

**Flame brightness** is a Select entity with `high`, `low`, `flicker_high`, and `flicker_low`, created when the device declares `FlameDimming`. **Flame speed** is a Number entity with integer values **1–5**, requiring `FlameFanSpeed`.

The optional **Flame color** selector offers the model's discrete palette, not arbitrary RGB colors. It requires the experimental option plus `RgbFlameAccent` or `FlameAmber`, and starts disabled. Labels depend on `FlamePresetOptions`; combinations use stable keys such as `yellow_red_blue` and `blue_red`. Changes to color and brightness preserve the other received parameter bytes.

## Experimental controls

Enable **Create experimental controls** in the integration options, then enable each desired entity on the fireplace's device page. These controls still require physical validation. Missing parameters leave the corresponding controls unavailable.

| Control | Entity | Requirements and accepted values |
|---|---|---|
| Flame color | Select | Supported model palette as described above. |
| Countdown | Switch | Requires `CountDownTimer`; enables/disables the reported countdown state. |
| Countdown duration | Number | Requires `CountDownTimer`; whole minutes, currently **0–32767** at the protocol level. This is not a guarantee that the device accepts the entire range. Start with a short duration and validate in the app. |
| Sound volume | Number | Requires `Sound`; **0–255** is the protocol byte capacity, not a verified volume scale. |
| Sound file | Number | Requires `Sound`; **0–255** is the protocol range, not a discovered list of playable files. |
| Device temperature scale | Select | `fahrenheit` / `celsius`; writes the fireplace display preference. Separate from the integration's preferred unit option. |

Countdown duration writes the reported setting immediately and preserves its current enabled/disabled status. The integration does not keep a separate local countdown configuration or expose a timer-end sensor. Configure and validate a duration before enabling Countdown.

## Connection and diagnostics

**Connection** is a binary connectivity sensor indicating whether the last state read succeeded. It does not distinguish every manufacturer connection state or diagnose your local network.

**Firmware bytes** and **Error bytes** are read-only diagnostic sensors, disabled by default. They show exact payload bytes rather than unverified firmware-version interpretations or translated fault descriptions. Downloadable integration diagnostics omit credentials and personal identifiers.

Commands perform a fresh read, modify known fields, write once, and read again. An unconfirmed command raises an error and is not retried automatically. Check the state and original app before repeating it. An unavailable fireplace does not prevent its siblings from operating.

## Scope

This integration does not expose separate RGBW media/overhead/log lights, pulsating effects, an ambient-light-sensor switch, or a dedicated refresh button. It does not create or edit weekly schedules, update firmware, reset devices, manage guests, transfer ownership, or provide local LAN/Bluetooth control. API documentation may include operations that are not exposed as Home Assistant controls.

See [installation and options](installation.md), [technical operation](technical.md), [troubleshooting](troubleshooting.md), and [validation status](compatibility.md).
