# Flame Connect API guide

The [technical reference](technical.md) describes servers, headers, authentication, binary parameters, commands, availability, and diagnostics.

The machine-readable contracts are [the device/account OpenAPI specification](openapi.json) and [the Azure B2C OpenAPI specification](b2c.openapi.json). See [compatibility and limitations](compatibility.md) for the distinction between observed behavior and reconstructed endpoints.

This integration is unofficial. Endpoint documentation does not imply that every operation has been validated or is exposed by the Home Assistant integration.

For the actual Home Assistant surface, use the [control guide](controls.md): editable target temperature, capability-filtered heating presets and Boost duration, power/flame controls, and optional experimental settings. Account setup supports direct B2C email/password sign-in and the browser alternative described in [installation](installation.md). Enabling an existing weekly heating program does not expose the API's schedule-editing operations.
