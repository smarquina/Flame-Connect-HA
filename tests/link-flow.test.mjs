import { test } from 'node:test';
import assert from 'node:assert/strict';
import { attachLoginFlow } from '../tools/link/login-flow.mjs';
import { launchLoginBrowser } from '../tools/link/browser.mjs';
import { B2C_HOST, CLIENT_ID, REDIRECT_URI } from '../tools/link/auth.mjs';

const callback = `${REDIRECT_URI}?code=fixture&state=fixture`;
const confirmation =
  '/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_Test/api/CombinedSigninAndSignup/confirmed?rememberMe=false';
function authorizationUrl() {
  const url = new URL(
    `https://${B2C_HOST}/gdhvb2cflameconnect.onmicrosoft.com/B2C_1A_FirePhoneSignUpOrSignInWithPhoneOrEmail/oauth2/v2.0/authorize`,
  );
  url.search = new URLSearchParams({
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    code_challenge_method: 'S256',
    code_challenge: 'fixture',
    state: 'fixture',
    nonce: 'fixture',
  });
  return url.toString();
}
class FakeCdp {
  calls = [];
  listeners = new Map();
  respond = async () => ({});
  async send(method, params = {}) {
    this.calls.push({ method, params });
    return this.respond(method, params);
  }
  on(name, listener) {
    this.listeners.set(name, listener);
  }
  async emit(name, params) {
    await this.listeners.get(name)?.(params);
  }
}
async function form(cdp, status = 200, requestId = 'form') {
  await cdp.emit('Network.responseReceived', {
    requestId,
    type: 'Document',
    response: {
      url: `https://${B2C_HOST}/tenant/policy/SelfAsserted`,
      status,
    },
  });
  await cdp.emit('Network.loadingFinished', { requestId });
}

test('all native callback channels complete once and cancellation suppresses later returns', async () => {
  for (const [event, params] of [
    ['Page.frameStartedNavigating', { url: callback }],
    ['Page.frameRequestedNavigation', { url: callback }],
    ['Network.requestWillBeSent', { request: { url: callback } }],
    [
      'Network.requestWillBeSent',
      {
        request: { url: 'https://example.invalid' },
        redirectResponse: { headers: { Location: callback } },
      },
    ],
    [
      'Fetch.requestPaused',
      {
        requestId: 'r',
        responseStatusCode: 302,
        responseHeaders: [{ name: 'Location', value: callback }],
      },
    ],
  ]) {
    const cdp = new FakeCdp();
    const returns = [];
    const flow = attachLoginFlow(cdp, { onCallback: (raw) => returns.push(raw) });
    await cdp.emit(event, params);
    await cdp.emit('Page.frameStartedNavigating', { url: callback });
    assert.deepEqual(returns, [callback]);
    flow.close();
  }
  const cdp = new FakeCdp();
  const flow = attachLoginFlow(cdp, { onCallback: () => assert.fail('cancelled') });
  flow.close();
  await cdp.emit('Page.frameStartedNavigating', { url: callback });
});

test('a successful B2C form continues only a trusted confirmation without resubmitting credentials', async () => {
  const cdp = new FakeCdp();
  const messages = [];
  cdp.respond = async (method) =>
    method === 'Network.getResponseBody'
      ? { body: Buffer.from('{"status":200}').toString('base64'), base64Encoded: true }
      : { result: { value: confirmation } };
  attachLoginFlow(cdp, {
    onCallback: () => {},
    onEvent: (message) => messages.push(message),
    wait: async () => {},
  });
  await form(cdp);
  await form(cdp, 200, 'second');
  const navigation = cdp.calls.filter((call) => call.method === 'Page.navigate');
  assert.deepEqual(navigation, [
    { method: 'Page.navigate', params: { url: `https://${B2C_HOST}${confirmation}` } },
  ]);
  assert.ok(messages.some((message) => message.includes('without resubmitting credentials')));
  assert.ok(cdp.calls.every((call) => !call.method.includes('PostData')));
});

test('failed and unknown forms never continue or disclose provider text', async () => {
  const cdp = new FakeCdp();
  const messages = [];
  attachLoginFlow(cdp, {
    onCallback: () => {},
    onEvent: (message) => messages.push(message),
    wait: async () => {},
  });
  cdp.respond = async () => ({ body: '{"status":400,"message":"private-password"}' });
  await form(cdp, 400);
  cdp.respond = async () => ({ body: '{}' });
  await form(cdp);
  assert.ok(cdp.calls.every((call) => call.method === 'Network.getResponseBody'));
  assert.ok(messages.every((message) => !message.includes('private-password')));
});

