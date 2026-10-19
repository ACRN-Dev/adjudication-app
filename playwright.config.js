// playwright.config.js
// ACRN Adjudication Portal — Playwright E2E browser test configuration

import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60 * 1000,
  retries: 0,
  workers: 1,   // sequential — portal has single shared demo DB
  reporter: [['list'], ['html', { outputFolder: 'playwright-report' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'node scripts/run-e2e-api.mjs',
      url: 'http://127.0.0.1:8000/health/ready',
      timeout: 120 * 1000,
      reuseExistingServer: false,
    },
    {
      command: 'npm run test:serve -- --host 127.0.0.1 --port 5173',
      url: 'http://127.0.0.1:5173',
      timeout: 120 * 1000,
      reuseExistingServer: false,
      env: { VITE_ENABLE_DEMO_UI: 'true' },
    },
  ],
  // webServer is optional — start dev server manually before running:
  // npm run dev  (frontend)
  // cd backend && python -m uvicorn main:app --reload  (backend)
});
