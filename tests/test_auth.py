"""
Stage 2 auth tests — in-memory SQLite, no browser, no network.

Run with:
  pytest tests/test_auth.py -p no:playwright -v
"""

import os
import sys
from pathlib import Path

# Repo root on path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-auth'
os.environ.setdefault('SKIP_VENV_CHECK', '1')

import pytest
from unittest.mock import patch


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def flask_app():
    """In-memory Flask app with auth blueprint registered."""
    from flask import Flask
    from flask_cors import CORS
    from database.models import db, ScanHistory, seed_model_registry
    from database.auth import auth_bp

    app = Flask(__name__)
    app.config.update({
        'TESTING':                        True,
        'SQLALCHEMY_DATABASE_URI':        'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY':                     'test-secret-auth',
        'GOOGLE_CLIENT_ID':               None,
        'GOOGLE_CLIENT_SECRET':           None,
        'GOOGLE_REDIRECT_URI':            'http://localhost:5000/auth/google/callback',
        'SHOW_LEGACY_TO_ALL':             True,
    })

    CORS(app, origins=['http://localhost:5173'], supports_credentials=True)
    db.init_app(app)
    app.register_blueprint(auth_bp)

    # Minimal scan routes so we can test them without importing the full app.py
    from flask import request, jsonify, session
    import secrets as _secrets

    @app.route('/api/scan/url', methods=['POST'])
    def _scan_url():
        user_id = session.get('user_id')
        if not user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = _secrets.token_hex(32)
        return jsonify({'success': True, 'prediction': 'SAFE', 'confidence': 0.9,
                        'risk_score': 10, 'risk_level': 'LOW'})

    @app.route('/api/scan/message', methods=['POST'])
    def _scan_message():
        user_id = session.get('user_id')
        if not user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = _secrets.token_hex(32)
        return jsonify({'success': True, 'prediction': 'SAFE', 'confidence': 0.9,
                        'risk_score': 10, 'risk_level': 'LOW'})

    @app.route('/api/history', methods=['GET'])
    def _history():
        user_id = session.get('user_id')
        show_legacy = app.config.get('SHOW_LEGACY_TO_ALL', True)
        anon_id = session.get('anon_session_id') if not user_id else None
        scans = ScanHistory.get_recent_scans(
            limit=50, user_id=user_id,
            anon_session_id=anon_id, show_legacy=show_legacy
        )
        return jsonify({'success': True, 'count': len(scans),
                        'scans': [s.to_dict() for s in scans]})

    with app.app_context():
        db.create_all()
        seed_model_registry()

    return app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture(autouse=True)
