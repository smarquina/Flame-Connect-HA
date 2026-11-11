export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
}
export interface RegistryEntry {
  entity_id: string;
  unique_id: string;
  platform: string;
  device_id: string | null;
  disabled_by: string | null;
  name?: string | null;
  original_name?: string | null;
}
export interface HomeAssistant {
  states: Record<string, HassEntity | undefined>;
  language: string;
  locale?: { language?: string };
  config?: { unit_system?: { temperature?: string } };
  callService(
    domain: string,
    service: string,
    data: Record<string, unknown>,
    target: { entity_id: string },
  ): Promise<unknown>;
  callWS<T>(message: { type: string }): Promise<T>;
}
