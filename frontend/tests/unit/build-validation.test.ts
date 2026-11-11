import { afterEach, beforeEach, expect, it, vi } from 'vitest';

const fixture = vi.hoisted(() => ({
  files: {} as Record<string, string>,
  directories: {} as Record<string, string[]>,
  bundleSize: 1024,
}));

vi.mock('node:fs', () => ({
  readFileSync: (path: string) => {
    if (!(path in fixture.files)) throw new Error(`Missing file: ${path}`);
    return fixture.files[path];
  },
  readdirSync: (path: string, options?: { withFileTypes?: boolean }) => {
    const entries = fixture.directories[path];
    if (!entries) throw new Error(`Missing directory: ${path}`);
    if (!options?.withFileTypes) return entries;
    return entries.map((entry) => ({
      name: entry.replace(/\/$/, ''),
      isDirectory: () => entry.endsWith('/'),
    }));
  },
  statSync: () => ({ size: fixture.bundleSize }),
}));

beforeEach(() => {
  vi.resetModules();
  vi.spyOn(console, 'log').mockImplementation(() => {});
  fixture.directories = {
    'src/domain': ['state.ts', 'models/'],
    'src/domain/models': ['value.ts'],
    'src/application': ['commands.ts'],
    dist: ['flame-connect-card.js'],
  };
  fixture.files = {
    'src/domain/state.ts': "import type { Value } from './models/value';",
    'src/domain/models/value.ts': 'export const value = 1;',
    'src/application/commands.ts': "import { value } from '../domain/state';",
    'package.json': JSON.stringify({ name: 'flame-connect-card', version: '0.1.0-beta.1' }),
    'hacs.json': JSON.stringify({ filename: 'flame-connect-card.js' }),
    'dist/flame-connect-card.js': 'const image = "data:image/png;base64,bundled-artwork";',
  };
  fixture.bundleSize = 1024;
});
afterEach(() => vi.restoreAllMocks());

it('architecture validation accepts inward imports and recursively checks domain modules', async () => {
  await import('../../scripts/check-architecture.mjs');
  expect(console.log).toHaveBeenCalledWith('Architecture boundaries verified.');
});
it.each([
  ['src/domain/state.ts', "import { LitElement } from 'lit';"],
  ['src/domain/models/value.ts', "import { execute } from '../../application/commands';"],
  [
    'src/application/commands.ts',
    "import { read } from '../adapters/home-assistant/state-mapper';",
  ],
])('architecture validation rejects a forbidden dependency in %s', async (path, source) => {
  fixture.files[path] = source;
  await expect(import('../../scripts/check-architecture.mjs')).rejects.toThrow(
    'forbidden inward dependency',
  );
  expect(console.log).not.toHaveBeenCalled();
});
it.each(['window', 'document', 'localStorage', 'fetch'])(
  'architecture validation rejects browser dependency %s in core',
  async (dependency) => {
    fixture.files['src/application/commands.ts'] = `export const value = ${dependency};`;
    await expect(import('../../scripts/check-architecture.mjs')).rejects.toThrow(
      'browser dependency in core',
    );
  },
);
it('architecture validation fails explicitly if a nested source file cannot be read', async () => {
  delete fixture.files['src/domain/models/value.ts'];
  await expect(import('../../scripts/check-architecture.mjs')).rejects.toThrow('Missing file');
});

it('package validation accepts one bounded self-contained module containing the supplied artwork', async () => {
  await import('../../scripts/check-package.mjs');
  expect(console.log).toHaveBeenCalledWith(
    'Verified self-contained flame-connect-card.js (0.1.0-beta.1).',
  );
});
it('package validation rejects a package name that does not match the module', async () => {
  fixture.files['package.json'] = JSON.stringify({ name: 'wrong-name', version: '0.1.0' });
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow();
});
it('package validation rejects additional distribution chunks', async () => {
  fixture.directories.dist!.push('editor.js');
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow();
});
it('package validation rejects a module without the four-state artwork', async () => {
  fixture.files['dist/flame-connect-card.js'] = 'export const card = {};';
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow(
    'supplied fireplace states',
  );
});
it.each([
  "import {html} from 'lit';",
  "import './missing.js';",
  "import('./editor.js');",
  "export * from '../missing.js';",
  "import 'https://example.com/module.js';",
])('package validation rejects an unresolved import: %s', async (statement) => {
  fixture.files['dist/flame-connect-card.js'] += statement;
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow(
    'external or missing module dependencies',
  );
});
it('package validation rejects an oversized artifact before it can be released', async () => {
  fixture.bundleSize = 2_500_000;
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow('below 2.5 MB');
});
it('package validation does not announce success when an input file is missing', async () => {
  delete fixture.files['package.json'];
  await expect(import('../../scripts/check-package.mjs')).rejects.toThrow('Missing file');
  expect(console.log).not.toHaveBeenCalled();
});

it.each([
  "export { read } from '../adapters/read';",
  "const load = () => import('../presentation/card');",
  "const load = () => require('../adapters/read');",
  "type View = import('../presentation/card').View;",
  'const load = (name) => import(name);',
  "import './models/../../../presentation/card';",
])('architecture rejects a module dependency expressed as %s', async (source) => {
  fixture.files['src/domain/state.ts'] = source;
  await expect(import('../../scripts/check-architecture.mjs')).rejects.toThrow(
    'forbidden inward dependency',
  );
});
it('architecture accepts inward exports, type imports and dynamic imports while ignoring comments and strings', async () => {
  fixture.files['src/domain/state.ts'] = `
    // document, fetch and import('../adapters/read') are documentation only.
    export { value } from './models/value';
    export const description = 'window document localStorage fetch';
    type Value = import('./models/value').Value;
    const load = () => import('./models/value');
    const common = require('./models/value');
    export const plain = 1;
  `;
  fixture.files['src/application/commands.ts'] =
    "import { command } from './other'; export { value };";
  await import('../../scripts/check-architecture.mjs');
  expect(console.log).toHaveBeenCalledWith('Architecture boundaries verified.');
});

it('allows local names and data properties resembling browser globals', async () => {
  fixture.files['src/domain/state.ts'] =
    'type Data = { fetch: number }; export function read(document: Data) { return document.fetch; }';
  await import('../../scripts/check-architecture.mjs');
});
