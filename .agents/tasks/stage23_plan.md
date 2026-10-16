# SecureVision — Stage 2 & 3 Implementation Plan

## Findings from code reading

**Conflicts / gaps resolved before planning:**

1. **`pytest.ini` has `--browser chromium`** — this is a pytest-playwright option that causes non-Playwright tests to fail unless `pytest-playwright` is installed. New Python tests must be written to run without pytest-playwright (they are pure Flask/unit tests) and should be invoked with `pytest tests/test_auth.py -p no:playwright` to bypass that default flag, or the pytest.ini `addopts` must be split. The plan uses the `-p no:playwright` escape hatch per test file to avoid changing pytest.ini globally.

2. **No `flask-cors` or `authlib` in `requirements.txt`** — both are absent; they must be pip-installed and added to `requirements.txt`.

3. **`ScanHistory.save_scan` takes no `user_id`** — ownership filtering requires adding a nullable `user_id` FK column to `scan_history` in migration 0003. `save_scan`'s signature must accept an optional `user_id` kwarg. The API caller passes `user_id` from the session when available; anonymous scans get `user_id=None`.

4. **`AuthContext` exports `User = null` as a type** — the type must be replaced with an interface; the existing shape is a simple placeholder and can be replaced wholesale.

5. **No Google OAuth client ID is in `.env.example`** (file doesn't exist yet) — we create it in item 1 with all new keys.

6. **`config.py` uses `Config.TESTING` flag directly** — session/cookie settings can piggyback on the same class; no second config class needed.

7. **`vite.config.ts` proxy for `/auth`** already exists but has no `cookieDomainRewrite` — must be added for session cookies to work across dev origins.

8. **Email scanner (Stage 3)** uses `imaplib` / `email` (stdlib) + the existing `message_detector` pipeline; no new Python ML package is needed. The `.eml` upload path is analogous to the APK upload path already in `app.py`.

9. **Statistics shape** (`get_statistics`) must be extended for EMAIL scan type; the frontend `Statistics` type and `api_get_statistics` must match. The extension is additive (new optional keys) to avoid breaking existing dashboard.

10. **`ScanTypeExtended`** in `types/index.ts` is `ScanType | 'URL_LIVE'`; it needs `| 'EMAIL'` added.

---

## Stage 2 — Authentication

### Item 1 — pip installs and requirements.txt

Install `authlib` and `flask-cors`, then record exact pinned versions in `requirements.txt`.

**Decision:** Use `Authlib` (OAuth 2.0 / OIDC client) rather than `Flask-Dance` because Authlib has first-class PKCE and token-introspection support and integrates cleanly with Flask sessions. Use `Flask-CORS` for cross-origin cookie support in development.

Files: `requirements.txt`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\pip.exe show authlib flask-cors` — both packages show a version.

---

### Item 2 — `.env.example` with all new keys

Create `.env.example` at the project root with placeholder values for every new environment variable introduced in Stage 2 and Stage 3. No real secrets; only key names and explanatory comments.

New keys needed:
- `SECRET_KEY` (already used, confirm placeholder)
- `GOOGLE_CLIENT_ID` — OAuth 2.0 client ID from Google Cloud Console
- `GOOGLE_CLIENT_SECRET` — OAuth 2.0 client secret
- `GOOGLE_REDIRECT_URI` — `http://localhost:5000/auth/callback`
- `CORS_ORIGINS` — `http://localhost:5173` (comma-separated for production)
- `SESSION_COOKIE_SAMESITE` — `Lax`
- `SESSION_COOKIE_SECURE` — `false` for dev, `true` for prod

Files: `.env.example`

Verify: File exists with all seven keys; no actual secrets.

---

### Item 3 — `config.py` additions

Add CORS, session-cookie, and Google OAuth settings to `Config`. Read from env vars with safe defaults that allow the app to start without any `.env` file (guest mode).

Add to `Config`:
```python
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
SESSION_COOKIE_SECURE   = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
GOOGLE_CLIENT_ID     = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI  = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback')
```

Files: `config.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "from config import Config; print(Config.CORS_ORIGINS)"` — prints `['http://localhost:5173']`.

---

### Item 4 — Alembic migration 0003: `users` table + `scan_history.user_id`

Create `migrations/versions/0003_auth_users.py` following the exact pattern of `0002_phase1_unified_schema.py`:
- Use `_table_exists` / `_column_exists` guards for idempotency.
- Use `op.batch_alter_table` for any `scan_history` changes (SQLite requirement; `render_as_batch=True` is already set in `migrate_app.py`).

New `users` table columns:
```
id           INTEGER PK autoincrement
email        VARCHAR(255) NOT NULL UNIQUE
display_name VARCHAR(100) nullable
avatar_url   VARCHAR(512) nullable
google_sub   VARCHAR(128) nullable UNIQUE  -- stable Google user identifier
created_at   DATETIME NOT NULL server_default=now()
last_login   DATETIME nullable
```

New column on `scan_history`:
```
user_id  INTEGER nullable FK→users.id ondelete=SET NULL
```

`down_revision = '0002_phase1_unified_schema'`

Files: `migrations/versions/0003_auth_users.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -m flask --app migrate_app db upgrade` — exits 0; `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('securevision.db'); print([r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()])"` — lists all six column names.

---

### Item 5 — `User` model in `database/models.py`

Add the `User` SQLAlchemy model and update `ScanHistory` to carry the FK.

Changes:
1. Add `class User(db.Model)` with `__tablename__ = 'users'` and all columns from item 4, plus `to_dict()`.
2. Add `user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)` to `ScanHistory`.
3. Add `owner = db.relationship('User', foreign_keys=[user_id], lazy='select')` to `ScanHistory`.
4. Update `ScanHistory.save_scan` to accept `user_id=None` kwarg and pass it to the constructor.
5. Update `ScanHistory.get_recent_scans` to accept an optional `user_id` parameter: when provided, filter by `ScanHistory.user_id == user_id`; when absent, return all (existing behavior, used by tests).
6. Update `ScanHistory.to_dict` to include `'user_id': self.user_id` (nullable int).

Files: `database/models.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "from database.models import User; print(User.__tablename__)"` prints `users`.

---

### Item 6 — Flask auth blueprint `database/auth.py`

**Decision:** Session-based auth (Flask `session` dict + `itsdangerous` which Flask ships) rather than JWTs. JWTs add client-side storage complexity; session cookies are simpler, already secured by `SECRET_KEY`, and the Vite proxy already forwards `/auth` routes to Flask.

Create `database/auth.py` as a Flask Blueprint with `url_prefix='/auth'`:

| Route | Method | Description |
|---|---|---|
| `/auth/login` | GET | Redirect to Google OAuth authorization URL (PKCE). Stores `state` + `code_verifier` in Flask session. |
| `/auth/callback` | GET | Exchange code for tokens, fetch userinfo, upsert `User` row, store `user_id` in `session['user_id']`, redirect to `/dashboard`. |
| `/auth/logout` | POST | Clear `session['user_id']`, return `{"success": true}`. |
| `/auth/me` | GET | Return current user dict or `{"user": null}` for anonymous. |

Use `authlib.integrations.flask_client.OAuth` to register the Google provider. Guard startup: if `GOOGLE_CLIENT_ID` is empty, the `/auth/login` route returns `{"error": "OAuth not configured"}` 501 instead of crashing.

Files: `database/auth.py`

Verify: App imports without error: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "from database.auth import auth_bp; print(auth_bp.name)"` — prints `auth`.

---

### Item 7 — Register auth blueprint and CORS in `app.py`

1. Import and register `auth_bp` with `app.register_blueprint(auth_bp)`.
2. Import `Flask-CORS` and call `CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)` immediately after `app = Flask(__name__)` / `app.config.from_object(Config)`.
3. Update `api_get_history` route: read `session.get('user_id')`; pass it to `ScanHistory.get_recent_scans(limit=limit, user_id=user_id)` — logged-in users see only their scans; anonymous users (`user_id=None`) see all scans (current behavior preserved for backward compat in dev/testing).
4. Update all four `ScanHistory.save_scan` call sites in `app.py` (URL, MESSAGE, APK, URL_LIVE) to pass `user_id=session.get('user_id')`.

Files: `app.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "import app; print([r.url_prefix for r in app.app.blueprints.values()])"` — shows `/auth` blueprint registered. Flask starts without error.

---

### Item 8 — `vite.config.ts` — add `cookieDomainRewrite` to `/auth` proxy

Add `cookieDomainRewrite: 'localhost'` to the `/auth` proxy entry so that session cookies set by Flask on port 5000 are rewritten to `localhost` and accepted by the browser on port 5173.

```ts
'/auth': {
  target: 'http://localhost:5000',
  changeOrigin: true,
  secure: false,
  cookieDomainRewrite: 'localhost',
},
```

Also add the same to the `/api` proxy so scan endpoints can read `session['user_id']`.

Files: `client/vite.config.ts`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 9 — Replace `AuthContext.tsx`

Replace the skeleton with a real implementation:

```tsx
export interface User {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  logout: () => Promise<void>;
}
```

`AuthProvider` calls `GET /auth/me` on mount (via `useEffect`) to hydrate the user from the existing session cookie. `logout` calls `POST /auth/logout` then clears local state. Use `useState` + `useEffect`. No third-party auth library on the frontend — the backend is the authority.

Files: `client/src/context/AuthContext.tsx`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 10 — Replace `Login.tsx` with functional login page

Replace the placeholder with a real sign-in page that:
1. Shows a "Sign in with Google" button that navigates to `/auth/login` (a plain `<a href="/auth/login">` so the browser follows it as a full navigation — not an `axios` call, because OAuth redirect must be a real navigation).
2. Shows a "Continue as guest" link to `/dashboard`.
3. If the user is already logged in (`useAuth().user !== null`) redirects immediately to `/dashboard` via `<Navigate>`.
4. Shows a loading spinner while `useAuth().loading` is true.

Files: `client/src/pages/Login.tsx`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 11 — Update `Layout.tsx` top bar with auth state

Replace the static top-bar right side (currently just an `ML API :5000` badge) with:
- When logged in: user avatar/initials chip + display name + logout button (calls `useAuth().logout()`).
- When logged out: a "Sign in" link to `/login`.
- Keep the `ML API :5000` badge regardless.

Use `useAuth()` hook. No new packages — use existing Tailwind tokens.

Files: `client/src/components/layout/Layout.tsx`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 12 — `tests/test_auth.py`

Write pytest tests for the auth blueprint using an in-memory SQLite app (following the `test_phase1.py` fixture pattern). Run with `-p no:playwright` to avoid the pytest.ini `--browser chromium` flag.

Tests to cover:
- `GET /auth/me` returns `{"user": null}` when no session.
- `POST /auth/logout` returns `{"success": true}` even with no active session.
- `GET /auth/login` returns 501 when `GOOGLE_CLIENT_ID` is empty (guard).
- `ScanHistory.get_recent_scans(user_id=<id>)` returns only that user's scans.
- `ScanHistory.save_scan(..., user_id=<id>)` stores and retrieves `user_id` correctly.
- `User.to_dict()` returns expected keys.

Files: `tests/test_auth.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -m pytest tests/test_auth.py -p no:playwright -v` — all tests pass.

---

## Stage 3 — Email Scanner

### Item 13 — `detection/email_scanner.py`

Create `detection/email_scanner.py` with class `EmailScanner`. This reuses the existing `message_detector` (already instantiated in `app.py`) rather than training a new model.

**Decision:** Parse uploaded `.eml` files (stdlib `email.message_from_bytes`) plus accept raw text/body POST as a fallback. Extract subject + body text, then run through `MessageDetector.predict()`. Extract URLs from body and run through `URLDetector.predict()` for each (capped at 5 to avoid timeout). Produce a combined result.

```python
class EmailScanner:
    def __init__(self, message_detector, url_detector):
        ...

    def analyze_eml_bytes(self, raw_bytes: bytes) -> dict:
        """Parse .eml, extract text parts, run detectors, return result dict."""

    def analyze_text(self, subject: str, body: str) -> dict:
        """Analyze plain-text email (no file upload). For API flexibility."""
