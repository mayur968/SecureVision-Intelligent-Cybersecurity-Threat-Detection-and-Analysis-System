"""URL preprocessing utilities."""

import re
from urllib.parse import urlparse, unquote
from typing import Optional


def clean_url(url: str) -> str:
    """
    Clean and normalize URL.
    
    Args:
        url: Raw URL string
        
    Returns:
        Cleaned URL string
    """
    if not url:
        return ""
    
    # Strip whitespace
    url = url.strip()
    
    # Add http:// if no scheme present
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # URL decode
    url = unquote(url)
    
    # Remove trailing slash from domain
    parsed = urlparse(url)
    if parsed.path == '/':
        url = url.rstrip('/')
    
    return url


def extract_domain(url: str) -> Optional[str]:
    """
    Extract domain from URL.
    
    Args:
        url: URL string
        
    Returns:
        Domain string or None
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove port if present
        if ':' in domain and not domain.startswith('['):
            domain = domain.split(':')[0]
        
        return domain
    except Exception:
        return None


def is_valid_url_format(url: str) -> bool:
    """
    Check if URL has valid format.
    
    Args:
        url: URL string
        
    Returns:
        True if valid format, False otherwise
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """
    Normalize URL for consistent processing.
    
    Args:
        url: URL string
        
    Returns:
        Normalized URL
    """
    url = clean_url(url)
    
    # Convert to lowercase (except path for case-sensitive servers)
    parsed = urlparse(url)
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    
    if parsed.path:
        normalized += parsed.path
    if parsed.query:
        normalized += f"?{parsed.query}"
    if parsed.fragment:
        normalized += f"#{parsed.fragment}"
    
    return normalized
