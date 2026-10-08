# SecureVision — Migration Notes

**Phase 1 → Phase 2 migration**  
Date: October 2026

---

## What Changed

### Architecture

| Aspect | Before (Phase 1) | After (Phase 2) |
|--------|-----------------|-----------------|
| Rendering | Server-side Jinja2 templates | React SPA (Vite + TypeScript) |
| Backend | Single Flask app (HTML + API) | Flask ML microservice + Node.js gateway |
| Frontend | jQuery + Bootstrap + Chart.js | React + TailwindCSS + Recharts |
| State | Full page reloads | TanStack Query with caching |
| File upload | Flask/Werkzeug | Multer in Node gateway |
| Logging | Python logging to file | Pino (structured JSON) in Node |
| CORS | None (same origin) | Scoped per service |
| Rate limiting | None | express-rate-limit (200/15 min global, 30/min scans) |

### Python ML Service (`ml-service/`)

- **Stripped** all 6 HTML-rendering routes (`/`, `/dashboard`, `/scan/url`, `/scan/message`, `/scan/apk`, `/history`)
- **Removed** `render_template`, `redirect`, `url_for` imports
- **Added** `flask-cors` scoped to Node gateway origin only (`ML_ALLOWED_ORIGIN` env var)
- **Added** `/api/health` endpoint so the gateway can poll readiness
- **Kept** all 5 JSON API routes unchanged — same request/response shapes
- **Kept** SQLite database schema and all existing scan history data
- Original `app.py` at the repo root is **preserved** for direct local use

### Node.js Gateway (`server/`)

New service. Owns:
- Input validation via **Zod** schemas
- APK file upload via **Multer** (memory storage, 50 MB limit, .apk-only filter)
- Proxies all requests to the Python ML service via **axios**
- Structured logging via **pino**
- Rate limiting via **express-rate-limit**
- Security headers via **helmet**
- Centralised error handling (Zod errors → 400, Axios errors → forwarded, unhandled → 500)

### React Frontend (`client/`)

New service. Replaces all Jinja2 templates:

| Old template | New page |
|-------------|----------|
| `dashboard.html` | `src/pages/Dashboard.tsx` — live stat cards + Recharts area/pie |
| `url_scanner.html` | `src/pages/UrlScanner.tsx` — inline validation + threat banner |
| `message_scanner.html` | `src/pages/MessageScanner.tsx` — annotated text + indicator chips |
| `apk_scanner.html` | `src/pages/ApkScanner.tsx` — drag-drop zone + upload progress bar |
| `history.html` | `src/pages/History.tsx` — sortable/filterable table + CSV export |

Shared components used identically across all scanner pages:
- `<RiskBadge>` — colour-coded prediction/risk level pill
- `<ConfidenceBar>` — animated progress bar (framer-motion)
- `<ExplanationPanel>` — "Why this was flagged" bullet list
- `<RecommendationList>` — numbered action items
- `<ScanResultCard>` — composes all of the above

### ML Feature Engineering (Part A)

| Detector | Features before | Features after | Key additions |
|----------|----------------|----------------|---------------|
| APK | 10 | 44 | Androguard API calls, certificates, obfuscation, manifest anomalies |
| URL | 20 | 43 | WHOIS domain age, Levenshtein typosquatting, suspicious TLDs, shortener detection |
| Message | 21 | 57 | Social engineering scoring, linguistic analysis, 8 keyword categories |

---

## Database

Schema is **unchanged** — no migration required.  
The SQLite file (`securevision.db`) is bind-mounted into the ML service container so history persists across container restarts.

If you move to Postgres later:
1. Change `SQLALCHEMY_DATABASE_URI` in `config.py` to a `postgresql://` URL
2. Run `flask db upgrade` (add Flask-Migrate first)

---

## Environment Variables

### ml-service
| Variable | Default | Description |
|----------|---------|-------------|
| `ML_PORT` | `5000` | Port the Flask app listens on |
| `ML_ALLOWED_ORIGIN` | `http://localhost:4000` | CORS allowed origin |
| `SECRET_KEY` | *(required)* | Flask secret key |

