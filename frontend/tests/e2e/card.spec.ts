import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import type { FlameConnectCard } from '../../src/presentation/card';
import { CARD_TYPE } from '../../src/domain/model';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Living room', exact: true })).toBeVisible();
});

test('compiled HACS module loads with embedded artwork and sends actions', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/tests/fixtures/production.html');
  await expect(page.getByRole('heading', { name: 'Living room', exact: true })).toBeVisible();
  await expect(page.getByRole('img')).toHaveCSS('background-image', /data:image\/png;base64/);
  await page.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Flame · Off', exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test('renders the four supplied fireplace states and a neutral unknown state', async ({
  page,
}, info) => {
  const scene = page.getByRole('img');
  for (const [heat, flame, position] of [
    [false, false, '0% 0%'],
    [false, true, '100% 0%'],
    [true, false, '0% 100%'],
    [true, true, '100% 100%'],
  ] as const) {
    await page.evaluate(
      ({ heat, flame }) => {
        window.demo.hass.states['climate.fire_heating']!.state = heat ? 'heat' : 'off';
        window.demo.hass.states['light.fire_flame']!.state = flame ? 'on' : 'off';
        window.demo.update();
      },
      { heat, flame },
    );
    await expect(scene).toHaveCSS('background-position', position);
    await expect(scene).toHaveCSS('background-image', /data:image\/png;base64/);
  }
  await page
    .locator('flame-connect-card')
    .screenshot({ path: `test-results/card-${info.project.name}.png` });
  await page.evaluate(() => {
    window.demo.hass.states['light.fire_flame']!.state = 'unavailable';
    window.demo.update();
  });
  await expect(scene).toHaveAccessibleName(/State unavailable/);
  await expect(scene.locator('svg')).toBeVisible();
  await expect(scene).toHaveCSS('background-image', 'none');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('controls flame and heating independently and reflects external updates', async ({ page }) => {
  await page.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Flame · Off', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heating · On', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Heating · On', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Heating · Off', exact: true })).toBeVisible();
  const calls = await page.evaluate(() => window.demo.calls);
  expect(calls).toEqual([
    { domain: 'light', service: 'turn_off', data: {}, target: { entity_id: 'light.fire_flame' } },
    {
      domain: 'climate',
      service: 'set_hvac_mode',
      data: { hvac_mode: 'off' },
      target: { entity_id: 'climate.fire_heating' },
    },
  ]);
  await page.evaluate(() => {
    window.demo.hass.states['light.fire_flame']!.state = 'on';
    window.demo.update();
  });
  await expect(page.getByRole('button', { name: 'Flame · On', exact: true })).toBeVisible();
});

test('keeps room and target temperatures independent and validates bounds', async ({ page }) => {
  await expect(page.getByText('19.5 °C', { exact: true })).toBeVisible();
  await page.getByRole('slider', { name: 'Target temperature', exact: true }).press('ArrowRight');
  await expect(page.getByRole('slider', { name: 'Target temperature', exact: true })).toHaveValue(
    '22.5',
  );
  await expect(page.getByText('19.5 °C', { exact: true })).toBeVisible();
  const slider = page.getByRole('slider', { name: 'Target temperature', exact: true });
  await slider.press('End');
  await expect(slider).toHaveValue('30');
  await slider.press('Home');
  await expect(slider).toHaveValue('15');
  await slider.press('ArrowLeft');
  await expect(slider).toHaveValue('15');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(3);
});

test('reads preset/color/brightness options and sends supported discrete selections', async ({
  page,
}) => {
  await page
    .getByRole('combobox', { name: 'Heating / fan mode', exact: true })
    .selectOption('fan_only');
  await expect(page.getByRole('button', { name: 'Ventilation · On' })).toBeVisible();
  await expect(page.getByRole('img')).toHaveCSS('background-position', '100% 0%');
  await page.getByRole('combobox', { name: 'Flame color' }).selectOption('blue');
  await page.getByRole('combobox', { name: 'Flame brightness' }).selectOption('flicker_low');
  await expect(page.getByRole('combobox', { name: 'Flame color' })).toHaveValue('blue');
  await expect(page.getByRole('combobox', { name: 'Flame brightness' })).toHaveValue('flicker_low');
  await expect(
    page.getByRole('combobox', { name: 'Heating / fan mode', exact: true }).locator('option'),
  ).toHaveCount(3);
});

