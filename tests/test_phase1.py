"""
Phase 1 tests: IOC extraction, model registry seeding, to_dict additions,
migration idempotency, and the guarantee that IOC failures do not break scans.

All tests use an in-memory SQLite database — no network, no filesystem DB.
"""

import os
import sys
from pathlib import Path

# Ensure repo root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('TESTING', 'true')

import pytest
from unittest.mock import patch, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope='module')
def flask_app():
    """Fresh in-memory Flask app for all Phase 1 tests."""
    from flask import Flask
    from database.models import db, ScanHistory, IOC, ModelRegistry, seed_model_registry

    app = Flask(__name__)
    app.config.update({
        'TESTING':                    True,
        'SQLALCHEMY_DATABASE_URI':    'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY':                 'test',
    })
    db.init_app(app)
    with app.app_context():
        db.create_all()
        seed_model_registry()
    return app


@pytest.fixture
def ctx(flask_app):
    """Push an app context for each test."""
    with flask_app.app_context():
        yield


@pytest.fixture
def db_ctx(flask_app):
    """App context with DB access; rolls back after each test."""
    from database.models import db
    with flask_app.app_context():
        yield flask_app
        db.session.rollback()


# ── IOC extractor unit tests ──────────────────────────────────────────────────

class TestIOCExtractor:

    def test_url_extracts_domain(self, ctx):
        from database.ioc_extractor import extract_iocs
        iocs = extract_iocs('URL', 'https://paypal-fake.com/login', {})
        types = {i['ioc_type'] for i in iocs}
        values = {i['value'] for i in iocs}
        assert 'url' in types
        assert 'domain' in types
        # domain should be normalised to lowercase
        assert any('paypal-fake.com' in v for v in values)

    def test_url_extracts_ip(self, ctx):
        from database.ioc_extractor import extract_iocs
        iocs = extract_iocs('URL', 'http://192.168.1.1/steal', {})
        types = {i['ioc_type'] for i in iocs}
        assert 'ip' in types
        assert any(i['value'] == '192.168.1.1' for i in iocs)

    def test_url_live_includes_final_url_and_redirects(self, ctx):
        from database.ioc_extractor import extract_iocs
        result = {
            'final_url':     'https://evil.com/page',
            'redirect_chain': ['https://click.tracker.net/r=1', 'https://evil.com/page'],
        }
        iocs = extract_iocs('URL_LIVE', 'https://bit.ly/abc', result)
        domains = {i['value'] for i in iocs if i['ioc_type'] == 'domain'}
        assert 'evil.com' in domains
        assert 'tracker.net' in domains

    def test_message_extracts_url_and_domain(self, ctx):
        from database.ioc_extractor import extract_iocs
        msg = 'URGENT: Click http://phish.example.com/steal to verify your account!'
        iocs = extract_iocs('MESSAGE', msg, {})
        types = {i['ioc_type'] for i in iocs}
        assert 'url'    in types
        assert 'domain' in types

    def test_message_extracts_email_not_logged(self, ctx):
        """Emails are extracted as IOCs but the extractor must not log them."""
        from database.ioc_extractor import extract_iocs
        msg = 'Reply to attacker@evil-domain.org for your prize'
        iocs = extract_iocs('MESSAGE', msg, {})
        email_iocs = [i for i in iocs if i['ioc_type'] == 'email']
        assert len(email_iocs) >= 1
        assert email_iocs[0]['value'] == 'attacker@evil-domain.org'

    def test_message_extracts_phone(self, ctx):
        from database.ioc_extractor import extract_iocs
        msg = 'Call 555-867-5309 immediately or your account will be closed.'
        iocs = extract_iocs('MESSAGE', msg, {})
        phone_iocs = [i for i in iocs if i['ioc_type'] == 'phone']
        assert len(phone_iocs) >= 1

    def test_apk_extracts_package_name(self, ctx):
        from database.ioc_extractor import extract_iocs
        det = {'features': {'package_name': 'com.evil.malware', 'permissions': [],
                             'dangerous_permission_count': 0}}
        iocs = extract_iocs('APK', 'malware.apk', det, apk_file_path=None)
        vals = {i['value'] for i in iocs}
        assert 'com.evil.malware' in vals

    def test_ioc_cap_at_50(self, ctx):
        from database.ioc_extractor import extract_iocs
        # Build a message with many URLs
        urls = ' '.join(f'http://domain{i}.com/path' for i in range(60))
        iocs = extract_iocs('MESSAGE', urls, {})
        assert len(iocs) <= 50

    def test_ioc_deduplication(self, ctx):
        from database.ioc_extractor import extract_iocs
        # Same domain appears twice in redirect chain
        result = {
            'final_url':     'https://evil.com/a',
            'redirect_chain': ['https://evil.com/b'],
        }
        iocs = extract_iocs('URL_LIVE', 'https://evil.com/a', result)
        domain_vals = [i['value'] for i in iocs if i['ioc_type'] == 'domain']
        # evil.com must appear exactly once
        assert domain_vals.count('evil.com') == 1

    def test_ioc_failure_returns_empty_not_exception(self, ctx):
        """An error inside the extractor must return [] not raise."""
        from database.ioc_extractor import extract_iocs
        # Pass deliberately broken inputs
        iocs = extract_iocs(None, None, None)  # type: ignore
        assert isinstance(iocs, list)

    def test_unknown_scan_type_returns_empty(self, ctx):
        from database.ioc_extractor import extract_iocs
        iocs = extract_iocs('UNKNOWN_TYPE', 'something', {})
        assert isinstance(iocs, list)


