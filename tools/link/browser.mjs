import { B2C_HOST, validateAuthorizeUrl } from './auth.mjs';
import { attachLoginFlow } from './login-flow.mjs';
import { startBrowserProcess } from './browser-process.mjs';

export { CDP } from './cdp.mjs';
export { stopBrowserProcess, chromeExecutable } from './browser-process.mjs';

// Inject only the desktop boundary: policy tests never start a real browser.
export async function launchLoginBrowser({
  url,
  headers = {},
  onCallback,
  onEvent = () => {},
  onClose = () => {},
  headless = false,
  startBrowser = startBrowserProcess,
}) {
  validateAuthorizeUrl(url);
  let completed = false,
    closed = false,
    closing;
  const browser = await startBrowser({
    headless,
    onExit: () => {
      if (!closed && !completed) onClose();
    },
  });
  const { cdp } = browser;
  const login = attachLoginFlow(cdp, {
    headers,
    onEvent,
    onCallback: async (raw) => {
      completed = true;
      await onCallback(raw);
    },
  });
  const controller = {
    profile: browser.profile,
    cdp,
    async close() {
      if (closing) return closing;
      closed = true;
      login.close();
      closing = browser.close();
      return closing;
    },
  };
  try {
    await cdp.send('Page.enable');
    await cdp.send('Network.enable');
    await cdp.send('Fetch.enable', {
      patterns: [
        {
          urlPattern: `https://${B2C_HOST}/*/api/*/confirmed*`,
          resourceType: 'Document',
          requestStage: 'Response',
        },
        ...(Object.keys(headers).length
          ? [{ urlPattern: `https://${B2C_HOST}/*`, requestStage: 'Request' }]
          : []),
      ],
    });
    await cdp.send('Page.navigate', { url });
    return controller;
  } catch (error) {
    await controller.close();
    throw error;
  }
}
