# SecureVision — Live URL Scanner

The Live URL Scanner visits a URL in a sandboxed headless Chromium browser (via Playwright), collects behavioral evidence from the live page, and combines the result with the existing ML URL score to produce a final verdict.

---

## What It Does

Unlike the standard ML-only URL scan that analyses the URL string itself, the Live Scanner actually navigates to the page and observes what happens:

1. Launches a hardened headless Chromium instance via Playwright
2. Intercepts all network requests to enforce SSRF protection before they leave the machine
3. Navigates to the target URL and follows redirects
4. Collects behavioral signals: DOM elements, form actions, brand mentions, iframe attributes
5. Takes a screenshot (held in memory only — never stored)
6. Computes a rule-based `live_score` from the evidence signals
7. Combines `live_score` with the ML phishing probability for a `combined_score`
8. Returns a structured verdict with the redirect chain, evidence list, and optional LLM analysis

---

## Evidence Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Password field | 25 | Page contains an `input[type=password]` |
| Card/OTP fields | 15 | Inputs with names or placeholders mentioning `cvv`, `card`, `otp`, `ssn`, `aadhaar`, or `pan` |
| Cross-domain form action | 25 | Form `action` domain differs from the page's registered domain |
| Brand mismatch | 30 | Page mentions a known brand (PayPal, Google, Microsoft, Apple, Amazon, Netflix, etc.) but the domain is not the official one |
| Cross-domain redirect | 10 | Redirect chain crosses a registered domain boundary |
| Too many redirects | 10 | More than 3 redirects in the chain |
| Non-HTTPS final page | 10 | Final URL uses HTTP, not HTTPS |
| Hidden/tiny iframes | 10 | Iframes with `display:none`, `visibility:hidden`, or dimensions < 5 px |

The `live_score` is the sum of weights for all triggered signals, capped at 100.

---

## Combined Scoring Formula

```
combined = 0.6 × live_score + 0.4 × (ML phishing probability × 100)
```

This weights live behavioral evidence more heavily than the static ML score, while still letting the ML model contribute context (domain age, typosquatting, TLD reputation, etc.) that the browser cannot observe.

If the page could not be loaded (see `COULD_NOT_VERIFY` below), the system falls back to the ML score alone:

```
combined = ML phishing probability × 100
```

---

## Verdict Bands

| Verdict | Condition |
|---------|-----------|
| `PHISHING` | `combined_score` ≥ 60 |
| `SUSPICIOUS` | `combined_score` 30–59 |
| `LIKELY_SAFE` | `combined_score` < 30 |
| `COULD_NOT_VERIFY` | Page failed to load (timeout, DNS failure, bot-blocked, or taken down) |

When the verdict is `COULD_NOT_VERIFY`, the `combined_score` is derived from the ML model alone and the result clearly indicates the live scan did not complete.

---

## Limitations

- **Cloaking** — Sophisticated phishing pages may detect headless browsers (via user-agent, WebGL fingerprint, or timing) and serve a benign page to evade detection.
- **Bot detection** — Sites that block automated browsers return errors or redirect loops, yielding `COULD_NOT_VERIFY`.
- **Performance** — Each scan takes 5–15 seconds depending on page load time and redirect depth.
- **Takedowns** — A phishing page may have been removed between when it was reported and when the scan runs.
- **No JS sandbox** — Playwright can observe the page's behavior and DOM state, but it cannot fully sandbox JavaScript execution or prevent all side effects.
- **Screenshots** — Screenshots may contain sensitive information (e.g., pre-filled credential forms). They are held in memory only for the duration of the job and are never stored in the database.

---

## Safety Model

### SSRF Protection

Every network request the browser makes — including redirects, sub-resource loads (images, scripts, stylesheets), and fetch/XHR calls — is intercepted via Playwright's `page.route` handler before it reaches the network stack. The interceptor resolves the target hostname to an IP address and checks it against a blocklist of private and reserved ranges:

| Range | Description |
|-------|-------------|
| `10.0.0.0/8` | RFC 1918 private |
| `172.16.0.0/12` | RFC 1918 private |
| `192.168.0.0/16` | RFC 1918 private |
| `127.0.0.0/8` | Loopback |
| `169.254.0.0/16` | Link-local / AWS metadata |
| `100.64.0.0/10` | Carrier-grade NAT |
| `::1/128` | IPv6 loopback |
| `fc00::/7` | IPv6 unique local |
| `fe80::/10` | IPv6 link-local |

Any request that resolves to a blocked range is aborted and logged. This prevents the scanner from being used as an SSRF proxy to reach internal services.

> **TEST_MODE**: Setting `TEST_MODE=true` bypasses the localhost block to allow test URLs like `http://127.0.0.1`. Never enable this in production.

### Observation Only

The scanner never types into form fields, clicks submit buttons, or interacts with the page in any way. It is a passive observer.

### Browser Hardening

The Chromium instance is launched with:
- `--no-sandbox` (required in Docker; mitigated by running as a non-root user inside a container)
- `--disable-extensions`
- `accept_downloads=False`
- `ignore_https_errors=False`

### Container Isolation

