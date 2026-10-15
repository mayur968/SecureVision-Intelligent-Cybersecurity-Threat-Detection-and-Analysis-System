"""Authentication blueprint for SecureVision — Stage 2 Google OAuth.

Provides:
  GET  /auth/google/login     → redirect to Google OAuth
  GET  /auth/google/callback  → exchange code, upsert User, set session
  POST /auth/logout           → clear session
  GET  /api/auth/me           → current user info (never 401)

Session-based auth using Flask's signed cookie session.
If GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not configured the login
route returns 501 and the app runs in guest-only mode.
"""
from __future__ import annotations

import hmac
import secrets
import time
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlencode, urlparse
import urllib.request
import json

from flask import (
    Blueprint, current_app, jsonify, redirect, request, session, url_for
)
from database.models import db, User

auth_bp = Blueprint('auth', __name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _google_enabled() -> bool:
    return bool(
        current_app.config.get('GOOGLE_CLIENT_ID') and
        current_app.config.get('GOOGLE_CLIENT_SECRET')
    )


def require_auth(f):
    """Decorator: returns 401 JSON if no user_id in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated


def _safe_redirect_url(next_url: str | None) -> str:
    """Validate 'next' param: must be a local path (starts with / but not //)."""
    if next_url and next_url.startswith('/') and not next_url.startswith('//'):
        # Reject anything that looks like a different host
        parsed = urlparse(next_url)
        if not parsed.scheme and not parsed.netloc:
            return next_url
    return '/dashboard'


def _exchange_code_for_tokens(code: str, redirect_uri: str) -> dict:
    """POST to Google token endpoint and return the JSON response."""
    payload = urlencode({
        'code':          code,
        'client_id':     current_app.config['GOOGLE_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
        'redirect_uri':  redirect_uri,
        'grant_type':    'authorization_code',
    }).encode()
    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=payload,
        method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _decode_id_token(id_token: str) -> dict:
    """Decode the JWT payload without full signature verification.

    We verify iss, aud, and exp. Full RSA signature verification would
    require fetching Google's JWKS endpoint; for a server-side only flow
    this lightweight check is sufficient when the token comes directly
    from the token endpoint over TLS.
    """
    parts = id_token.split('.')
    if len(parts) != 3:
        raise ValueError('Invalid JWT structure')

    import base64
    # Pad to a multiple of 4
    payload_b64 = parts[1] + '=' * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))

    # Basic validation
    iss = payload.get('iss', '')
    if iss not in ('https://accounts.google.com', 'accounts.google.com'):
        raise ValueError(f'Unexpected issuer: {iss}')

    aud = payload.get('aud', '')
    client_id = current_app.config['GOOGLE_CLIENT_ID']
    if isinstance(aud, list):
        if client_id not in aud:
            raise ValueError('Client ID not in aud claim')
    elif aud != client_id:
        raise ValueError(f'aud mismatch: {aud}')

    exp = payload.get('exp', 0)
    if time.time() > exp:
        raise ValueError('Token has expired')

    return payload


def _upsert_user(claims: dict) -> User:
    """Create or update a User row from Google ID token claims."""
    google_sub = claims['sub']
    user = User.query.filter_by(google_sub=google_sub).first()
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(
            google_sub=google_sub,
            email=claims.get('email'),
            name=claims.get('name'),
            picture=claims.get('picture'),
            created_at=now,
            last_login=now,
        )
        db.session.add(user)
    else:
        # Update mutable fields on each login
        user.email      = claims.get('email', user.email)
        user.name       = claims.get('name', user.name)
        user.picture    = claims.get('picture', user.picture)
        user.last_login = now
    db.session.commit()
    return user


# ── Routes ─────────────────────────────────────────────────────────────────────

@auth_bp.route('/auth/google/login', methods=['GET'])
def google_login():
    """Redirect browser to Google's OAuth 2.0 authorization endpoint."""
    if not _google_enabled():
        return jsonify({'success': False, 'error': 'Google sign-in is not configured'}), 501

    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    # Preserve 'next' so we can redirect there after login
    next_url = request.args.get('next', '')
    if next_url:
        session['oauth_next'] = next_url

    redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
    params = urlencode({
        'response_type': 'code',
        'client_id':     current_app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri':  redirect_uri,
        'scope':         'openid email profile',
        'state':         state,
        'access_type':   'online',
        'prompt':        'select_account',
    })
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{params}')


@auth_bp.route('/auth/google/callback', methods=['GET'])
def google_callback():
    """Handle Google's redirect: exchange code for tokens, upsert user."""
    # Validate state to prevent CSRF
    state = request.args.get('state', '')
    expected = session.pop('oauth_state', None)
    if not expected or not hmac.compare_digest(state, expected):
        return jsonify({'success': False, 'error': 'Invalid OAuth state'}), 400

    error = request.args.get('error')
    if error:
        return jsonify({'success': False, 'error': f'OAuth error: {error}'}), 400

    code = request.args.get('code', '')
    if not code:
        return jsonify({'success': False, 'error': 'Missing authorization code'}), 400

    try:
        redirect_uri = current_app.config['GOOGLE_REDIRECT_URI']
        token_resp = _exchange_code_for_tokens(code, redirect_uri)
        id_token_str = token_resp.get('id_token', '')
        if not id_token_str:
            return jsonify({'success': False, 'error': 'No ID token returned'}), 500

        claims = _decode_id_token(id_token_str)
        user = _upsert_user(claims)
        session['user_id'] = user.id
        session.permanent = True

        next_url = _safe_redirect_url(session.pop('oauth_next', None))
        return redirect(next_url)

    except Exception as exc:
        current_app.logger.error(f'OAuth callback error: {type(exc).__name__}')
        return jsonify({'success': False, 'error': 'Authentication failed'}), 500


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    """Clear the session. Validates Origin to prevent CSRF.

    The origin's *hostname* must match the Flask server's hostname, or the
    origin netloc must be ``localhost:5173`` (Vite dev server).  An explicit
    hostname comparison is used so that a crafted origin like
    ``http://localhost.evil.com`` cannot pass — its hostname is
    ``localhost.evil.com``, not ``localhost``.
    """
    origin = request.headers.get('Origin', '')

    if origin:
        origin_netloc  = urlparse(origin).netloc           # e.g. localhost:5000
        origin_host    = origin_netloc.split(':')[0]       # e.g. localhost
        server_host    = request.host.split(':')[0]        # e.g. localhost

        # Allow requests from the same server hostname (any port) or the Vite
        # dev server (localhost:5173).
        if origin_host != server_host and origin_netloc != 'localhost:5173':
            return jsonify({'success': False, 'error': 'Forbidden'}), 403

    session.clear()
    return jsonify({'success': True})


@auth_bp.route('/api/auth/me', methods=['GET'])
def auth_me():
    """Return current user info. Always 200 — never 401."""
    google_enabled = _google_enabled()
    user_id = session.get('user_id')
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            return jsonify({
                'authenticated':  True,
                'google_enabled': google_enabled,
                'name':           user.name,
                'email':          user.email,
                'picture':        user.picture,
            })
        # Session has stale user_id; clean it up
        session.pop('user_id', None)

    return jsonify({
        'authenticated':  False,
        'google_enabled': google_enabled,
    })