```

Result dict shape (mirrors `ScanResult` on the frontend):
```python
{
  'success': True,
  'prediction': 'PHISHING'|'SAFE'|'SUSPICIOUS',
  'confidence': float,
  'risk_score': int,
  'risk_level': 'LOW'|'MEDIUM'|'HIGH',
  'explanation': str,
  'recommendations': [str],
  'indicators': [str],        # e.g. suspicious URLs found, spoofed sender
  'subject': str,
  'sender': str,
  'url_findings': [           # one entry per URL scanned (up to 5)
      {'url': str, 'prediction': str, 'confidence': float}
  ],
}
```

Files: `detection/email_scanner.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "from detection.email_scanner import EmailScanner; print('OK')"` — prints `OK`.

---

### Item 14 — Flask route `POST /api/scan/email/upload` in `app.py`

Add the email scanner route following the APK scan pattern:
1. Accept `multipart/form-data` with field `file` (.eml) OR `application/json` with `{"subject": "...", "body": "..."}`.
2. Validate: `.eml` extension for file upload; `body` required for JSON mode.
3. Instantiate `EmailScanner(message_detector, url_detector)` once at module load (alongside the other detectors).
4. Call `email_scanner.analyze_eml_bytes(file.read())` or `email_scanner.analyze_text(subject, body)`.
5. Run `RiskScorer`, `ThreatExplainer`, `RecommendationEngine` on the result.
6. Call `ScanHistory.save_scan(scan_type='EMAIL', ..., user_id=session.get('user_id'))`.
7. Extract IOCs from body URLs via `extract_iocs('EMAIL', body_preview, result)`.
8. Return JSON matching `ScanResult` shape + the `subject`, `sender`, `url_findings` extras.

Files: `app.py`

Verify: Flask starts without error: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "import app; print('OK')"` — prints `OK`.