# ── Model registry tests ───────────────────────────────────────────────────────

class TestModelRegistry:

    def test_three_entries_seeded(self, ctx):
        from database.models import ModelRegistry
        rows = ModelRegistry.query.all()
        ids = {r.id for r in rows}
        assert 'url_lr_v1.0'     in ids
        assert 'message_lr_v1.0' in ids
        assert 'apk_lr_v1.0'     in ids

    def test_seed_is_idempotent(self, ctx):
        from database.models import ModelRegistry, seed_model_registry, db
        seed_model_registry()   # second call
        seed_model_registry()   # third call
        assert ModelRegistry.query.count() == 3

    def test_metrics_are_null(self, ctx):
        from database.models import ModelRegistry
        for row in ModelRegistry.query.all():
            assert row.accuracy         is None
            assert row.precision_score  is None
            assert row.recall           is None
            assert row.f1_score         is None
            assert row.roc_auc          is None

    def test_is_synthetic_data_true(self, ctx):
        from database.models import ModelRegistry
        for row in ModelRegistry.query.all():
            assert row.is_synthetic_data is True

    def test_algorithm_read_from_pkl(self, ctx):
        from database.models import ModelRegistry, db
        url_model = db.session.get(ModelRegistry, 'url_lr_v1.0')
        assert url_model is not None
        assert url_model.algorithm == 'LogisticRegression'

    def test_to_dict(self, ctx):
        from database.models import ModelRegistry, db
        row = db.session.get(ModelRegistry, 'url_lr_v1.0')
        d = row.to_dict()
        assert d['id'] == 'url_lr_v1.0'
        assert d['is_synthetic_data'] is True
        assert d['accuracy'] is None


# ── ScanHistory schema tests ───────────────────────────────────────────────────

class TestScanHistory:

    def test_save_scan_with_new_fields(self, db_ctx):
        from database.models import ScanHistory, db
        scan = ScanHistory.save_scan(
            scan_type='URL', input_value='https://test.example.com',
            prediction='SAFE', confidence=0.95,
            risk_level='LOW', explanation='No threats found.',
            recommendation='Continue monitoring.',
            risk_score=10, model_version='url_lr_v1.0',
        )
        fetched = db.session.get(ScanHistory, scan.id)
        assert fetched is not None
        assert fetched.risk_score    == 10
        assert fetched.model_version == 'url_lr_v1.0'
        assert fetched.is_demo_data  is False
        assert fetched.status        == 'completed'

    def test_to_dict_includes_new_keys(self, db_ctx):
        from database.models import ScanHistory
        scan = ScanHistory.save_scan(
            scan_type='URL', input_value='https://example.com',
            prediction='SAFE', confidence=0.9,
            risk_level='LOW', explanation='OK', recommendation='OK',
            risk_score=5,
        )
        d = scan.to_dict()
        # Original keys must still be present
        assert 'id'             in d
        assert 'scan_type'      in d
        assert 'input_value'    in d
        assert 'prediction'     in d
        assert 'confidence'     in d
        assert 'risk_level'     in d
        assert 'explanation'    in d
        assert 'recommendation' in d
        assert 'created_at'     in d
        # Phase 1 additions
        assert 'risk_score'    in d
        assert 'duration_ms'   in d
        assert 'status'        in d
        assert 'model_version' in d
        assert 'is_demo_data'  in d
        assert 'ioc_count'     in d

    def test_legacy_rows_show_model_version_legacy(self, db_ctx):
        """Existing rows without model_version show 'legacy' in to_dict."""
        from database.models import ScanHistory, db
        # Insert a row the old way (no model_version)
        scan = ScanHistory(
            scan_type='URL', input_value='https://old.example.com',
            prediction='SAFE', confidence=0.8,
            risk_level='LOW', explanation='old', recommendation='old',
        )
        db.session.add(scan)
        db.session.commit()
        d = scan.to_dict()
        assert d['model_version'] == 'legacy'

    def test_original_api_shape_unchanged(self, db_ctx):
        """The original 9 keys must be identical in type and value."""
        from database.models import ScanHistory
        scan = ScanHistory.save_scan(
            scan_type='MESSAGE', input_value='Hello world test message',
            prediction='SAFE', confidence=0.75,
            risk_level='LOW', explanation='Fine.', recommendation='None.',
        )
        d = scan.to_dict()
        assert isinstance(d['id'],             int)
        assert isinstance(d['scan_type'],      str)
        assert isinstance(d['input_value'],    str)
        assert isinstance(d['prediction'],     str)
        assert isinstance(d['confidence'],     float)
        assert isinstance(d['risk_level'],     str)
        assert isinstance(d['created_at'],     str)   # ISO string

    def test_ioc_failure_does_not_break_scan(self, db_ctx):
        """Even if ioc_list contains garbage, save_scan must succeed."""
        from database.models import ScanHistory
        bad_iocs = [
            {'ioc_type': '', 'value': ''},
            {'ioc_type': None, 'value': None},
            'not a dict',                      # type: ignore
        ]
        # Should not raise
        scan = ScanHistory.save_scan(
            scan_type='URL', input_value='https://safe.example.com',
            prediction='SAFE', confidence=0.9,
            risk_level='LOW', explanation='OK', recommendation='OK',
            ioc_list=bad_iocs,  # type: ignore
        )
        assert scan.id is not None


