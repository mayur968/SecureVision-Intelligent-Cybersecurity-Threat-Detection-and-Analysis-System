"""Unit tests for APK detector."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from features.apk_features import APKFeatureExtractor
from explanation.risk_score import RiskScorer
from explanation.recommendations import RecommendationEngine


class TestAPKFeatureExtractor:
    """Test APK feature extraction."""
    
    def test_feature_names(self):
        """Test feature names."""
        extractor = APKFeatureExtractor()
        feature_names = extractor.get_feature_names()
        
        assert 'permission_count' in feature_names
        assert 'dangerous_permission_count' in feature_names
        assert 'component_count' in feature_names
    
    def test_feature_vector_length(self):
        """Test feature vector has correct length."""
        extractor = APKFeatureExtractor()
        features = {
            'permission_count': 10,
            'dangerous_permission_count': 2,
            'component_count': 5
        }
        vector = extractor.get_feature_vector(features)
        
        assert len(vector) == len(extractor.get_feature_names())


class TestRiskScorer:
    """Test risk scoring."""
    
    def test_safe_risk_score(self):
        """Test risk score for safe prediction."""
        scorer = RiskScorer()
        result = scorer.calculate_risk_score('SAFE', 0.95, 'URL', {})
        
        assert result['risk_level'] == 'LOW'
        assert result['risk_score'] < 40
    
    def test_phishing_risk_score(self):
        """Test risk score for phishing prediction."""
        scorer = RiskScorer()
        result = scorer.calculate_risk_score('PHISHING', 0.95, 'URL', {})
        
        assert result['risk_level'] == 'HIGH'
        assert result['risk_score'] > 70
    
    def test_medium_risk(self):
        """Test medium risk classification."""
        scorer = RiskScorer()
        result = scorer.calculate_risk_score('PHISHING', 0.5, 'MESSAGE', {})
        
        assert 40 <= result['risk_score'] <= 100


class TestRecommendationEngine:
    """Test recommendation generation."""
    
    def test_url_safe_recommendations(self):
        """Test recommendations for safe URL."""
        engine = RecommendationEngine()
        recs = engine.get_recommendations('SAFE', 'URL', 'LOW', {})
        
        assert len(recs) > 0
        assert isinstance(recs, list)
    
    def test_url_phishing_recommendations(self):
        """Test recommendations for phishing URL."""
        engine = RecommendationEngine()
        recs = engine.get_recommendations('PHISHING', 'URL', 'HIGH', {})
        
        assert len(recs) > 0
        assert any('NOT' in rec or 'not' in rec.lower() for rec in recs)
    
    def test_apk_malicious_recommendations(self):
        """Test recommendations for malicious APK."""
        engine = RecommendationEngine()
        recs = engine.get_recommendations('MALICIOUS', 'APK', 'HIGH', {})
        
        assert len(recs) > 0
        assert any('NOT install' in rec or 'Delete' in rec for rec in recs)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
