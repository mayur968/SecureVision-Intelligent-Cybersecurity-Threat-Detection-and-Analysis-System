# SecureVision v2

**Intelligent Cybersecurity Threat Detection System**

Three-tier monorepo: Python ML microservice · Node.js/Express API gateway · React SPA

```
[React + TypeScript]  ←→  [Node.js/Express]  ←→  [Python Flask ML]
     :5173                     :4000                    :5000
```

---

## Quick Start (local, no Docker)

### Prerequisites
- Python 3.10+
- Node.js 20+
- The `venv/` virtual environment already set up (run `python -m venv venv` if not)

### 1 — Install everything

```powershell
# Python deps (from repo root)
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install flask-cors==4.0.0

# Node deps
npm install            # root (installs concurrently)
cd server && npm install && cd ..
cd client && npm install && cd ..
```

### 2 — Start all three services

```powershell
npm run dev
```

This runs concurrently:
| Service | Command | URL |
|---------|---------|-----|
| ML microservice | `python ml-service/app.py` | http://localhost:5000 |
| Node gateway | `cd server && npm run dev` | http://localhost:4000 |
| React SPA | `cd client && npm run dev` | http://localhost:5173 |

Open **http://localhost:5173** in your browser.

> **Legacy Flask UI** (original Jinja2 dashboard) still works independently:
> ```powershell
> python app.py   # → http://localhost:5000
> ```

---

## Quick Start (Docker)

```bash
# Copy and edit env file
cp server/.env.example .env

docker compose up --build
```

| Service | URL |
|---------|-----|
| React SPA | http://localhost:5173 |
| Node gateway | http://localhost:4000 |
| ML service | http://localhost:5000 |

---

## Project Structure

```
SecureVision/
├── app.py                  # Original Flask app (legacy, still works)
├── package.json            # Root — npm run dev starts all 3 services
├── docker-compose.yml
│
├── ml-service/             # Python Flask — JSON API only
│   ├── app.py              # Stripped to 5 API endpoints + /api/health
│   ├── requirements.txt
│   └── Dockerfile
│
├── server/                 # Node.js / Express — API gateway
│   ├── src/
│   │   ├── index.ts        # Express app, rate limiting, CORS, pino logging
│   │   ├── routes/         # Route definitions + multer APK upload
│   │   ├── controllers/    # Request handlers (Zod validation)
│   │   ├── services/       # mlClient — typed axios wrapper to Python
│   │   ├── middleware/     # Error handler (Zod + Axios + generic)
│   │   └── types/          # Shared TypeScript interfaces
│   ├── package.json
│   └── Dockerfile
│
├── client/                 # React / Vite / TypeScript SPA
│   ├── src/
│   │   ├── main.tsx        # App entry, React Router, QueryClient
│   │   ├── pages/          # Dashboard, UrlScanner, MessageScanner, ApkScanner, History
│   │   ├── components/
│   │   │   ├── layout/     # Layout, Sidebar
│   │   │   └── ui/         # RiskBadge, ConfidenceBar, ExplanationPanel,
│   │   │                   # RecommendationList, ScanResultCard
│   │   ├── api/client.ts   # Typed axios calls to Node gateway
│   │   └── types/          # ScanResult, HistoryScan, Statistics …
│   ├── package.json
│   └── Dockerfile
│
├── detection/              # ML detectors (URL, Message, APK)
├── features/               # Feature extractors (enhanced in Part A)
├── explanation/            # Risk scoring, threat explanation, recommendations
├── database/               # SQLAlchemy models (ScanHistory)
├── models/                 # Trained .pkl files
├── training/               # Model training scripts
└── tests/                  # Pytest unit tests
```

---

## API Reference

All requests go through the Node gateway at `:4000/api/`.

### Health
```
GET  /api/health
```

### Scan URL
```
POST /api/scan/url
Content-Type: application/json
{ "url": "https://example.com" }
```

### Scan Message
```
POST /api/scan/message
Content-Type: application/json
{ "message": "Your account has been suspended..." }
```

### Scan APK
```
POST /api/scan/apk
Content-Type: multipart/form-data
file: <apk_file>   (max 50 MB)
```

### History
```
GET  /api/history?limit=50
```

### Statistics
```
GET  /api/statistics
```

All scan responses share this shape:
```json
{
  "success": true,
  "prediction":    "SAFE | PHISHING | MALICIOUS",
  "confidence":    0.94,
  "risk_score":    82,
  "risk_level":    "HIGH",
  "explanation":   "...",
  "recommendations": ["..."],
  "indicators":    ["..."]
}
```

---

## ML Improvements (Part A summary)

| Detector | Features (before) | Features (after) | Key additions |
|----------|--------------------|-------------------|---------------|
| APK | 10 | 44 | Androguard static analysis, API call patterns, certificate validation, obfuscation detection |
| URL | 20 | 43 | WHOIS domain age, Levenshtein typosquatting (20 brands), suspicious TLD list, shortener detection |
| Message | 21 | 57 | Social engineering scoring (scarcity/authority/fear/greed), linguistic analysis, 106 keywords |

> Models need retraining with larger datasets to fully realise these improvements.
> See `MIGRATION_NOTES.md` for dataset sourcing guidance.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML service | Python 3.10, Flask 3.0, SQLAlchemy, scikit-learn, XGBoost, Androguard |
| Gateway | Node.js 20, Express 4, TypeScript 5, Zod, Multer, Pino, Helmet |
| Frontend | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, TanStack Query 5, Recharts, Framer Motion |
| Database | SQLite (dev) — drop-in Postgres support via SQLAlchemy URI |
| Containers | Docker Compose v3.9 |

---

## Running Tests

```powershell
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

---

## Stopping All Services

`Ctrl+C` in the terminal running `npm run dev` stops all three processes.

For Docker: `docker compose down`


## Live URL Scanner

The Live Scanner visits a URL in a sandboxed headless browser, collects behavioral evidence, and combines it with the ML score for a phishing verdict.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /scan/url/live | Start a live scan job. Body: `{"url": "..."}`. Returns 202 with `{job_id, status}`. |
| GET | /scan/url/live/:jobId | Poll job status. Returns `{status, result?, error?}`. |

### Job lifecycle

```
queued → running → done
                 → failed
```

Poll every 1.5 seconds until status is `done` or `failed` (5–15 seconds typical).

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIVE_SCAN_ENABLED` | `true` | Feature flag — set to `false` to disable |
| `LIVE_SCAN_TIMEOUT_MS` | `15000` | Playwright browser timeout in ms |
| `LIVE_SCAN_MAX_WORKERS` | `2` | Max concurrent background scan workers |
| `LLM_VERDICT_ENABLED` | `false` | Enable Anthropic API brand check (optional) |
| `ANTHROPIC_API_KEY` | *(unset)* | Anthropic key for LLM verdict |

### Setup

```bash
# Install dependencies
pip install playwright==1.44.0 tldextract anthropic
playwright install chromium

# Or with Docker
docker compose up --build live-scanner
```

### Security Notes

- The scanner never submits forms or interacts with the page — observe-only
- All requests (including sub-resources) are checked against an IP blocklist to prevent SSRF
- Screenshots are held in memory only and never stored in the database
- The Docker service runs as a non-root user with no access to the database volume
- Recommended: add egress firewall rules at the Docker network level blocking RFC 1918 address spaces
