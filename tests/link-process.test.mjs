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
  const calls = { removed: 0, closed: 0, reads: 0, prepared: null, args: [] };
  const cdp = {
    ready: Promise.resolve(),
    send: async () => {},
    close: () => {
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
    spawn: (_executable, args) => {
      calls.args = args;
      return child;
    },
    readFile: async () => {
      calls.reads++;
      return '12345\n/socket';
    },
    rm: async () => {
      calls.removed++;
    },
    wait: async () => {},
    connect: () => cdp,
    fetch: async (url, options) => {
      assert.equal(url, 'http://127.0.0.1:12345/json/list');
      assert.ok(options.signal);
      return {
        json: async () => [
          { type: 'page', url: 'about:blank', webSocketDebuggerUrl: 'ws://127.0.0.1/socket' },
        ],
      };
    },
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
  assert.ok(calls.args.includes('--remote-debugging-address=127.0.0.1'));
  assert.ok(calls.args.includes('--headless=new'));
  assert.equal(browser.profile, '/fixture/profile');
  child.emit('exit');
  assert.equal(exits, 1);
  await Promise.all([browser.close(), browser.close()]);
  assert.equal(calls.removed, 1);
  assert.equal(calls.closed, 1);
  assert.equal(exits, 1);
});

test('desktop waits for the private port file and continues after an incomplete file', async () => {
  const { desktop, calls } = desktopFixture();
  let reads = 0;
  desktop.readFile = async () => {
    if (++reads === 1) throw Error('not ready');
    return reads === 2 ? '0' : '12345\n/socket';
  };
  const browser = await startBrowserProcess({}, desktop);
  assert.equal(reads, 3);
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

test('startup failures release the profile and process without exposing provider responses', async () => {
  for (const failure of ['spawn', 'exited', 'timeout', 'target', 'connection', 'discovery']) {
    const { desktop, calls, cdp, child } = desktopFixture();
    if (failure === 'spawn')
      desktop.spawn = () => {
        queueMicrotask(() => child.emit('error'));
        return child;
      };
    if (failure === 'spawn')
      desktop.readFile = async () => {
        throw Error('not ready');
      };
    if (failure === 'exited') child.exitCode = 1;
    if (failure === 'timeout') desktop.readFile = async () => '65536';
    if (failure === 'target') desktop.fetch = async () => ({ json: async () => [] });
    if (failure === 'connection')
      cdp.send = async () => {
        throw Error('cannot close socket');
      };
    if (failure === 'connection')
      desktop.connect = () => {
        throw Error('connection failed');
      };
    if (failure === 'discovery')
      desktop.fetch = async () => {
        throw Error('discovery failed');
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
