/// <reference types="vitest/config" />
import path from 'node:path';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, 'src'),
      '@demo': path.resolve(import.meta.dirname, '../demo_data'),
    },
  },
  // amazon-cognito-identity-js expects a Node-style `global`.
  define: { global: 'globalThis' },
  server: {
    port: 5173,
    fs: { allow: ['..'] },
    proxy: {
      '/api': { target: process.env.VITE_DEV_API_PROXY ?? 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes('recharts') || id.includes('lightweight-charts') || id.includes('d3-')) return 'charts';
          if (id.includes('@xyflow')) return 'graph';
          if (id.includes('amazon-cognito-identity-js')) return 'auth';
          return undefined;
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    env: { VITE_DEMO_MODE: 'false' },
  },
});
