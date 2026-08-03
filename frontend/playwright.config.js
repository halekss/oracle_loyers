import { defineConfig, devices } from '@playwright/test';

// Test E2E contre un build de production réel (pas `npm run dev`), voir
// ORA-59 : Playwright démarre lui-même le backend Flask et le build
// frontend servi par `vite preview`, sur des ports dédiés pour ne pas
// entrer en conflit avec un serveur de dev déjà lancé localement.
const FRONTEND_PORT = 4173;
const BACKEND_PORT = 5055;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'dot' : 'list',
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python3 app.py',
      cwd: '../backend',
      url: `${BACKEND_URL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        PORT: String(BACKEND_PORT),
        FLASK_DEBUG: '0',
        CORS_ORIGINS: `http://localhost:${FRONTEND_PORT}`,
      },
    },
    {
      command: `npm run build && npx vite preview --port ${FRONTEND_PORT} --strictPort`,
      url: `http://localhost:${FRONTEND_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        VITE_API_URL: `${BACKEND_URL}/api`,
      },
    },
  ],
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
