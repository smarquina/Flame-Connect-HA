import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, access, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { B2C_HOST, isCallback } from './auth.mjs';
import { b2cErrorSummary, classifyFormResponse, isConfirmationUrl } from './diagnostics.mjs';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

export class CDP {
  constructor(url) {
    const u = new URL(url);
    if (u.protocol !== 'ws:' || !['127.0.0.1', 'localhost'].includes(u.hostname)) throw new Error('Chrome debe estar en loopback.');
    this.socket = new WebSocket(url); this.pending = new Map(); this.listeners = new Map(); this.next = 0;
    this.ready = new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Chrome no respondió.')), 10000);
      this.socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
      this.socket.addEventListener('error', () => { clearTimeout(timer); reject(new Error('No se pudo conectar con Chrome.')); }, { once: true });
    });
    this.socket.addEventListener('message', event => {
      let msg; try { msg = JSON.parse(event.data); } catch { return; }
      if (msg.id) {
        const p = this.pending.get(msg.id); if (!p) return;
        this.pending.delete(msg.id); clearTimeout(p.timer);
        if (msg.error) p.reject(new Error(`Chrome: ${msg.error.code}`)); else p.resolve(msg.result);
      } else {
        for (const listener of this.listeners.get(msg.method) ?? []) Promise.resolve(listener(msg.params)).catch(() => {});
      }
    });
    this.socket.addEventListener('close', () => {
      for (const p of this.pending.values()) { clearTimeout(p.timer); p.reject(new Error('Se cerró la ventana de login.')); }
      this.pending.clear();
    });
  }
  async send(method, params = {}) {
    await this.ready;
    if (this.socket.readyState !== WebSocket.OPEN) throw new Error('Chrome está cerrado.');
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { this.pending.delete(id); reject(new Error(`Chrome no respondió a ${method}.`)); }, 15000);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  on(name, listener) { const list = this.listeners.get(name) ?? []; list.push(listener); this.listeners.set(name, list); }
  close() { this.socket.close(); }
}

export async function chromeExecutable() {
  const candidates = [process.env.FLAME_CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ].filter(Boolean);
  for (const path of candidates) { try { await access(path); return path; } catch {} }
  throw new Error('No encuentro Chrome. Define FLAME_CHROME_PATH o utiliza el retorno manual.');
}

