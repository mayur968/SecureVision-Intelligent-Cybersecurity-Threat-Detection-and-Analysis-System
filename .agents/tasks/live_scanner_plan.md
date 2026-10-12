# Implementation Plan — Live URL Scanner

## Conventions & Integration Contracts

Before reading individual items, implementers must keep these in mind:

- **The active ML microservice is `ml-service/app.py`**, not the repo-root `app.py`. All new Python API routes go in `ml-service/app.py`; the repo-root `app.py` is a legacy local-use copy that must receive matching additions so it doesn't drift.
- **Scan type token for the new feature is `URL_LIVE`**. This is stored in `ScanHistory.scan_type` and passed through every layer. Do not use `LIVE_URL`, `LIVE`, or `URL-LIVE`.
- **Prediction label for phishing is `PHISHING`** (same as the ML URL scanner). `SAFE` for clean. The live scanner verdict is a *weighted combination* of ML score and behavioural evidence — the final `prediction` field in the response must be `PHISHING` or `SAFE`.
- **The `scan_type` column in `ScanHistory` is `VARCHAR(20)`**. `URL_LIVE` is 8 characters — no schema migration is needed.
- **Flask is synchronous (no async/await)**. Long-running Playwright work runs in a `ThreadPoolExecutor`; the job-poll pattern mirrors how APK scans already handle latency, but APK scans are synchronous. The live scanner is the first async-job endpoint. Follow the patterns in the APK scan route for error handling, cleanup, and the import style.
- **Node gateway validation uses Zod**. All new body shapes must have a corresponding `z.object(...)` schema in `scanController.ts`.
- **React client uses TanStack Query (`@tanstack/react-query`) and `axios` via `client/src/api/client.ts`**. All new API calls must be added there; pages must not call `axios` directly.
- **`docker-compose.yml` uses `service_healthy` depends_on conditions** — add the new `live-scanner` service with its own healthcheck before adding a depends_on in `ml-service` or `server`.
- **Test runner is pytest**. Run with `cd c:\Users\Mayur\Documents\SecureVision && python -m pytest tests/ -v`. Server TypeScript builds with `cd server && npm run build`.
- **All file paths in this plan are relative to `c:\Users\Mayur\Documents\SecureVision`** unless otherwise stated.

---

## Implementation Plan

