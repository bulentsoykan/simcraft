// ABOUTME: Vite configuration for the SimCraft visualization viewer.
// ABOUTME: Configures TypeScript and Three.js bundling.

import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 3000,
    open: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
