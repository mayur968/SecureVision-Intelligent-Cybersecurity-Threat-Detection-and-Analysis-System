# Stage 2 — Optional Google Sign-In: Complete

## Summary

Stage 2 implemented optional Google OAuth 2.0 authentication for SecureVision. The app
runs in full guest-only mode when no Google credentials are configured.

## What was built

### Backend
- **`database/auth.py`** — Auth blueprint: `GET /auth/google/login`, `GET /auth/google/callback`,
  `POST /auth/logout`, `GET /api/auth/me` (never 401).
- **`database/models.py`** — `User` model (google_sub, email, name, picture, created_at,
  last_login); `ScanHistory` gains `user_id` FK and `anon_session_id`.
- **`migrations/versions/0003_auth.py`** — Alembic migration adding `users` table and
  `scan_history` ownership columns; idempotent upgrade **and** downgrade.
- **`config.py`** — `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`,
  `SECRET_KEY` (single assignment), `SESSION_COOKIE_SAMESITE='Lax'`,
  `SESSION_COOKIE_SECURE=not DEBUG`, `SESSION_COOKIE_HTTPONLY=True`,
  `SHOW_LEGACY_TO_ALL`, `GOOGLE_ENABLED` property.
- **`app.py`** — CORS init, auth blueprint registration, anon session assignment on scan
  routes, ownership filtering on `/api/history`, `is_legacy` field in `ScanHistory.to_dict()`.

### Frontend
- **`AuthContext.tsx`** — Fetches `/api/auth/me` on mount; exposes `{user, loading, refetch}`.
- **`Login.tsx`** — Full-page dark layout; Google button / not-configured message / guest link.
- **`Layout.tsx`** — Top bar: sign-in link (guest), spinner (loading), avatar+dropdown (signed in).
- **`vite.config.ts`** — `cookieDomainRewrite: 'localhost'` on `/api` and `/auth` proxies.

### Tests
- **`tests/test_auth.py`** — 13 tests across 5 classes; all pass.

## Review findings fixed (iteration 2)

| Finding | Fix |
|---|---|
| Session cookie flags not set | Added `SESSION_COOKIE_SAMESITE='Lax'`, `SESSION_COOKIE_SECURE=not DEBUG`, `SESSION_COOKIE_HTTPONLY=True` to `Config` |
| Logout CSRF bypass via hostname substring | Replaced substring test with hostname comparison: `origin_host != server_host` and `origin_netloc != 'localhost:5173'` |
| Non-idempotent downgrade in 0003_auth | Wrapped `drop_column` and `drop_table` in `_column_exists` / `_table_exists` guards |
| Duplicate `SECRET_KEY` in config.py | Removed first (dead) assignment; single assignment remains at line 66 area |

## Verification

- `pytest tests/test_auth.py -p no:playwright --override-ini="addopts=" -v` — 13 passed
- `npx tsc --noEmit` (client/) — exit 0