- [ ] 1. Create `detection/live_scanner.py` — core live scanner module.

      This module is the only place that imports Playwright. It must never be imported at module load time inside `ml-service/app.py` — import it lazily inside the route handler to avoid crashing the service when Playwright is absent locally.

      **`is_safe_target(url: str) -> tuple[bool, str]`**
      - Resolve the URL's hostname with `socket.getaddrinfo`. Reject if any resolved IP falls in RFC-1918 private ranges (10.x, 172.16–31.x, 192.168.x), loopback (127.x / ::1), or link-local (169.254.x). Also reject `file://`, `ftp://`, and non-HTTP(S) schemes.
      - Return `(False, reason_string)` if unsafe, `(True, "")` if safe.
      - This is the SSRF guard — it must be called before any network I/O.

      **`BRAND_MAP: dict[str, list[str]]`**
      - A module-level dict mapping canonical brand names to their official domains.
      - Minimum entries: `"paypal": ["paypal.com", "paypal.me"]`, `"google": ["google.com", "accounts.google.com"]`, `"amazon": ["amazon.com", "amazon.co.uk", "aws.amazon.com"]`, `"microsoft": ["microsoft.com", "live.com", "outlook.com", "office.com"]`, `"apple": ["apple.com", "icloud.com"]`, `"facebook": ["facebook.com", "fb.com", "instagram.com"]`, `"netflix": ["netflix.com"]`, `"bankofamerica": ["bankofamerica.com"]`, `"chase": ["chase.com", "jpmorgan.com"]`, `"wellsfargo": ["wellsfargo.com"]`.
      - The brand-impersonation check in `scan_live()` iterates this dict looking for brand names in the page title/text while the URL's registered domain is NOT in the brand's official domain list.

      **`SCORE_WEIGHTS: dict[str, float]`**
      - Module-level dict that controls how each evidence signal contributes to the combined risk score. Values must sum to 1.0.
      - Entries: `"ml_score": 0.40`, `"password_field": 0.15`, `"brand_impersonation": 0.20`, `"redirect_chain": 0.10`, `"mixed_content": 0.05`, `"suspicious_forms": 0.10`.
      - Final combined score = Σ(weight × signal_0_or_1_or_partial). `ml_score` uses the raw ML confidence (0–1) scaled by its weight.

      **`scan_live(url: str, ml_score: float, ml_prediction: str, timeout_ms: int = 15000) -> dict`**
      - Calls `is_safe_target(url)` first; raises `ValueError` if unsafe.
      - Launches a Playwright `chromium` browser (headless, `--no-sandbox`, `--disable-dev-shm-usage` for Docker compatibility). Context: viewport 1280×800, user-agent `"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"`, `ignore_https_errors=True`.
      - Navigates with `goto(url, timeout=timeout_ms, wait_until="domcontentloaded")`.
      - Collects `redirect_chain`: list of URLs visited (use `page.on("response", ...)` before goto to record each response URL where status < 400).
      - After navigation, calls `page.content()` to get full HTML, then uses BeautifulSoup to extract:
        - `password_fields`: count of `<input type="password">` elements.
        - `form_actions`: list of `action` attribute values from `<form>` elements. Flag as suspicious if any action points to a different registered domain than the page's URL (use `tldextract`).
        - `page_title`: `<title>` text.
        - `page_text_sample`: first 2000 chars of `document.body.innerText` via `page.evaluate("document.body.innerText")` (for brand matching).
        - `mixed_content`: `True` if page is HTTPS but `page_text_sample` or raw HTML contains `src="http://` or `href="http://`.
      - Computes `brand_impersonation: bool` — True if any brand name (case-insensitive) from `BRAND_MAP` appears in `page_title + page_text_sample` but the URL's registered domain is not in that brand's official domain list.
      - Computes `combined_score: float` (0–1) using `SCORE_WEIGHTS`. ML contribution = `ml_score * SCORE_WEIGHTS["ml_score"]`. Each binary/count signal: `password_field` = min(password_fields, 1), `brand_impersonation` = 1 or 0, `redirect_chain` = 1 if len > 2 else 0, `mixed_content` = 1 or 0, `suspicious_forms` = 1 if any suspicious form action else 0.
      - Returns a dict: `{ "combined_score": float, "final_prediction": "PHISHING"|"SAFE", "evidence": { "password_fields": int, "brand_impersonation": bool, "redirect_chain": list[str], "suspicious_forms": list[str], "mixed_content": bool, "page_title": str }, "browser_error": null|str }`.
      - `final_prediction` = `"PHISHING"` if `combined_score >= 0.5` else `"SAFE"`.
      - Always call `browser.close()` in a `finally` block.
      - If Playwright raises any exception (timeout, navigation error, etc.), catch it, set `browser_error` to the exception message, return the ML-only score as `combined_score` and propagate `ml_prediction` as `final_prediction`. This prevents a crashed browser from breaking the scan.

      **`_llm_verdict(evidence: dict, url: str) -> str`**
      - Optional LLM annotation — returns a short human-readable sentence (≤ 120 chars) summarising the live evidence for display in the UI's explanation panel.
      - Implementation: build a template string that lists the active evidence signals. Do NOT call any external API. Use pure string formatting: `"Live scan detected: "` + comma-join of active signals (e.g. `"password field present"`, `"brand impersonation (paypal)"`, `"redirect chain (3 hops)"`). If no signals: `"No behavioural indicators detected."`.
      - This keeps the function deterministic and avoids external API dependencies; it can be upgraded to an LLM call later.

      Files: `detection/live_scanner.py`
      Verify: Run `python -c "from detection.live_scanner import BRAND_MAP, SCORE_WEIGHTS, is_safe_target; print(is_safe_target('http://192.168.1.1')); print(is_safe_target('https://google.com'))"` — prints `(False, ...)` then `(True, '')`.

