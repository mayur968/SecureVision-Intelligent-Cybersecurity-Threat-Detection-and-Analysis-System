"""Input validation utilities for SecureVision."""

import re
from urllib.parse import urlparse
from typing import Tuple, Optional


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format and basic safety checks.
    
    Args:
        url: URL string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty"
    
    url = url.strip()
    
    if len(url) > 2048:
        return False, "URL too long (max 2048 characters)"
    
    if len(url) < 4:
        return False, "URL too short"
    
    # Basic URL pattern check
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    if not url_pattern.match(url):
        return False, "Invalid URL format"
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "URL must have scheme and domain"
    except Exception as e:
        return False, f"URL parsing error: {str(e)}"
    
    return True, None


def validate_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Validate message/text input.
    
    Args:
        message: Message text to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not isinstance(message, str):
        return False, "Message cannot be empty"
    
    message = message.strip()
    
    if len(message) < 10:
        return False, "Message too short (minimum 10 characters)"
    
    if len(message) > 10000:
        return False, "Message too long (max 10,000 characters)"
    
    return True, None


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """
    Validate file extension.
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions
        
    Returns:
        True if valid, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        max_length: Maximum filename length
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Keep only alphanumeric, dots, hyphens, underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name
    
    return filename
