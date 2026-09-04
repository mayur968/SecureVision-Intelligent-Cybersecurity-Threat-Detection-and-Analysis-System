"""File security utilities for SecureVision."""

import os
import secrets
from pathlib import Path
from typing import Optional, Tuple
from werkzeug.utils import secure_filename


def generate_secure_filename(original_filename: str) -> str:
    """
    Generate a secure random filename while preserving extension.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Secure random filename
    """
    # Extract extension
    if '.' in original_filename:
        ext = original_filename.rsplit('.', 1)[1].lower()
    else:
        ext = ''
    
    # Generate random filename
    random_name = secrets.token_hex(16)
    
    return f"{random_name}.{ext}" if ext else random_name


def validate_file_size(file_path: Path, max_size_mb: int = 50) -> Tuple[bool, Optional[str]]:
    """
    Validate file size.
    
    Args:
        file_path: Path to file
        max_size_mb: Maximum size in MB
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not file_path.exists():
        return False, "File does not exist"
    
    size_bytes = file_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    
    if size_mb > max_size_mb:
        return False, f"File too large: {size_mb:.2f}MB (max {max_size_mb}MB)"
    
    if size_bytes == 0:
        return False, "File is empty"
    
    return True, None


def safe_file_cleanup(file_path: Path) -> bool:
    """
    Safely delete a file.
    
    Args:
        file_path: Path to file to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            return True
    except Exception:
        pass
    return False


def get_file_extension(filename: str) -> str:
    """
    Get file extension safely.
    
    Args:
        filename: Filename
        
    Returns:
        File extension (lowercase) or empty string
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def is_allowed_file(filename: str, allowed_extensions: set) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename: Filename to check
        allowed_extensions: Set of allowed extensions
        
    Returns:
        True if allowed, False otherwise
    """
    ext = get_file_extension(filename)
    return ext in allowed_extensions
