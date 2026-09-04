"""Unit tests for URL detector."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from features.url_features import URLFeatureExtractor
from preprocessing.url_preprocessing import clean_url, normalize_url
from utils.validators import validate_url


class TestURLFeatureExtractor:
    """Test URL feature extraction."""
    
    def test_extract_features(self):
        """Test basic feature extraction."""
        extractor = URLFeatureExtractor()
        features = extractor.extract_features("https://www.google.com")
        
        assert 'url_length' in features
        assert 'domain_length' in features
        assert 'is_https' in features
        assert features['is_https'] == 1
    
    def test_suspicious_keywords(self):
        """Test suspicious keyword detection."""
        extractor = URLFeatureExtractor()
        features = extractor.extract_features("http://secure-login-verify.com")
        
        assert features['suspicious_keywords'] > 0
    
    def test_ip_address_detection(self):
        """Test IP address detection."""
        extractor = URLFeatureExtractor()
        features = extractor.extract_features("http://192.168.1.1/login")
        
        assert features['has_ip'] == 1
    
    def test_https_detection(self):
        """Test HTTPS detection."""
        extractor = URLFeatureExtractor()
        
        https_features = extractor.extract_features("https://example.com")
        http_features = extractor.extract_features("http://example.com")
        
        assert https_features['is_https'] == 1
        assert http_features['is_https'] == 0


class TestURLPreprocessing:
    """Test URL preprocessing."""
    
    def test_clean_url(self):
        """Test URL cleaning."""
        url = "  https://example.com  "
        cleaned = clean_url(url)
        
        assert cleaned == "https://example.com"
    
    def test_normalize_url(self):
        """Test URL normalization."""
        url = "HTTPS://EXAMPLE.COM/PATH"
        normalized = normalize_url(url)
        
        assert normalized.startswith("https://example.com")


class TestURLValidation:
    """Test URL validation."""
    
    def test_valid_url(self):
        """Test valid URL validation."""
        is_valid, error = validate_url("https://www.google.com")
        
        assert is_valid is True
        assert error is None
    
    def test_invalid_url(self):
        """Test invalid URL validation."""
        is_valid, error = validate_url("not-a-url")
        
        assert is_valid is False
        assert error is not None
    
    def test_empty_url(self):
        """Test empty URL validation."""
        is_valid, error = validate_url("")
        
        assert is_valid is False
        assert error is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
