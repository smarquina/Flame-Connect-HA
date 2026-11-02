import { spawn } from 'node:child_process';
import { mkdtemp, rm, access, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { CDP } from './cdp.mjs';

const SHUTDOWN_GRACE_POLLS = 30;
const PROCESS_POLL_MS = 100;
const FORCED_SHUTDOWN_WAIT_MS = 200;
const CHROME_COMMAND_PIPE = 3;
const CHROME_RESPONSE_PIPE = 4;

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
  rm,
  connect: (child) => new CDP(child.stdio[CHROME_RESPONSE_PIPE], child.stdio[CHROME_COMMAND_PIPE]),
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
        '--remote-debugging-pipe',
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
      { stdio: ['ignore', 'ignore', 'ignore', 'pipe', 'pipe'] },
    );
    child.on('error', () => {
      cdp?.close();
    });
    child.on('exit', () => {
      cdp?.close();
      if (!closed) onExit();
    });
    cdp = desktop.connect(child);
    controller.cdp = cdp;
    await cdp.initialize();
    return { ...controller, cdp };
  } catch (error) {
    await controller.close();
    throw error;
  }
}