export async function launchLoginBrowser({ url, headers = {}, onCallback, onEvent = () => {}, onClose = () => {}, headless = false }) {
  const executable = await chromeExecutable();
  const profile = await mkdtemp(join(tmpdir(), 'flame-login-'));
  // Disable password saving in this disposable profile; never reuse the user's Chrome profile.
  const { mkdir } = await import('node:fs/promises');
  await mkdir(join(profile, 'Default'));
  await writeFile(join(profile, 'Default', 'Preferences'), JSON.stringify({ credentials_enable_service:false, profile:{ password_manager_enabled:false }, signin:{ allowed:false } }));
  let child, cdp, closed = false, callbackSeen = false, closing;
  const finishCallback = async raw => {
    if (callbackSeen || !isCallback(raw)) return;
    callbackSeen = true;
    await onCallback(raw);
  };
  const controller = {
    profile, cdp: null,
    async close() {
      if (closing) return closing;
      closing = (async () => {
        closed = true;
        try { if (cdp) await cdp.send('Browser.close'); } catch {}
        cdp?.close();
        if (child && child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
        for (let i = 0; child && child.exitCode === null && child.signalCode === null && i < 30; i++) await sleep(100);
        if (child && child.exitCode === null && child.signalCode === null) { child.kill('SIGKILL'); await sleep(200); }
        await rm(profile, { recursive: true, force: true, maxRetries: 4, retryDelay: 150 }).catch(() => {});
      })();
      return closing;
    },
  };
  try {
    child = spawn(executable, [
      `--user-data-dir=${profile}`, '--remote-debugging-port=0', '--remote-debugging-address=127.0.0.1',
      '--no-first-run', '--no-default-browser-check', '--disable-sync', '--disable-background-networking',
      '--disable-breakpad', '--disable-features=PasswordLeakDetection', '--password-store=basic',
      '--new-window', '--window-size=1080,840', ...(headless ? ['--headless=new'] : []), 'about:blank',
    ], { stdio: 'ignore' });
    let spawnError;
    child.on('error', () => { spawnError = true; });
    child.on('exit', () => { if (!closed && !callbackSeen) onClose(); });
    let port;
    for (let i = 0; i < 100; i++) {
      if (spawnError || child.exitCode !== null) throw new Error('Chrome no pudo arrancar. Prueba el modo manual.');
      try {
        const lines = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).trim().split('\n');
        const candidate = Number(lines[0]); if (candidate > 0 && candidate < 65536) { port = candidate; break; }
      } catch {}
      await sleep(100);
    }
    if (!port) throw new Error('Chrome tardó demasiado en abrir el login.');
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`, { signal: AbortSignal.timeout(5000) })).json();
    const target = targets.find(t => t.type === 'page' && t.url === 'about:blank');
    if (!target) throw new Error('No se encontró la ventana de login.');
    cdp = new CDP(target.webSocketDebuggerUrl); controller.cdp = cdp;
    await cdp.ready;
    cdp.on('Page.frameStartedNavigating', async ({ url: destination }) => {
      if (isCallback(destination)) await finishCallback(destination);
    });
    cdp.on('Page.frameRequestedNavigation', async ({ url: destination }) => {
      if (isCallback(destination)) { await cdp.send('Page.stopLoading').catch(() => {}); await finishCallback(destination); }
    });
    cdp.on('Network.requestWillBeSent', async ({ request, redirectResponse }) => {
      const location = redirectResponse && Object.entries(redirectResponse.headers ?? {}).find(([k]) => k.toLowerCase() === 'location')?.[1];
      if (isCallback(request.url)) await finishCallback(request.url);
      else if (location && isCallback(location)) await finishCallback(location);
    });
    const formResponses = new Map();
    let continuationScheduled = false;
    cdp.on('Network.responseReceived', ({ response, type, requestId }) => {
      const target = new URL(response.url);
      if (type === 'Document' && target.hostname === B2C_HOST) onEvent(`B2C respondió HTTP ${response.status} en la página de acceso.`);
      if (target.hostname === B2C_HOST && target.pathname.endsWith('/SelfAsserted')) formResponses.set(requestId, response.status);
    });
    cdp.on('Network.loadingFinished', async ({ requestId }) => {
      if (!formResponses.has(requestId)) return;
      const status = formResponses.get(requestId);
      formResponses.delete(requestId);
      try {
        const result = await cdp.send('Network.getResponseBody', { requestId });
        const body = result.base64Encoded ? Buffer.from(result.body, 'base64').toString('utf8') : result.body;
        const state = classifyFormResponse(body, status);
        if (state === 'error') { onEvent(b2cErrorSummary(body, status)); return; }
        if (state !== 'success' || continuationScheduled) return;
        continuationScheduled = true;
        onEvent('B2C validó el formulario. Esperando la continuación de la autorización.');
        // B2C's desktop redirect helper becomes a no-op after its first call.
        // If its own navigation stalled, continue only an already successful step.
        await sleep(800);
        if (closed || callbackSeen) return;
        const next = await cdp.send('Runtime.evaluate', {
          expression: `(() => {
            if (!location.pathname.endsWith('/authorize') || typeof $i2e !== 'object' || typeof $i2e.getRedirectLink !== 'function') return null;
            return $i2e.getRedirectLink('confirmed?rememberMe=false');
          })()`, returnByValue: true,
        });
        const nextUrl = next.result?.value;
        if (!isConfirmationUrl(nextUrl)) return;
        onEvent('Se reanuda el paso de confirmación B2C sin volver a enviar credenciales.');
        await cdp.send('Page.navigate', { url: new URL(nextUrl, `https://${B2C_HOST}`).toString() });
      } catch { if (!closed && !callbackSeen && status >= 400) onEvent(`B2C rechazó el formulario (HTTP ${status}); no se pudo leer el motivo.`); }
    });
    cdp.on('Fetch.requestPaused', async event => {
      if (event.responseStatusCode !== undefined) {
        const location = event.responseHeaders?.find(h => h.name.toLowerCase() === 'location')?.value;
        if (location && isCallback(location)) {
          await cdp.send('Fetch.failRequest', { requestId: event.requestId, errorReason: 'Aborted' }).catch(() => {});
          await finishCallback(location); return;
        }
        await cdp.send('Fetch.continueRequest', { requestId: event.requestId });
      } else {
        const merged = { ...event.request.headers };
        for (const [name, value] of Object.entries(headers)) {
          for (const old of Object.keys(merged)) if (old.toLowerCase() === name.toLowerCase()) delete merged[old];
          merged[name] = value;
        }
        await cdp.send('Fetch.continueRequest', { requestId: event.requestId, headers: Object.entries(merged).map(([name, value]) => ({ name, value: String(value) })) });
      }
    });
    await cdp.send('Page.enable'); await cdp.send('Network.enable');
    await cdp.send('Fetch.enable', { patterns: [
      { urlPattern: `https://${B2C_HOST}/*/api/*/confirmed*`, resourceType: 'Document', requestStage: 'Response' },
      ...(Object.keys(headers).length ? [{ urlPattern: `https://${B2C_HOST}/*`, requestStage: 'Request' }] : []),
    ] });
    await cdp.send('Page.navigate', { url });
    return controller;
  } catch (error) { await controller.close(); throw error; }
}
