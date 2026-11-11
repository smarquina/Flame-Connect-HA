import type { ActionGateway } from '../../application/ports';
import { ControlError, type Bindings, type Command, type EntityRole } from '../../domain/model';
import type { HomeAssistant } from './types';

export class HassActionGateway implements ActionGateway {
  constructor(
    private readonly getHass: () => HomeAssistant | undefined,
    private readonly entities: Bindings,
  ) {}
  async send(command: Command): Promise<void> {
    const hass = this.getHass();
    if (!hass) throw new ControlError('unavailable');
    const role: EntityRole =
      command.kind === 'heating' || command.kind === 'mode' || command.kind === 'temperature'
        ? 'climate'
        : command.kind;
    const entity = this.entities[role];
    if (!entity) throw new ControlError('unavailable');
    let domain: string;
    let service: string;
    let data: Record<string, unknown> = {};
    switch (command.kind) {
      case 'power':
      case 'flame':
        domain = command.kind === 'power' ? 'switch' : 'light';
        service = command.value ? 'turn_on' : 'turn_off';
        break;
      case 'heating':
        domain = 'climate';
        service = 'set_hvac_mode';
        data = { hvac_mode: command.value ? 'heat' : 'off' };
        break;
      case 'speed':
        domain = 'number';
        service = 'set_value';
        data = { value: command.value };
        break;
      case 'temperature':
        domain = 'climate';
        service = 'set_temperature';
        data = { temperature: command.value };
        break;
      case 'mode':
        domain = 'climate';
        service = 'set_preset_mode';
        data = { preset_mode: command.value };
        break;
      case 'color':
      case 'brightness':
        domain = 'select';
        service = 'select_option';
        data = { option: command.value };
    }
    await hass.callService(domain, service, data, { entity_id: entity });
  }
}
