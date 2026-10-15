# Stage 2 Complete — Optional Google Sign-In

## Summary

Stage 2 adds optional Google OAuth 2.0 sign-in to SecureVision. When no Google credentials
are configured the app runs in full guest-only mode — no sign-in button, no crashes.

## What Was Done

### Backend

**Packages installed**: `authlib==1.9.1`, `flask-cors==4.0.0` (added to `requirements.txt`)

**.env.example**: Created at project root with placeholders for `SECRET_KEY`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SHOW_LEGACY_TO_ALL`.

**config.py**: Added `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`,
`SHOW_LEGACY_TO_ALL`, and `GOOGLE_ENABLED` property to `Config`.

**Migration 0003** (`migrations/versions/0003_auth.py`):
- Creates `users` table: `id`, `google_sub` (unique), `email`, `name`, `picture`,
  `created_at`, `last_login`.
- Adds `user_id` (INTEGER NULL FK→users.id) and `anon_session_id` (VARCHAR 64 NULL) to
  `scan_history`.
- Idempotent upgrade; clean downgrade tested (up→down→up cycle passes).
- Applied to `securevision.db`; backup at `securevision.db.bak2`.

**database/models.py**:
- Added `User` model with `to_dict()`.
- Added `user_id` FK, `anon_session_id`, and `owner` relationship to `ScanHistory`.
- `ScanHistory.to_dict()` now includes `user_id` and `is_legacy` (True when both owner
  fields are NULL).
- `ScanHistory.get_recent_scans()` accepts `user_id`, `anon_session_id`, `show_legacy`
  for ownership-based filtering.
- `ScanHistory.save_scan()` accepts `user_id` and `anon_session_id` kwargs.

**database/auth.py** (new Flask blueprint `auth`):
- `GET /auth/google/login` — redirects to Google; returns 501 when unconfigured.
- `GET /auth/google/callback` — validates CSRF state, exchanges code, decodes ID token
  (iss/aud/exp checks), upserts User, sets `session['user_id']`.
- `POST /auth/logout` — validates Origin header, clears session.
- `GET /api/auth/me` — always 200; returns `{authenticated, google_enabled, name?, email?,
  picture?}`.

**app.py**:
- Added `flask-cors` CORS init (`origins=['http://localhost:5173']`, `supports_credentials=True`).
- Registered `auth_bp` blueprint.
- Added `import secrets`.
- All four scan routes (`/api/scan/url`, `/api/scan/message`, `/api/scan/apk`,
  `/api/scan/url/live`) now assign `anon_session_id` for guests and pass `user_id` /
  `anon_session_id` to `ScanHistory.save_scan`.
- `/api/history` filters by ownership using `user_id` / `anon_session_id` / `SHOW_LEGACY_TO_ALL`.

### Frontend

**AuthContext.tsx**: Full implementation fetching `/api/auth/me` on mount. Exports
`AuthUser` interface, `AuthProvider` with `{user, loading, refetch}`.

**Login.tsx**: Full dark-themed login page. Google sign-in button (`#4285F4`, inline G SVG)
when `google_enabled=true`; "Sign-in not configured" message when false. "Continue as guest"
button. Privacy note.

**Layout.tsx**: Top bar shows Sign-in link (guest), loading placeholder, or avatar with
name/email dropdown and Sign-out button (signed in).

**vite.config.ts**: Added `cookieDomainRewrite: 'localhost'` to both `/api` and `/auth`
proxy entries.

### Tests

**tests/test_auth.py** — 13 tests, all pass:
- `TestAuthMe` — guest response, signed-in response, stale session
- `TestGoogleLogin` — 501 when unconfigured, redirect when configured
- `TestLogout` — clears session, idempotent with no session
- `TestScanRoutes` — URL and message scans work for guests (no 401)
- `TestHistoryOwnership` — legacy visible/hidden by flag, user sees own scans
- `TestMigration0003` — up/down/up cycle on isolated DB copy

## Verification Results

```
TypeScript (npx tsc --noEmit): EXIT 0
pytest tests/test_auth.py -p no:playwright --override-ini="addopts=": 13/13 PASSED
```

## Notes

- Run tests with: `pytest tests/test_auth.py -p no:playwright --override-ini="addopts=" -v`
- The `--override-ini="addopts="` flag is needed to suppress `--browser chromium` from
  `pytest.ini` for pure unit tests.
- Pre-existing test failures (`test_clean_text`, `test_normalize_url`,
  `test_algorithm_read_from_pkl`) are unchanged by this stage.