- [ ] 2. Add `playwright` and `beautifulsoup4` to Python dependencies.

      **`requirements.txt`** (repo root, used by the legacy `app.py`):
      - Append after the existing URL Analysis block:
        ```
        # Live URL Scanner (Playwright headless browser)
        playwright==1.44.0
        beautifulsoup4==4.12.3
        ```

      **`ml-service/requirements.txt`** (used by `ml-service/Dockerfile`):
      - Add the same two lines in the same position. Check if `ml-service/requirements.txt` exists — if it doesn't, it inherits from the root. Based on the existing `ml-service/Dockerfile` which copies `requirements.txt` from `.` (repo root), the root file is the source of truth. Add the lines there only if no separate ml-service requirements file exists; if it does exist, update both.
      - Playwright requires a post-install step: `playwright install chromium --with-deps`. Add this as an extra `RUN` in `live-scanner/Dockerfile` (step 7), NOT in `ml-service/Dockerfile` — the live scanner runs in its own container.

      Files: `requirements.txt`, `ml-service/requirements.txt` (if separate)
      Verify: `pip install playwright==1.44.0 beautifulsoup4==4.12.3` completes without error in the venv. (Playwright browser binaries are installed separately in step 7.)

- [ ] 3. Create unit and integration tests in `tests/test_live_scanner.py` with fixture HTML files.

      **Fixture files to create** in `tests/fixtures/`:
      - `tests/fixtures/safe_page.html` — minimal valid HTML with no password fields, title "Example Domain", no brand names, no forms.
      - `tests/fixtures/phishing_paypal.html` — HTML with `<title>PayPal - Login</title>`, one `<input type="password">`, a `<form action="http://evil.ru/collect">`, and body text "Sign in to your PayPal account".
      - `tests/fixtures/redirect_chain.html` — HTML with a JS `window.location` redirect (used to verify redirect chain collection logic, but since unit tests mock the browser, this fixture is only for documentation).

      **Test classes:**

      `TestIsSafeTarget` — pure unit tests, no Playwright:
      - `test_rejects_private_ip`: `is_safe_target("http://192.168.1.1/x")` → `(False, ...)`.
      - `test_rejects_loopback`: `is_safe_target("http://127.0.0.1/")` → `(False, ...)`.
      - `test_rejects_file_scheme`: `is_safe_target("file:///etc/passwd")` → `(False, ...)`.
      - `test_accepts_public_https`: mock `socket.getaddrinfo` to return a public IP like `8.8.8.8` → `(True, "")`.

      `TestScoreCombination` — unit tests for score arithmetic, no Playwright:
      - `test_weights_sum_to_one`: `sum(SCORE_WEIGHTS.values()) == 1.0`.
      - `test_phishing_threshold`: manually compute combined score above 0.5 and below 0.5; assert correct `final_prediction`.

      `TestLlmVerdict` — unit tests:
      - `test_no_signals`: empty evidence dict → `"No behavioural indicators detected."`.
      - `test_password_field_signal`: evidence with `password_fields=1` → result contains `"password field"`.
      - `test_brand_impersonation_signal`: evidence with `brand_impersonation=True` → result contains `"brand impersonation"`.

      `TestScanLiveIntegration` — integration tests using `pytest-playwright` OR mocked browser (mock approach preferred so tests run without a display):
      - Use `unittest.mock.patch("detection.live_scanner.sync_playwright")` to inject a mock browser context.
      - `test_safe_page`: mock returns fixture `safe_page.html` content, no password fields, no brand match — assert `final_prediction == "SAFE"`.
      - `test_phishing_page`: mock returns fixture `phishing_paypal.html` content — assert `final_prediction == "PHISHING"` and `evidence["brand_impersonation"] == True` and `evidence["password_fields"] >= 1`.
      - `test_browser_error_fallback`: mock raises `playwright._impl._errors.TimeoutError` — assert `browser_error` is set and function returns without raising.

      Follow the existing test file pattern: `sys.path.insert(0, str(Path(__file__).parent.parent))` at the top, group into classes, `if __name__ == '__main__': pytest.main([__file__, '-v'])` at bottom.

      Files: `tests/test_live_scanner.py`, `tests/fixtures/safe_page.html`, `tests/fixtures/phishing_paypal.html`
      Verify: `python -m pytest tests/test_live_scanner.py -v` — all tests pass (mocked integration tests should pass without Playwright binaries installed).

