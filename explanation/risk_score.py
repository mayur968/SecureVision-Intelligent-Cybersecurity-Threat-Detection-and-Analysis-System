"""Risk scoring module for threat assessment."""

from typing import Dict


class RiskScorer:
    """Calculate risk scores for detected threats."""
    
    # Risk level thresholds
    LOW_THRESHOLD = 40
    MEDIUM_THRESHOLD = 70
    
    def __init__(self):
        """Initialize risk scorer."""
        pass
    
    def calculate_risk_score(
        self,
        prediction: str,
        confidence: float,
        scan_type: str,
        features: Dict = None
    ) -> Dict:
        """
        Calculate risk score based on prediction and features.
        
        Args:
            prediction: Prediction label (SAFE, PHISHING, MALICIOUS, etc.)
            confidence: Model confidence (0.0 to 1.0)
            scan_type: Type of scan (URL, MESSAGE, APK)
            features: Additional features that may affect risk
            
        Returns:
            Dictionary with risk_score (0-100) and risk_level (LOW/MEDIUM/HIGH)
        """
        # Base score from prediction
        if prediction in ['SAFE']:
            base_score = 10  # Low base risk for safe predictions
        elif prediction in ['PHISHING', 'MALICIOUS']:
            base_score = 70  # High base risk for threats
        else:
            base_score = 50  # Unknown/error state
        
        # Adjust by confidence
        confidence_adjusted = base_score + (confidence * 30)
        
        # Additional adjustments based on scan type and features
        if features:
            if scan_type == 'URL':
                confidence_adjusted = self._adjust_url_risk(confidence_adjusted, features)
            elif scan_type == 'MESSAGE':
                confidence_adjusted = self._adjust_message_risk(confidence_adjusted, features)
            elif scan_type == 'APK':
                confidence_adjusted = self._adjust_apk_risk(confidence_adjusted, features)
        
        # Ensure score is in valid range
        final_score = int(max(0, min(100, confidence_adjusted)))
        
        # Determine risk level
        if final_score < self.LOW_THRESHOLD:
            risk_level = 'LOW'
        elif final_score < self.MEDIUM_THRESHOLD:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'HIGH'
        
        return {
            'risk_score': final_score,
            'risk_level': risk_level
        }
    
    def _adjust_url_risk(self, base_score: float, features: Dict) -> float:
        """Adjust risk score for URL-specific features."""
        score = base_score
        
        important_features = features.get('important_features', {})
        
        # IP address in URL - high risk
        if important_features.get('has_ip_address'):
            score += 10
        
        # No HTTPS - medium risk
        if important_features.get('no_https'):
            score += 5
        
        # Multiple suspicious keywords
        keyword_count = important_features.get('suspicious_keywords_count', 0)
        if keyword_count > 2:
            score += 10
        elif keyword_count > 0:
            score += 5
        
        # Many subdomains - medium risk
        subdomain_count = important_features.get('multiple_subdomains', 0)
        if subdomain_count > 3:
            score += 8
        
        return score
    
    def _adjust_message_risk(self, base_score: float, features: Dict) -> float:
        """Adjust risk score for message-specific features."""
        score = base_score
        
        indicators = features.get('indicators', [])
        
        # Count high-risk indicators
        high_risk_patterns = [
            'Urgent language',
            'Financial/monetary',
            'Security/verification',
            'Threatening language',
            'Account suspension'
        ]
        
        for indicator in indicators:
            for pattern in high_risk_patterns:
                if pattern.lower() in indicator.lower():
                    score += 5
                    break
        
        # URL in message
        if features.get('has_url'):
            score += 5
        
        return score
    
    def _adjust_apk_risk(self, base_score: float, features: Dict) -> float:
        """Adjust risk score for APK-specific features."""
        score = base_score
        
        # Dangerous permissions
        dangerous_count = features.get('dangerous_permission_count', 0)
        if dangerous_count > 15:
            score += 15
        elif dangerous_count > 10:
            score += 10
        elif dangerous_count > 5:
            score += 5
        
        # Multiple DEX files (obfuscation indicator)
        dex_count = features.get('dex_count', 1)
        if dex_count > 3:
            score += 10
        elif dex_count > 1:
            score += 5
        
        # Many components
        component_count = features.get('component_count', 0)
        if component_count > 50:
            score += 8
        
        return score
    
    def get_risk_description(self, risk_level: str) -> str:
        """Get description for risk level."""
        descriptions = {
            'LOW': 'No immediate threat indicators detected. Continue following normal security practices.',
            'MEDIUM': 'Some suspicious characteristics detected. Exercise caution and verify before proceeding.',
            'HIGH': 'Multiple threat indicators detected. High risk of malicious activity. Avoid interaction.'
        }
        return descriptions.get(risk_level, 'Risk level unknown.')