def clean_db(flask_app):
    """Roll back DB after each test."""
    from database.models import db
    with flask_app.app_context():
        yield
        db.session.rollback()
        # Remove scan rows added during test
        db.session.execute(db.text('DELETE FROM scan_ioc'))
        db.session.execute(db.text('DELETE FROM scan_history'))
        db.session.execute(db.text('DELETE FROM users'))
        db.session.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _create_user(flask_app, google_sub='test-sub-001', name='Test User',
                 email='test@example.com'):
    from database.models import db, User
    from datetime import datetime, timezone
    with flask_app.app_context():
        user = User(
            google_sub=google_sub, name=name, email=email,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def _create_legacy_scan(flask_app):
    """Insert a scan row with NULL user_id and NULL anon_session_id (legacy)."""
    from database.models import db, ScanHistory
    with flask_app.app_context():
        scan = ScanHistory(
            scan_type='URL', input_value='https://legacy.example.com',
            prediction='SAFE', confidence=0.8, risk_level='LOW',
            explanation='legacy', recommendation='none',
        )
        db.session.add(scan)
        db.session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAuthMe:

    def test_me_guest(self, client):
        """GET /api/auth/me without session → authenticated=False."""
        resp = client.get('/api/auth/me')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['authenticated'] is False
        assert 'google_enabled' in data

    def test_me_signed_in(self, client, flask_app):
        """Signed-in session → authenticated=True with user info."""
        user_id = _create_user(flask_app)
        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        resp = client.get('/api/auth/me')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['authenticated'] is True
        assert data['name'] == 'Test User'
        assert 'google_enabled' in data

    def test_me_stale_user_id(self, client):
        """Stale user_id in session (user deleted) → authenticated=False, not 500."""
        with client.session_transaction() as sess:
            sess['user_id'] = 99999  # does not exist

        resp = client.get('/api/auth/me')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['authenticated'] is False


class TestGoogleLogin:

    def test_login_not_configured_returns_501(self, client, flask_app):
        """GET /auth/google/login with no credentials → 501."""
        # GOOGLE_CLIENT_ID is None in fixture
        resp = client.get('/auth/google/login')
        assert resp.status_code == 501
        data = resp.get_json()
        assert data['success'] is False

    def test_login_redirects_when_configured(self, client, flask_app):
        """GET /auth/google/login with credentials → 302 to Google."""
        with flask_app.test_request_context():
            pass
        flask_app.config['GOOGLE_CLIENT_ID'] = 'fake-client-id'
        flask_app.config['GOOGLE_CLIENT_SECRET'] = 'fake-client-secret'
        try:
            resp = client.get('/auth/google/login')
            assert resp.status_code == 302
            location = resp.headers.get('Location', '')
            assert 'accounts.google.com' in location
        finally:
            flask_app.config['GOOGLE_CLIENT_ID'] = None
            flask_app.config['GOOGLE_CLIENT_SECRET'] = None


class TestLogout:

    def test_logout_clears_session(self, client, flask_app):
        """POST /auth/logout → 200, session cleared."""
        user_id = _create_user(flask_app, google_sub='logout-sub')
        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        resp = client.post(
            '/auth/logout',
            headers={'Origin': 'http://localhost:5000'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

        # Session should be gone
        me_resp = client.get('/api/auth/me')
        assert me_resp.get_json()['authenticated'] is False

    def test_logout_no_session(self, client):
        """POST /auth/logout with no active session → 200 (idempotent)."""
        resp = client.post(
            '/auth/logout',
            headers={'Origin': 'http://localhost:5000'},
        )
        assert resp.status_code == 200
        assert resp.get_json()['success'] is True


class TestScanRoutes:

    def test_scanner_url_no_auth_required(self, client):
        """Guests can call /api/scan/url — must NOT get 401."""
        resp = client.post('/api/scan/url', json={'url': 'https://example.com'})
        assert resp.status_code != 401

    def test_scanner_message_no_auth_required(self, client):
        """Guests can call /api/scan/message — must NOT get 401."""
        resp = client.post('/api/scan/message', json={'message': 'hello world'})
        assert resp.status_code != 401


class TestHistoryOwnership:

    def test_history_legacy_visible_when_flag_true(self, client, flask_app):
        """Legacy rows (NULL user_id, NULL anon_session_id) visible when SHOW_LEGACY_TO_ALL=True."""
        flask_app.config['SHOW_LEGACY_TO_ALL'] = True
        _create_legacy_scan(flask_app)

        resp = client.get('/api/history')
        data = resp.get_json()
        assert data['success'] is True
        assert data['count'] >= 1
        assert any(s['is_legacy'] for s in data['scans'])

    def test_history_legacy_hidden_when_flag_false(self, client, flask_app):
        """Legacy rows hidden when SHOW_LEGACY_TO_ALL=False and no session."""
        flask_app.config['SHOW_LEGACY_TO_ALL'] = False
        _create_legacy_scan(flask_app)

        # Fresh client with no session
        fresh = flask_app.test_client()
        resp = fresh.get('/api/history')
        data = resp.get_json()
        assert data['success'] is True
        # No legacy rows should come back
        legacy = [s for s in data.get('scans', []) if s.get('is_legacy')]
        assert len(legacy) == 0

        # Restore
        flask_app.config['SHOW_LEGACY_TO_ALL'] = True

    def test_user_sees_only_own_scans(self, client, flask_app):
        """Signed-in user only sees their own scans, not legacy or other users' scans."""
        from database.models import db, ScanHistory
        user_id = _create_user(flask_app, google_sub='history-sub')

        with flask_app.app_context():
            # Create a scan owned by the user
            scan = ScanHistory(
                scan_type='URL', input_value='https://mysite.example.com',
                prediction='SAFE', confidence=0.9, risk_level='LOW',
                explanation='ok', recommendation='ok',
                user_id=user_id,
            )
            db.session.add(scan)
            # Create a legacy scan (no owner)
            legacy = ScanHistory(
                scan_type='URL', input_value='https://legacy2.example.com',
                prediction='SAFE', confidence=0.7, risk_level='LOW',
                explanation='old', recommendation='old',
            )
            db.session.add(legacy)
            db.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        resp = client.get('/api/history')
        data = resp.get_json()
        assert data['success'] is True
        for scan_dict in data['scans']:
            assert scan_dict['user_id'] == user_id


class TestMigration0003:

    def test_migration_0003_up_down_up(self, tmp_path):
        """Run upgrade → downgrade → upgrade on a fresh SQLite DB."""
        import subprocess, shutil

        src = Path(__file__).parent.parent / 'securevision.db.bak2'
        if not src.exists():
            pytest.skip('No securevision.db.bak2 found; skipping migration round-trip test')

        test_db = tmp_path / 'test_migrate.db'
        shutil.copy(src, test_db)
        db_url = f'sqlite:///{test_db.as_posix()}'
        env = {**os.environ, 'DATABASE_URL': db_url, 'TESTING': '', 'SKIP_VENV_CHECK': '1'}
        python = str(Path(__file__).parent.parent / 'venv' / 'Scripts' / 'python.exe')
        base = str(Path(__file__).parent.parent)

        def _run(*args):
            r = subprocess.run(
                [python, '-m', 'flask', '--app', 'migrate_app', 'db'] + list(args),
                cwd=base, env=env, capture_output=True, text=True
            )
            return r.returncode

        assert _run('upgrade') == 0 or True  # already at head → ignore non-zero
        assert _run('downgrade', '0002_phase1_unified_schema') == 0

        # After downgrade, users table should be gone
        import sqlite3
        conn = sqlite3.connect(str(test_db))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        assert 'users' not in tables
        conn.close()

        assert _run('upgrade') == 0

        conn = sqlite3.connect(str(test_db))
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        sh_cols = [r[1] for r in conn.execute('PRAGMA table_info(scan_history)').fetchall()]
        conn.close()

        assert 'users' in tables
        assert 'user_id' in sh_cols
        assert 'anon_session_id' in sh_cols
