"""APK file preprocessing and validation."""

from pathlib import Path
from typing import Tuple, Optional
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_security import validate_file_size, get_file_extension
from utils.logger import logger


class APKPreprocessor:
    """Preprocess and validate APK files."""
    
    ALLOWED_EXTENSIONS = {'apk'}
    MAX_SIZE_MB = 50
    
    def __init__(self):
        """Initialize APK preprocessor."""
        pass
    
    def validate_apk(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate APK file.
        
        Args:
            file_path: Path to APK file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if file exists
        if not file_path.exists():
            return False, "File does not exist"
        
        # Check file extension
        ext = get_file_extension(file_path.name)
        if ext not in self.ALLOWED_EXTENSIONS:
            return False, f"Invalid file extension. Expected .apk, got .{ext}"
        
        # Check file size
        is_valid_size, size_error = validate_file_size(file_path, self.MAX_SIZE_MB)
        if not is_valid_size:
            return False, size_error
        
        # Basic APK signature check (ZIP file signature)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                # APK files are ZIP archives, check for ZIP signature
                if header != b'PK\x03\x04':
                    return False, "Invalid APK file format (not a valid ZIP archive)"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"
        
        logger.info(f"APK validation passed: {file_path.name}")
        return True, None
    
    def get_file_info(self, file_path: Path) -> dict:
        """
        Get basic file information.
        
        Args:
            file_path: Path to APK file
            
        Returns:
            Dictionary with file information
        """
        try:
            stat = file_path.stat()
            return {
                'filename': file_path.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'extension': get_file_extension(file_path.name)
            }
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {
                'filename': file_path.name,
                'size_bytes': 0,
                'size_mb': 0.0,
                'extension': 'unknown'
            }