---

### Item 15 — Update `get_statistics` for EMAIL scans

In `database/models.py`, update `ScanHistory.get_statistics()`:
1. Add `email_scans = ScanHistory.query.filter_by(scan_type='EMAIL').count()`.
2. Add `email_threats = ScanHistory.query.filter_by(scan_type='EMAIL', prediction='PHISHING').count()`.
3. Include `email_scans` in the return dict.
4. Add `'email': email_threats` to `threat_breakdown`.

The shape change is additive — existing frontend keys are unchanged.

Files: `database/models.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -c "from database.models import ScanHistory; import inspect; src=inspect.getsource(ScanHistory.get_statistics); print('email_scans' in src)"` — prints `True`.

---

### Item 16 — TypeScript types update

In `client/src/types/index.ts`:
1. Add `'EMAIL'` to `ScanTypeExtended`: `export type ScanTypeExtended = ScanType | 'URL_LIVE' | 'EMAIL'`.
2. Add `email_scans` (number) to `Statistics` interface.
3. Add `email: number` to the `threat_breakdown` object type in `Statistics`.
4. Add new `EmailScanResult` interface extending `ScanResult` with: `subject: string; sender: string; url_findings: Array<{ url: string; prediction: string; confidence: number }>`.

Files: `client/src/types/index.ts`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 17 — API client method for email scanning

