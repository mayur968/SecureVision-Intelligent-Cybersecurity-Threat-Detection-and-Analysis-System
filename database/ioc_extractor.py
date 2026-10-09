"""IOC extraction for SecureVision — Phase 1.

Extracts Indicators of Compromise from scan inputs and results.
Returns a list of dicts [{ioc_type, value}] ready to pass to save_scan().

Rules:
- All domain/email values are lowercased.
- Phone numbers and email addresses are extracted but NEVER written to logs.
- Maximum 50 IOCs returned per scan (caller enforces the cap in _attach_iocs).
- This module has no network I/O and no DB access; it is a pure extractor.
- All regex operations are protected by try/except; failures return partial results.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

# ── Compiled patterns ──────────────────────────────────────────────────────────
_RE_URL    = re.compile(r'https?://[^\s\'"<>]{4,512}',   re.IGNORECASE)
_RE_EMAIL  = re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b')
_RE_PHONE  = re.compile(r'(?<!\d)(?:\+?\d[\d\s\-().]{7,15}\d)(?!\d)')
_RE_IP     = re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b')

# Minimum domain label length to avoid false positives like "a.b"
_MIN_DOMAIN_LEN = 4


def _norm_domain(d: str) -> str:
    return d.lower().strip().lstrip('www.').lstrip('www2.').lstrip('www3.')


def _extract_domain(url: str) -> Optional[str]:
    """Return the registered domain from a URL, or None."""
    try:
        try:
            import tldextract
            ext = tldextract.extract(url)
            if ext.domain and ext.suffix:
                return f'{ext.domain}.{ext.suffix}'.lower()
        except ImportError:
            pass
        host = urlparse(url).hostname or ''
        if host and len(host) >= _MIN_DOMAIN_LEN:
            return host.lower()
    except Exception:
        pass
    return None


def _is_ip(s: str) -> bool:
    return bool(_RE_IP.fullmatch(s.strip()))


# ── Public API ─────────────────────────────────────────────────────────────────

def extract_iocs(
    scan_type: str,
    input_value: str,
    detection_result: dict,
    apk_file_path: Optional[Path] = None,
) -> list[dict]:
    """Return a list of IOC dicts for the given scan.

    Parameters
    ----------
    scan_type        : 'URL' | 'URL_LIVE' | 'MESSAGE' | 'APK'
    input_value      : the raw input (URL string, message text, APK filename)
    detection_result : the dict returned by the detector / _run_live_scan_job
    apk_file_path    : Path to the APK temp file (before cleanup) — for hash extraction

    Returns
    -------
    List of dicts, each with keys 'ioc_type' and 'value'.
    At most 50 items; caller caps via _attach_iocs.
    """
    iocs: list[dict] = []

    try:
        st = (scan_type or '').upper()

        if st in ('URL', 'URL_LIVE'):
            _extract_url_iocs(iocs, input_value, detection_result)
        elif st == 'MESSAGE':
            _extract_message_iocs(iocs, input_value, detection_result)
        elif st == 'APK':
            _extract_apk_iocs(iocs, input_value, detection_result, apk_file_path)

    except Exception:
        pass   # IOC failure must never propagate

    # Deduplicate before returning
    seen: set[tuple] = set()
    unique: list[dict] = []
    for ioc in iocs:
        key = (ioc.get('ioc_type', ''), ioc.get('value', ''))
        if key not in seen and key[0] and key[1]:
            seen.add(key)
            unique.append(ioc)

    return unique[:50]


# ── Per-type extractors ────────────────────────────────────────────────────────

def _add(iocs: list, ioc_type: str, value: str) -> None:
    if value:
        iocs.append({'ioc_type': ioc_type, 'value': value.strip()})


def _extract_url_iocs(iocs: list, url: str, result: dict) -> None:
    """URL and URL_LIVE IOCs: primary URL + final_url + redirect chain + form actions."""
    try:
        # Primary input URL
        _add(iocs, 'url', url)
        d = _extract_domain(url)
        if d:
            _add(iocs, 'domain', _norm_domain(d))

        # IP address in URL
        host = urlparse(url).hostname or ''
        if host and _is_ip(host):
            _add(iocs, 'ip', host)

        # URL_LIVE extras
        final_url = result.get('final_url') or result.get('url_analyzed', '')
        if final_url and final_url != url:
            _add(iocs, 'url', final_url)
            fd = _extract_domain(final_url)
            if fd:
                _add(iocs, 'domain', _norm_domain(fd))

        # Redirect chain domains
        for hop in (result.get('redirect_chain') or [])[:10]:
            if hop:
                hd = _extract_domain(hop)
                if hd:
                    _add(iocs, 'domain', _norm_domain(hd))

        # Cross-domain form action targets (from live scanner DOM data or features)
        for action in (result.get('formActions') or [])[:5]:
            if action:
                ad = _extract_domain(action)
                if ad:
                    _add(iocs, 'domain', _norm_domain(ad))

    except Exception:
        pass


def _extract_message_iocs(iocs: list, message: str, result: dict) -> None:
    """MESSAGE IOCs: URLs, domains, IPs, email addresses, phone numbers."""
    try:
        text = message[:5000]   # cap for performance

        # URLs
        for m in _RE_URL.findall(text)[:20]:
            _add(iocs, 'url', m)
            d = _extract_domain(m)
            if d:
                _add(iocs, 'domain', _norm_domain(d))

        # IP addresses
        for ip in _RE_IP.findall(text)[:10]:
            _add(iocs, 'ip', ip)

        # Email addresses (stored but never logged)
        for email in _RE_EMAIL.findall(text)[:5]:
            _add(iocs, 'email', email.lower())

        # Phone numbers (stored but never logged)
        # Strip down to digits only for normalisation
        for phone in _RE_PHONE.findall(text)[:5]:
            digits = re.sub(r'\D', '', phone)
            if 7 <= len(digits) <= 15:
                _add(iocs, 'phone', digits)

    except Exception:
        pass


def _extract_apk_iocs(
    iocs: list,
    apk_filename: str,
    result: dict,
    apk_file_path: Optional[Path],
) -> None:
    """APK IOCs: SHA-256, MD5, package name, dangerous permissions."""
    try:
        # File hashes — computed before the temp file is cleaned up
        if apk_file_path and Path(apk_file_path).exists():
            try:
                data = Path(apk_file_path).read_bytes()
                _add(iocs, 'hash_sha256', hashlib.sha256(data).hexdigest())
                _add(iocs, 'hash_md5',    hashlib.md5(data).hexdigest())
            except Exception:
                pass

        # Package name as domain-style identifier
        features = result.get('features') or {}
        pkg = features.get('package_name') or ''
        if pkg and pkg != 'unknown' and len(pkg) >= 3:
            _add(iocs, 'domain', pkg.lower())   # reverse-domain notation

        # Dangerous permissions — each as a distinct IOC so they can be searched
        permissions = features.get('permissions') or []
        dangerous   = features.get('dangerous_permission_count', 0)
        if dangerous > 0:
            # Only record the explicit dangerous ones (up to 10)
            from features.apk_features import APKFeatureExtractor
            dangerous_set = APKFeatureExtractor.DANGEROUS_PERMISSIONS
            count = 0
            for perm in permissions[:30]:
                perm_short = perm.split('.')[-1] if '.' in perm else perm
                if any(d in perm_short for d in dangerous_set) and count < 10:
                    _add(iocs, 'permission', perm_short.upper())
                    count += 1

    except Exception:
        pass
