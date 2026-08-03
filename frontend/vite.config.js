import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const allowedHosts = ['oracle-loyers.onrender.com']

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    allowedHosts,
  },
  preview: {
    allowedHosts,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.js'],
    globals: true,
    // tests/e2e/ contient les specs Playwright (ORA-59), exécutées via
    // `npm run test:e2e`, pas par Vitest.
    exclude: ['tests/e2e/**', 'node_modules/**'],
  },
})
