const { chromium } = require('@playwright/test');
(async () => {
  try {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
    
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
    
    await page.fill('#user-email', 'tariro@acrnhealth.com');
    await page.fill('#user-password', 'ACRN@2026');
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(2000);
    const content = await page.content();
    console.log(content.length > 800 ? content.substring(0, 800) + '...' : content);
    if (content.includes('Executive Overview')) console.log('✅ Executive Overview found');
    if (content.includes('Owner Command Center')) console.log('✅ Owner Command Center found');
    
    // Check if error overlay is present
    if (content.includes('vite-error-overlay')) {
       console.log('🚨 Vite error overlay found!');
    }
    await browser.close();
  } catch (err) {
    console.error(err);
  }
})();
