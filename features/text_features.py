"""Text feature extraction for email/SMS phishing detection."""

from typing import List, Dict
import re


class TextFeatureExtractor:
    """Extract features from text messages for phishing detection."""
    
    # Phishing indicator keywords
    URGENT_WORDS = [
        'urgent', 'immediately', 'action required', 'act now', 'limited time',
        'expires', 'hurry', 'quick', 'fast', 'asap', 'emergency'
    ]
    
    FINANCIAL_WORDS = [
        'bank', 'account', 'credit card', 'payment', 'money', 'transfer',
        'wire', 'refund', 'tax', 'irs', 'cash', 'prize', 'winner', 'lottery',
        'inheritance', 'claim', 'reward'
    ]
    
    SECURITY_WORDS = [
        'verify', 'confirm', 'update', 'secure', 'suspend', 'lock', 'unlock',
        'password', 'pin', 'otp', 'security', 'authentication', 'credentials',
        'id', 'ssn', 'social security'
    ]
    
    THREAT_WORDS = [
        'suspended', 'terminated', 'blocked', 'closed', 'cancelled', 'expire',
        'fraud', 'unauthorized', 'unusual activity', 'security alert'
    ]
    
    REQUEST_WORDS = [
        'click here', 'click link', 'follow link', 'download', 'open attachment',
        'reply', 'respond', 'call', 'contact us', 'visit', 'go to'
    ]
    
    def __init__(self):
        """Initialize feature extractor."""
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.email_pattern = re.compile(r'\S+@\S+')
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    
    def extract_features(self, text: str) -> Dict[str, int]:
        """
        Extract features from text message.
        
        Args:
            text: Message text
            
        Returns:
            Dictionary of features
        """
        text_lower = text.lower()
        
        features = {
            'length': len(text),
            'word_count': len(text.split()),
            'char_count': len(text),
            'sentence_count': max(1, text.count('.') + text.count('!') + text.count('?')),
            
            # Pattern-based features
            'has_url': 1 if self.url_pattern.search(text) else 0,
            'url_count': len(self.url_pattern.findall(text)),
            'has_email': 1 if self.email_pattern.search(text) else 0,
            'has_phone': 1 if self.phone_pattern.search(text) else 0,
            
            # Character features
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'uppercase_words': sum(1 for word in text.split() if word.isupper() and len(word) > 1),
            'digit_count': sum(1 for c in text if c.isdigit()),
            
            # Keyword features
            'urgent_words': self._count_keywords(text_lower, self.URGENT_WORDS),
            'financial_words': self._count_keywords(text_lower, self.FINANCIAL_WORDS),
            'security_words': self._count_keywords(text_lower, self.SECURITY_WORDS),
            'threat_words': self._count_keywords(text_lower, self.THREAT_WORDS),
            'request_words': self._count_keywords(text_lower, self.REQUEST_WORDS),
            
            # Suspicious patterns
            'has_click_here': 1 if 'click here' in text_lower or 'click link' in text_lower else 0,
            'has_verify': 1 if 'verify' in text_lower else 0,
            'has_urgent': 1 if 'urgent' in text_lower or 'immediately' in text_lower else 0,
            'has_suspended': 1 if 'suspend' in text_lower or 'locked' in text_lower else 0,
        }
        
        return features
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count occurrences of keywords in text."""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names."""
        return [
            'length', 'word_count', 'char_count', 'sentence_count',
            'has_url', 'url_count', 'has_email', 'has_phone',
            'exclamation_count', 'question_count', 'uppercase_words', 'digit_count',
            'urgent_words', 'financial_words', 'security_words', 'threat_words', 'request_words',
            'has_click_here', 'has_verify', 'has_urgent', 'has_suspended'
        ]
