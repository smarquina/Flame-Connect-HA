import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { chromeExecutable, startBrowserProcess } from '../tools/link/browser-process.mjs';

function desktopFixture() {
  const child = new EventEmitter();
  child.exitCode = null;
  child.signalCode = null;
  child.kill = () => {
    child.exitCode = 0;
    child.emit('exit');
  };
  const calls = { removed: 0, closed: 0, prepared: null, args: [], stdio: [] };
  const cdp = {
    initialize: async () => {},
    send: async () => {},
    close: () => {
      if (cdp.closed) return;
      cdp.closed = true;
      calls.closed++;
    },
  };
  const desktop = {
    findExecutable: async () => '/fixture/chrome',
    createProfile: async () => '/fixture/profile',
    mkdir: async () => {},
    writeFile: async (_file, text) => {
      calls.prepared = JSON.parse(text);
    },
    spawn: (_executable, args, options) => {
      calls.args = args;
      calls.stdio = options.stdio;
      return child;
    },
    rm: async () => {
      calls.removed++;
    },
    wait: async () => {},
    connect: () => cdp,
  };
  return { desktop, child, calls, cdp };
}

test('browser executable lookup respects candidates and reports absence without starting a process', async () => {
  const seen = [];
  assert.equal(
    await chromeExecutable(['missing', 'fixture'], async (name) => {
      seen.push(name);
      if (name === 'missing') throw Error('absent');
    }),
    'fixture',
  );
  assert.deepEqual(seen, ['missing', 'fixture']);
  await assert.rejects(
    chromeExecutable([], async () => {}),
    /Chrome was not found/,
  );
  assert.equal(await chromeExecutable([process.execPath]), process.execPath);
});

test('desktop lifecycle creates a private profile and bounds startup, cleanup and repeated close', async () => {
  const { desktop, child, calls } = desktopFixture();
  let exits = 0;
  const browser = await startBrowserProcess(
    {
      headless: true,
      onExit: () => {
        exits++;
      },
    },
    desktop,
  );
  assert.equal(calls.prepared.credentials_enable_service, false);
  assert.equal(calls.prepared.profile.password_manager_enabled, false);
  assert.ok(calls.args.includes('--remote-debugging-pipe'));
  assert.ok(
    calls.args.every(
      (arg) =>
        !arg.startsWith('--remote-debugging-port') && !arg.startsWith('--remote-debugging-address'),
    ),
  );
  assert.deepEqual(calls.stdio, ['ignore', 'ignore', 'ignore', 'pipe', 'pipe']);
  assert.ok(calls.args.includes('--headless=new'));
  assert.equal(browser.profile, '/fixture/profile');
  child.emit('exit');
  assert.equal(exits, 1);
  await Promise.all([browser.close(), browser.close()]);
  assert.equal(calls.removed, 1);
  assert.equal(calls.closed, 1);
  assert.equal(exits, 1);
});

test('desktop connects the inherited child streams without discovery requests', async () => {
  const { desktop, child, calls, cdp } = desktopFixture();
  let connected;
  desktop.connect = (received) => {
    connected = received;
    return cdp;
  };
  const browser = await startBrowserProcess({}, desktop);
  assert.equal(connected, child);
  assert.ok(!calls.args.includes('--headless=new'));
  await browser.close();
});

test('profile preparation errors still remove the temporary directory', async () => {
  const { desktop, calls } = desktopFixture();
  desktop.writeFile = async () => {
    throw Error('cannot prepare');
  };
  await assert.rejects(startBrowserProcess({}, desktop), /cannot prepare/);
  assert.equal(calls.removed, 1);
});

test('startup failures release private channels, process and profile', async () => {
  for (const failure of ['spawn', 'exited', 'timeout', 'connection']) {
    const { desktop, calls, cdp, child } = desktopFixture();
    if (failure !== 'connection')
      desktop.connect = () => {
        cdp.initialize = () =>
          new Promise((_resolve, reject) =>
            queueMicrotask(() => {
              if (failure !== 'timeout') child.emit(failure === 'spawn' ? 'error' : 'exit');
              reject(Error('private channel closed'));
            }),
          );
        return cdp;
      };
    if (failure === 'connection')
      desktop.connect = () => {
        throw Error('private pipes missing');
      };
    await assert.rejects(startBrowserProcess({}, desktop));
    assert.equal(calls.removed, 1, failure);
  }
  const { desktop, calls, cdp } = desktopFixture();
  cdp.send = async () => {
    throw Error('closed already');
  };
  desktop.rm = async () => {
    calls.removed++;
    throw Error('best effort');
  };
  const browser = await startBrowserProcess({}, desktop);
  await browser.close();
  assert.equal(calls.closed, 1);
});