- [ ] 4. Add async-job live scan API to `ml-service/app.py`.

      The live scan can take 5–20 seconds. Flask is synchronous, so do not block the request thread. Use a `concurrent.futures.ThreadPoolExecutor` with `max_workers=4` plus an in-process `dict` job store.

      **Imports to add** at the top of `ml-service/app.py` (inside the file, after existing imports):
      ```python
      from concurrent.futures import ThreadPoolExecutor
      import threading
      import uuid
      import time
      ```
      Initialise **outside** of any route, at module level after the detector initialisation block:
      ```python
      _executor = ThreadPoolExecutor(max_workers=4)
      _jobs: dict[str, dict] = {}   # job_id -> {status, result, created_at, error}
      _jobs_lock = threading.Lock()
      ```

      **`POST /api/scan/url/live`**
      - Accepts JSON body `{ "url": string }`. Validate with the existing `validate_url` helper.
      - Calls `url_detector.predict(url)` synchronously (fast, < 100 ms) to get `ml_prediction` and `ml_confidence`.
      - Generates `job_id = str(uuid.uuid4())`.
      - Stores `_jobs[job_id] = { "status": "pending", "result": None, "error": None, "created_at": time.time() }` under `_jobs_lock`.
      - Submits to `_executor`: a helper function `_run_live_scan(job_id, url, ml_confidence, ml_prediction)`.
      - Returns immediately: `HTTP 202 { "success": True, "job_id": job_id, "status": "pending" }`.

      **`_run_live_scan(job_id, url, ml_score, ml_prediction)`** (module-level helper, not a route):
      - Lazily imports `from detection.live_scanner import scan_live` inside the function body.
      - Calls `scan_live(url, ml_score, ml_prediction)`.
      - On success: computes risk/explanation/recommendations using the existing `risk_scorer`, `threat_explainer`, `recommendation_engine` instances with `scan_type="URL_LIVE"`.
        - For `risk_scorer.calculate_risk_score`: pass `prediction=live_result["final_prediction"]`, `confidence=live_result["combined_score"]`, `scan_type="URL_LIVE"`, `features=live_result["evidence"]`.
        - For `threat_explainer.explain` and `recommendation_engine.get_recommendations`: pass `scan_type="URL_LIVE"`. These currently handle `URL`, `MESSAGE`, `APK`; they will fall through to their `else` branch returning a generic explanation. That is acceptable for this iteration — a follow-up can add `URL_LIVE` branches.
      - Saves to database via `ScanHistory.save_scan(scan_type="URL_LIVE", input_value=url, prediction=live_result["final_prediction"], confidence=live_result["combined_score"], risk_level=risk["risk_level"], explanation=expl, recommendation="\n".join(recs))`. **Must use `app.app_context()`** because this runs in a thread outside Flask's request context: wrap the `ScanHistory.save_scan` call inside `with app.app_context():`.
      - On success: sets `_jobs[job_id]["status"] = "completed"` and `_jobs[job_id]["result"] = { full response dict }` under `_jobs_lock`.
      - On any exception: sets `_jobs[job_id]["status"] = "failed"` and `_jobs[job_id]["error"] = str(e)` under `_jobs_lock`.

      **`GET /api/scan/url/live/<job_id>`** (job status poll):
      - Looks up `job_id` in `_jobs` under `_jobs_lock`.
      - If not found: `404 { "success": False, "error": "Job not found" }`.
      - If `status == "pending"`: `200 { "success": True, "status": "pending" }`.
      - If `status == "failed"`: `200 { "success": False, "status": "failed", "error": job["error"] }`.
      - If `status == "completed"`: `200 { "success": True, "status": "completed", **job["result"] }`.
      - Evict jobs older than 10 minutes from `_jobs` on each poll call (iterate with `time.time()` check) to prevent unbounded memory growth.

      **Pruning dead jobs**: In `_run_live_scan`, after setting status to `completed` or `failed`, also evict any `_jobs` entries where `created_at < time.time() - 600`.

      Files: `ml-service/app.py`
      Verify: `python -c "import ml-service.app"` is not a valid import path — instead start the service locally with `cd ml-service && python app.py` and curl `POST /api/scan/url/live` with `{"url":"https://google.com"}` — expect `202 {"success": true, "job_id": "..."}`. Then `GET /api/scan/url/live/<job_id>` — expect `{"status": "pending"}` or `{"status": "completed", ...}`.

