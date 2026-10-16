"""
Tests for explanation/risk_score.py

Key invariant: risk_level MUST agree with prediction.
  SAFE                → LOW   (score 0-39)
  PHISHING/MALICIOUS  → HIGH  (score 70-100)
  SUSPICIOUS          → MEDIUM (score 40-69)
"""
import pytest
from explanation.risk_score import RiskScorer


@pytest.fixture
def rs():
    return RiskScorer()


class TestRiskLevelPredictionAgreement:
    """risk_level and prediction must never contradict each other."""

    @pytest.mark.parametrize("confidence", [0.01, 0.50, 0.75, 0.99, 1.0])
    def test_safe_always_low(self, rs, confidence):
        r = rs.calculate_risk_score('SAFE', confidence, 'URL')
        assert r['risk_level'] == 'LOW', (
            f"SAFE+conf={confidence} produced risk_level={r['risk_level']}"
        )

    @pytest.mark.parametrize("confidence", [0.01, 0.50, 0.75, 0.99, 1.0])
    def test_phishing_always_high(self, rs, confidence):
        r = rs.calculate_risk_score('PHISHING', confidence, 'URL')
        assert r['risk_level'] == 'HIGH', (
            f"PHISHING+conf={confidence} produced risk_level={r['risk_level']}"
        )

    @pytest.mark.parametrize("confidence", [0.01, 0.50, 0.99])
    def test_malicious_always_high(self, rs, confidence):
        r = rs.calculate_risk_score('MALICIOUS', confidence, 'APK')
        assert r['risk_level'] == 'HIGH'

    @pytest.mark.parametrize("confidence", [0.01, 0.50, 0.99])
    def test_suspicious_always_medium(self, rs, confidence):
        r = rs.calculate_risk_score('SUSPICIOUS', confidence, 'URL')
        assert r['risk_level'] == 'MEDIUM'


class TestRiskScoreBands:
    """Score must stay within the correct band for each prediction."""

    def test_safe_score_in_low_band(self, rs):
        for conf in [0.01, 0.50, 0.99, 1.0]:
            r = rs.calculate_risk_score('SAFE', conf, 'URL')
            assert 0 <= r['risk_score'] <= 39, (
                f"SAFE conf={conf} score={r['risk_score']} outside LOW band 0-39"
            )

    def test_phishing_score_in_high_band(self, rs):
        for conf in [0.01, 0.50, 0.99, 1.0]:
            r = rs.calculate_risk_score('PHISHING', conf, 'URL')
            assert 70 <= r['risk_score'] <= 100, (
                f"PHISHING conf={conf} score={r['risk_score']} outside HIGH band 70-100"
            )

    def test_suspicious_score_in_medium_band(self, rs):
        for conf in [0.01, 0.50, 0.99]:
            r = rs.calculate_risk_score('SUSPICIOUS', conf, 'URL')
            assert 40 <= r['risk_score'] <= 69, (
                f"SUSPICIOUS conf={conf} score={r['risk_score']} outside MEDIUM band 40-69"
            )

    def test_score_never_exceeds_100(self, rs):
        r = rs.calculate_risk_score('PHISHING', 1.0, 'URL',
                                    features={'important_features': {'has_ip_address': True,
                                                                      'no_https': True,
                                                                      'suspicious_keywords_count': 5,
                                                                      'multiple_subdomains': 5}})
        assert r['risk_score'] <= 100

    def test_score_never_below_0(self, rs):
        r = rs.calculate_risk_score('SAFE', 0.0, 'URL')
        assert r['risk_score'] >= 0


class TestFeatureAdjustmentsStayInBand:
    """Feature adjustments must not push score outside the prediction band."""

    def test_safe_with_suspicious_url_features_stays_low(self, rs):
        """Even if the URL has suspicious features, a SAFE verdict stays LOW."""
        features = {
            'important_features': {
                'has_ip_address': True,
                'no_https': True,
                'suspicious_keywords_count': 5,
                'multiple_subdomains': 4,
            }
        }
        r = rs.calculate_risk_score('SAFE', 0.99, 'URL', features=features)
        assert r['risk_level'] == 'LOW'
        assert r['risk_score'] <= 39

    def test_phishing_with_message_features_stays_high(self, rs):
        features = {
            'indicators': ['Urgent language', 'Financial/monetary', 'Account suspension'],
            'has_url': True,
        }
        r = rs.calculate_risk_score('PHISHING', 0.9, 'MESSAGE', features=features)
        assert r['risk_level'] == 'HIGH'
        assert r['risk_score'] >= 70

    def test_safe_message_scan_stays_low(self, rs):
        r = rs.calculate_risk_score('SAFE', 0.95, 'MESSAGE',
                                    features={'indicators': [], 'has_url': False})
        assert r['risk_level'] == 'LOW'
        assert r['risk_score'] <= 39

    def test_safe_apk_scan_stays_low(self, rs):
        r = rs.calculate_risk_score('SAFE', 0.9, 'APK',
                                    features={'dangerous_permission_count': 20,
                                              'dex_count': 5,
                                              'component_count': 100})
        assert r['risk_level'] == 'LOW'
        assert r['risk_score'] <= 39


class TestHighConfidenceSafeIsPreviouslyBrokenCase:
    """Regression: google.com at 99% confidence was returning risk=39 / level ambiguous.
    After fix: must be LOW and score <= 39."""

    def test_google_safe_99pct(self, rs):
        r = rs.calculate_risk_score('SAFE', 0.99, 'URL')
        assert r['risk_level'] == 'LOW'
        assert r['risk_score'] <= 39

    def test_amazon_safe_87pct(self, rs):
        r = rs.calculate_risk_score('SAFE', 0.87, 'URL')
        assert r['risk_level'] == 'LOW'
        assert r['risk_score'] <= 39
