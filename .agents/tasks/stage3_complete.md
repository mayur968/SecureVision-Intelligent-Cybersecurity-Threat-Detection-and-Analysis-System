# Stage 3 Complete — .eml Email Scanner

## Status
Review findings fixed. All tests pass. TypeScript clean.

## Commit
- Initial implementation: `a66c7aa` — `feat: Stage 3 — .eml email scanner, EmailScanner page, route, 10 tests`
- Review fixes: `ab77fce` — `fix: Stage 3 review — content_length guard before read, Prediction includes SUSPICIOUS, document rate-limit gap`

## Files Created
- `detection/email_scanner.py` — Core .eml parser and risk scorer
- `client/src/pages/EmailScanner.tsx` — React page with file drop zone, scan results
- `tests/test_email_scanner.py` — 12 pytest tests (10 required + 2 bonus rejection tests)
- `.agents/tasks/screenshot_stage3.cjs` — Playwright screenshot script

## Files Modified
- `app.py` — Added `/api/scan/email/upload` route; patched `/api/statistics` with `email_scans`; added `request.content_length` guard (review fix)
- `client/src/types/index.ts` — Added `EmailSender`, `EmailAuthResults`, `EmailLink`, `EmailAttachment`, `EmailScanResult` interfaces; extended `ScanTypeExtended` with `'EMAIL'`; extended `Prediction` with `'SUSPICIOUS'` (review fix)
- `client/src/api/client.ts` — Added `scanEmail()` method
- `client/src/components/layout/Sidebar.tsx` — Added Email icon and nav item
- `client/src/main.tsx` — Registered `scan/email` route

## Test Results
- Email scanner tests: **12/12 passed** (10 required + 2 bonus rejection tests)
- Full test suite: **110 passed, 6 failed** (6 pre-existing failures unrelated to Stage 3)

## TypeScript Check
- `npx tsc --noEmit`: **0 errors**

## Review Findings Fixed
1. **Finding 1 (50 MB buffer before 5 MB gate)**: Added `request.content_length` check before `f.read()` — rejects oversized requests before allocating memory buffer.
2. **Finding 2 (EmailScanResult.prediction typed as string)**: Extended `Prediction` union to include `'SUSPICIOUS'`; `EmailScanResult.prediction` now uses `Prediction` type for full exhaustiveness checking.
3. **Finding 3 (No rate-limiting)**: Documented deliberate gap with code comment — consistent with all other scan endpoints (APK, URL, Message) which also have no per-IP rate limiting.

## Screenshot
- Vite dev server was not running at time of verification; screenshot script saved to `.agents/tasks/screenshot_stage3.cjs`
- Playwright is available at `client/node_modules/playwright` (not root `node_modules`)
- Run manually: start Vite (`cd client && npm run dev`), then `node .agents/tasks/screenshot_stage3.cjs`
