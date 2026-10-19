import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe.configure({ timeout: 90_000 });

const accounts = [
  ['Admin', 'admin@acrnhealth.com'],
  ['Monitor', 'monitor1@acrnhealth.com'],
  ['Adjudicator', 'adjudicatora@acrnhealth.com'],
  ['Chairperson', 'chairperson@acrnhealth.com'],
  ['Owner', 'tariro@acrnhealth.com'],
];

async function login(page, email) {
  page.on('pageerror', error => console.error(`[browser page error] ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error') console.error(`[browser console] ${message.text()}`);
  });
  await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 45000 });
  const emailInput = page.getByLabel('Email Address', { exact: true });
  const passwordInput = page.getByLabel('Password', { exact: true });
  // The auth configuration asynchronously loads optional demo defaults. Give
  // that request a bounded settling period before replacing them; production-
  // style builds intentionally leave the fields empty.
  await expect(emailInput).toBeVisible();
  await page.waitForTimeout(750);
  await emailInput.fill(email);
  await passwordInput.fill('ACRN@2026');
  await expect(emailInput).toHaveValue(email);
  await page.getByRole('button', { name: 'Sign In', exact: true }).click();
  await expect(page.locator('main').first()).toBeVisible({ timeout: 45000 });
  // Portals legitimately poll operational endpoints, so network-idle is not a
  // valid readiness signal. The visible main landmark is the user-facing one.
  await page.waitForTimeout(250);
}

for (const [portal, email] of accounts) {
  test(`${portal} landing page has no automatic WCAG A/AA violations`, async ({ page }) => {
    await login(page, email);
    const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']).analyze();
    expect(results.violations, results.violations.map(item => `${item.id}: ${item.help} (${item.nodes.length})`).join('\n')).toEqual([]);
  });
}

test('keyboard users can bypass navigation and focus the main region', async ({ page }) => {
  await login(page, 'adjudicatora@acrnhealth.com');
  await page.keyboard.press('Home');
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: 'Skip to main content' });
  await expect(skip).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});

test('reduced-motion preference is honored by the application stylesheet', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await login(page, 'monitor1@acrnhealth.com');
  const transitionDuration = await page.locator('button').first().evaluate(element => getComputedStyle(element).transitionDuration);
  expect(Number.parseFloat(transitionDuration)).toBeLessThanOrEqual(0.00001);
});
