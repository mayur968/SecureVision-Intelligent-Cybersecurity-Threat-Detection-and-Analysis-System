# Stage 4 Ready

Stages 1–3 are complete and committed.
Stage 4 (Gmail OAuth scan) is ready to implement whenever you approve.

## What Stage 4 will add
- Incremental Gmail OAuth consent (gmail.readonly scope, separate from normal login)
- Encrypted refresh token storage (Fernet, key from env)
- Routes: GET /api/gmail/status, GET /auth/gmail/connect, GET /auth/gmail/callback, POST /api/gmail/disconnect, POST /api/gmail/scan
- Gmail Inbox Scan page: connect/disconnect button, label dropdown, scan N emails, results table with verdict + risk score, expandable detail panel
- Rate limiting on /api/gmail/scan
- Privacy: no email body stored, subject snippet + hash only
- Requires sign-in (require_auth decorator); guest sees "Sign in to use Gmail scanning"