test('shows English and Spanish according to Home Assistant language', async ({ page }) => {
  await page.evaluate(() => {
    window.demo.hass.language = 'es';
    window.demo.update();
  });
  await expect(page.getByRole('button', { name: 'Llama · Encendido' })).toBeVisible();
  await expect(
    page.getByRole('slider', { name: 'Temperatura objetivo', exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Brillo de llama' })).toBeVisible();
  await expect(page.getByRole('slider', { name: 'Velocidad de llama', exact: true })).toBeVisible();
  await expect(page.getByText('19,5 °C', { exact: true })).toBeVisible();
  await page.evaluate(() => {
    window.demo.hass.language = 'en';
    window.demo.update();
  });
  await expect(page.getByRole('button', { name: 'Flame · On', exact: true })).toBeVisible();
});

test('does not equate service acceptance with device confirmation or replay commands', async ({
  page,
}) => {
  await page.evaluate(() => {
    window.demo.defer = true;
  });
  await page.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(page.locator('.feedback')).toBeVisible();
  await expect(page.locator('.feedback')).toHaveAttribute('title', 'Waiting for confirmed state…');
  await expect(page.getByRole('button', { name: 'Flame · On', exact: true })).toBeDisabled();
  await page.evaluate(() => {
    window.demo.hass.states['light.fire_flame']!.state = 'off';
    window.demo.update();
  });
  await expect(page.getByText('Waiting for confirmed state…')).toHaveCount(0);
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
});

test('service errors are redacted and do not change confirmed state', async ({ page }) => {
  await page.evaluate(() => {
    window.demo.fail = true;
  });
  await page.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('The action failed');
  await expect(page.getByRole('button', { name: 'Flame · On', exact: true })).toBeEnabled();
  await expect(page.getByRole('alert')).not.toContainText('Synthetic');
});

test('standby never implicitly enables power when clicking a flame control', async ({ page }) => {
  await page.evaluate(() => {
    window.demo.hass.states['switch.fire_power']!.state = 'off';
    window.demo.hass.states['light.fire_flame']!.state = 'off';
    window.demo.update();
  });
  await expect(page.getByRole('button', { name: 'Flame · Off', exact: true })).toBeDisabled();
  await expect(page.getByRole('img')).toHaveAccessibleName(/Standby/);
  await expect(page.getByRole('button', { name: 'Turn fireplace on', exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('preview sends no commands and multiple cards share confirmed updates', async ({ page }) => {
  await page.evaluate(() => {
    const card = window.demo.add('Second fireplace');
    card.preview = true;
    card.requestUpdate();
  });
  const second = page.locator('flame-connect-card').nth(1);
  await expect(second.getByRole('button', { name: 'Flame · On', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Flame · On', exact: true }).first().click();
  await expect(second.getByRole('button', { name: 'Flame · Off', exact: true })).toBeVisible();
});

test('editor supports registry discovery, external sensors and safe image configuration', async ({
  page,
}) => {
  await page.evaluate(async () => {
    const ctor = customElements.get('flame-connect-card') as unknown as {
      getConfigElement(): Promise<HTMLElement>;
    };
    const editor = (await ctor.getConfigElement()) as HTMLElement & {
      hass: typeof window.demo.hass;
      setConfig(config: unknown): void;
    };
    editor.setConfig({ type: 'custom:flame-connect-card', entities: {} });
    editor.hass = window.demo.hass;
    document.body.append(editor);
    editor.addEventListener('config-changed', (event) => {
      const card = document.querySelector('flame-connect-card') as FlameConnectCard;
      card.setConfig((event as CustomEvent).detail.config);
      card.hass = window.demo.hass;
    });
  });
  const editor = page.locator('flame-connect-card-editor');
  await editor
    .getByRole('combobox', { name: 'Choose a Flame Connect fireplace' })
    .selectOption('fire-device');
  await editor
    .getByRole('combobox', { name: 'Room temperature', exact: true })
    .selectOption('sensor.room_temperature');
  await editor.getByRole('textbox', { name: 'Card title' }).fill('My fireplace');
  await editor.getByRole('textbox', { name: 'Card title' }).press('Tab');
  await expect(page.getByRole('heading', { name: 'My fireplace' })).toBeVisible();
  await editor.locator('summary').click();
  await editor
    .getByRole('textbox', { name: 'Image: effects off', exact: true })
    .fill('https://untrusted.test/test.png');
  await editor.getByRole('textbox', { name: 'Image: effects off', exact: true }).press('Tab');
  await expect(editor.getByRole('alert')).toContainText('Invalid configuration: images');
});

test('supports keyboard navigation, responsive layout and accessible controls', async ({
  page,
}) => {
  const results = await new AxeBuilder({ page }).include('flame-connect-card').analyze();
  expect(results.violations).toEqual([]);
  await page.getByRole('button', { name: 'Flame · On', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'Flame · Off', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(
    true,
  );
});

test('renders untrusted names as text and uses only safe custom images', async ({ page }) => {
  await page.evaluate((type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      name: '<img src=x onerror=alert(1)>',
      entities: { flame: 'light.fire_flame' },
      images: { flame: '/src/assets/fireplaces.png' },
    });
    card.hass = window.demo.hass;
  }, CARD_TYPE);
  await expect(page.getByRole('heading', { name: '<img src=x onerror=alert(1)>' })).toBeVisible();
  expect(await page.locator('flame-connect-card').locator('img').count()).toBe(0);
  await expect(page.getByRole('img')).toHaveCSS('background-size', 'contain');
});

test('supports the dark theme without losing contrast or keyboard controls', async ({ page }) => {
  await page.evaluate(() => {
    const card = document.querySelector('flame-connect-card') as HTMLElement;
    const variables = {
      '--primary-text-color': '#f4f4f4',
      '--secondary-text-color': '#ccc',
      '--card-background-color': '#202020',
      '--ha-card-background': '#202020',
      '--divider-color': '#999',
      '--primary-color': '#9b4215',
      '--text-primary-color': '#fff',
    };
    for (const [name, value] of Object.entries(variables)) card.style.setProperty(name, value);
  });
  expect(
    (await new AxeBuilder({ page }).include('flame-connect-card').analyze()).violations,
  ).toEqual([]);
  await expect(page.getByRole('slider', { name: 'Target temperature', exact: true })).toBeEnabled();
});

test('groups icon-only actions and switches the power icon between start and shutdown', async ({
  page,
}, info) => {
  const group = page.getByRole('group', { name: 'Fireplace controls' });
  await expect(group.getByRole('button')).toHaveCount(3);
  const shutdown = group.getByRole('button', { name: 'Turn fireplace off', exact: true });
  const shutdownPath = await shutdown.locator('path').getAttribute('d');
  for (const control of await group.getByRole('button').all()) {
    expect((await control.innerText()).trim()).toBe('');
    await expect(control.locator('svg')).toBeVisible();
    const box = await control.boundingBox();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);
  }
  await shutdown.click();
  const start = group.getByRole('button', { name: 'Turn fireplace on', exact: true });
  await expect(start).toBeEnabled();
  expect(await start.locator('path').getAttribute('d')).not.toBe(shutdownPath);
  await start.click();
  await expect(shutdown).toBeEnabled();
  expect(await page.evaluate(() => window.demo.calls)).toEqual([
    { domain: 'switch', service: 'turn_off', data: {}, target: { entity_id: 'switch.fire_power' } },
    { domain: 'switch', service: 'turn_on', data: {}, target: { entity_id: 'switch.fire_power' } },
  ]);
  await expect(page.locator('flame-connect-card .hint')).toHaveCount(0);
  await page
    .locator('flame-connect-card')
    .screenshot({ path: `test-results/icon-controls-${info.project.name}.png` });
});

test('visual editor hides the target independently while heating remains controllable', async ({
  page,
}) => {
  await page.evaluate((type) => {
    const ctor = customElements.get('flame-connect-card') as unknown as {
      getConfigElement(): HTMLElement;
    };
    const editor = ctor.getConfigElement() as HTMLElement & {
      hass: typeof window.demo.hass;
      setConfig(config: unknown): void;
    };
    editor.setConfig({
      type,
      entities: {
        climate: 'climate.fire_heating',
        flame: 'light.fire_flame',
        ambient: 'sensor.room_temperature',
        speed: 'number.fire_speed',
      },
    });
    editor.hass = window.demo.hass;
    editor.addEventListener('config-changed', (event) => {
      const card = document.querySelector('flame-connect-card') as FlameConnectCard;
      card.setConfig((event as CustomEvent).detail.config);
      card.hass = window.demo.hass;
    });
    document.body.append(editor);
  }, CARD_TYPE);
  const editor = page.locator('flame-connect-card-editor');
  const scene = page.locator('flame-connect-card .scene');
  await editor.getByLabel('Background color', { exact: true }).fill('#ffffff');
  await expect(scene).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  await editor
    .getByRole('combobox', { name: 'Background style', exact: true })
    .selectOption('none');
  await expect(scene).toHaveCSS('background-color', 'rgba(0, 0, 0, 0)');
  await expect(editor.getByLabel('Background color', { exact: true })).toBeDisabled();
  await editor
    .getByRole('combobox', { name: 'Background style', exact: true })
    .selectOption('color');
  await expect(scene).toHaveCSS('background-color', 'rgb(0, 0, 0)');
  await editor.getByLabel('Background color', { exact: true }).fill('#2155aa');
  await expect(scene).toHaveCSS('background-color', 'rgb(33, 85, 170)');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
  await editor.getByRole('button', { name: 'Move down: Target temperature', exact: true }).click();
  expect(
    await page
      .locator('flame-connect-card [data-control]')
      .evaluateAll((elements) => elements.map((element) => element.getAttribute('data-control'))),
  ).toEqual(['ambient', 'mode', 'target', 'speed']);
  await editor.getByRole('checkbox', { name: 'Show target temperature', exact: true }).uncheck();
  await expect(page.getByRole('slider', { name: 'Target temperature', exact: true })).toHaveCount(
    0,
  );
  await expect(page.getByText('19.5 °C', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Heating · On', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Heating · Off', exact: true })).toBeVisible();
  await editor.getByRole('checkbox', { name: 'Show room temperature', exact: true }).uncheck();
  await expect(page.locator('flame-connect-card [data-control=ambient]')).toHaveCount(0);
  await editor.getByRole('checkbox', { name: 'Show heating / fan mode', exact: true }).uncheck();
  await editor.getByRole('checkbox', { name: 'Show flame speed', exact: true }).uncheck();
  await expect(page.locator('flame-connect-card .settings')).toBeHidden();
  await editor.getByRole('checkbox', { name: 'Show flame control', exact: true }).uncheck();
  await editor.getByRole('checkbox', { name: 'Show heating control', exact: true }).uncheck();
  await expect(page.locator('flame-connect-card .toggles')).toBeHidden();
  await editor.getByRole('checkbox', { name: 'Show target temperature', exact: true }).check();
  await expect(page.getByRole('slider', { name: 'Target temperature', exact: true })).toHaveValue(
    '22',
  );
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
});

test('temperature slider commits once per drag and displays confirmed readback', async ({
  page,
}) => {
  await page.evaluate(() => {
    window.demo.defer = true;
  });
  const slider = page.getByRole('slider', { name: 'Target temperature', exact: true });
  const box = (await slider.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.45, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2, { steps: 8 });
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
  await expect(page.locator('flame-connect-card .target-value')).toHaveText('22 °C');
  const requested = await slider.inputValue();
  await page.mouse.up();
  await expect(slider).toBeDisabled();
  await expect(slider).toHaveValue('22');
  await expect(page.locator('flame-connect-card .target-value')).toHaveText('22 °C');
  const calls = await page.evaluate(() => window.demo.calls);
  expect(calls).toHaveLength(1);
  expect(calls[0]).toMatchObject({
    domain: 'climate',
    service: 'set_temperature',
    data: { temperature: Number(requested) },
    target: { entity_id: 'climate.fire_heating' },
  });
  await page.evaluate((temperature) => {
    window.demo.hass.states['climate.fire_heating']!.attributes.temperature = temperature;
    window.demo.update();
  }, Number(requested));
  await expect(slider).toBeEnabled();
  await expect(slider).toHaveValue(requested);
  await expect(page.getByText('19.5 °C', { exact: true })).toBeVisible();
});

test('flame speed slider commits once per drag, tracks readback and never changes other effects', async ({
  page,
}) => {
  await page.evaluate(() => {
    window.demo.defer = true;
  });
  const slider = page.getByRole('slider', { name: 'Flame speed', exact: true });
  await expect(slider).toHaveValue('3');
  await expect(slider).toHaveAttribute('min', '1');
  await expect(slider).toHaveAttribute('max', '5');
  await expect(slider).toHaveAttribute('step', '1');
  await slider.scrollIntoViewIfNeeded();
  const box = (await slider.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.5, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height / 2, { steps: 8 });
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
  const requested = await slider.inputValue();
  expect(requested).not.toBe('3');
  await expect(page.locator('flame-connect-card .speed-value')).toHaveText('3');
  await page.mouse.up();
  await expect(slider).toBeDisabled();
  await expect(slider).toHaveValue('3');
  expect(await page.evaluate(() => window.demo.calls)).toEqual([
    {
      domain: 'number',
      service: 'set_value',
      data: { value: Number(requested) },
      target: { entity_id: 'number.fire_speed' },
    },
  ]);
  await page.evaluate((value) => {
    window.demo.hass.states['number.fire_speed']!.state = value;
    window.demo.defer = false;
    window.demo.update();
  }, requested);
  await expect(slider).toBeEnabled();
  await expect(slider).toHaveValue(requested);
  await slider.press('End');
  await expect(slider).toHaveValue('5');
  await slider.press('Home');
  await expect(slider).toHaveValue('1');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(3);
  await expect(page.getByRole('button', { name: 'Flame · On', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Heating · On', exact: true })).toBeVisible();
  await expect(page.getByRole('combobox', { name: 'Flame brightness' })).toHaveValue('high');
  await expect(page.getByRole('slider', { name: 'Target temperature', exact: true })).toHaveValue(
    '22',
  );
  await page.evaluate(() => {
    window.demo.hass.states['number.fire_speed']!.state = 'unavailable';
    window.demo.update();
  });
  await expect(slider).toBeDisabled();
  await expect(page.locator('flame-connect-card .speed-value')).toHaveText('—');
});

test('compact and expanded views share controls, readback and hidden preferences', async ({
  page,
}, info) => {
  await page.evaluate((type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      entities: {
        flame: 'light.fire_flame',
        climate: 'climate.fire_heating',
        ambient: 'sensor.room_temperature',
      },
      initial_view: 'compact',
      compact_controls: ['ambient', 'target'],
      show_target: false,
    });
    card.hass = window.demo.hass;
    window.demo.defer = true;
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  await expect(card.locator('ha-card')).toHaveAttribute('data-view', 'compact');
  await expect(card.getByRole('img')).toHaveCount(0);
  await expect(card.getByText('19.5 °C', { exact: true })).toBeVisible();
  await expect(card.getByRole('slider', { name: 'Target temperature' })).toHaveCount(0);
  await expect(card.locator('[data-status=flame]')).toHaveAttribute('data-state', 'on');
  await card.screenshot({ path: `test-results/compact-${info.project.name}.png` });
  await card.getByRole('button', { name: 'Flame · On', exact: true }).click();
  const expand = card.getByRole('button', { name: 'Expand controls', exact: true });
  await expand.focus();
  await page.keyboard.press('Enter');
  await expect(card.getByRole('button', { name: 'Collapse controls' })).toBeFocused();
  await expect(card.getByRole('img')).toBeVisible();
  await expect(card.getByRole('button', { name: 'Flame · On', exact: true })).toBeDisabled();
  await expect(card.getByRole('slider', { name: 'Target temperature' })).toHaveCount(0);
  await card.getByRole('button', { name: 'Collapse controls' }).click();
  await page.evaluate(() => {
    window.demo.hass.states['light.fire_flame']!.state = 'off';
    window.demo.update();
  });
  await expect(card.getByRole('button', { name: 'Flame · Off', exact: true })).toBeEnabled();
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
  await page.evaluate(() => {
    window.demo.hass.states['climate.fire_heating']!.state = 'unavailable';
    window.demo.update();
  });
  await expect(card.locator('[data-status=heating]')).toHaveAttribute('data-state', 'unknown');
  expect(
    (await new AxeBuilder({ page }).include('flame-connect-card').analyze()).violations,
  ).toEqual([]);
});

test('editor configures compact selection without commands and card instances expand independently', async ({
  page,
}) => {
  await page.evaluate(() => {
    window.demo.add('Second fireplace');
  });
  const first = page.locator('flame-connect-card').first();
  const second = page.locator('flame-connect-card').nth(1);
  await first.getByRole('button', { name: 'Collapse controls' }).click();
  await expect(first.locator('ha-card')).toHaveAttribute('data-view', 'compact');
  await expect(second.locator('ha-card')).toHaveAttribute('data-view', 'expanded');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('visual editor can retry registry discovery after a transient failure', async ({ page }) => {
  await page.evaluate(() => {
    const ctor = customElements.get('flame-connect-card') as unknown as {
      getConfigElement(): HTMLElement;
    };
    const editor = ctor.getConfigElement() as HTMLElement & {
      hass: typeof window.demo.hass;
      setConfig(config: unknown): void;
    };
    window.demo.hass.callWS = async () => {
      throw new Error('Temporary registry failure');
    };
    editor.setConfig({
      type: 'custom:flame-connect-card',
      entities: { flame: 'light.fire_flame' },
    });
    editor.hass = window.demo.hass;
    document.body.append(editor);
  });
  const editor = page.locator('flame-connect-card-editor');
  await expect(editor.getByRole('status')).toContainText('Automatic discovery is unavailable');
  await page.evaluate(() => {
    window.demo.hass.callWS = async <T>() => [] as T;
  });
  await editor.getByRole('button', { name: 'Refresh fireplaces', exact: true }).click();
  await expect(editor.getByRole('status')).toHaveCount(0);
  await expect(
    editor.getByRole('button', { name: 'Refresh fireplaces', exact: true }),
  ).toBeEnabled();
  await expect(editor.getByRole('combobox', { name: 'Flame', exact: true })).toHaveValue(
    'light.fire_flame',
  );
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('chip provides independent quick actions and keyboard expansion', async ({ page }, info) => {
  await page.evaluate((type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      initial_view: 'compact',
      compact_style: 'chip',
      chip_expansion: 'inline',
      entities: { flame: 'light.fire_flame', climate: 'climate.fire_heating' },
    });
    card.hass = window.demo.hass;
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  await expect(card.locator('ha-card')).toHaveAttribute('data-view', 'chip');
  await expect(card.locator('.chip-icon')).toHaveAttribute('data-active', 'true');
  await card.screenshot({ path: `test-results/chip-${info.project.name}.png` });
  await card.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(card.locator('ha-card')).toHaveAttribute('data-view', 'chip');
  await expect(card.getByRole('button', { name: 'Flame · Off', exact: true })).toBeEnabled();
  await expect(card.getByRole('button', { name: 'Heating · On', exact: true })).toBeEnabled();
  await card.getByRole('button', { name: /Expand controls:/ }).focus();
  await page.keyboard.press('Enter');
  await expect(card.locator('ha-card')).toHaveAttribute('data-view', 'expanded');
  await expect(card.getByRole('button', { name: 'Collapse controls' })).toBeFocused();
  await card.getByRole('button', { name: 'Collapse controls' }).click();
  await expect(card.locator('ha-card')).toHaveAttribute('data-view', 'chip');
  expect(
    (await new AxeBuilder({ page }).include('flame-connect-card').analyze()).violations,
  ).toEqual([]);
});

test('chip opens a native modal by default, keeps its panel size and restores keyboard focus', async ({
  page,
}, info) => {
  await page.evaluate((type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      initial_view: 'compact',
      compact_style: 'chip',
      entities: { flame: 'light.fire_flame', climate: 'climate.fire_heating' },
    });
    card.hass = window.demo.hass;
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  const summary = card.getByRole('button', { name: /Expand controls:/ });
  await expect(summary).toHaveAttribute('aria-haspopup', 'dialog');
  const before = await card.boundingBox();
  expect(before!.height).toBeLessThanOrEqual(60);
  await expect(card.locator('.chip-text strong')).toHaveCSS('font-size', '14px');
  await expect(card.locator('.chip-text > span')).toHaveCSS('font-size', '12px');
  await expect(card.locator('.chip-icon')).toHaveCSS('width', '36px');
  await card.screenshot({ path: `test-results/chip-modal-summary-${info.project.name}.png` });
  await summary.focus();
  await page.keyboard.press('Enter');
  const dialog = card.getByRole('dialog', { name: 'Fireplace controls' });
  await expect(dialog).toBeVisible();
  expect((await card.boundingBox())!.height).toBe(before!.height);
  await expect(dialog.getByRole('button', { name: 'Close controls' })).toBeFocused();
  await dialog.screenshot({ path: `test-results/chip-modal-details-${info.project.name}.png` });
  expect(
    (await new AxeBuilder({ page }).include('flame-connect-card').analyze()).violations,
  ).toEqual([]);
  await page.keyboard.press('Escape');
  await expect(dialog).not.toBeVisible();
  await expect(summary).toBeFocused();
  await summary.click();
  await expect(dialog).toBeVisible();
  await page.mouse.click(1, 1);
  await expect(dialog).not.toBeVisible();
  await expect(summary).toBeFocused();
  await summary.click();
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Close controls' }).click();
  await expect(dialog).not.toBeVisible();
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('modal shares pending commands and external readback with chip actions', async ({ page }) => {
  await page.evaluate((type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      initial_view: 'compact',
      compact_style: 'chip',
      entities: { flame: 'light.fire_flame', climate: 'climate.fire_heating' },
    });
    card.hass = window.demo.hass;
    window.demo.defer = true;
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  await card.getByRole('button', { name: 'Flame · On', exact: true }).click();
  await expect(card.getByRole('dialog')).not.toBeVisible();
  await card.getByRole('button', { name: /Expand controls:/ }).click();
  const dialog = card.getByRole('dialog');
  await expect(dialog.getByRole('button', { name: 'Heating · On', exact: true })).toBeDisabled();
  await page.evaluate(() => {
    window.demo.hass.states['light.fire_flame']!.state = 'off';
    window.demo.update();
  });
  await expect(dialog.getByRole('button', { name: 'Flame · Off', exact: true })).toBeEnabled();
  await dialog.getByRole('button', { name: 'Close controls' }).click();
  await expect(card.getByRole('button', { name: 'Flame · Off', exact: true })).toBeEnabled();
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
});

test('visual editor preserves card-mod CSS and nested options for the HA wrapper', async ({
  page,
}) => {
  const cardMod = {
    style: {
      '.': 'ha-card { --ha-card-background: #194438; }',
      'ha-icon $': { svg: 'path { stroke-width: 2; }' },
    },
    class: ['fireplace', 'living-room'],
    debug: true,
    prepend: false,
  };
  await page.evaluate((card_mod) => {
    const card = document.querySelector('flame-connect-card') as unknown as {
      config: Record<string, unknown>;
      setConfig(config: unknown): void;
    };
    const initial = { ...card.config, card_mod };
    card.setConfig(initial);
    const editor = document.createElement('flame-connect-card-editor') as HTMLElement & {
      hass: typeof window.demo.hass;
      setConfig(config: unknown): void;
    };
    editor.setConfig(initial);
    editor.hass = window.demo.hass;
    document.body.append(editor);
    editor.addEventListener('config-changed', (event) =>
      card.setConfig((event as CustomEvent).detail.config),
    );
  }, cardMod);
  const editor = page.locator('flame-connect-card-editor');
  await editor.getByRole('combobox', { name: 'Compact style' }).selectOption('chip');
  await expect
    .poll(async () =>
      page.evaluate(() => {
        const card = document.querySelector('flame-connect-card') as unknown as {
          config: Record<string, unknown>;
        };
        return card.config.card_mod;
      }),
    )
    .toEqual(cardMod);
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(0);
});

test('Mushroom chip background variables style each action in the chip and modal', async ({
  page,
}) => {
  await page.evaluate(async (type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      initial_view: 'compact',
      compact_style: 'chip',
      entities: { flame: 'light.fire_flame', climate: 'climate.fire_heating' },
      card_mod: {
        style:
          'ha-card { --chip-background: rgb(12, 60, 90); --fireplace-action-color: rgb(250, 240, 230); } .toggles [data-action="flame"] { --fireplace-action-active-background: rgb(140, 30, 40); }',
      },
    });
    card.hass = window.demo.hass;
    await card.updateComplete;
    const style = document.createElement('style');
    style.textContent =
      'ha-card { --chip-background: rgb(12, 60, 90); --fireplace-action-color: rgb(250, 240, 230); } .toggles [data-action="flame"] { --fireplace-action-active-background: rgb(140, 30, 40); }';
    card.shadowRoot!.append(style);
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  const flame = card.locator('[data-view="chip"] [data-action="flame"]');
  const heat = card.locator('[data-view="chip"] [data-action="heating"]');
  await expect(flame).toHaveCSS('background-color', 'rgb(140, 30, 40)');
  await expect(heat).toHaveCSS('background-color', 'rgb(12, 60, 90)');
  await expect(heat).toHaveCSS('color', 'rgb(250, 240, 230)');
  await flame.click();
  await expect(flame).toHaveCSS('background-color', 'rgb(12, 60, 90)');
  await card.getByRole('button', { name: /Expand controls:/ }).click();
  const dialog = card.getByRole('dialog');
  await expect(dialog.locator('[data-action="flame"]')).toHaveCSS(
    'background-color',
    'rgb(12, 60, 90)',
  );
  await expect(dialog.locator('[data-action="heating"]')).toHaveCSS(
    'background-color',
    'rgb(12, 60, 90)',
  );
  await expect(dialog.locator('[data-action="heating"]')).toHaveCSS('color', 'rgb(250, 240, 230)');
  await dialog.getByRole('button', { name: 'Close controls' }).click();
  await page.evaluate(() => {
    window.demo.hass.states['climate.fire_heating']!.state = 'unavailable';
    window.demo.update();
  });
  await expect(heat).toBeDisabled();
  await expect(heat).toHaveCSS('background-color', 'rgb(12, 60, 90)');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
});

test('direct card-mod selectors override action styles without affecting other controls', async ({
  page,
}) => {
  await page.evaluate(async (type) => {
    const card = document.querySelector('flame-connect-card') as FlameConnectCard;
    card.setConfig({
      type,
      initial_view: 'compact',
      compact_style: 'chip',
      entities: { flame: 'light.fire_flame', climate: 'climate.fire_heating' },
    });
    card.hass = window.demo.hass;
    await card.updateComplete;
    const style = document.createElement('style');
    style.textContent =
      '.toggles [data-action="flame"] { background: rgb(34, 92, 170); color: rgb(255, 255, 0); }';
    card.shadowRoot!.append(style);
  }, CARD_TYPE);
  const card = page.locator('flame-connect-card');
  const flame = card.locator('[data-view="chip"] [data-action="flame"]');
  const heat = card.locator('[data-view="chip"] [data-action="heating"]');
  await expect(flame).toHaveCSS('background-color', 'rgb(34, 92, 170)');
  await expect(flame).toHaveCSS('color', 'rgb(255, 255, 0)');
  await expect(heat).not.toHaveCSS('background-color', 'rgb(34, 92, 170)');
  await flame.click();
  await expect(flame).toHaveCSS('background-color', 'rgb(34, 92, 170)');
  expect(await page.evaluate(() => window.demo.calls)).toHaveLength(1);
});

test('user dark glass card-mod style adapts action and icon backgrounds automatically', async ({
  page,
}, info) => {
  const userStyle = `ha-card { --primary-text-color: #f8f7f3; --secondary-text-color: #c8cecb; --primary-color: #50dbc9; --accent-color: #50dbc9; color: #f8f7f3; background: rgba(30, 38, 39, 0.38) !important; border: 1px solid rgba(255,255,255,0.17) !important; border-radius: 18px !important; box-shadow: 0 8px 24px rgba(0,0,0,0.18); backdrop-filter: blur(12px) saturate(120%); -webkit-backdrop-filter: blur(12px) saturate(120%); } :host { --primary-text-color: #fff; --secondary-text-color: #cbd1ce; --card-primary-color: #fff; --card-secondary-color: #cbd1ce; --mush-rgb-state-cover: 67, 225, 204; --mush-rgb-state-light: 67, 225, 204; }`;
  const expected = await page.evaluate(
    async ({ type, css }) => {
      const card = document.querySelector('flame-connect-card') as FlameConnectCard;
      card.setConfig({
        type,
        initial_view: 'compact',
        compact_style: 'chip',
        entities: {
          flame: 'light.fire_flame',
          climate: 'climate.fire_heating',
          color: 'select.fire_color',
          brightness: 'select.fire_brightness',
          speed: 'number.fire_speed',
        },
        card_mod: { style: css },
      });
      card.hass = window.demo.hass;
      card.style.setProperty('--secondary-background-color', '#fff');
      await card.updateComplete;
      const style = document.createElement('style');
      style.textContent = css;
      card.shadowRoot!.append(style);
      const reference = document.createElement('div');
      reference.style.background = 'color-mix(in srgb, #f8f7f3 6%, transparent)';
      document.body.append(reference);
      const expected = getComputedStyle(reference).backgroundColor;
      reference.remove();
      return expected;
    },
    { type: CARD_TYPE, css: userStyle },
  );
  const card = page.locator('flame-connect-card');
  const flame = card.locator('[data-view="chip"] [data-action="flame"]');
  const heat = card.locator('[data-view="chip"] [data-action="heating"]');
  await expect(flame).toHaveCSS('background-color', expected);
  await expect(heat).toHaveCSS('background-color', expected);
  await expect(card.locator('.chip-icon')).toHaveCSS('background-color', expected);
  await expect(flame).toHaveCSS('color', 'rgb(80, 219, 201)');
  await expect(heat).toHaveCSS('color', 'rgb(80, 219, 201)');
  await card.screenshot({ path: `test-results/card-mod-glass-${info.project.name}.png` });
  await flame.click();
  await expect(flame).toHaveCSS('color', 'rgb(248, 247, 243)');
  await expect(flame).toHaveCSS('background-color', expected);
  await card.getByRole('button', { name: /Expand controls:/ }).click();
  await expect(card.getByRole('dialog').locator('[data-action="heating"]')).toHaveCSS(
    'background-color',
    expected,
  );
  const dialog = card.getByRole('dialog');
  const close = dialog.locator('.view-toggle');
  await expect(close).toHaveCSS('background-color', expected);
  await expect(close).toHaveCSS('color', 'rgb(248, 247, 243)');
  for (const name of ['Heating / fan mode', 'Flame color', 'Flame brightness']) {
    const control = dialog.getByRole('combobox', { name, exact: true });
    await expect(control).toHaveCSS('background-color', expected);
    await expect(control).toHaveCSS('color', 'rgb(248, 247, 243)');
    const optionColors = await control
      .locator('option')
      .first()
      .evaluate((option) => {
        const styles = getComputedStyle(option);
        return { color: styles.color, background: styles.backgroundColor };
      });
    expect(optionColors.color).not.toBe(optionColors.background);
  }
  await expect(dialog.locator('.slider-label > svg').first()).toHaveCSS(
    'background-color',
    expected,
  );
  await dialog.getByRole('combobox', { name: 'Flame color' }).selectOption('blue');
  await expect(dialog.getByRole('combobox', { name: 'Flame color' })).toHaveValue('blue');
});