In `client/src/api/client.ts`, add:
```ts
scanEmail: (file: File, onProgress?: (pct: number) => void) => {
  const fd = new FormData();
  fd.append('file', file);
  return http.post<EmailScanResult>('/scan/email/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60_000,
    onUploadProgress: e => onProgress?.(Math.round((e.loaded / (e.total ?? 1)) * 100)),
  }).then(r => r.data);
},
```

Import `EmailScanResult` from `'../types/index.js'`.

Files: `client/src/api/client.ts`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 18 — `EmailScanner.tsx` page

Create `client/src/pages/EmailScanner.tsx` following the `ApkScanner.tsx` pattern (file drop + upload). Use the same design tokens and component structure.

Features:
- Drag-and-drop or click-to-select `.eml` file (accepts `.eml` MIME only).
- Upload progress bar (uses `onProgress` callback).
- Displays result in existing `ScanResultCard` + `ExplanationPanel` + `RecommendationList` components.
- Shows `url_findings` as a collapsible table below the main result (inline, no new component needed).
- Shows `subject` and `sender` in a metadata row above the result card.
- Loading/error states consistent with other scanner pages.
- Uses `useMutation` from `@tanstack/react-query` (same as `ApkScanner.tsx`).

Files: `client/src/pages/EmailScanner.tsx`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 19 — Sidebar and routes

