import { FireplaceController } from './application/controller';
import { HassActionGateway } from './adapters/home-assistant/action-gateway';
import type { HomeAssistant } from './adapters/home-assistant/types';
import type { Bindings } from './domain/model';
export function composeController(
  hass: () => HomeAssistant | undefined,
  entities: Bindings,
  changed: () => void,
): FireplaceController {
  return new FireplaceController(new HassActionGateway(hass, entities), changed);
}
