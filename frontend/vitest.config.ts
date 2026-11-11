import { defineConfig } from 'vitest/config';
export default defineConfig({
  test: {
    environment: 'happy-dom',
    include: ['tests/unit/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts', 'scripts/**/*.mjs'],
      reporter: ['text', 'lcov', 'json-summary'],
      thresholds: { lines: 100, statements: 100, branches: 100, functions: 100 },
    },
  },
});
