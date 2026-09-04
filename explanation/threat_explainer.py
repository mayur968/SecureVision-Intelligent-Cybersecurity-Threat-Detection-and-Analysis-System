"""Threat explanation engine for SecureVision."""

from typing import Dict, List


class ThreatExplainer:
    """Generate human-readable explanations for threat detections."""
    
    def __init__(self):
        """Initialize threat explainer."""
        pass
    
    def explain(
        self,
        prediction: str,
        confidence: float,
        scan_type: str,
        features: Dict
    ) -> str:
        """
        Generate explanation for a threat prediction.
        
        Args:
            prediction: Prediction label (SAFE, PHISHING, MALICIOUS)
            confidence: Model confidence (0.0 to 1.0)
            scan_type: Type of scan (URL, MESSAGE, APK)
            features: Features or indicators from detection
            
        Returns:
            Human-readable explanation string
        """
        if scan_type == 'URL':
            return self._explain_url(prediction, confidence, features)
        elif scan_type == 'MESSAGE':
            return self._explain_message(prediction, confidence, features)
        elif scan_type == 'APK':
            return self._explain_apk(prediction, confidence, features)
        else:
            return f"Analysis result: {prediction}"
    
    def _explain_url(self, prediction: str, confidence: float, features: Dict) -> str:
        """Generate explanation for URL scan."""
        if prediction == 'SAFE':
            return (
                f"This URL was classified as safe with {confidence*100:.1f}% confidence. "
                "No significant phishing indicators were detected. However, always verify "
                "the legitimacy of websites before entering sensitive information."
            )
        
        elif prediction == 'PHISHING':
            important_features = features.get('important_features', {})
            
            explanation = (
                f"This URL was flagged as potentially phishing with {confidence*100:.1f}% confidence. "
                "The following suspicious characteristics were detected:\n\n"
            )
            
            reasons = []
            
            if important_features.get('no_https'):
                reasons.append("• The URL does not use HTTPS encryption")
            
            if important_features.get('has_ip_address'):
                reasons.append("• The URL uses an IP address instead of a domain name")
            
            if important_features.get('suspicious_keywords_count', 0) > 0:
                count = important_features['suspicious_keywords_count']
                reasons.append(f"• Contains {count} suspicious keyword(s) commonly used in phishing attacks")
            
            if important_features.get('multiple_subdomains', 0) > 0:
                count = important_features['multiple_subdomains']
                reasons.append(f"• Has {count} subdomain(s), which may indicate URL obfuscation")
            
            if important_features.get('long_url'):
                reasons.append("• The URL is unusually long, which is common in phishing attempts")
            
            if important_features.get('many_hyphens'):
                reasons.append("• Contains many hyphens, possibly mimicking legitimate domains")
            
            if important_features.get('at_symbol_present'):
                reasons.append("• Contains @ symbol, which can be used for credential theft")
            
            if important_features.get('domain_has_digits'):
                reasons.append("• The domain contains numbers, which is unusual for legitimate sites")
            
            if not reasons:
                reasons.append("• Multiple pattern-based indicators suggest phishing behavior")
            
            explanation += '\n'.join(reasons)
            
            return explanation
        
        else:
            return f"URL analysis result: {prediction}"
    
    def _explain_message(self, prediction: str, confidence: float, features: Dict) -> str:
        """Generate explanation for message scan."""
        if prediction == 'SAFE':
            return (
                f"This message was classified as safe with {confidence*100:.1f}% confidence. "
                "No significant phishing patterns were detected. Continue to exercise normal caution "
                "with unsolicited messages."
            )
        
        elif prediction == 'PHISHING':
            indicators = features.get('indicators', [])
            
            explanation = (
                f"This message was flagged as potentially phishing with {confidence*100:.1f}% confidence. "
                "The following suspicious patterns were detected:\n\n"
            )
            
            # Group and format indicators
            formatted_indicators = []
            for indicator in indicators:
                if indicator and indicator != 'No specific indicators detected':
                    formatted_indicators.append(f"• {indicator}")
            
            if formatted_indicators:
                explanation += '\n'.join(formatted_indicators)
            else:
                explanation += "• Text patterns consistent with phishing messages were detected"
            
            explanation += (
                "\n\nPhishing messages often create urgency, request personal information, "
                "or direct you to suspicious links. Always verify the sender's identity through "
                "official channels before responding."
            )
            
            return explanation
        
        else:
            return f"Message analysis result: {prediction}"
    
    def _explain_apk(self, prediction: str, confidence: float, features: Dict) -> str:
        """Generate explanation for APK scan."""
        analysis_method = features.get('analysis_method', 'unknown')
        
        if prediction == 'SAFE':
            explanation = (
                f"This APK was classified as safe with {confidence*100:.1f}% confidence "
                f"using {analysis_method} analysis. "
            )
            
            if analysis_method == 'androguard':
                perm_count = features.get('permission_count', 0)
                dangerous_count = features.get('dangerous_permission_count', 0)
                explanation += (
                    f"The application requests {perm_count} permissions, "
                    f"including {dangerous_count} potentially dangerous permissions. "
                )
            
            explanation += (
                "No immediate malware indicators were detected in static analysis. "
                "However, install applications only from trusted sources."
            )
            
            return explanation
        
        elif prediction == 'MALICIOUS':
            indicators = features.get('indicators', []) if 'indicators' in features else []
            
            explanation = (
                f"This APK was flagged as potentially malicious with {confidence*100:.1f}% confidence "
                f"based on {analysis_method} analysis. "
                "The following suspicious characteristics were detected:\n\n"
            )
            
            # Add indicators
            formatted_indicators = []
            for indicator in indicators:
                if indicator and 'No significant threats' not in indicator:
                    formatted_indicators.append(f"• {indicator}")
            
            if formatted_indicators:
                explanation += '\n'.join(formatted_indicators)
            else:
                explanation += "• Multiple characteristics associated with malware were detected"
            
            explanation += (
                "\n\nNote: This analysis is based on static inspection only. "
                "The application was not executed. For comprehensive analysis, additional "
                "dynamic analysis would be recommended."
            )
            
            return explanation
        
        else:
            return f"APK analysis result: {prediction}"
    
    def get_detection_summary(
        self,
        prediction: str,
        risk_level: str,
        scan_type: str
    ) -> str:
        """
        Get a brief summary of the detection.
        
        Args:
            prediction: Prediction label
            risk_level: Risk level (LOW/MEDIUM/HIGH)
            scan_type: Type of scan
            
        Returns:
            Brief summary string
        """
        if prediction == 'SAFE':
            return f"No immediate threats detected in {scan_type.lower()} scan."
        elif prediction in ['PHISHING', 'MALICIOUS']:
            return f"{risk_level} risk {prediction.lower()} detected in {scan_type.lower()} scan."
        else:
            return f"{scan_type} scan completed with {prediction} result."