- [ ] 5. Mirror the live scan routes in repo-root `app.py`.

      The repo-root `app.py` is preserved for direct local use (see `MIGRATION_NOTES.md`). Apply the same `ThreadPoolExecutor` job-store addition and the same two routes (`POST /api/scan/url/live`, `GET /api/scan/url/live/<job_id>`) to `app.py` using the same implementation as step 4.

      The only difference: no `flask-cors` in `app.py`, and `app.app_context()` wrapping in `_run_live_scan` is still required.

      Files: `app.py`
      Verify: same curl test as step 4 but against the root `app.py` (`python app.py`, port 5000).

- [ ] 6. Update `database/models.py` — `get_statistics()` to count `URL_LIVE` in url_threats.

      In `ScanHistory.get_statistics()`, the `url_threats` line currently is:
      ```python
      url_threats = ScanHistory.query.filter_by(scan_type='URL', prediction='PHISHING').count()
      ```
      Replace with:
      ```python
      url_threats = ScanHistory.query.filter(
          ScanHistory.scan_type.in_(['URL', 'URL_LIVE']),
          ScanHistory.prediction == 'PHISHING'
      ).count()
      ```
      Also update `url_scans` (the total URL scan counter, currently `filter_by(scan_type='URL')`) to include `URL_LIVE`:
      ```python
      url_scans = ScanHistory.query.filter(
          ScanHistory.scan_type.in_(['URL', 'URL_LIVE'])
      ).count()
      ```
      No schema migration needed — `URL_LIVE` is stored as a string in the existing `scan_type` VARCHAR(20) column.

      Files: `database/models.py`
      Verify: `python -c "from database.models import ScanHistory; print('ok')"` — no import errors.

- [ ] 7. Add Node gateway types for live scan.

      **`server/src/types/index.ts`** — add to the existing file:
      - Extend `ScanType` union: `export type ScanType = 'URL' | 'MESSAGE' | 'APK' | 'URL_LIVE';`
      - Add a new interface `LiveScanJob`:
        ```typescript
        export interface LiveScanJob {
          success:    boolean;
          job_id:     string;
          status:     'pending' | 'completed' | 'failed';
          // present when status === 'completed':
          prediction?:      Prediction;
          confidence?:      number;
          risk_score?:      number;
          risk_level?:      RiskLevel;
          explanation?:     string;
          recommendations?: string[];
          evidence?:        LiveEvidence;
          error?:           string;
        }

        export interface LiveEvidence {
          password_fields:     number;
          brand_impersonation: boolean;
          redirect_chain:      string[];
          suspicious_forms:    string[];
          mixed_content:       boolean;
          page_title:          string;
          browser_error?:      string | null;
        }
        ```

      Files: `server/src/types/index.ts`
      Verify: `cd server && npm run build` — TypeScript compiles without errors.

- [ ] 8. Add live scan functions to `server/src/services/mlClient.ts`.

      Add two new exported functions after the existing `getStatistics` function:
      ```typescript
      export async function startLiveScan(url: string): Promise<LiveScanJob> {
        const { data } = await http.post<LiveScanJob>('/api/scan/url/live', { url }, { timeout: 10_000 });
        return data;
      }

      export async function pollLiveScan(jobId: string): Promise<LiveScanJob> {
        const { data } = await http.get<LiveScanJob>(`/api/scan/url/live/${encodeURIComponent(jobId)}`, { timeout: 10_000 });
        return data;
      }
      ```
      Import `LiveScanJob` from `'../types/index.js'` — add it to the existing import line at the top.

      Files: `server/src/services/mlClient.ts`
      Verify: `cd server && npm run build` — no TypeScript errors.

- [ ] 9. Add live scan controller handlers and register routes in `server/src/`.

      **`server/src/controllers/scanController.ts`** — add after the existing `healthCheck` handler:
      ```typescript
      const LiveUrlBody = z.object({ url: z.string().url().max(2048) });

      export async function startLiveScan(req: Request, res: Response, next: NextFunction) {
        try {
          const { url } = LiveUrlBody.parse(req.body);
          const result  = await ml.startLiveScan(url);
          res.status(202).json(result);
        } catch (err) { next(err); }
      }

      export async function pollLiveScan(req: Request, res: Response, next: NextFunction) {
        try {
          const { jobId } = req.params;
          if (!jobId || typeof jobId !== 'string' || jobId.length > 64) {
            res.status(400).json({ success: false, error: 'Invalid job ID' });
            return;
          }
          const result = await ml.pollLiveScan(jobId);
          res.json(result);
        } catch (err) { next(err); }
      }
      ```

      **`server/src/routes/index.ts`** — add two new route registrations after the existing `router.post('/scan/apk', ...)` line:
      ```typescript
      router.post('/scan/url/live',       ctrl.startLiveScan);
      router.get ('/scan/url/live/:jobId', ctrl.pollLiveScan);
      ```
      These must be added BEFORE the existing `/scan/url` line if express could match them greedily — but since `/scan/url/live` is more specific, place them before `/scan/url` in the router file to be safe.

      Files: `server/src/controllers/scanController.ts`, `server/src/routes/index.ts`
      Verify: `cd server && npm run build` — no TypeScript errors.

