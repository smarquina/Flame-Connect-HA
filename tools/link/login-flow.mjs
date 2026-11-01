import { Buffer } from 'node:buffer';
import { B2C_HOST, isCallback } from './auth.mjs';
import { b2cErrorSummary, classifyFormResponse, isConfirmationUrl } from './diagnostics.mjs';

const CONFIRMATION_DELAY_MS = 800;

/**
 * @param {import('./cdp.mjs').CdpPort} cdp
 * @param {{headers?: Record<string,string>, onCallback: (raw: string) => any,
 * onEvent?: (message: string) => void, wait?: (ms: number) => Promise<void>}} options
 */
export function attachLoginFlow(
  cdp,
  {
    headers = {},
    onCallback,
    onEvent = () => {},
    wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  },
) {
  let closed = false,
    callbackSeen = false;
  const sleep = wait;
  /** @param {string} raw */
  const complete = async (raw) => {
    if (closed || callbackSeen || !isCallback(raw)) return;
    callbackSeen = true;
    await onCallback(raw);
  };
  cdp.on('Page.frameStartedNavigating', async ({ url: destination }) => {
    if (isCallback(destination)) await complete(destination);
  });
  cdp.on('Page.frameRequestedNavigation', async ({ url: destination }) => {
    if (isCallback(destination)) {
      await cdp.send('Page.stopLoading').catch(() => {});
      await complete(destination);
    }
  });
  cdp.on('Network.requestWillBeSent', async ({ request, redirectResponse }) => {
    const location =
      redirectResponse &&
      Object.entries(redirectResponse.headers ?? {}).find(
        ([k]) => k.toLowerCase() === 'location',
      )?.[1];
    if (isCallback(request.url)) await complete(request.url);
    else if (location && isCallback(location)) await complete(location);
  });
  const formResponses = new Map();
  let continuationScheduled = false;
  cdp.on('Network.responseReceived', ({ response, type, requestId }) => {
    const target = new URL(response.url);
    if (type === 'Document' && target.hostname === B2C_HOST)
      onEvent(`The B2C login page returned HTTP ${response.status}.`);
    if (target.hostname === B2C_HOST && target.pathname.endsWith('/SelfAsserted'))
      formResponses.set(requestId, response.status);
  });
  cdp.on('Network.loadingFinished', async ({ requestId }) => {
    if (!formResponses.has(requestId)) return;
    const status = formResponses.get(requestId);
    formResponses.delete(requestId);
    try {
      const result = await cdp.send('Network.getResponseBody', { requestId });
      const body = result.base64Encoded
        ? Buffer.from(result.body, 'base64').toString('utf8')
        : result.body;
      const state = classifyFormResponse(body, status);
      if (state === 'error') {
        onEvent(b2cErrorSummary(body, status));
        return;
      }
      if (state !== 'success' || continuationScheduled) return;
      continuationScheduled = true;
      onEvent('B2C accepted the form. Waiting for authorization to continue.');
      // B2C's desktop redirect helper becomes a no-op after its first call.
      // If its own navigation stalled, continue only an already successful step.
      await sleep(CONFIRMATION_DELAY_MS);
      if (closed || callbackSeen) return;
      const next = await cdp.send('Runtime.evaluate', {
        expression: `(() => {
            if (!location.pathname.endsWith('/authorize') || typeof $i2e !== 'object' || typeof $i2e.getRedirectLink !== 'function') return null;
            return $i2e.getRedirectLink('confirmed?rememberMe=false');
          })()`,
        returnByValue: true,
      });
      const nextUrl = next.result?.value;
      if (!isConfirmationUrl(nextUrl)) return;
      onEvent('Resuming B2C confirmation without resubmitting credentials.');
      await cdp.send('Page.navigate', { url: new URL(nextUrl, `https://${B2C_HOST}`).toString() });
    } catch {
      if (!closed && !callbackSeen && status >= 400)
        onEvent(`B2C rejected the form (HTTP ${status}); the reason could not be read.`);
    }
  });
  cdp.on('Fetch.requestPaused', async (event) => {
    if (event.responseStatusCode !== undefined) {
      const location = event.responseHeaders?.find(
        /** @param {{name: string, value: string}} h */ (h) => h.name.toLowerCase() === 'location',
      )?.value;
      if (location && isCallback(location)) {
        await cdp
          .send('Fetch.failRequest', { requestId: event.requestId, errorReason: 'Aborted' })
          .catch(() => {});
        await complete(location);
        return;
      }
      await cdp.send('Fetch.continueRequest', { requestId: event.requestId });
    } else {
      const merged = { ...event.request.headers };
      for (const [name, value] of Object.entries(headers)) {
        for (const old of Object.keys(merged))
          if (old.toLowerCase() === name.toLowerCase()) delete merged[old];
        merged[name] = value;
      }
      await cdp.send('Fetch.continueRequest', {
        requestId: event.requestId,
        headers: Object.entries(merged).map(([name, value]) => ({ name, value: String(value) })),
      });
    }
  });

  return {
    close() {
      closed = true;
      formResponses.clear();
    },
  };
}
