import { test } from 'node:test';
import assert from 'node:assert/strict';
import { PassThrough, Writable } from 'node:stream';
import { CDP } from '../tools/link/cdp.mjs';

function pipeFixture({
  targets = [{ type: 'page', url: 'about:blank', targetId: 'page' }],
  session = 'fixture-session',
  respond,
} = {}) {
  const reader = new PassThrough();
  const commands = [];
  const reply = (message) => reader.write(JSON.stringify(message) + '\0');
  const writer = new Writable({
    write(chunk, _encoding, done) {
      const command = JSON.parse(chunk.toString().replace(/\0$/, ''));
      commands.push(command);
      queueMicrotask(() => {
        let result;
        if (command.method === 'Target.getTargets') result = { targetInfos: targets };
        else if (command.method === 'Target.createTarget') result = { targetId: 'created-page' };
        else if (command.method === 'Target.attachToTarget') result = { sessionId: session };
        else if (respond) {
          respond(command, reply);
          return;
        } else result = {};
        reply({
          id: command.id,
          result,
          ...(command.sessionId ? { sessionId: command.sessionId } : {}),
        });
      });
      done();
    },
  });
  return { reader, writer, commands, reply, cdp: new CDP(reader, writer) };
}

test('pipe startup attaches a page session; shutdown remains browser-scoped', async () => {
  const { cdp, commands } = pipeFixture();
  await cdp.ready;
  assert.deepEqual(commands[1].params, { targetId: 'page', flatten: true });
  await cdp.send('Page.enable');
  assert.equal(commands.at(-1).sessionId, 'fixture-session');
  await cdp.send('Browser.close');
  assert.equal(commands.at(-1).sessionId, undefined);
  cdp.close();
  cdp.close();
  await assert.rejects(cdp.send('Page.enable'), /closed/);
  const other = pipeFixture({ targets: [] });
  await other.cdp.ready;
  assert.equal(other.commands[1].method, 'Target.createTarget');
  assert.equal(other.commands[2].params.targetId, 'created-page');
  other.cdp.close();
});

test('fragmented UTF-8 frames and multiple messages preserve session isolation', async () => {
  const fixture = pipeFixture({
    respond: (command, reply) => {
      reply({ id: command.id, result: { value: 'wrong' }, sessionId: 'another-session' });
      const frame = Buffer.from(
        JSON.stringify({
          id: command.id,
          result: { value: 'temperatura 🔥' },
          sessionId: command.sessionId,
        }) + '\0',
      );
      const split = frame.indexOf(Buffer.from('🔥')) + 1;
      fixture.reader.write(frame.subarray(0, split));
      fixture.reader.write(frame.subarray(split));
    },
  });
  const { cdp, reader } = fixture;
  await cdp.ready;
  assert.deepEqual(await cdp.send('Runtime.evaluate'), { value: 'temperatura 🔥' });
  const received = [];
  cdp.on('Page.event', (value) => received.push(value));
  cdp.on('Page.event', () => {
    throw Error('listener failed');
  });
  reader.write(
    '\0' +
      JSON.stringify({ method: 'Page.event', sessionId: 'another-session', params: 'ignore' }) +
      '\0' +
      JSON.stringify({ method: 'Page.event', sessionId: 'fixture-session', params: 'first' }) +
      '\0' +
      JSON.stringify({ method: 'Page.event', sessionId: 'fixture-session', params: 'second' }) +
      '\0' +
      JSON.stringify({ id: 999, result: {} }) +
      '\0',
  );
  await Promise.resolve();
  assert.deepEqual(received, ['first', 'second']);
  cdp.close();
  cdp.receive(Buffer.from('ignored'));
});

test('protocol failures expose only numeric error codes', async () => {
  const { cdp } = pipeFixture({
    respond: (command, reply) =>
      reply({
        id: command.id,
        sessionId: command.sessionId,
        error: { code: -1, message: 'private-data' },
      }),
  });
  await cdp.ready;
  await assert.rejects(cdp.send('Runtime.evaluate'), (error) => error.message === 'Chrome: -1');
  cdp.close();
});

test('EOF, stream errors and write failures reject pending commands and close both descriptors', async () => {
  for (const event of [
    'end',
    'close',
    'reader-error',
    'writer-error',
    'write-throw',
    'write-callback',
  ]) {
    const { reader, writer, cdp } = pipeFixture({ respond: () => {} });
    await cdp.ready;
    if (event === 'write-throw')
      writer.write = () => {
        throw Error('private-error');
      };
    if (event === 'write-callback')
      writer.write = (_raw, callback) => callback(Error('private-error'));
    const pending = assert.rejects(cdp.send('Runtime.evaluate'), /closed/);
    await Promise.resolve();
    if (event === 'reader-error') reader.emit('error', Error('private-error'));
    else if (event === 'writer-error') writer.emit('error', Error('private-error'));
    else if (!event.startsWith('write-')) reader.emit(event);
    await pending;
    assert.equal(reader.destroyed, true);
    assert.equal(writer.destroyed, true);
  }
});

test('startup failure closes private pipes without trying a network fallback', async () => {
  for (const session of ['', null]) {
    const { cdp, reader, writer } = pipeFixture({ session });
    await assert.rejects(cdp.ready, /private Chrome channel/);
    assert.equal(reader.destroyed, true);
    assert.equal(writer.destroyed, true);
  }
  assert.throws(() => new CDP(null, null), /private debugging pipes/);
});

test('malformed and oversized pipe frames fail closed', async () => {
  for (const frame of [
    'not-json\0',
    'null\0',
    '[]\0',
    'x'.repeat(8 * 1024 * 1024 + 1),
    'x'.repeat(8 * 1024 * 1024 + 1) + '\0',
  ]) {
    const { reader, cdp } = pipeFixture();
    await cdp.ready;
    reader.write(frame);
    assert.equal(cdp.closed, true);
  }
});

test('command deadlines and startup EOF are bounded', async (context) => {
  const { cdp } = pipeFixture({ respond: () => {} });
  await cdp.ready;
  context.mock.timers.enable({ apis: ['setTimeout'] });
  const deadline = assert.rejects(cdp.send('Runtime.evaluate'), /did not respond/);
  await Promise.resolve();
  context.mock.timers.tick(15000);
  await deadline;
  assert.equal(cdp.pending.size, 0);
  cdp.close();
  context.mock.timers.reset();
  const early = pipeFixture();
  const failed = assert.rejects(early.cdp.ready, /private Chrome channel/);
  early.reader.emit('end');
  await failed;
});
