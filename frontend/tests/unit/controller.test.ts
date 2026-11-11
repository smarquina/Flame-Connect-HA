import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { FireplaceController } from '../../src/application/controller';
import { mapState } from '../../src/adapters/home-assistant/state-mapper';
import { config, fakeHass } from '../fixtures/state';

const snapshot = () => mapState(config, fakeHass());
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());
it('waits for confirmed readback rather than accepting a service response as confirmation', async () => {
  const send = vi.fn().mockResolvedValue(undefined);
  const changed = vi.fn();
  const controller = new FireplaceController({ send }, changed);
  const result = controller.execute(snapshot(), { kind: 'flame', value: false });
  await Promise.resolve();
  expect(controller.busy).toBe(true);
  controller.update(snapshot());
  expect(controller.busy).toBe(true);
  controller.update({ ...snapshot(), flame: false });
  await expect(result).resolves.toBeUndefined();
  expect(controller.busy).toBe(false);
  expect(changed).toHaveBeenCalledTimes(2);
  expect(vi.getTimerCount()).toBe(0);
});
it('does not send an already satisfied or invalid request', async () => {
  const send = vi.fn();
  const controller = new FireplaceController({ send }, vi.fn());
  await expect(
    controller.execute(snapshot(), { kind: 'flame', value: true }),
  ).resolves.toBeUndefined();
  await expect(controller.execute(snapshot(), { kind: 'temperature', value: NaN })).rejects.toThrow(
    'invalid_value',
  );
  expect(send).not.toHaveBeenCalled();
});
it('serializes commands and bounds a service that never settles', async () => {
  const controller = new FireplaceController({ send: () => new Promise(() => {}) }, vi.fn(), 100);
  const pending = controller.execute(snapshot(), { kind: 'flame', value: false });
  const assertion = expect(pending).rejects.toThrow('timeout');
  await expect(controller.execute(snapshot(), { kind: 'heating', value: false })).rejects.toThrow(
    'busy',
  );
  await vi.advanceTimersByTimeAsync(101);
  await assertion;
  expect(controller.busy).toBe(false);
});
it('reports errors without replaying commands or exposing service payloads', async () => {
  const send = vi.fn().mockRejectedValue(new Error('secret provider payload'));
  const controller = new FireplaceController({ send }, vi.fn());
  await expect(controller.execute(snapshot(), { kind: 'flame', value: false })).rejects.toThrow(
    /^failed$/,
  );
  expect(send).toHaveBeenCalledTimes(1);
  expect(vi.getTimerCount()).toBe(0);
});
it('cancels on teardown and ignores a late failure from a previous command', async () => {
  let rejectOld: (reason: Error) => void = () => {};
  const send = vi
    .fn()
    .mockImplementationOnce(
      () =>
        new Promise<void>((_, reject) => {
          rejectOld = reject;
        }),
    )
    .mockResolvedValue(undefined);
  const controller = new FireplaceController({ send }, vi.fn());
  const pending = controller.execute(snapshot(), { kind: 'flame', value: false });
  controller.dispose();
  await expect(pending).rejects.toThrow('unavailable');
  controller.dispose();
  controller.update(snapshot());
  const second = controller.execute(snapshot(), { kind: 'heating', value: false });
  rejectOld(new Error('late error'));
  await Promise.resolve();
  expect(controller.busy).toBe(true);
  controller.update({ ...snapshot(), heating: false });
  await expect(second).resolves.toBeUndefined();
});
