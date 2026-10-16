# Stage 2 Complete — Optional Google Sign-In

## What was implemented (first pass)

- **Packages**: `authlib` and `flask-cors` installed; added to `requirements.txt`
- **`.env.example`**: Added `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SECRET_KEY`, `SHOW_LEGACY_TO_ALL` placeholders
- **`config.py`**: Added `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SECRET_KEY`, `SHOW_LEGACY_TO_ALL`, `GOOGLE_ENABLED` property
- **Migration 0003** (`migrations/versions/0003_auth.py`): Creates `users` table and adds `user_id` + `anon_session_id` columns to `scan_history`; idempotent up/down; applied to `securevision.db`
- **`database/models.py`**: Added `User` model; `ScanHistory` gains `user_id`, `anon_session_id`, `is_legacy` derived field; `save_scan` and `get_recent_scans` updated with ownership params
- **`database/auth.py`**: Auth blueprint — `/auth/google/login`, `/auth/google/callback`, `/auth/logout`, `/api/auth/me`; session-based, no JWT client storage
- **`app.py`**: CORS init, blueprint registration, anon session assignment on scan routes, history ownership filtering
- **`client/vite.config.ts`**: `cookieDomainRewrite: 'localhost'` on both `/api` and `/auth` proxies
- **`client/src/context/AuthContext.tsx`**: Real `AuthUser` interface, `AuthProvider` fetching `/api/auth/me`
- **`client/src/pages/Login.tsx`**: Full-page login — Google button or guest mode based on `google_enabled`
- **`client/src/components/layout/Layout.tsx`**: Top bar with guest/loading/signed-in states and avatar dropdown
- **`tests/test_auth.py`**: 13 tests covering all routes, ownership filtering, and migration round-trip

## Review findings fixed (second pass)

| Finding | Fix applied |
|---|---|
| Logout CSRF fail-open — `if origin:` bypassed on missing header | Changed to `if not origin: return 403` — now fail-closed |
| `render_as_batch` only via Flask-Migrate path | Added `conf_args.setdefault('render_as_batch', True)` to `migrations/env.py` `run_migrations_online` |
| `SECRET_KEY` no production guard | Added assertion in `Config.init_app` that raises `RuntimeError` when `DEBUG=False` and key equals the default |
| Migration test silently skips in CI | Replaced `pytest.skip` + backup-file dependency with inline DB generation (`upgrade 0002` → `upgrade` → `downgrade` → `upgrade`); test always executes |
| (bonus) Two new logout tests | Added `test_logout_missing_origin_rejected` (→ 403) and `test_logout_foreign_origin_rejected` (→ 403) to document the fix |

## Test results

```
15 passed in 6.67s
```

All 15 tests pass. No skips. The two pre-existing failures (`test_clean_text`, `test_normalize_url`) are unrelated to Stage 2 and were not touched.

## Git commits

1. `feat: Stage 2 — optional Google sign-in, migration 0003, ownership filtering`
2. `fix: Stage 2 review findings — CSRF fail-closed, render_as_batch, SECRET_KEY guard, migration test`
