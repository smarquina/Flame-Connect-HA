/** @typedef {{send(method: string, params?: object): Promise<any>, on(name: string, listener: (params: any) => any): void}} CdpPort */

const CONNECTION_TIMEOUT_MS = 10000;
const COMMAND_TIMEOUT_MS = 15000;

export class CDP {
  /** @param {string} url */
  constructor(url) {
    const u = new URL(url);
    if (u.protocol !== 'ws:' || !['127.0.0.1', 'localhost'].includes(u.hostname))
      throw new Error('Chrome must use a loopback address.');
    this.socket = new WebSocket(url);
    this.pending = new Map();
    this.listeners = new Map();
    this.next = 0;
    /** @type {Promise<void>} */
    this.ready = new Promise((resolve, reject) => {
      const timer = setTimeout(
        () => reject(new Error('Chrome did not respond.')),
        CONNECTION_TIMEOUT_MS,
      );
      this.socket.addEventListener(
        'open',
        () => {
          clearTimeout(timer);
          resolve();
        },
        { once: true },
      );
      this.socket.addEventListener(
        'error',
        () => {
          clearTimeout(timer);
          reject(new Error('Could not connect to Chrome.'));
        },
        { once: true },
      );
    });
    this.socket.addEventListener('message', (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.id) {
        const p = this.pending.get(msg.id);
        if (!p) return;
        this.pending.delete(msg.id);
        clearTimeout(p.timer);
        if (msg.error) p.reject(new Error(`Chrome: ${msg.error.code}`));
        else p.resolve(msg.result);
      } else {
        for (const listener of this.listeners.get(msg.method) ?? [])
          Promise.resolve(listener(msg.params)).catch(() => {});
      }
    });
    this.socket.addEventListener('close', () => {
      for (const p of this.pending.values()) {
        clearTimeout(p.timer);
        p.reject(new Error('The login window was closed.'));
      }
      this.pending.clear();
    });
  }
  /** @param {string} method @param {object} params @returns {Promise<any>} */
  async send(method, params = {}) {
    await this.ready;
    if (this.socket.readyState !== WebSocket.OPEN) throw new Error('Chrome is closed.');
    const id = ++this.next;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Chrome did not respond to ${method}.`));
      }, COMMAND_TIMEOUT_MS);
      this.pending.set(id, { resolve, reject, timer });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }
  /** @param {string} name @param {(params: any) => any} listener */
  on(name, listener) {
    const list = this.listeners.get(name) ?? [];
    list.push(listener);
    this.listeners.set(name, list);
  }
  close() {
    this.socket.close();
  }
}
