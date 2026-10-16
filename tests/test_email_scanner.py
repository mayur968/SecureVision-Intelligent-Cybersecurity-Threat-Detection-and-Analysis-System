"""
tests/test_email_scanner.py — 10 pytest tests for the email scanner.
"""

import io
import os
import email as stdlib_email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Set env vars BEFORE any app import so Config picks them up at class-parse time.
# Use os.environ[] (not setdefault) so these always override prior test modules.
os.environ['TESTING'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-email'
os.environ['SKIP_VENV_CHECK'] = '1'

import pytest

from detection.email_scanner import scan_eml


# ── Helper ────────────────────────────────────────────────────────────────────

def _make_eml(
    from_name: str = 'Sender',
    from_addr: str = 'sender@example.com',
    reply_to: str = '',
    subject: str = 'Test Subject',
    body: str = 'Hello, this is a test email.',
    auth_results: str = '',
    attachments: list[tuple[str, bytes]] | None = None,
) -> bytes:
    """
    Build a minimal .eml byte string for testing.

    Args:
        from_name:    Display name in From header.
        from_addr:    E-mail address in From header.
        reply_to:     Optional Reply-To address.
        subject:      Subject line.
        body:         Plain-text body.
        auth_results: Optional Authentication-Results header value.
        attachments:  List of (filename, content_bytes) tuples.

    Returns:
        Raw .eml bytes.
    """
    if attachments:
        msg: stdlib_email.message.Message = MIMEMultipart()
        msg.attach(MIMEText(body, 'plain'))
        for fname, content in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
            msg.attach(part)
    else:
        msg = MIMEText(body, 'plain')

    msg['From'] = f'"{from_name}" <{from_addr}>' if from_name else from_addr
    msg['To'] = 'recipient@example.com'
    msg['Subject'] = subject
    msg['Date'] = 'Mon, 01 Jan 2024 00:00:00 +0000'
    msg['Message-ID'] = '<test-id-12345@example.com>'

    if reply_to:
        msg['Reply-To'] = reply_to
    if auth_results:
        msg['Authentication-Results'] = auth_results

    return msg.as_bytes()


# ── Flask test client fixture ─────────────────────────────────────────────────

@pytest.fixture(scope='module')
def flask_client():
    # Ensure Config has a non-default SECRET_KEY before app.py is imported.
    # config.py may have already been imported with the class-level default
    # by an earlier test module; patch it directly so init_app does not raise.
    from config import Config
    Config.SECRET_KEY = 'test-secret-email'

    import app as flask_app_module
    flask_app = flask_app_module.app
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-email'

    with flask_app.test_client() as client:
        yield client


# ── Tests 1–9: direct scan_eml() calls (no Flask) ────────────────────────────

def test_parse_from_header():
    """From display name and address are correctly extracted."""
    eml = _make_eml(from_name='Sender', from_addr='sender@example.com')
    result = scan_eml(eml)
    assert result['sender']['from_display'] == 'Sender'
    assert result['sender']['from_email'] == 'sender@example.com'


def test_reply_to_mismatch_detected():
    """Reply-To domain differs from From domain → mismatch flag set."""
    eml = _make_eml(
        from_addr='sender@example.com',
        reply_to='attacker@evil.com',
    )
    result = scan_eml(eml)
    assert result['sender']['reply_to_mismatch'] is True


def test_no_reply_to_mismatch_when_same_domain():
    """Reply-To domain same as From domain → no mismatch."""
    eml = _make_eml(
        from_addr='sender@example.com',
        reply_to='other@example.com',
    )
    result = scan_eml(eml)
    assert result['sender']['reply_to_mismatch'] is False


def test_display_name_mismatch_detected():
    """Brand word in display name but sending domain is different → mismatch."""
    eml = _make_eml(
        from_name='PayPal Support',
        from_addr='support@evil.com',
    )
    result = scan_eml(eml)
    assert result['sender']['display_name_mismatch'] is True


def test_spf_fail_parsed():
    """SPF=fail is extracted from Authentication-Results header."""
    eml = _make_eml(
        auth_results='mx.example.com; spf=fail smtp.mailfrom=evil.com'
    )
    result = scan_eml(eml)
    assert result['auth_results']['spf'] == 'fail'


def test_dkim_pass_parsed():
    """DKIM=pass is extracted from Authentication-Results header."""
    eml = _make_eml(
        auth_results='mx.example.com; dkim=pass header.d=example.com'
    )
    result = scan_eml(eml)
    assert result['auth_results']['dkim'] == 'pass'


def test_risky_attachment_flagged():
    """An .exe attachment is classified as HIGH risk."""
    eml = _make_eml(attachments=[('malware.exe', b'MZ\x90\x00')])
    result = scan_eml(eml)
    assert len(result['attachments']) >= 1
    exe_att = next(
        (a for a in result['attachments'] if a['filename'] == 'malware.exe'), None
    )
    assert exe_att is not None, 'malware.exe not found in attachments'
    assert exe_att['risk'] == 'HIGH'


def test_safe_attachment_not_flagged():
    """A .pdf attachment is classified as LOW risk."""
    eml = _make_eml(attachments=[('report.pdf', b'%PDF-1.4')])
    result = scan_eml(eml)
    assert len(result['attachments']) >= 1
    pdf_att = next(
        (a for a in result['attachments'] if a['filename'] == 'report.pdf'), None
    )
    assert pdf_att is not None, 'report.pdf not found in attachments'
    assert pdf_att['risk'] == 'LOW'


def test_body_not_in_response():
    """body_preview is always None; body text never leaks into the result."""
    secret_body = 'SECRET_BODY_TEXT_XYZ_DO_NOT_EXPOSE'
    eml = _make_eml(body=secret_body)
    result = scan_eml(eml)

    assert result['body_preview'] is None

    # Recursively ensure the secret body text is not anywhere in the result
    def _contains_secret(obj) -> bool:
        if isinstance(obj, str):
            return secret_body in obj
        if isinstance(obj, dict):
            return any(_contains_secret(v) for v in obj.values())
        if isinstance(obj, (list, tuple)):
            return any(_contains_secret(v) for v in obj)
        return False

    assert not _contains_secret(result), (
        'Body text was found somewhere in the scan result dict'
    )


# ── Test 10: Flask endpoint ───────────────────────────────────────────────────

def test_email_upload_endpoint(flask_client):
    """POST to /api/scan/email/upload with a valid .eml returns 200 + success."""
    eml = _make_eml()
    data = {'file': (io.BytesIO(eml), 'test.eml', 'message/rfc822')}
    resp = flask_client.post(
        '/api/scan/email/upload',
        data=data,
        content_type='multipart/form-data',
    )
    assert resp.status_code == 200
    result = resp.get_json()
    assert result['success'] is True
    assert result['prediction'] in {'SAFE', 'SUSPICIOUS', 'PHISHING'}