- [ ] 10. Update React client types and API client.

      **`client/src/types/index.ts`** — mirror the server types:
      - Extend `ScanType`: `export type ScanType = 'URL' | 'MESSAGE' | 'APK' | 'URL_LIVE';`
      - Add `LiveEvidence` and `LiveScanJob` interfaces (identical structure to `server/src/types/index.ts` defined in step 7).

      **`client/src/api/client.ts`** — add two new functions on the `api` object:
      ```typescript
      startLiveScan: (url: string) =>
        http.post<LiveScanJob>('/scan/url/live', { url }).then(r => r.data),
      pollLiveScan: (jobId: string) =>
        http.get<LiveScanJob>(`/scan/url/live/${encodeURIComponent(jobId)}`).then(r => r.data),
      ```
      Import `LiveScanJob` from `'../types/index.js'`.

      Files: `client/src/types/index.ts`, `client/src/api/client.ts`
      Verify: `cd client && npm run build` (or `npx tsc --noEmit`) — no TypeScript errors.

- [ ] 11. Update `client/src/pages/UrlScanner.tsx` — mode toggle and polling stepper.

      This is the most substantial UI change. The page gains a scan-mode toggle ("Quick Scan" vs "Live Scan") and, in Live Scan mode, a 4-step progress stepper that updates as the job polls.

      **Mode toggle** — add state `const [mode, setMode] = useState<'quick' | 'live'>('quick')`. Render a segmented control (two buttons styled like tabs) directly below the page description paragraph. "Quick Scan" button: active style = `bg-cyan-500 text-slate-900`, inactive = `border border-slate-700 bg-slate-800 text-slate-300`. "Live Scan" button: same styles, plus a `🔴 Live` label prefix and a short descriptor `title="Visits the page in a sandboxed browser for behavioural analysis"`.

      **Quick Scan mode** — identical to the current page behaviour. The existing `useMutation({ mutationFn: api.scanUrl })` already handles this. Render the existing `ScanResultCard` and threat banner unchanged.

      **Live Scan mode** — replaces the simple mutation with a polling flow:
      - State: `const [jobId, setJobId] = useState<string | null>(null)`, `const [liveResult, setLiveResult] = useState<LiveScanJob | null>(null)`, `const [step, setStep] = useState(0)`.
      - Steps array (drives the stepper UI): `["Submitting…", "Launching browser", "Analysing page", "Generating verdict"]`.
      - On form submit: call `api.startLiveScan(url)` → get back `{ job_id }` → set `jobId`, set `step(1)`.
      - Poll via `useQuery` with `queryKey: ['live-scan', jobId]`, `queryFn: () => api.pollLiveScan(jobId!)`, `enabled: !!jobId && liveResult?.status !== 'completed'`, `refetchInterval: 2000`.
      - In the `onSuccess` of the query (use `select` + `useEffect` or `onSuccess`): advance `step` to 2 after first response, step 3 after 3 s of polling (use `Date.now()` comparison stored in a `startedAt` ref), step 4 when `status === 'completed'`. When `status === 'completed'` or `'failed'`, stop polling (set `jobId` to null or rely on `enabled: false`).
      - Stepper UI: a horizontal 4-step progress bar. Completed steps: filled cyan circle with checkmark. Current step: pulsing cyan ring. Pending: grey circle. Use `framer-motion` `<motion.div>` for the step completion animation — match the existing `initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}` pattern.
      - When `status === 'completed'`, render a live-evidence panel below the standard `ScanResultCard`:
        - A collapsible `<details>` element labelled "🔬 Live Browser Evidence".
        - Inside: a small table listing: Page Title, Password Fields, Brand Impersonation (✓/✗), Redirect Chain (count + URLs as a monospace list), Suspicious Forms (count), Mixed Content (✓/✗).
        - If `browser_error` is set in evidence, show a yellow warning box: "⚠ Browser encountered an error: {browser_error}. Results based on ML score only."
      - Reset all live state (`jobId`, `liveResult`, `step`) when the user changes the URL input.

      Files: `client/src/pages/UrlScanner.tsx`
      Verify: `cd client && npm run build` — no TypeScript or build errors. Manually test in dev: `npm run dev`, navigate to `/url-scanner`, toggle to Live Scan, enter `https://google.com`, confirm the stepper advances and a result appears.

