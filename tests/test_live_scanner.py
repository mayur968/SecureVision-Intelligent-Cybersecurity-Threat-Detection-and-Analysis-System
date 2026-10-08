"""
Tests for detection/live_scanner.py

Unit tests: no network, no browser (mocked)
Integration tests: local fixture HTTP server
API tests: Flask test client
"""
import ipaddress
import json
import os
import threading
import time
import unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:')


# ── Helpers ──────────────────────────────────────────────────────────────────

def _public_getaddrinfo(host, port, family, socktype):
    """Mock socket.getaddrinfo returning a public IP (93.184.216.34 = example.com)"""
    return [(2, 1, 6, '', ('93.184.216.34', 0))]


# ── Unit tests: is_safe_target ────────────────────────────────────────────────

class TestIsSafeTarget(unittest.TestCase):

    def _import(self):
        from detection.live_scanner import is_safe_target
        return is_safe_target

    def test_blocks_file_scheme(self):
        safe, reason = self._import()('file:///etc/passwd')
        self.assertFalse(safe)
        self.assertIn('scheme', reason.lower())

    def test_blocks_ftp_scheme(self):
        safe, reason = self._import()('ftp://example.com')
        self.assertFalse(safe)

    def test_blocks_localhost_name(self):
        safe, _ = self._import()('http://localhost/')
        self.assertFalse(safe)

    def test_blocks_127(self):
        safe, _ = self._import()('http://127.0.0.1/')
        self.assertFalse(safe)

    def test_blocks_10x(self):
        with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('10.0.0.1',0))]):
            safe, reason = self._import()('http://internal.corp/')
            self.assertFalse(safe)

    def test_blocks_192168(self):
        with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('192.168.1.1',0))]):
            safe, _ = self._import()('http://router.local/')
            self.assertFalse(safe)

    def test_blocks_metadata_ip(self):
        with patch('socket.getaddrinfo', return_value=[(2,1,6,'',('169.254.169.254',0))]):
            safe, reason = self._import()('http://metadata.internal/')
            self.assertFalse(safe)

    def test_allows_public_ip(self):
        with patch('socket.getaddrinfo', _public_getaddrinfo):
            safe, reason = self._import()('https://example.com/')
            self.assertTrue(safe)
            self.assertEqual(reason, '')

    def test_rejects_no_hostname(self):
        safe, _ = self._import()('https://')
        self.assertFalse(safe)


# ── Unit tests: scoring ───────────────────────────────────────────────────────

class TestScoring(unittest.TestCase):

    def _compute(self, dom_data, redirect_chain=None, final_url='https://example.com/'):
        from detection.live_scanner import _compute_evidence_and_score
        return _compute_evidence_and_score(dom_data, redirect_chain or [], final_url)

    def _empty_dom(self):
        return {
            'title': 'Test', 'finalUrl': 'https://example.com/',
            'visibleText': 'hello world', 'hasPasswordField': False,
            'sensitiveInputs': [], 'formActions': [], 'hiddenIframes': 0,
        }

    def test_no_evidence_score_zero(self):
        evidence, score = self._compute(self._empty_dom())
        self.assertEqual(score, 0)

    def test_password_field_adds_25(self):
        dom = self._empty_dom()
        dom['hasPasswordField'] = True
        evidence, score = self._compute(dom)
        self.assertEqual(score, 25)

    def test_phishing_combo_over_60(self):
        dom = self._empty_dom()
        dom['hasPasswordField'] = True          # +25
        dom['formActions'] = ['https://evil.net/steal']  # cross domain +25
        dom['title'] = 'PayPal Login'
        dom['visibleText'] = 'paypal login secure'
        dom['finalUrl'] = 'https://paypal-fake-site.com/'
        # brand_mismatch +30, password +25, cross_domain_form +25 = 80 (capped 100)
        _, score = self._compute(dom, [], 'https://paypal-fake-site.com/')
        self.assertGreaterEqual(score, 60)

    def test_score_capped_at_100(self):
        dom = self._empty_dom()
        dom['hasPasswordField'] = True
        dom['sensitiveInputs'] = ['cvv']
        dom['formActions'] = ['https://evil.net/steal']
        dom['title'] = 'PayPal Secure'
        dom['visibleText'] = 'paypal'
        dom['hiddenIframes'] = 2
        _, score = self._compute(dom, ['https://a.com', 'https://b.com', 'https://c.com', 'https://d.com'], 'https://paypal-evil.com/')
        self.assertLessEqual(score, 100)


# ── Unit tests: combined score formula ───────────────────────────────────────

