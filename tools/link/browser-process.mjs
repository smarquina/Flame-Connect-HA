import { spawn } from 'node:child_process';
import { mkdtemp, readFile, rm, access, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { CDP } from './cdp.mjs';

const SHUTDOWN_GRACE_POLLS = 30;
const PROCESS_POLL_MS = 100;
const FORCED_SHUTDOWN_WAIT_MS = 200;
const STARTUP_PORT_POLLS = 100;
const TCP_PORT_LIMIT = 65536;
const TARGET_DISCOVERY_TIMEOUT_MS = 5000;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Poll for asynchronous ChildProcess exit updates with a bounded grace period.
export async function stopBrowserProcess(child, wait = sleep) {
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  child.kill('SIGTERM');
  for (let attempt = 0; attempt < SHUTDOWN_GRACE_POLLS; attempt++) {
    if (child.exitCode !== null || child.signalCode !== null) return;
    await wait(PROCESS_POLL_MS);
  }
  if (child.exitCode === null && child.signalCode === null) {
    child.kill('SIGKILL');
    await wait(FORCED_SHUTDOWN_WAIT_MS);
  }
}

export async function chromeExecutable(
  candidates = [
    process.env.FLAME_CHROME_PATH,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean),
  exists = access,
) {
  for (const path of candidates) {
    try {
      await exists(path);
      return path;
    } catch {}
  }
  throw new Error('Chrome was not found. Set FLAME_CHROME_PATH or capture the return manually.');
}

const DESKTOP = {
  findExecutable: chromeExecutable,
  createProfile: () => mkdtemp(join(tmpdir(), 'flame-login-')),
  mkdir,
  writeFile,
  spawn,
  readFile,
  rm,
  connect: (url) => new CDP(url),
  fetch,
  wait: sleep,
};

export async function startBrowserProcess(
  { headless = false, onExit = () => {} },
  desktop = DESKTOP,
) {
  const executable = await desktop.findExecutable();
  const profile = await desktop.createProfile();
  let child,
    cdp,
    closed = false,
    closing;
  const controller = {
    profile,
    cdp: null,
    async close() {
      if (closing) return closing;
      closing = (async () => {
        closed = true;
        try {
          if (cdp) await cdp.send('Browser.close');
        } catch {}
        cdp?.close();
        await stopBrowserProcess(child, desktop.wait);
        await desktop
          .rm(profile, { recursive: true, force: true, maxRetries: 4, retryDelay: 150 })
          .catch(() => {});
      })();
      return closing;
    },
  };
  try {
    // Disable password saving in this disposable profile; never reuse the user's Chrome profile.
    await desktop.mkdir(join(profile, 'Default'));
    await desktop.writeFile(
      join(profile, 'Default', 'Preferences'),
      JSON.stringify({
        credentials_enable_service: false,
        profile: { password_manager_enabled: false },
        signin: { allowed: false },
      }),
    );
    child = desktop.spawn(
      executable,
      [
        `--user-data-dir=${profile}`,
        '--remote-debugging-port=0',
        '--remote-debugging-address=127.0.0.1',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-sync',
        '--disable-background-networking',
        '--disable-breakpad',
        '--disable-features=PasswordLeakDetection',
        '--password-store=basic',
        '--new-window',
        '--window-size=1080,840',
        ...(headless ? ['--headless=new'] : []),
        'about:blank',
      ],
      { stdio: 'ignore' },
    );
    let spawnError;
    child.on('error', () => {
      spawnError = true;
    });
    child.on('exit', () => {
      if (!closed) onExit();
    });
    let port;
    for (let i = 0; i < STARTUP_PORT_POLLS; i++) {
      if (spawnError || child.exitCode !== null)
        throw new Error('Chrome could not start. Try capturing the return manually.');
      try {
        const lines = (await desktop.readFile(join(profile, 'DevToolsActivePort'), 'utf8'))
          .trim()
          .split('\n');
        const candidate = Number(lines[0]);
        if (candidate > 0 && candidate < TCP_PORT_LIMIT) {
          port = candidate;
          break;
        }
      } catch {}
      await desktop.wait(PROCESS_POLL_MS);
    }
    if (!port) throw new Error('Chrome took too long to open the login window.');
    const targets = await (
      await desktop.fetch(`http://127.0.0.1:${port}/json/list`, {
        signal: AbortSignal.timeout(TARGET_DISCOVERY_TIMEOUT_MS),
      })
    ).json();
    const target = targets.find((t) => t.type === 'page' && t.url === 'about:blank');
    if (!target) throw new Error('The login window was not found.');
    cdp = desktop.connect(target.webSocketDebuggerUrl);
    controller.cdp = cdp;
    await cdp.ready;
    return { ...controller, cdp };
  } catch (error) {
    await controller.close();
    throw error;
  }
}