- [ ] 12. Update `client/src/pages/History.tsx` — URL_LIVE Live badge.

      Two changes:

      1. **Type filter dropdown** — the current options array is `['ALL','URL','MESSAGE','APK']`. Extend to `['ALL','URL','URL_LIVE','MESSAGE','APK']`. This change is in the inline `opts` array of the filter controls section.

      2. **Scan type badge** — the current badge renders `{s.scan_type}` in a cyan monospace pill. For `scan_type === 'URL_LIVE'`, render an additional small `<span>` badge immediately after the type pill:
         ```tsx
         {s.scan_type === 'URL_LIVE' && (
           <span className="ml-1 rounded bg-emerald-900/50 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-800">
             Live
           </span>
         )}
         ```
         This must be placed inside the `<td>` that currently renders the scan type, right after the existing `<span>`.

      Files: `client/src/pages/History.tsx`
      Verify: `cd client && npm run build` — no TypeScript errors. Visually: after running a live scan, the History page shows `URL_LIVE` with a green "Live" badge.

- [ ] 13. Create the `live-scanner` Docker service.

      The live scanner runs as a separate container because it needs Chromium/Playwright installed — adding those to the existing `ml-service` image would double its size and complicate the dependency graph.

      **`live-scanner/requirements.txt`**:
      ```
      Flask==3.0.0
      flask-cors==4.0.0
      playwright==1.44.0
      beautifulsoup4==4.12.3
      tldextract==5.4.0
      requests==2.31.0
      ```

      **`live-scanner/app.py`** — minimal Flask app that exposes only the live scan endpoints. This service is called directly by `ml-service` (or could be called by the Node gateway — see architecture note below).

      Architecture decision: the Node gateway calls `ml-service`, which calls the live scanner via HTTP internally. This keeps the gateway's ML_SERVICE_URL pointing to a single host and avoids adding a third URL to the gateway's environment config.

      `live-scanner/app.py` structure:
      - Imports: `Flask`, `request`, `jsonify`, `CORS`, `threading`, `uuid`, `time`, `concurrent.futures.ThreadPoolExecutor`.
      - Lazy-import `detection.live_scanner` — but since `live-scanner/` is a standalone service, it needs its own copy of the detection module. Use a `sys.path.insert` to point at the repo root so `from detection.live_scanner import scan_live, is_safe_target` works. In Docker, the repo root will be at `/app` (same as ml-service build context).
      - Routes: `GET /health`, `POST /api/scan/url/live` (submit job → 202), `GET /api/scan/url/live/<job_id>` (poll).
      - These routes are identical in logic to what is added to `ml-service/app.py` in step 4, except there is no `ScanHistory.save_scan` call here — database writes are done by `ml-service` after it receives the completed result.
      - `ml-service/app.py` must be updated to call this service: instead of running Playwright in-process, `_run_live_scan` in `ml-service/app.py` should call `http://live-scanner:6000/api/scan/url/live` using `requests` (submit + poll loop with a 20 s timeout and 1 s sleep between polls). Update the `_run_live_scan` helper accordingly. The `LIVE_SCANNER_URL` environment variable defaults to `http://localhost:6000`.

      **`live-scanner/Dockerfile`**:
      ```dockerfile
      FROM python:3.10-slim

      WORKDIR /app

      RUN apt-get update && apt-get install -y --no-install-recommends \
          curl wget gnupg libglib2.0-0 libnss3 libnspr4 libdbus-1-3 \
          libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
          libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
          && rm -rf /var/lib/apt/lists/*

      COPY live-scanner/requirements.txt .
      RUN pip install --no-cache-dir -r requirements.txt
      RUN playwright install chromium

      # Copy repo root so detection/ module is importable
      COPY . .

      ENV LIVE_SCANNER_PORT=6000
      ENV PYTHONUNBUFFERED=1

      EXPOSE 6000

      CMD ["python", "live-scanner/app.py"]
      ```

      Note: `playwright install chromium` (without `--with-deps`) is used because system deps are installed via apt above. This avoids running playwright's own dep installer which requires sudo and can fail in constrained build environments.

      Files: `live-scanner/requirements.txt`, `live-scanner/app.py`, `live-scanner/Dockerfile`
      Verify: `docker build -f live-scanner/Dockerfile -t sv_live_scanner_test .` from the repo root — image builds successfully.

