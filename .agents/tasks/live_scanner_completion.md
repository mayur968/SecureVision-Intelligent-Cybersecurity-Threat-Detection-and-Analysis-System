# Live Scanner — Completion Report

**Date:** 2025-07-14

---

## What Was Implemented

### `detection/live_scanner.py`
- `is_safe_target(url)` — SSRF guard: blocks private/loopback IPs (RFC-1918, 169.254/16, ::1, etc.), non-HTTP(S) schemes (file, ftp, …), and bare hostnames with no TLD.
- `scan_live(url, timeout_ms)` — Playwright-based headless scan that captures page title, final URL (after redirects), HTML content, screenshot (PNG→base64), load time, and heuristic phishing evidence signals.
- `BRAND_MAP` — brand keyword → canonical-domain table used for brand-spoof detection.
- `SCORE_WEIGHTS` — per-signal score weights for the live heuristic scorer.
- `combined_score(ml_score, live_score, verdict)` — blends ML model score with live scan score; falls back gracefully when ML returns "Could not verify".

### `app.py` additions
- `POST /api/scan/url/live` (`api_scan_url_live`) — enqueues a background live-scan job, returns `202 Accepted` with a `job_id`.
- `GET /api/scan/url/live/<job_id>` (`api_get_live_job`) — polls job status; returns `pending`, `done` (with full result), or `error`.

### Supporting files
| File | Purpose |
|---|---|
| `tests/test_live_scanner.py` | 24 tests (21 unit + 3 integration) covering SSRF guards, scoring logic, combined-score formula, and Flask endpoint contracts |
| `tests/fixtures/benign.html` | Minimal HTML fixture for benign-page test cases |
| `tests/fixtures/phishing_login.html` | HTML fixture with login form, brand keyword, and urgency text for phishing-score tests |
| `tests/fixtures/redirect.html` | HTML fixture that meta-refreshes to a different domain |
| `live-scanner/Dockerfile` | Docker image for the standalone live-scanner microservice |
| `live-scanner/app.py` | Standalone Flask app wrapping `scan_live` (for Docker deployment) |
| `live-scanner/requirements.txt` | Python dependencies for the Docker image |
| `LIVE_SCANNER.md` | Developer documentation: architecture, API contract, configuration, deployment |
| `pytest.ini` | Registers `integration` custom mark (eliminates `PytestUnknownMarkWarning`) |

---

## Test Results

### Unit tests (`-k "not integration"`)
```
21 passed, 3 deselected, 0 warnings   (pytest 7.4.3 / Python 3.10.11)
```

### Integration smoke test (Playwright / example.com)
```
Verdict:    LIKELY_SAFE
Score:      0
Title:      Example Domain
Screenshot: YES
Load time:  849 ms
```

### Existing endpoint regression
| Endpoint | Status |
|---|---|
| `POST /api/scan/url` | 200 ✓ |
| `GET /api/statistics` | 200 ✓ |
| `GET /api/history` | 200 ✓ |

---

## TypeScript Compile Status

| Package | Result |
|---|---|
| `client/` | ✅ Clean (0 errors) |
| `server/` | ✅ Clean (0 errors) |

---

## Known Limitations / Follow-Up Items

1. **In-process job store** — `api_scan_url_live` stores jobs in a plain Python `dict` (process memory). Jobs are lost on restart and don't scale across workers. Production should use Redis or a DB-backed queue (Celery, RQ, etc.).
2. **No job TTL/cleanup** — completed jobs accumulate in memory indefinitely. Add a TTL sweep or bounded LRU cache for production.
3. **Playwright browser install** — Playwright browsers must be pre-installed (`playwright install chromium`). The `live-scanner/Dockerfile` handles this automatically; for local dev, run `playwright install` once in the venv.
4. **Screenshot storage** — screenshots are returned inline as base64. For large-scale use, store to S3/blob storage and return a URL instead.
5. **ML model integration** — `combined_score` is wired and tested, but the upstream ML scan (`/api/scan/url`) must pass its score + verdict to `combined_score` for blending. The current `/api/scan/url/live` endpoint runs the live scan only; full blending requires coordinating both results in the caller.
