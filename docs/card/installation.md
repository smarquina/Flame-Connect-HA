# Fireplace card installation

The Flame Connect integration includes the dashboard card. Install the integration from HACS or the Marketplace, restart Home Assistant, and add and configure Flame Connect under Devices & Services. Open a dashboard, choose **Edit dashboard**, **Add card**, and select **Flame Connect Card**. Select a fireplace and any optional room-temperature sensor in the editor.

The JavaScript module is automatically registered when Home Assistant manages dashboard resources in storage mode. Refresh the browser after installation or an update. With `lovelace.resource_mode: yaml`, add the module to `configuration.yaml` and restart Home Assistant:

```yaml
lovelace:
  resource_mode: yaml
  resources:
    - url: /flame_connect/flame-connect-card.js?v=4510a0d2966145ce07111fbcf17b837d9b3d0bbd232f8376a432e5937778669e
      type: module
```

If HTTP or Lovelace is temporarily unavailable, registration is retried automatically. In storage mode the module URL includes a content hash so updates load a fresh copy. In YAML mode, update the URL above when updating the integration.

## Migrating from the separate card

Install the bundled integration and remove the old Flame Connect Card resource from **Settings → Dashboards → Resources**, or from `configuration.yaml` if managed in YAML. Old paths can start with `/hacsfiles/flame-connect-card/`, `/local/community/flame-connect-card/`, or point to a manually installed file. For storage-mode resources, reload the Flame Connect integration or restart Home Assistant to register the bundled resource. In YAML resource mode, add the resource above and restart. Refresh the browser and verify the existing cards, controls, and card-mod styling. Then uninstall the separate dashboard plugin if it is no longer needed. Existing `custom:flame-connect-card` configuration and entity IDs do not need to change.

The integration leaves a detected HACS resource in place and does not register a second copy. A manually installed resource under a different filename must be removed by the user before enabling the bundled card.

If automatic registration is unavailable, add `/flame_connect/flame-connect-card.js?v=4510a0d2966145ce07111fbcf17b837d9b3d0bbd232f8376a432e5937778669e` as a JavaScript module in the dashboard resource settings after setting up the integration. Removing the integration may leave the resource in the dashboard settings; remove that entry when it is no longer needed.
