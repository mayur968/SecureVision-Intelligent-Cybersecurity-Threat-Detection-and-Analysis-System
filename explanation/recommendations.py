"""Security recommendations generator."""

from typing import List


class RecommendationEngine:
    """Generate security recommendations based on threats."""
    
    def __init__(self):
        """Initialize recommendation engine."""
        pass
    
    def get_recommendations(
        self,
        prediction: str,
        scan_type: str,
        risk_level: str,
        features: dict = None
    ) -> List[str]:
        """
        Generate security recommendations.
        
        Args:
            prediction: Prediction label (SAFE, PHISHING, MALICIOUS)
            scan_type: Type of scan (URL, MESSAGE, APK)
            risk_level: Risk level (LOW/MEDIUM/HIGH)
            features: Additional features that may affect recommendations
            
        Returns:
            List of recommendation strings
        """
        if scan_type == 'URL':
            return self._url_recommendations(prediction, risk_level, features)
        elif scan_type == 'MESSAGE':
            return self._message_recommendations(prediction, risk_level, features)
        elif scan_type == 'APK':
            return self._apk_recommendations(prediction, risk_level, features)
        else:
            return self._general_recommendations(prediction)
    
    def _url_recommendations(
        self,
        prediction: str,
        risk_level: str,
        features: dict
    ) -> List[str]:
        """Generate URL-specific recommendations."""
        if prediction == 'SAFE':
            return [
                "No immediate threat detected, but always verify the URL before entering sensitive data",
                "Check for HTTPS encryption when entering passwords or payment information",
                "Bookmark frequently used websites to avoid typosquatting attacks",
                "Be cautious of URLs received through unsolicited messages"
            ]
        
        elif prediction == 'PHISHING':
            recommendations = [
                "Do NOT enter personal information, passwords, or credentials on this website",
                "Do NOT provide banking information, credit card details, or OTP codes",
                "Close this website immediately and do not click any links",
                "Verify the legitimate website address independently through official sources",
                "Report this phishing attempt to your organization's IT security team"
            ]
            
            # Add specific recommendations based on features
            if features and features.get('important_features', {}).get('no_https'):
                recommendations.append(
                    "This site does not use HTTPS - never enter sensitive information on non-encrypted sites"
                )
            
            if features and features.get('important_features', {}).get('has_ip_address'):
                recommendations.append(
                    "Legitimate websites rarely use IP addresses directly - this is highly suspicious"
                )
            
            return recommendations
        
        else:
            return self._general_recommendations(prediction)
    
    def _message_recommendations(
        self,
        prediction: str,
        risk_level: str,
        features: dict
    ) -> List[str]:
        """Generate message-specific recommendations."""
        if prediction == 'SAFE':
            return [
                "No phishing patterns detected, but remain vigilant with unsolicited messages",
                "Verify sender identity through official channels before responding",
                "Do not click on links from unknown or unexpected sources",
                "Be cautious of messages creating urgency or requesting personal information"
            ]
        
        elif prediction == 'PHISHING':
            recommendations = [
                "Do NOT click on any links in this message",
                "Do NOT reply to this message or provide any information",
                "Do NOT share passwords, OTP codes, or personal identification numbers",
                "Do NOT download attachments or files from this message",
                "Verify the sender's identity through official contact channels independently",
                "Report this message as phishing to your email provider or mobile carrier",
                "Delete the message after reporting it"
            ]
            
            # Add specific recommendations based on indicators
            if features and features.get('indicators'):
                indicators = features['indicators']
                
                if any('urgent' in str(i).lower() for i in indicators):
                    recommendations.append(
                        "Urgent language is a common phishing tactic - take time to verify independently"
                    )
                
                if any('account' in str(i).lower() and 'suspend' in str(i).lower() for i in indicators):
                    recommendations.append(
                        "Legitimate companies rarely threaten account suspension - verify through official website"
                    )
                
                if any('prize' in str(i).lower() or 'winner' in str(i).lower() for i in indicators):
                    recommendations.append(
                        "Unsolicited prize notifications are typically scams - do not respond"
                    )
            
            return recommendations
        
        else:
            return self._general_recommendations(prediction)
    
    def _apk_recommendations(
        self,
        prediction: str,
        risk_level: str,
        features: dict
    ) -> List[str]:
        """Generate APK-specific recommendations."""
        if prediction == 'SAFE':
            recommendations = [
                "Static analysis shows no immediate malware indicators",
                "Install applications only from official app stores (Google Play, etc.)",
                "Review app permissions before installation and deny unnecessary permissions",
                "Keep your device's security software updated",
                "Regularly review installed applications and remove unused apps"
            ]
            
            # Add specific advice based on features
            if features and features.get('dangerous_permission_count', 0) > 0:
                count = features['dangerous_permission_count']
                recommendations.insert(1, 
                    f"This app requests {count} sensitive permission(s) - ensure you trust the source"
                )
            
            return recommendations
        
        elif prediction == 'MALICIOUS':
            recommendations = [
                "Do NOT install this application",
                "Delete the APK file from your device immediately",
                "If already installed, uninstall the application immediately",
                "Run a security scan on your device",
                "Only download applications from trusted sources like Google Play Store",
                "Avoid sideloading APK files from unknown websites or third parties",
                "Check app reviews and ratings before installing any application"
            ]
            
            # Add specific recommendations based on features
            if features:
                dangerous_count = features.get('dangerous_permission_count', 0)
                if dangerous_count > 10:
                    recommendations.insert(2,
                        f"This app requests {dangerous_count} dangerous permissions - typical of malware"
                    )
                
                if features.get('dex_count', 1) > 1:
                    recommendations.insert(3,
                        "Multiple DEX files detected - may indicate code obfuscation or packing"
                    )
            
            recommendations.append(
                "If you received this APK through email or messaging, report it as malware"
            )
            
            return recommendations
        
        else:
            return self._general_recommendations(prediction)
    
    def _general_recommendations(self, prediction: str) -> List[str]:
        """General security recommendations."""
        return [
            "Follow cybersecurity best practices",
            "Keep your software and security tools updated",
            "Use strong, unique passwords for all accounts",
            "Enable two-factor authentication where available",
            "Be cautious of unsolicited communications",
            "Verify sources before providing personal information"
        ]
    
    def format_recommendations(self, recommendations: List[str]) -> str:
        """
        Format recommendations as a readable string.
        
        Args:
            recommendations: List of recommendation strings
            
        Returns:
            Formatted recommendation text
        """
        if not recommendations:
            return "No specific recommendations available."
        
        formatted = "Security Recommendations:\n\n"
        for i, rec in enumerate(recommendations, 1):
            formatted += f"{i}. {rec}\n"
        
        return formatted.strip()
