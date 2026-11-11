import {
  COMMAND_TIMEOUT_MS,
  ControlError,
  type Command,
  type FireplaceState,
} from '../domain/model';
import { isConfirmed, validateCommand } from '../domain/state';
import type { ActionGateway } from './ports';

interface Pending {
  command: Command;
  timer: ReturnType<typeof setTimeout>;
  resolve: () => void;
  reject: (error: ControlError) => void;
}

export class FireplaceController {
  private pending?: Pending;
  constructor(
    private readonly gateway: ActionGateway,
    private readonly changed: () => void,
    private readonly timeout = COMMAND_TIMEOUT_MS,
  ) {}
  get busy(): boolean {
    return this.pending !== undefined;
  }

  execute(state: FireplaceState, command: Command): Promise<void> {
    if (this.pending) return Promise.reject(new ControlError('busy'));
    try {
      validateCommand(state, command);
    } catch (error) {
      return Promise.reject(error);
    }
    if (isConfirmed(state, command)) return Promise.resolve();
    return new Promise<void>((resolve, reject) => {
      const pending: Pending = {
        command,
        resolve,
        reject,
        timer: setTimeout(() => this.finish(pending, 'timeout'), this.timeout),
      };
      this.pending = pending;
      this.changed();
      void this.gateway.send(command).catch(() => this.finish(pending, 'failed'));
    });
  }

  update(state: FireplaceState): void {
    if (this.pending && isConfirmed(state, this.pending.command)) this.finish(this.pending);
  }

  dispose(): void {
    if (this.pending) this.finish(this.pending, 'unavailable');
  }

  private finish(pending: Pending, error?: 'timeout' | 'failed' | 'unavailable'): void {
    if (this.pending !== pending) return;
    clearTimeout(pending.timer);
    this.pending = undefined;
    if (error) pending.reject(new ControlError(error));
    else pending.resolve();
    this.changed();
  }
}
