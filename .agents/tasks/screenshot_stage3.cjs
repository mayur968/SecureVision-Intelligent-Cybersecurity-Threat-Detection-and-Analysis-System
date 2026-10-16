// Screenshot script for Stage 3 — EmailScanner page at /scan/email
// Run with: node .agents/tasks/screenshot_stage3.cjs
// Requires Vite dev server running at http://localhost:5173

const { chromium } = require('c:\\Users\\Mayur\\Documents\\SecureVision\\node_modules\\playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage();
    await page.goto('http://localhost:5173/scan/email', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    await page.screenshot({
      path: 'c:\\Users\\Mayur\\Documents\\SecureVision\\.agents\\tasks\\stage3_email.png',
      fullPage: true,
    });
    console.log('Screenshot saved to .agents/tasks/stage3_email.png');
  } finally {
    await browser.close();
  }
})();