### server
| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `4000` | Gateway listen port |
| `ML_SERVICE_URL` | `http://localhost:5000` | Python service base URL |
| `CLIENT_ORIGIN` | `http://localhost:5173` | CORS allowed origin for React dev server |
| `LOG_LEVEL` | `info` | Pino log level |

### client (build-time)
| Variable | Default | Description |
|----------|---------|-------------|
| `/api` proxy | `http://localhost:4000` | Configured in `vite.config.ts` dev proxy |

---

## Known Limitations & Follow-up Work

### Immediate
- [ ] **Models need retraining** with larger datasets to benefit from the expanded feature sets (Part A). Current `.pkl` files were trained on 50–100 sample rows — the new 44/43/57-feature vectors require re-fit models.
- [ ] **Androguard API** changed between 3.x and 4.x (`androguard.core.apk` not `androguard.core.bytecodes.apk`). The import fix is in `features/apk_features.py` — verify with a real APK file.

### Short-term
- [ ] **Authentication** — no auth layer yet. Add JWT in the Node gateway before any public deployment.
- [ ] **HTTPS** — add a reverse-proxy (nginx/Caddy) with TLS in front of all three services for production.
- [ ] **Production WSGI** — replace Flask dev server with gunicorn (already in `ml-service/requirements.txt`, used in the Dockerfile).

### Dataset sourcing (to realise Part A accuracy gains)
- URL detector: download PhishTank feed + Tranco top-1M for negatives
- Message detector: Enron spam corpus + UCI SMS Spam Collection
- APK detector: Drebin dataset or CICMalDroid2020 (requires research access)

### Future enhancements
- [ ] Add SHAP feature-importance values to API responses for explainability UI
- [ ] Ensemble retraining scripts in `training/ensemble/`
- [ ] DistilBERT option for message detector (feature-flagged)
- [ ] Migrate from SQLite → Postgres for multi-worker deployments
- [ ] Add OpenAPI/Swagger spec to the Node gateway
- [ ] Add `@tanstack/react-query` devtools panel in development builds


---

## Phase 3: Live URL Scanner

Date: July 2025

### What was added

| Component | Changes |
|-----------|----------|
| `detection/live_scanner.py` | New Playwright-based live URL scanner with SSRF protection, behavioral evidence collection, and rule-based scoring |
| `app.py` | Added async job API: POST /api/scan/url/live, GET /api/scan/url/live/<job_id>, ThreadPoolExecutor, in-memory job store with TTL |
| `database/models.py` | get_statistics() now counts URL_LIVE in url_scans and url_threats |
| `server/src/` | mlClient functions startLiveScan/getLiveScanJob, scanController handlers, routes with 5/min rate limit |
| `client/src/` | UrlScanner mode toggle (Quick/Live), polling stepper, verdict badge, redirect timeline, evidence list, screenshot preview; History page Live badge |
| `live-scanner/` | Isolated Docker service (Playwright image, non-root, no DB mount, memory/CPU limits) |
| `tests/test_live_scanner.py` | Unit + API tests for safety checks, scoring, combined formula, Flask endpoints |

### New environment variables

| Variable | Default | Service | Description |
|----------|---------|---------|-------------|
| `LIVE_SCAN_ENABLED` | `true` | ml-service, live-scanner | Feature flag |
| `LIVE_SCAN_TIMEOUT_MS` | `15000` | ml-service, live-scanner | Browser timeout |
| `LIVE_SCAN_MAX_WORKERS` | `2` | ml-service, live-scanner | ThreadPoolExecutor workers |
| `LLM_VERDICT_ENABLED` | `false` | live-scanner | Enable Anthropic LLM verdict |
| `ANTHROPIC_API_KEY` | *(unset)* | live-scanner | Anthropic API key |
| `LIVE_SCANNER_ORIGIN` | `http://ml-service:5000` | live-scanner | CORS allowed origin |

### Breaking changes
None. All existing endpoints (/api/scan/url, /api/scan/message, /api/scan/apk, /api/history, /api/statistics) are unchanged.
