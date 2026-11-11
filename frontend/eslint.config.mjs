import js from '@eslint/js';
import ts from 'typescript-eslint';
import sonarjs from 'eslint-plugin-sonarjs';
export default ts.config(
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
    ],
  },
  js.configs.recommended,
  ...ts.configs.recommended,
  { ...sonarjs.configs.recommended, files: ['src/**/*.ts'] },
  {
    files: ['**/*.mjs'],
    languageOptions: {
      globals: { console: 'readonly', process: 'readonly', URL: 'readonly', Buffer: 'readonly' },
    },
  },
  { rules: { '@typescript-eslint/no-explicit-any': 'error' } },
);
