# Optional Google Sign-In with Session-Based Auth and Scan Ownership

Stage 2 adds optional Google OAuth 2.0 sign-in to SecureVision. When credentials are configured, users can authenticate via a standard server-side OAuth flow; when they aren't, the app runs in anonymous-guest mode unchanged. Scan history rows are now tagged with either a `user_id` (authenticated) or an `anon_session_id` (guest), and legacy pre-auth rows remain queryable via a `SHOW_LEGACY_TO_ALL` flag. The frontend gains a login page, an auth context, and a top-bar that reflects the three states: loading, signed-in with avatar, and guest with "Sign in" link.

Watch for: (1) **confirmed** — `SESSION_COOKIE_SECURE` is evaluated at class-parse time against the class-level `DEBUG` attribute; if the env var changes after the class is defined but before `app.config.from_object(Config)` is called there is no issue, but the comment "read from env so SESSION_COOKIE_SECURE resolves correctly at startup" is inaccurate — it resolves at *class definition* time, not at startup. In practice this works correctly given how Flask loads config, but it is a latent trap for anyone who subclasses `Config`. (2) **confirmed** — The `_safe_redirect_url` open-redirect guard is untested: no test exercises `next=//evil.com`, `next=https://evil.com`, or `next=/legit/path`. (3) **possible** — `handleSignOut` in `Layout.tsx` does not explicitly set an `Origin` header; browsers inject it automatically for credentialed cross-origin fetches, but a non-browser client or a same-origin request from a production deployment behind a reverse proxy may omit it, triggering the 403 guard unexpectedly.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The OAuth flow is correctly structured end-to-end: state parameter is CSRF-protected with `hmac.compare_digest`, the ID token is decoded and validated for `iss`, `aud`, `exp`, and `email_verified`, the token never touches client storage, and the session is a signed Flask cookie. The signature is not RSA-verified — the code relies on the token arriving over TLS from the token endpoint — which is a documented, widely-accepted trade-off for server-side flows and is called out in a comment.

Session cookie flags (`HttpOnly`, `SameSite=Lax`, `Secure` when not in debug) are all set. The `SECRET_KEY` production guard raises `RuntimeError` at startup if the default key is used outside debug mode. `SESSION_COOKIE_SECURE = not DEBUG` is evaluated at class-parse time, which is correct for this codebase's single-class config pattern but is described misleadingly in a comment.

The logout CSRF guard requires a present `Origin` header whose hostname matches the server or equals `localhost:5173`, and is fail-closed on missing `Origin`. The frontend's `handleSignOut` does not set an explicit `Origin` header; it relies on the browser injecting it. This is correct browser behavior, but the guard will fire for any non-browser consumer and warrants a note in the API docs.

