// diagnose_history.cjs — run with: node diagnose_history.cjs
// from c:\Users\Mayur\Documents\SecureVision
const { chromium } = require('./node_modules/playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const screenshotPath = path.join(__dirname, '.agents', 'tasks', 'history_screenshot_before.png');
  fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  const consoleErrors = [];
  const consoleWarnings = [];
  const failedRequests = [];
  let pageCrash = null;

  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
    if (msg.type() === 'warning') consoleWarnings.push(msg.text());
  });
  page.on('pageerror', err => { pageCrash = String(err); });
  page.on('requestfailed', req => {
    failedRequests.push({ url: req.url(), failure: req.failure()?.errorText });
  });
  page.on('response', resp => {
    if (resp.status() >= 400) {
      failedRequests.push({ url: resp.url(), status: resp.status() });
    }
  });

  try {
    await page.goto('http://localhost:5173/history', { timeout: 15000 });
    await Promise.race([
      page.waitForLoadState('networkidle', { timeout: 10000 }),
      page.waitForSelector('table tbody tr, [data-testid="empty-state"], [data-testid="error-state"]', { timeout: 10000 }),
    ]).catch(() => {});
  } catch (e) {
    pageCrash = pageCrash || String(e);
  }

  await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});

  let tableRowCount = 0;
  try { tableRowCount = await page.locator('table tbody tr').count(); } catch (_) {}

  await browser.close();

  const report = { consoleErrors, consoleWarnings, pageCrash, failedRequests, tableRowCount, screenshotPath };
  console.log(JSON.stringify(report, null, 2));
})();