test('closing during the continuation delay cancels navigation and ignores unrelated network traffic', async () => {
  const cdp = new FakeCdp();
  let release;
  const waiting = new Promise((resolve) => {
    release = resolve;
  });
  cdp.respond = async () => ({ body: '{"status":200}' });
  const flow = attachLoginFlow(cdp, {
    onCallback: () => assert.fail('cancelled'),
    wait: () => waiting,
  });
  await cdp.emit('Network.responseReceived', {
    requestId: 'unrelated',
    type: 'Script',
    response: { url: 'https://example.invalid/script', status: 200 },
  });
  await cdp.emit('Network.loadingFinished', { requestId: 'unrelated' });
  const pending = form(cdp);
  await Promise.resolve();
  await Promise.resolve();
  flow.close();
  release();
  await pending;
  assert.ok(cdp.calls.every((call) => call.method !== 'Page.navigate'));
});

test('headers replace case-insensitively and unrelated responses continue normally', async () => {
  const cdp = new FakeCdp();
  attachLoginFlow(cdp, { headers: { 'User-Agent': 'fixture-agent' }, onCallback: () => {} });
  await cdp.emit('Fetch.requestPaused', {
    requestId: 'request',
    request: { headers: { 'user-agent': 'old', Accept: 'text/html' } },
  });
  assert.deepEqual(cdp.calls.at(-1).params.headers, [
    { name: 'Accept', value: 'text/html' },
    { name: 'User-Agent', value: 'fixture-agent' },
  ]);
  await cdp.emit('Fetch.requestPaused', { requestId: 'response', responseStatusCode: 200 });
  assert.deepEqual(cdp.calls.at(-1), {
    method: 'Fetch.continueRequest',
    params: { requestId: 'response' },
  });
});

test('an untrusted continuation and unreadable error response never trigger navigation', async () => {
  const cdp = new FakeCdp();
  const messages = [];
  attachLoginFlow(cdp, {
    onCallback: () => {},
    onEvent: (message) => messages.push(message),
    wait: async () => {},
  });
  cdp.respond = async (method) =>
    method === 'Network.getResponseBody'
      ? { body: '{"status":200}' }
      : { result: { value: 'https://example.invalid/confirmed' } };
  await form(cdp);
  assert.ok(cdp.calls.every((call) => call.method !== 'Page.navigate'));
  cdp.respond = async () => {
    throw new Error('private-provider-error');
  };
  await form(cdp, 400);
  assert.ok(messages.some((message) => message.includes('could not be read')));
  assert.ok(messages.every((message) => !message.includes('private-provider-error')));
});

test('browser orchestration enables capture, notifies early exit, and cleans up exactly once', async () => {
  const cdp = new FakeCdp();
  let exited,
    closes = 0,
    notifications = 0;
  const startBrowser = async ({ onExit }) => {
    exited = onExit;
    return {
      cdp,
      profile: '/fixture',
      close: async () => {
        closes++;
      },
    };
  };
  const browser = await launchLoginBrowser({
    url: authorizationUrl(),
    headers: { 'User-Agent': 'fixture' },
    onCallback: () => {},
    onClose: () => {
      notifications++;
    },
    startBrowser,
  });
  assert.ok(
    cdp.calls.some((call) => call.method === 'Fetch.enable' && call.params.patterns.length === 2),
  );
  exited();
  assert.equal(notifications, 1);
  await cdp.emit('Page.frameStartedNavigating', { url: callback });
  exited();
  assert.equal(notifications, 1);
  await Promise.all([browser.close(), browser.close()]);
  assert.equal(closes, 1);
  exited();
  assert.equal(notifications, 1);
});

test('browser startup failure cleans up and invalid URLs are rejected before starting a process', async () => {
  const cdp = new FakeCdp();
  let closes = 0;
  cdp.respond = async () => {
    throw new Error('capture failed');
  };
  const startBrowser = async () => ({
    cdp,
    profile: '/fixture',
    close: async () => {
      closes++;
    },
  });
  await assert.rejects(
    launchLoginBrowser({ url: authorizationUrl(), onCallback: () => {}, startBrowser }),
    /capture failed/,
  );
  assert.equal(closes, 1);
  await assert.rejects(
    launchLoginBrowser({
      url: 'https://example.invalid',
      onCallback: () => {},
      startBrowser: async () => assert.fail('invalid URL'),
    }),
  );
});