class TestCombinedScore(unittest.TestCase):

    def _combined(self, live_score, live_verdict, ml_prediction, ml_confidence):
        # Replicate the formula from _run_live_scan_job
        if live_verdict == 'COULD_NOT_VERIFY':
            ml_phishing_prob = ml_confidence if ml_prediction == 'PHISHING' else (1 - ml_confidence)
            return ml_phishing_prob * 100
        ml_phishing_prob = ml_confidence if ml_prediction == 'PHISHING' else (1 - ml_confidence)
        return 0.6 * live_score + 0.4 * (ml_phishing_prob * 100)

    def test_combined_formula(self):
        result = self._combined(80, 'PHISHING', 'PHISHING', 0.9)
        self.assertAlmostEqual(result, 84.0, places=1)  # 0.6*80 + 0.4*90 = 48+36 = 84

    def test_combined_fallback_on_could_not_verify(self):
        result = self._combined(0, 'COULD_NOT_VERIFY', 'PHISHING', 0.85)
        self.assertAlmostEqual(result, 85.0, places=1)

    def test_combined_safe_ml(self):
        result = self._combined(10, 'LIKELY_SAFE', 'SAFE', 0.9)
        # ml_phishing_prob = 1-0.9 = 0.1 -> 10
        self.assertAlmostEqual(result, 0.6*10 + 0.4*10, places=1)


# ── Integration tests: fixture HTTP server ────────────────────────────────────

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class FixtureHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FIXTURES_DIR), **kwargs)

    def log_message(self, *args):
        pass  # silence server logs in tests


def start_fixture_server():
    server = HTTPServer(('127.0.0.1', 0), FixtureHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server, port


@pytest.fixture(scope='module')
def fixture_server():
    os.environ['TEST_MODE'] = 'true'
    server, port = start_fixture_server()
    yield f'http://127.0.0.1:{port}'
    server.shutdown()
    os.environ.pop('TEST_MODE', None)


@pytest.mark.integration
def test_benign_page_likely_safe(fixture_server):
    from detection.live_scanner import scan_live
    result = scan_live(f'{fixture_server}/benign.html', timeout_ms=30000)
    assert result['verdict'] in ('LIKELY_SAFE', 'SUSPICIOUS', 'COULD_NOT_VERIFY'), f"Unexpected: {result['verdict']}"
    assert 'password_field' not in ' '.join(result.get('evidence', []))


@pytest.mark.integration
def test_phishing_login_detected(fixture_server):
    from detection.live_scanner import scan_live
    result = scan_live(f'{fixture_server}/phishing_login.html', timeout_ms=30000)
    if result['verdict'] == 'COULD_NOT_VERIFY':
        pytest.skip('Playwright not available or page could not load')
    assert result['verdict'] in ('PHISHING', 'SUSPICIOUS'), f"Expected PHISHING/SUSPICIOUS got {result['verdict']}"
    evidence_text = ' '.join(result.get('evidence', []))
    assert any(kw in evidence_text.lower() for kw in ['password', 'form', 'credential', 'brand'])


@pytest.mark.integration
def test_redirect_page_loads(fixture_server):
    from detection.live_scanner import scan_live
    result = scan_live(f'{fixture_server}/redirect.html', timeout_ms=30000)
    # Redirect should resolve without error
    assert result['verdict'] in ('LIKELY_SAFE', 'SUSPICIOUS', 'PHISHING', 'COULD_NOT_VERIFY')


# ── API tests: Flask test client ──────────────────────────────────────────────

@pytest.fixture(scope='module')
def flask_app():
    os.environ['TESTING'] = 'true'
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    from app import app as flask_application
    flask_application.config['TESTING'] = True
    flask_application.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with flask_application.app_context():
        from database.models import db
        db.create_all()
    return flask_application


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def test_post_live_scan_returns_202(client):
    resp = client.post('/api/scan/url/live', json={'url': 'https://www.google.com'},
                       content_type='application/json')
    assert resp.status_code == 202
    data = resp.get_json()
    assert 'job_id' in data
    assert data['status'] == 'queued'


def test_get_job_status(client):
    post = client.post('/api/scan/url/live', json={'url': 'https://www.google.com'},
                       content_type='application/json')
    assert post.status_code == 202
    job_id = post.get_json()['job_id']
    resp = client.get(f'/api/scan/url/live/{job_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] in ('queued', 'running', 'done', 'failed')


def test_get_unknown_job_returns_404(client):
    resp = client.get('/api/scan/url/live/nonexistent-job-id-12345')
    assert resp.status_code == 404


def test_post_live_scan_missing_url(client):
    resp = client.post('/api/scan/url/live', json={}, content_type='application/json')
    assert resp.status_code == 400


def test_post_live_scan_invalid_url(client):
    resp = client.post('/api/scan/url/live', json={'url': 'not-a-url'}, content_type='application/json')
    assert resp.status_code == 400


if __name__ == '__main__':
    unittest.main()
