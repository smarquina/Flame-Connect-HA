import { defineConfig } from 'vite';
export default defineConfig({
  build: {
    lib: { entry: 'src/index.ts', formats: ['es'], fileName: () => 'flame-connect-card.js' },
    sourcemap: false,
    target: 'es2022',
  },
});