The live-scanner runs as a separate Docker service (see [Docker Isolation](#docker-isolation)). It does not share a volume with the database and runs as a non-root user (`scanner`).

---

## Setup

### Install dependencies

```bash
pip install playwright==1.44.0 tldextract anthropic
playwright install chromium
```

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LIVE_SCAN_ENABLED` | `true` | Feature flag — set to `false` to disable live scanning |
| `LIVE_SCAN_TIMEOUT_MS` | `15000` | Playwright browser navigation timeout in milliseconds |
| `LIVE_SCAN_MAX_WORKERS` | `2` | `ThreadPoolExecutor` workers for concurrent background scans |
| `LLM_VERDICT_ENABLED` | `false` | Enable Anthropic LLM-based brand impersonation check |
| `ANTHROPIC_API_KEY` | *(unset)* | Anthropic API key (required if `LLM_VERDICT_ENABLED=true`) |
| `LIVE_SCANNER_ORIGIN` | `http://ml-service:5000` | CORS allowed origin for the live-scanner service |
| `TEST_MODE` | `false` | Allow localhost scanning — **never enable in production** |

---

## Optional LLM Verdict

Set `LLM_VERDICT_ENABLED=true` and provide `ANTHROPIC_API_KEY=sk-ant-...` to enable an additional Anthropic Claude analysis step.

When enabled, after the rule-based scan completes, the scanner sends:
- A screenshot of the final page (base64-encoded PNG)
- The visible page text (stripped of scripts/styles)

to the Anthropic API. The model returns whether the page appears to impersonate a known brand or collect credentials.

**Prompt injection protection**: The system prompt explicitly instructs the model to treat all page content as untrusted data and to ignore any instructions it finds embedded in the page text or screenshot. The model's role is limited to answering a structured classification question.

The LLM verdict is advisory — it does not change the `combined_score` bands but is included in the response as `llm_verdict` for human review.

---

## Docker Isolation

The live-scanner is deployed as a separate Docker Compose service to limit blast radius:

```yaml
# docker-compose.yml (relevant excerpt)
live-scanner:
  build: ./live-scanner
  user: "scanner"           # non-root user
  mem_limit: 1g
  cpus: 1.0
  tmpfs:
    - /tmp
    - /home/scanner
  # No database volume mount — stateless service
  environment:
    - LIVE_SCAN_ENABLED=true
    - LIVE_SCAN_TIMEOUT_MS=15000
    - LIVE_SCAN_MAX_WORKERS=2
    - LIVE_SCANNER_ORIGIN=http://ml-service:5000
```

Key isolation properties:

| Property | Value | Reason |
|----------|-------|--------|
| User | `scanner` (non-root, UID 1001) | Limits damage if Chromium is exploited |
| Memory limit | 1 GB | Prevents a runaway browser from starving other services |
| CPU limit | 1.0 core | Prevents scan storms from impacting the ML service |
| tmpfs mounts | `/tmp`, `/home/scanner` | Ephemeral storage — nothing persists after the container stops |
| Database volume | Not mounted | Scanner cannot read or write scan history |

**Recommended**: Add egress firewall rules at the Docker network level (e.g., `iptables` rules on the host or a network policy in Kubernetes) to block traffic to RFC 1918 address spaces as a defence-in-depth measure alongside the application-level SSRF protection.

---

## API Endpoints

These are the two endpoints added to the Node gateway for live scanning:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scan/url/live` | Start a live scan job. Body: `{"url": "..."}`. Returns `202` with `{job_id, status: "queued"}`. |
| `GET` | `/api/scan/url/live/:jobId` | Poll for job result. Returns `{status, result?, error?}`. |

### Job lifecycle

```
queued → running → done
                 ↘ failed
```

Poll every 1.5 seconds until `status` is `done` or `failed`. Typical scan time is 5–15 seconds.

### Example response (`done`)

```json
{
  "job_id": "a3f2c1d9",
  "status": "done",
  "result": {
    "url": "https://paypa1-secure.example.com/login",
    "verdict": "PHISHING",
    "combined_score": 78,
    "live_score": 85,
    "ml_score": 67,
    "evidence": [
      { "signal": "password_field",     "weight": 25, "detail": "Found 1 password input" },
      { "signal": "brand_mismatch",     "weight": 30, "detail": "Mentions PayPal; domain is not paypal.com" },
      { "signal": "cross_domain_form",  "weight": 25, "detail": "Form posts to data-collect.ru" }
    ],
    "redirect_chain": [
      "http://paypa1-secure.example.com/login",
      "https://paypa1-secure.example.com/login"
    ],
    "final_url": "https://paypa1-secure.example.com/login",
    "llm_verdict": null,
    "scan_duration_ms": 7432
  }
}
```

---

## Related Files

| File | Purpose |
|------|---------|
| `detection/live_scanner.py` | Core scanner: Playwright launch, SSRF intercept, evidence collection, scoring |
| `ml-service/app.py` | Flask endpoints: `POST /api/scan/url/live`, `GET /api/scan/url/live/<job_id>`, job store, TTL cleanup |
| `server/src/services/mlClient.ts` | `startLiveScan()` and `getLiveScanJob()` typed axios wrappers |
| `server/src/controllers/scanController.ts` | Express handlers for live scan routes |
| `server/src/routes/` | Routes with 5/min rate limit on live scan endpoints |
| `client/src/pages/UrlScanner.tsx` | Mode toggle (Quick / Live), polling stepper, verdict badge, evidence list, redirect timeline, screenshot preview |
| `client/src/pages/History.tsx` | "Live" badge on history rows for `URL_LIVE` scan type |
| `live-scanner/` | Isolated Docker service (Playwright image, non-root user, no DB volume) |
| `tests/test_live_scanner.py` | Unit and API tests: SSRF safety checks, scoring, combined formula, Flask endpoints |
