const { chromium } = require('./client/node_modules/playwright');
const path = require('path');

async function shot(page, url, file) {
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
  await page.waitForTimeout(800);
  await page.screenshot({ path: file, fullPage: true });
  console.log(JSON.stringify({ url, file, consoleErrors: errors, ok: errors.length === 0 }));
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await ctx.newPage();

  await shot(page, 'http://localhost:5173/', path.join(__dirname, '.agents/tasks/stage1_landing.png'));
  await shot(page, 'http://localhost:5173/login', path.join(__dirname, '.agents/tasks/stage2_login.png'));
  await shot(page, 'http://localhost:5173/scan/email', path.join(__dirname, '.agents/tasks/stage3_email.png'));
  await shot(page, 'http://localhost:5173/dashboard', path.join(__dirname, '.agents/tasks/stage3_dashboard.png'));

  await browser.close();
})();