1. Add an `Email` icon (inline SVG, consistent with existing icon style) and `{ to: '/scan/email', icon: Icon.Email, label: 'Email Scanner' }` entry to `NAV_ITEMS` in `Sidebar.tsx`, inserted after the `APK Scanner` entry.
2. In `main.tsx`, import `EmailScanner` from `'./pages/EmailScanner.js'` and add:
   ```tsx
   <Route path="scan/email" element={<ErrorBoundary><EmailScanner /></ErrorBoundary>} />
   ```
   inside the `<Route element={<Layout />}>` block, after the APK route.

Files:
- `client/src/components/layout/Sidebar.tsx`
- `client/src/main.tsx`

Verify: `cd c:\Users\Mayur\Documents\SecureVision\client && npx tsc --noEmit` — exits 0.

---

### Item 20 — `tests/test_email_scanner.py`

Write pytest tests for `EmailScanner` and the `/api/scan/email/upload` route. Run with `-p no:playwright`.

Tests to cover:
- `EmailScanner.analyze_text` returns a dict with `success`, `prediction`, `confidence`, `risk_level`.
- `EmailScanner.analyze_eml_bytes` correctly parses a minimal RFC 2822 `.eml` bytes fixture.
- `POST /api/scan/email/upload` with a text/plain body JSON `{"subject": "...", "body": "..."}` returns 200 with `success: true`.
- `POST /api/scan/email/upload` with a `.eml` multipart upload returns 200.
- `POST /api/scan/email/upload` with a non-.eml file returns 400.
- `GET /api/statistics` includes `email_scans` key after an email scan is saved.

The test fixture for `.eml` bytes: create a minimal `email.mime.text.MIMEText` in-memory and use `.as_bytes()` — no file needed on disk.

Files: `tests/test_email_scanner.py`

Verify: `c:\Users\Mayur\Documents\SecureVision\venv\Scripts\python.exe -m pytest tests/test_email_scanner.py -p no:playwright -v` — all tests pass.

---

## Stage 4 gate — Items 21 & 22

### Item 21 — Write `stage4_ready.md`

Create `.agents/tasks/stage4_ready.md` confirming Stage 2 and Stage 3 are complete and listing the verified items:
- Auth blueprint registered at `/auth`
- Session-based login/logout/me working
- Migration 0003 applied
- Email scanner route `/api/scan/email/upload` working
- Frontend routes `/login` and `/scan/email` type-checking clean
- All new tests passing

Files: `.agents/tasks/stage4_ready.md`

Verify: File exists and is non-empty.

---

### Item 22 — Write `phases1_3_complete.md`

Create `.agents/tasks/phases1_3_complete.md` summarising what was built across Stages 1–3: landing page, auth, email scanner. Include the test commands to run for a full regression.

Files: `.agents/tasks/phases1_3_complete.md`

Verify: File exists and is non-empty. **Stop — do not proceed to Stage 4.**

---

## Dependency order summary

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8   (Stage 2 backend then frontend)
             4 ← needed by 5
             5 ← needed by 7
             6 ← needed by 7
9 → 10 → 11 → 12                   (Stage 2 frontend + tests; depends on 7 being done)
13 → 14 → 15 → 16 → 17 → 18 → 19 → 20   (Stage 3; item 14 depends on 13, 15 on 5)
21 → 22                             (Stage 4 gate; depends on all prior items)
```
