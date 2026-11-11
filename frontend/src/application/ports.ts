import type { Command } from '../domain/model';
export interface ActionGateway {
  send(command: Command): Promise<void>;
}
