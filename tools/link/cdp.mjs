import { Buffer } from 'node:buffer';

/** @typedef {{send(method: string, params?: object): Promise<any>, on(name: string, listener: (params: any) => any): void}} CdpPort */

const COMMAND_TIMEOUT_MS = 15000;
const MAX_MESSAGE_BYTES = 8 * 1024 * 1024;

/** Chrome's private pipe addresses the browser; login events belong to one page session. */
export class CDP {
  pending = new Map();
  listeners = new Map();
  next = 0;
  closed = false;
  buffer = Buffer.alloc(0);
  /** @type {string | undefined} */
  sessionId;

  /** @param {import('node:stream').Readable} reader @param {import('node:stream').Writable} writer */
  constructor(reader, writer) {
    if (!reader || !writer || typeof reader.on !== 'function' || typeof writer.write !== 'function')
      throw new Error('Chrome did not provide private debugging pipes.');
    this.reader = reader;
    this.writer = writer;
    reader.on('data', (chunk) => this.receive(chunk));
    for (const event of ['end', 'close', 'error']) reader.on(event, () => this.close());
    for (const event of ['close', 'error']) writer.on(event, () => this.close());
    this.ready = this.attachPage().catch(() => {
      this.close();
      throw new Error('Could not connect to the private Chrome channel.');
    });
  }

  async attachPage() {
    const { targetInfos } = await this.request('Target.getTargets');
    const target = targetInfos.find(
      (/** @type {{type: string, url: string}} */ info) =>
        info.type === 'page' && info.url === 'about:blank',
    );
    const { targetId } =
      target ?? (await this.request('Target.createTarget', { url: 'about:blank' }));
    const { sessionId } = await this.request('Target.attachToTarget', { targetId, flatten: true });
    if (typeof sessionId !== 'string' || !sessionId) throw new Error('Invalid page session.');
    this.sessionId = sessionId;
  }

  /** @param {Buffer} chunk */
  receive(chunk) {
    if (this.closed) return;
    this.buffer = Buffer.concat([this.buffer, chunk]);
    let end;
    while ((end = this.buffer.indexOf(0)) !== -1) {
      if (end > MAX_MESSAGE_BYTES) return this.close();
      const frame = this.buffer.subarray(0, end);
      this.buffer = this.buffer.subarray(end + 1);
      if (!frame.length) continue;
      let message;
      try {
        message = JSON.parse(frame.toString('utf8'));
        if (!message || typeof message !== 'object' || Array.isArray(message)) throw new Error();
      } catch {
        return this.close();
      }
      this.dispatch(message);
    }
    if (this.buffer.length > MAX_MESSAGE_BYTES) this.close();
  }

  /** @param {any} message */
  dispatch(message) {
    if (message.id) {
      const pending = this.pending.get(message.id);
      if (!pending || message.sessionId !== pending.sessionId) return;
      this.pending.delete(message.id);
      clearTimeout(pending.timer);
      if (message.error) pending.reject(new Error(`Chrome: ${message.error.code}`));
      else pending.resolve(message.result);
    } else if (this.sessionId && message.sessionId === this.sessionId) {
      for (const listener of this.listeners.get(message.method) ?? [])
        Promise.resolve()
          .then(() => listener(message.params))
          .catch(() => {});
    }
  }

  /** @param {string} method @param {object} params @param {string | undefined} sessionId @returns {Promise<any>} */
  request(method, params = {}, sessionId = undefined) {
    if (this.closed) return Promise.reject(new Error('Chrome is closed.'));
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Chrome did not respond to ${method}.`));
      }, COMMAND_TIMEOUT_MS);
      this.pending.set(id, { resolve, reject, timer, sessionId });
      try {
        this.writer.write(JSON.stringify({ id, method, params, sessionId }) + '\0', (error) => {
          if (error) this.close();
        });
      } catch {
        this.close();
      }
    });
  }

  /** @param {string} method @param {object} params @returns {Promise<any>} */
  async send(method, params = {}) {
    // Shutdown must work even if target attachment failed or is still pending.
    if (method === 'Browser.close') return this.request(method, params);
    await this.ready;
    return this.request(method, params, this.sessionId);
  }

  /** @param {string} name @param {(params: any) => any} listener */
  on(name, listener) {
    const list = this.listeners.get(name) ?? [];
    list.push(listener);
    this.listeners.set(name, list);
  }

  close() {
    if (this.closed) return;
    this.closed = true;
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(new Error('The login window was closed.'));
    }
    this.pending.clear();
    this.listeners.clear();
    this.buffer = Buffer.alloc(0);
    this.reader.destroy();
    this.writer.destroy();
  }
}
