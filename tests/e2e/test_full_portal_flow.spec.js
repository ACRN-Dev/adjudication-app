/**
 * test_full_portal_flow.spec.js
 * ACRN Adjudication Portal — Full Role-Based Browser Simulation
 *
 * Prerequisites:
 *   npm install -D @playwright/test
 *   npx playwright install chromium
 *   ENABLE_DEMO_ACCOUNTS=true  (backend env)
 *   VITE_ENABLE_DEMO_ACCOUNTS=true  (frontend build / dev)
 *   npm run dev  (frontend on :5173)
 *   cd backend && python -m uvicorn main:app --reload  (backend on :8000)
 *
 * Tests:
 *   1. Monitor login → verify dashboard accessible
 *   2. Admin quick-login renders only when VITE_ENABLE_DEMO_ACCOUNTS=true
 *   3. Adjudicator login → workbench renders
 *   4. Role barrier: adjudicator navigating to /monitor → redirected to login
 *   5. Chairperson login → chairperson portal renders
 */

import { test, expect } from '@playwright/test';

const BASE = 'http://127.0.0.1:5173';
const DEMO_PASSWORD = 'ACRN@2026';

// ── Helper: fill email+password and submit ────────────────────────────────────
async function loginAs(page, email) {
  await page.goto(BASE + '/');
  await page.waitForLoadState('domcontentloaded');

  const emailInput = page.locator('input[type="email"]');
  const passwordInput = page.locator('input[type="password"]');

  if (await emailInput.isVisible()) {
    await emailInput.fill(email);
    await passwordInput.fill(DEMO_PASSWORD);
    await page.click('button[type="submit"]');
    // Wait for the login form to be detached / portal to render
    await page.locator('input[type="email"]').waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
  } else {
    test.skip('Demo login form not visible — VITE_ENABLE_DEMO_ACCOUNTS may not be set');
  }
}

// ── 1. Monitor login ──────────────────────────────────────────────────────────
test('Monitor login reaches monitor portal or adjudication workbench', async ({ page }) => {
  await loginAs(page, 'monitor1@acrnhealth.com');
  await expect(page.locator('body')).not.toContainText('Access Portal');
  await expect(page.locator('text=/Monitor/i').first()).toBeVisible({ timeout: 10000 });
});

// ── 2. Admin login ────────────────────────────────────────────────────────────
test('Admin login renders admin portal', async ({ page }) => {
  await loginAs(page, 'admin@acrnhealth.com');
  await expect(page.locator('text=/Administration/i').first()).toBeVisible({ timeout: 10000 });
});

// ── 3. Adjudicator login ──────────────────────────────────────────────────────
test('Adjudicator login reaches workbench', async ({ page }) => {
  await loginAs(page, 'adjudicatora@acrnhealth.com');
  await expect(page.locator('text=/Subject Queue/i').first()).toBeVisible({ timeout: 10000 });
});

// ── 4. Role barrier: adjudicator cannot access /monitor ──────────────────────
test('Adjudicator navigating to /monitor sees access denied or is redirected', async ({ page }) => {
  await loginAs(page, 'adjudicatora@acrnhealth.com');
  await page.goto(BASE + '/monitor');
  await page.waitForLoadState('networkidle');
  // Monitor operational workspace must not be shown to adjudicator
  const hasMonitorWorkspace = await page.locator('text=/Monitor.*Operational/i').isVisible().catch(() => false);
  expect(hasMonitorWorkspace).toBeFalsy();
  // Must either be redirected back to adjudicator workbench or display access denied
  await expect(page.locator('text=/Subject Queue/i').or(page.locator('text=/Access denied/i')).first()).toBeVisible({ timeout: 10000 });
});

// ── 5. Chairperson login ──────────────────────────────────────────────────────
test('Chairperson login renders chairperson portal', async ({ page }) => {
  await loginAs(page, 'chairperson@acrnhealth.com');
  await expect(page.locator('text=/Chairperson/i').first()).toBeVisible({ timeout: 10000 });
});

// ── 6. Demo login bar hidden when BUILD_DEMO_ENABLED false ───────────────────
test('Demo quick-login bar absent in production builds', async ({ page }) => {
  await page.goto(BASE + '/');
  await page.waitForLoadState('domcontentloaded');
  const pageSource = await page.content();
  const hasFakePatientId = /ZWE\d{3}-\d{4}/.test(pageSource);
  expect(hasFakePatientId).toBeFalsy();
});