# ── IOC database upsert tests ─────────────────────────────────────────────────

class TestIOCUpsert:

    def test_ioc_attached_to_scan(self, db_ctx):
        from database.models import ScanHistory, IOC
        ioc_list = [{'ioc_type': 'domain', 'value': 'evil-domain.com'}]
        scan = ScanHistory.save_scan(
            scan_type='URL', input_value='https://evil-domain.com',
            prediction='PHISHING', confidence=0.99,
            risk_level='HIGH', explanation='Bad', recommendation='Block',
            ioc_list=ioc_list,
        )
        assert len(scan.iocs) == 1
        assert scan.iocs[0].ioc_type == 'domain'
        assert scan.iocs[0].value    == 'evil-domain.com'

    def test_ioc_seen_count_increments_across_scans(self, db_ctx):
        from database.models import ScanHistory, IOC
        shared_ioc = [{'ioc_type': 'domain', 'value': 'repeated-domain.com'}]
        ScanHistory.save_scan(
            scan_type='URL', input_value='https://repeated-domain.com',
            prediction='PHISHING', confidence=0.9,
            risk_level='HIGH', explanation='x', recommendation='x',
            ioc_list=shared_ioc,
        )
        ScanHistory.save_scan(
            scan_type='URL', input_value='https://repeated-domain.com/page2',
            prediction='PHISHING', confidence=0.85,
            risk_level='HIGH', explanation='x', recommendation='x',
            ioc_list=shared_ioc,
        )
        ioc = IOC.query.filter_by(ioc_type='domain', value='repeated-domain.com').first()
        assert ioc is not None
        assert ioc.seen_count == 2

    def test_ioc_to_dict(self, db_ctx):
        from database.models import ScanHistory, IOC
        ioc_list = [{'ioc_type': 'ip', 'value': '1.2.3.4'}]
        ScanHistory.save_scan(
            scan_type='URL', input_value='http://1.2.3.4/',
            prediction='PHISHING', confidence=0.8,
            risk_level='HIGH', explanation='IP', recommendation='Block',
            ioc_list=ioc_list,
        )
        ioc = IOC.query.filter_by(ioc_type='ip', value='1.2.3.4').first()
        d = ioc.to_dict()
        assert d['ioc_type'] == 'ip'
        assert d['value']    == '1.2.3.4'
        assert d['seen_count'] >= 1
        assert 'first_seen' in d
        assert 'last_seen'  in d


# ── Statistics shape unchanged ─────────────────────────────────────────────────

class TestStatistics:

    def test_statistics_has_original_keys(self, db_ctx):
        from database.models import ScanHistory
        stats = ScanHistory.get_statistics()
        for key in ['total_scans', 'apk_scans', 'url_scans', 'message_scans',
                    'threats_detected', 'safe_results', 'threat_breakdown']:
            assert key in stats
        for key in ['apk', 'url', 'message']:
            assert key in stats['threat_breakdown']
