"""Unit tests for message detector."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.text_preprocessing import TextPreprocessor
from features.text_features import TextFeatureExtractor
from utils.validators import validate_message


class TestTextPreprocessor:
    """Test text preprocessing."""
    
    def test_clean_text(self):
        """Test text cleaning — URLs replaced with 'URL' placeholder (uppercase by design)."""
        preprocessor = TextPreprocessor()
        text = "URGENT: Your account has been SUSPENDED! Click here: https://example.com"
        cleaned = preprocessor.clean_text(text)

        # Non-URL text should be lowercased
        assert 'urgent' in cleaned or 'URGENT' not in cleaned.replace('URL', '')
        # URL placeholder is intentionally uppercase
        assert 'URL' in cleaned
    
    def test_remove_punctuation(self):
        """Test punctuation removal."""
        preprocessor = TextPreprocessor()
        text = "Hello, world!"
        cleaned = preprocessor.remove_punctuation(text)
        
        assert ',' not in cleaned
        assert '!' not in cleaned


class TestTextFeatureExtractor:
    """Test text feature extraction."""
    
    def test_extract_features(self):
        """Test basic feature extraction."""
        extractor = TextFeatureExtractor()
        text = "Your account has been suspended. Verify immediately."
        features = extractor.extract_features(text)
        
        assert 'length' in features
        assert 'word_count' in features
        assert features['security_words'] > 0
        assert features['urgent_words'] > 0
    
    def test_url_detection(self):
        """Test URL detection in text."""
        extractor = TextFeatureExtractor()
        text = "Click here: https://phishing-site.com"
        features = extractor.extract_features(text)
        
        assert features['has_url'] == 1
        assert features['url_count'] > 0
    
    def test_financial_keywords(self):
        """Test financial keyword detection."""
        extractor = TextFeatureExtractor()
        text = "Your bank account has been charged $500. Refund available."
        features = extractor.extract_features(text)
        
        assert features['financial_words'] > 0


class TestMessageValidation:
    """Test message validation."""
    
    def test_valid_message(self):
        """Test valid message validation."""
        is_valid, error = validate_message("This is a test message with sufficient length")
        
        assert is_valid is True
        assert error is None
    
    def test_short_message(self):
        """Test short message validation."""
        is_valid, error = validate_message("Short")
        
        assert is_valid is False
        assert error is not None
    
    def test_empty_message(self):
        """Test empty message validation."""
        is_valid, error = validate_message("")
        
        assert is_valid is False
        assert error is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