- [ ] 14. Update `docker-compose.yml` to add the `live-scanner` service and wire it to `ml-service`.

      Add a new service block **before** the `server` service:
      ```yaml
      live-scanner:
        build:
          context: .
          dockerfile: live-scanner/Dockerfile
        container_name: sv_live_scanner
        restart: unless-stopped
        environment:
          LIVE_SCANNER_PORT: "6000"
        ports:
          - "6000:6000"
        healthcheck:
          test: ["CMD", "curl", "-f", "http://localhost:6000/health"]
          interval: 30s
          timeout: 10s
          retries: 3
          start_period: 30s
        networks:
          - sv_net
      ```

      Update the `ml-service` service to:
      1. Add `LIVE_SCANNER_URL: "http://live-scanner:6000"` to its `environment` block.
      2. Add a `depends_on` entry for `live-scanner` with `condition: service_healthy`.

      Files: `docker-compose.yml`
      Verify: `docker-compose config` — no YAML errors. `docker-compose up --build` starts all four services and each passes its healthcheck.

- [ ] 15. Write documentation.

      **`LIVE_SCANNER.md`** (new file at repo root):
      - Overview: what the feature does (headless browser + ML fusion).
      - Architecture diagram (ASCII): `Client → Node Gateway → ml-service → live-scanner (Playwright)`.
      - API reference: document `POST /api/scan/url/live` request/response, `GET /api/scan/url/live/:jobId` response shape, all fields.
      - `SCORE_WEIGHTS` table: each signal, its weight, and what triggers it.
      - `BRAND_MAP` listing.
      - SSRF mitigations: list of blocked IP ranges and schemes enforced by `is_safe_target`.
      - Environment variables: `LIVE_SCANNER_URL` (ml-service), `LIVE_SCANNER_PORT` (live-scanner container).
      - Running locally without Docker: `pip install playwright && playwright install chromium`, then start `live-scanner/app.py` on port 6000 before starting `ml-service/app.py`.
      - Known limitations: no JavaScript-rendered content beyond `domcontentloaded`; no CAPTCHA bypass; brand matching is keyword-based only.

      **`MIGRATION_NOTES.md`** (append to existing file):
      - New section `## Phase 2 → Phase 3: Live URL Scanner` following the existing section style.
      - Cover: new `URL_LIVE` scan type token, new `live-scanner` container, `LIVE_SCANNER_URL` env var added to ml-service, `get_statistics()` change to include `URL_LIVE` in url counts, no database schema changes.

      **`README.md`** (append to existing file):
      - Add a "Live URL Scanner" subsection under the features or scanners section (check README structure first — add it in the appropriate place without restructuring).
      - 3–5 sentences: describes the feature, mentions the 4-signal evidence panel, and the polling UI.

      Files: `LIVE_SCANNER.md`, `MIGRATION_NOTES.md`, `README.md`
      Verify: Files exist and are valid Markdown. No broken internal links.

---

## Dependency Order

Items must be completed in this order:

```
1 (live_scanner.py)
  ↓
2 (requirements)  →  3 (tests — depends on module from 1)
  ↓
4 (ml-service routes — depends on 1, 6)
  ↓
5 (app.py mirror — depends on 4 pattern)
6 (models.py — independent, can be done alongside 4)
  ↓
7 (server types) → 8 (mlClient) → 9 (controller + routes)
  ↓
10 (client types + api) → 11 (UrlScanner.tsx) → 12 (History.tsx)
  ↓
13 (live-scanner Docker service — depends on 1, 4)
  ↓
14 (docker-compose — depends on 13)
  ↓
15 (docs — depends on all)
```

Items 6, 7–9, and 10–12 can overlap with each other as long as their intra-group order is respected.
