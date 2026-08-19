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
    // Demo headers for monitor-level requests
    extraHTTPHeaders: {
      'X-Demo-User': 'monitor@test.acrn',
      'X-Demo-Role': 'ADJUDICATION_COORDINATOR',
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // webServer is optional — start dev server manually before running:
  // npm run dev  (frontend)
  // cd backend && python -m uvicorn main:app --reload  (backend)
});
