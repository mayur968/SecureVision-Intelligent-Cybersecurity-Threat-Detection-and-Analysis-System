"""
email_scanner.py — .eml file phishing/spam scanner.

Public API:
    scan_eml(eml_bytes, message_detector=None, url_detector=None) -> dict
"""

import email
import email.header
import email.policy
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

# ── Brand words used for display-name mismatch detection ─────────────────────
_BRAND_WORDS = {
    'paypal', 'amazon', 'apple', 'google', 'microsoft', 'netflix', 'bank',
    'chase', 'wellsfargo', 'citibank', 'ebay', 'fedex', 'ups', 'dhl', 'irs', 'usps',
}

# ── Attachment extensions considered risky ────────────────────────────────────
_RISKY_EXTENSIONS = {
    '.apk', '.exe', '.scr', '.js', '.html', '.zip', '.iso',
    '.bat', '.cmd', '.ps1', '.vbs', '.jar',
}


# ── HTML helpers ─────────────────────────────────────────────────────────────

class _TextStripper(HTMLParser):
    """Extract plain text from an HTML string."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str):
        self._parts.append(data)

    def get_text(self) -> str:
        return ' '.join(self._parts)


class _HrefExtractor(HTMLParser):
    """Extract href attribute values from anchor tags."""

    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and value:
                    # Filter out mailto: and javascript: schemes
                    scheme = value.split(':')[0].lower() if ':' in value else ''
                    if scheme not in ('mailto', 'javascript', 'data', 'tel'):
                        self.hrefs.append(value)


def _strip_html(html_text: str) -> str:
    parser = _TextStripper()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    return parser.get_text()


def _extract_hrefs(html_text: str) -> list[str]:
    parser = _HrefExtractor()
    try:
        parser.feed(html_text)
    except Exception:
        pass
    return parser.hrefs


# ── Header decoding ───────────────────────────────────────────────────────────

def _decode_header(raw: str | None) -> str:
    """Decode a MIME-encoded header value to a plain string."""
    if not raw:
        return ''
    parts = email.header.decode_header(raw)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded.append(part.decode(charset or 'utf-8', errors='replace'))
            except (LookupError, UnicodeDecodeError):
                decoded.append(part.decode('latin-1', errors='replace'))
        else:
            decoded.append(part)
    return ''.join(decoded).strip()


# ── Address parsing ───────────────────────────────────────────────────────────

def _parse_address(header_val: str) -> tuple[str, str]:
    """Return (display_name, email_address) from a From/Reply-To header."""
    if not header_val:
        return '', ''

    # Try: "Display Name" <user@domain>  or  Display Name <user@domain>
    m = re.match(r'^(.*?)\s*<([^>]+)>\s*$', header_val.strip())
    if m:
        display = m.group(1).strip().strip('"\'')
        addr = m.group(2).strip()
        return display, addr

    # Plain address only
    addr = header_val.strip()
    return '', addr


def _extract_domain(email_addr: str) -> str:
    """Extract the domain portion from an e-mail address."""
    if '@' not in email_addr:
        return ''
    return email_addr.split('@', 1)[1].lower().strip()


# ── Auth-Results parsing ──────────────────────────────────────────────────────

def _parse_auth_results(header_val: str) -> dict[str, str]:
    """Extract spf/dkim/dmarc pass/fail values from Authentication-Results."""
    result = {'spf': 'unknown', 'dkim': 'unknown', 'dmarc': 'unknown'}
    if not header_val:
        return result

    for key in ('spf', 'dkim', 'dmarc'):
        # e.g. "spf=pass" or "spf=fail (reason)" or "dkim=pass header.d=…"
        pattern = rf'\b{key}=(\w+)'
        m = re.search(pattern, header_val, re.IGNORECASE)
        if m:
            result[key] = m.group(1).lower()

    return result


# ── Risk helpers ──────────────────────────────────────────────────────────────

def _is_risky_attachment(filename: str) -> bool:
    ext = ''
    if '.' in filename:
        ext = '.' + filename.rsplit('.', 1)[-1].lower()
    return ext in _RISKY_EXTENSIONS


def _attachment_ext(filename: str) -> str:
    if '.' in filename:
        return '.' + filename.rsplit('.', 1)[-1].lower()
    return ''


# ── Main public function ──────────────────────────────────────────────────────

def scan_eml(
    eml_bytes: bytes,
    message_detector=None,
    url_detector=None,
) -> dict:
    """
    Parse and analyse a raw .eml file.

    Args:
        eml_bytes: Raw bytes of the .eml file.
        message_detector: Optional pre-instantiated MessageDetector.
        url_detector:     Optional pre-instantiated URLDetector.

    Returns:
        Result dict (see module docstring).

    Raises:
        ValueError: If eml_bytes cannot be parsed as an e-mail message.
    """
    # ── Lazy-import detectors ─────────────────────────────────────────────────
    if message_detector is None:
        from detection.message_detector import MessageDetector
        message_detector = MessageDetector()
    if url_detector is None:
        from detection.url_detector import URLDetector
        url_detector = URLDetector()

    # ── Parse message ─────────────────────────────────────────────────────────
    try:
        msg = email.message_from_bytes(eml_bytes)
    except Exception as exc:
        raise ValueError(f'Cannot parse e-mail bytes: {exc}') from exc

    # Sanity check — an empty parse with no headers at all is not useful
    if not msg.keys():
        raise ValueError('E-mail message has no headers and cannot be analysed.')

    # ── Extract headers ───────────────────────────────────────────────────────
    raw_from    = _decode_header(msg.get('From', ''))
    raw_reply   = _decode_header(msg.get('Reply-To', ''))
    raw_subject = _decode_header(msg.get('Subject', ''))
    raw_date    = _decode_header(msg.get('Date', ''))
    raw_auth    = _decode_header(msg.get('Authentication-Results', ''))
    raw_msg_id  = _decode_header(msg.get('Message-ID', ''))

    from_display, from_email = _parse_address(raw_from)
    reply_to_addr = _parse_address(raw_reply)[1] if raw_reply else ''

    from_domain    = _extract_domain(from_email)
    reply_to_domain = _extract_domain(reply_to_addr) if reply_to_addr else ''

    # ── Mismatch flags ────────────────────────────────────────────────────────
    # display_name_mismatch: brand word in display name but NOT in from domain
    display_lower = from_display.lower()
    brand_in_display = {w for w in _BRAND_WORDS if w in display_lower}
    display_name_mismatch = bool(
        brand_in_display and
        not any(w in from_domain for w in brand_in_display)
    )

    # reply_to_mismatch: Reply-To domain differs from From domain
    reply_to_mismatch = bool(
        reply_to_domain and from_domain and reply_to_domain != from_domain
    )

    # ── Authentication results ────────────────────────────────────────────────
    auth_results = _parse_auth_results(raw_auth)

    # ── Body + links + attachments ────────────────────────────────────────────
    body_text: str = ''
    html_body: str = ''
    links_raw: list[str] = []
    attachments: list[dict] = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))

            if 'attachment' in disposition.lower() or part.get_filename():
                fname = _decode_header(part.get_filename() or 'unknown')
                ext = _attachment_ext(fname)
                risk = 'HIGH' if _is_risky_attachment(fname) else 'LOW'
                attachments.append({'filename': fname, 'extension': ext, 'risk': risk})
                continue  # never read attachment content

            if content_type == 'text/plain' and not body_text:
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    body_text = payload.decode(charset, errors='replace') if payload else ''
                except Exception:
                    body_text = ''

            elif content_type == 'text/html':
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    decoded_html = payload.decode(charset, errors='replace') if payload else ''
                    html_body += decoded_html
                    links_raw.extend(_extract_hrefs(decoded_html))
                except Exception:
                    pass
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            text = payload.decode(charset, errors='replace') if payload else ''
        except Exception:
            text = ''

        if content_type == 'text/plain':
            body_text = text
        elif content_type == 'text/html':
            html_body = text
            links_raw.extend(_extract_hrefs(text))

    # Fallback body: strip HTML if no plain text
    if not body_text and html_body:
        body_text = _strip_html(html_body)

    # Deduplicate links, cap at 20
    seen: set[str] = set()
    unique_links: list[str] = []
    for url in links_raw:
        if url not in seen:
            seen.add(url)
            unique_links.append(url)
        if len(unique_links) >= 20:
            break

    # ── Message detector ──────────────────────────────────────────────────────
    truncated_body = body_text[:5000]
    try:
        msg_result = message_detector.predict(truncated_body) if truncated_body else {
            'prediction': 'UNKNOWN', 'confidence': 0.3, 'indicators': [],
        }
    except Exception:
        msg_result = {'prediction': 'UNKNOWN', 'confidence': 0.3, 'indicators': []}

    # Derive base risk score from message detector
    prediction_raw = msg_result.get('prediction', 'UNKNOWN')
    confidence     = msg_result.get('confidence', 0.3)

    if prediction_raw == 'PHISHING':
        base_risk = int(confidence * 100)
    elif prediction_raw in ('UNKNOWN', 'ERROR'):
        base_risk = 30
    else:
        # SAFE — low base
        base_risk = int((1.0 - confidence) * 50)

    # ── URL detector ─────────────────────────────────────────────────────────
    scanned_links: list[dict] = []
    phishing_link_count = 0

    for url in unique_links:
        try:
            url_result = url_detector.predict(url)
            link_pred = url_result.get('prediction', 'UNKNOWN')
            link_conf = url_result.get('confidence', 0.5)
            if link_pred == 'PHISHING':
                phishing_link_count += 1
        except Exception:
            link_pred = 'UNKNOWN'
            link_conf = 0.5
        scanned_links.append({'url': url, 'prediction': link_pred, 'confidence': link_conf})

    # ── Risk score computation ────────────────────────────────────────────────
    risk = base_risk

    if display_name_mismatch:
        risk += 15
    if reply_to_mismatch:
        risk += 15

    spf_val   = auth_results.get('spf', 'unknown')
    dkim_val  = auth_results.get('dkim', 'unknown')
    dmarc_val = auth_results.get('dmarc', 'unknown')

    if spf_val in ('fail', 'softfail'):
        risk += 10
    if dkim_val == 'fail':
        risk += 10
    if dmarc_val == 'fail':
        risk += 10

    # Risky attachment penalty (capped at +30)
    risky_att_count = sum(1 for a in attachments if a['risk'] == 'HIGH')
    risk += min(risky_att_count * 10, 30)

    # Phishing link penalty (capped at +20)
    risk += min(phishing_link_count * 5, 20)

    # Clamp to [0, 100]
    risk = max(0, min(100, risk))

    # ── Risk level + prediction ───────────────────────────────────────────────
    if risk >= 60:
        risk_level = 'HIGH'
        final_prediction = 'PHISHING'
    elif risk >= 30:
        risk_level = 'MEDIUM'
        final_prediction = 'SUSPICIOUS'
    else:
        risk_level = 'LOW'
        # Defer to message detector prediction when risk is low
        final_prediction = prediction_raw if prediction_raw in ('SAFE', 'PHISHING', 'SUSPICIOUS') else 'SAFE'

    # Normalise confidence for the overall result
    final_confidence = round(risk / 100.0, 4)

    # ── Evidence list ─────────────────────────────────────────────────────────
    evidence: list[str] = []
    if display_name_mismatch:
        evidence.append(
            f'Display name "{from_display}" contains brand keyword(s) but sending domain is "{from_domain}"'
        )
    if reply_to_mismatch:
        evidence.append(
            f'Reply-To address ({reply_to_addr}) uses a different domain than the sender ({from_domain})'
        )
    if spf_val in ('fail', 'softfail'):
        evidence.append(f'SPF check {spf_val}: sender is not authorised to send from {from_domain}')
    if dkim_val == 'fail':
        evidence.append('DKIM signature verification failed — message may have been altered')
    if dmarc_val == 'fail':
        evidence.append('DMARC policy check failed for the sending domain')
    if risky_att_count:
        risky_names = [a['filename'] for a in attachments if a['risk'] == 'HIGH']
        evidence.append(f'Risky attachment(s) found: {", ".join(risky_names)}')
    if phishing_link_count:
        evidence.append(f'{phishing_link_count} link(s) classified as phishing by the URL detector')

    # ── Message-ID hash ───────────────────────────────────────────────────────
    msg_id_hash = hashlib.sha256((raw_msg_id or from_email + raw_date).encode()).hexdigest()[:16]

    # ── Subject snippet ───────────────────────────────────────────────────────
    subject_snippet = raw_subject[:120] if raw_subject else ''

    # ── Indicators (from message detector) ───────────────────────────────────
    indicators = msg_result.get('indicators', [])

    return {
        'success': True,
        'scan_type': 'EMAIL',
        'prediction': final_prediction,
        'confidence': final_confidence,
        'risk_score': risk,
        'risk_level': risk_level,
        'sender': {
            'from_display': from_display,
            'from_email': from_email,
            'from_domain': from_domain,
            'reply_to': reply_to_addr,
            'reply_to_domain': reply_to_domain,
            'display_name_mismatch': display_name_mismatch,
            'reply_to_mismatch': reply_to_mismatch,
        },
        'subject_snippet': subject_snippet,
        'date': raw_date,
        'auth_results': auth_results,
        'links': scanned_links,
        'attachments': attachments,
        'indicators': indicators,
        'evidence': evidence,
        'msg_id_hash': msg_id_hash,
        'body_preview': None,
    }