History ownership is cleanly layered: `get_recent_scans` branches on `user_id` first (returns only that user's rows), then on `anon_session_id` + `show_legacy` for guests. The `is_legacy` field in `to_dict()` is additive, the original key shape is preserved, and the test confirms that a signed-in user cannot see legacy or other users' rows.

The DB migration is idempotent in both directions via `_table_exists` / `_column_exists` guards, uses `batch_alter_table` for SQLite compatibility, and the round-trip test (up → down → up on a fresh SQLite file seeded from `0002`) always executes — it no longer depends on a committed backup file.

The test suite covers 15 cases: `/api/auth/me` for guest, signed-in, and stale-session; Google login 501 and 302; logout clearing session, idempotent no-session, missing-origin 403, and foreign-origin 403; guest scan access (no 401); history ownership with flag on/off and user-isolation; and the full migration round-trip.

---

<details>
<summary>Issues (4)</summary>

1. **`SESSION_COOKIE_SECURE` comment is misleading** — The comment says the value is resolved "at startup rather than being hard-wired"; it actually resolves at class-definition time. No functional bug today, but it will silently produce the wrong value if anyone reads `DEBUG` from an environment that changes after import. Remove or correct the comment, and consider moving the assignment into `init_app` so it genuinely resolves at startup. (LOW)

2. **`_safe_redirect_url` open-redirect guard is untested** — No test passes `next=//evil.com`, `next=https://evil.com`, or a normal local path like `next=/history` through the login flow. A regression in the guard could re-open open-redirect without the test suite catching it. Add at least three unit-level test cases for `_safe_redirect_url` directly, or exercise it through the callback route. (MEDIUM)

3. **`handleSignOut` relies on implicit browser `Origin` injection** — The logout fetch sends only `Content-Type: application/json` in the headers object; the `Origin` header is browser-injected. Any non-browser consumer (curl, Postman, a future mobile client, a server-side test that bypasses the CSRF guard by not setting Origin) will receive a 403 unexpectedly. This is intentional for CSRF, but the API contract should be documented and the logout test in `test_auth.py` should verify that the header is actually required in the production code path (the existing test does this for the server, but the client code silently ignores the 403 due to the `try/catch` best-effort block). (LOW)

4. **`_safe_redirect_url` is not exercised through the full callback flow** — The function exists and has correct logic, but because the OAuth callback is not testable without mocking `_exchange_code_for_tokens` and `_decode_id_token`, the `oauth_next` → redirect path is never exercised end-to-end in the test suite. A test that mocks the token exchange and verifies the redirect target after a successful callback would close this gap. (LOW)

</details>

---

<details>
<summary>Details</summary>

## `SESSION_COOKIE_SECURE` resolved at class-parse time

```python
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
...
SESSION_COOKIE_SECURE = not DEBUG   # resolves here, at import time
```

The class-level comment reads "read from env so SESSION_COOKIE_SECURE resolves correctly *at startup* rather than being hard-wired to False". This is inaccurate: the value resolves when the module is imported, not when the app starts. In the current codebase this makes no practical difference — `DEBUG` is read from env once and never mutated. But the comment sets a false expectation for a subclass author who might write `DEBUG = True` in a subclass and expect `SESSION_COOKIE_SECURE` to follow, which it won't because the parent class has already evaluated `not DEBUG`. Moving the assignment to `init_app` would make the claim true and remove the trap. Confirmed LOW severity.

## Open-redirect guard coverage gap

`_safe_redirect_url` correctly rejects `//evil.com` (starts with `//`) and `https://evil.com` (has a `netloc`). The logic is sound. What's missing is any automated verification: there are no tests for this function, and the callback route that uses `oauth_next` is not exercised in the test suite at all. If the guard were accidentally removed or a new code path bypassed it, no test would fail. Confirmed MEDIUM — open-redirect is a direct security regression risk, and the fix is a small set of direct unit tests.

## CSRF guard and the frontend client contract

The logout CSRF guard is correctly fail-closed: a missing `Origin` returns 403, a foreign origin returns 403. This is confirmed by `test_logout_missing_origin_rejected` and `test_logout_foreign_origin_rejected`. The frontend's `handleSignOut` does not need to set `Origin` explicitly — browsers inject it automatically for any credentialed cross-origin `fetch`. The gap is documentation: the `catch` block in `handleSignOut` is intentionally silent (best-effort sign-out), which means a 403 from the server is silently swallowed on the client side. This is acceptable for the browser case but should be noted — if this endpoint is ever called from a non-browser context that doesn't inject `Origin`, the session will appear cleared on the client (because `refetch()` is called regardless) while the server session persists. Possible LOW severity.

</details>

---

<details>
<summary>File map</summary>

| File | What changed |
|---|---|
| `database/auth.py` | New file — auth blueprint with Google OAuth routes, CSRF logout guard, `/api/auth/me` |
| `database/models.py` | `User` model added; `ScanHistory` gains `user_id`, `anon_session_id`, `is_legacy`; `get_recent_scans` and `save_scan` updated |
| `migrations/versions/0003_auth.py` | New migration — `users` table + `scan_history` ownership columns, idempotent up/down |
| `app.py` | CORS init, blueprint registration, anon session assignment on all three scan routes, history ownership filtering |
| `config.py` | Google OAuth settings, session cookie flags, `SECRET_KEY` production guard, `SHOW_LEGACY_TO_ALL` flag |
| `client/src/context/AuthContext.tsx` | New file — `AuthUser` interface, `AuthProvider`, `useAuth` hook fetching `/api/auth/me` with credentials |
| `client/src/pages/Login.tsx` | New file — Google sign-in or guest-mode card based on `google_enabled` |
| `client/src/components/layout/Layout.tsx` | Top bar extended with loading/signed-in/guest auth states and avatar dropdown |
| `client/vite.config.ts` | `cookieDomainRewrite: 'localhost'` added to both `/api` and `/auth` proxy entries |
| `tests/test_auth.py` | New file — 15 tests covering auth routes, CSRF, ownership filtering, migration round-trip |

Full diff: `git diff main` or compare commits listed in `stage2_complete.md`.

</details>
