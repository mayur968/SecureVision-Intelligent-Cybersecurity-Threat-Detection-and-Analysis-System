"""Text feature extraction for email/SMS phishing detection."""

from typing import List, Dict
import re
from collections import Counter


class TextFeatureExtractor:
    """Extract comprehensive features from text messages for phishing detection."""
    
    # Phishing indicator keywords (expanded)
    URGENT_WORDS = [
        'urgent', 'immediately', 'action required', 'act now', 'limited time',
        'expires', 'hurry', 'quick', 'fast', 'asap', 'emergency', 'expire',
        'deadline', 'today', 'now', 'rush', 'instant', 'final notice'
    ]
    
    FINANCIAL_WORDS = [
        'bank', 'account', 'credit card', 'payment', 'money', 'transfer',
        'wire', 'refund', 'tax', 'irs', 'cash', 'prize', 'winner', 'lottery',
        'inheritance', 'claim', 'reward', 'debt', 'owe', 'balance', 'paypal',
        'venmo', 'transaction', 'billing', 'invoice', 'purchase'
    ]
    
    SECURITY_WORDS = [
        'verify', 'confirm', 'update', 'secure', 'suspend', 'lock', 'unlock',
        'password', 'pin', 'otp', 'security', 'authentication', 'credentials',
        'id', 'ssn', 'social security', 'validate', 'reactivate', 'restore',
        'two-factor', '2fa', 'code', 'token'
    ]
    
    THREAT_WORDS = [
        'suspended', 'terminated', 'blocked', 'closed', 'cancelled', 'expire',
        'fraud', 'unauthorized', 'unusual activity', 'security alert', 'breach',
        'compromised', 'hacked', 'stolen', 'frozen', 'restricted', 'disabled'
    ]
    
    REQUEST_WORDS = [
        'click here', 'click link', 'follow link', 'download', 'open attachment',
        'reply', 'respond', 'call', 'contact us', 'visit', 'go to', 'log in',
        'sign in', 'enter', 'provide', 'submit', 'send', 'complete', 'fill out'
    ]
    
    # Social engineering tactics
    SCARCITY_WORDS = [
        'limited', 'only', 'exclusive', 'rare', 'final', 'last chance',
        'ending soon', 'act fast', 'limited time', 'while supplies last'
    ]
    
    AUTHORITY_WORDS = [
        'official', 'government', 'irs', 'fbi', 'police', 'court',
        'legal', 'law', 'authorized', 'verified', 'certified'
    ]
    
    REWARD_WORDS = [
        'congratulations', 'winner', 'won', 'prize', 'reward', 'gift',
        'free', 'bonus', 'selected', 'chosen', 'qualify', 'earn'
    ]
    
    def __init__(self):
        """Initialize feature extractor with enhanced patterns."""
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+|\b\w+\.\w{2,}\b')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b|\(\d{3}\)\s*\d{3}[-.]?\d{4}')
        self.money_pattern = re.compile(r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|usd|€|pounds?|gbp)')
        self.time_pattern = re.compile(r'\b(?:\d{1,2}:\d{2}|\d{1,2}\s*(?:am|pm|hours?))\b', re.IGNORECASE)
        
        # Suspicious patterns
        self.html_tag_pattern = re.compile(r'<[^>]+>')
        self.encoded_pattern = re.compile(r'%[0-9A-Fa-f]{2}')
        self.base64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
        self.ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    
    def extract_features(self, text: str) -> Dict[str, int]:
        """
        Extract comprehensive features from text message.
        
        Args:
            text: Message text
            
        Returns:
            Dictionary of features (50+ features)
        """
        text_lower = text.lower()
        words = text.split()
        
        features = {
            # Basic text statistics (10 features)
            'length': len(text),
            'word_count': len(words),
            'char_count': len(text),
            'sentence_count': max(1, text.count('.') + text.count('!') + text.count('?')),
            'avg_word_length': sum(len(word) for word in words) / max(len(words), 1),
            'line_count': text.count('\n') + 1,
            'whitespace_ratio': sum(1 for c in text if c.isspace()) / max(len(text), 1),
            
            # Pattern-based features (10 features)
            'has_url': 1 if self.url_pattern.search(text) else 0,
            'url_count': len(self.url_pattern.findall(text)),
            'has_email': 1 if self.email_pattern.search(text) else 0,
            'email_count': len(self.email_pattern.findall(text)),
            'has_phone': 1 if self.phone_pattern.search(text) else 0,
            'phone_count': len(self.phone_pattern.findall(text)),
            'has_money': 1 if self.money_pattern.search(text) else 0,
            'money_count': len(self.money_pattern.findall(text)),
            'has_time': 1 if self.time_pattern.search(text) else 0,
            'has_ip': 1 if self.ip_pattern.search(text) else 0,
            
            # Character features (10 features)
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'uppercase_words': sum(1 for word in words if word.isupper() and len(word) > 1),
            'digit_count': sum(1 for c in text if c.isdigit()),
            'special_char_count': sum(1 for c in text if not c.isalnum() and not c.isspace()),
            'caps_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
            'digit_ratio': sum(1 for c in text if c.isdigit()) / max(len(text), 1),
            'punctuation_density': (text.count('!') + text.count('?') + text.count('.')) / max(len(text), 1),
            'has_html_tags': 1 if self.html_tag_pattern.search(text) else 0,
            'has_encoded': 1 if self.encoded_pattern.search(text) else 0,
            
            # Keyword categories (10 features) - expanded
            'urgent_words': self._count_keywords(text_lower, self.URGENT_WORDS),
            'financial_words': self._count_keywords(text_lower, self.FINANCIAL_WORDS),
            'security_words': self._count_keywords(text_lower, self.SECURITY_WORDS),
            'threat_words': self._count_keywords(text_lower, self.THREAT_WORDS),
            'request_words': self._count_keywords(text_lower, self.REQUEST_WORDS),
            'scarcity_words': self._count_keywords(text_lower, self.SCARCITY_WORDS),
            'authority_words': self._count_keywords(text_lower, self.AUTHORITY_WORDS),
            'reward_words': self._count_keywords(text_lower, self.REWARD_WORDS),
            'total_suspicious_keywords': 0,  # Will be calculated
            'keyword_density': 0,  # Will be calculated
            
            # Suspicious patterns (10 features) - expanded
            'has_click_here': 1 if 'click here' in text_lower or 'click link' in text_lower else 0,
            'has_verify': 1 if 'verify' in text_lower else 0,
            'has_urgent': 1 if 'urgent' in text_lower or 'immediately' in text_lower else 0,
            'has_suspended': 1 if 'suspend' in text_lower or 'locked' in text_lower else 0,
            'has_winner': 1 if 'winner' in text_lower or 'won' in text_lower or 'prize' in text_lower else 0,
            'has_account': 1 if 'account' in text_lower else 0,
            'has_password': 1 if 'password' in text_lower or 'pin' in text_lower else 0,
            'has_alert': 1 if 'alert' in text_lower or 'warning' in text_lower else 0,
            'has_confirm': 1 if 'confirm' in text_lower else 0,
            'has_update': 1 if 'update' in text_lower else 0,
            
            # Social engineering tactics (5 features) - new
            'uses_scarcity': 1 if any(word in text_lower for word in ['limited', 'expires', 'hurry', 'last chance']) else 0,
            'uses_authority': 1 if any(word in text_lower for word in ['official', 'government', 'irs', 'legal']) else 0,
            'uses_fear': 1 if any(word in text_lower for word in ['suspended', 'fraud', 'unauthorized', 'breach']) else 0,
            'uses_greed': 1 if any(word in text_lower for word in ['prize', 'winner', 'reward', 'free']) else 0,
            'social_engineering_score': 0,  # Will be calculated
            
            # Advanced linguistic features (5 features) - new
            'misspelling_indicators': self._detect_misspellings(text_lower),
            'grammar_issues': self._detect_grammar_issues(text),
            'formality_score': self._calculate_formality(text_lower, words),
            'complexity_score': self._calculate_complexity(words),
            'entropy': self._calculate_text_entropy(text_lower),
        }
        
        # Calculate derived features
        features['total_suspicious_keywords'] = (
            features['urgent_words'] + features['financial_words'] +
            features['security_words'] + features['threat_words'] +
            features['request_words'] + features['scarcity_words'] +
            features['authority_words'] + features['reward_words']
        )
        
        features['keyword_density'] = features['total_suspicious_keywords'] / max(len(words), 1)
        
        features['social_engineering_score'] = (
            features['uses_scarcity'] + features['uses_authority'] +
            features['uses_fear'] + features['uses_greed']
        ) / 4.0
        
        return features
    
    def _detect_misspellings(self, text: str) -> int:
        """Detect potential intentional misspellings (1337 speak, character substitution)."""
        count = 0
        
        # Common phishing misspelling patterns
        patterns = {
            '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's',
            '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i'
        }
        
        for fake, real in patterns.items():
            if fake in text:
                count += text.count(fake)
        
        # Repeated letters (gooood deal -> good deal)
        repeated = re.findall(r'(.)\1{2,}', text)
        count += len(repeated)
        
        return min(count, 10)  # Cap at 10
    
    def _detect_grammar_issues(self, text: str) -> int:
        """Detect basic grammar issues (missing capitals, spacing issues)."""
        issues = 0
        
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 5:
                # Check if sentence starts with lowercase
                if sentence[0].islower():
                    issues += 1
        
        # Check for multiple spaces
        if '  ' in text:
            issues += 1
        
        # Check for missing spaces after punctuation
        if re.search(r'[.!?,][a-zA-Z]', text):
            issues += 1
        
        return min(issues, 5)  # Cap at 5
    
    def _calculate_formality(self, text: str, words: List[str]) -> float:
        """Calculate formality score (0-1, higher = more formal)."""
        if not words:
            return 0.5
        
        informal_indicators = ['gonna', 'wanna', 'gotta', 'yeah', 'nah', 'lol', 'omg', 'btw', 'idk']
        informal_count = sum(1 for word in words if word in informal_indicators)
        
        # Contractions count as informal
        contraction_count = text.count("'")
        
        # All caps words are informal/aggressive
        all_caps_count = sum(1 for word in words if word.isupper() and len(word) > 1)
        
        informal_score = (informal_count + contraction_count * 0.5 + all_caps_count * 0.5) / max(len(words), 1)
        
        # Return formality (inverse of informal)
        return max(0, min(1, 1 - informal_score * 5))
    
    def _calculate_complexity(self, words: List[str]) -> float:
        """Calculate text complexity based on word length and variety."""
        if not words:
            return 0
        
        # Average word length
        avg_len = sum(len(word) for word in words) / len(words)
        
        # Vocabulary richness (unique words / total words)
        unique_ratio = len(set(words)) / len(words)
        
        # Simple complexity score
        complexity = (avg_len / 10) * 0.5 + unique_ratio * 0.5
        
        return round(complexity, 3)
    
    def _calculate_text_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0
        
        try:
            import math
            from collections import Counter
            
            freq = Counter(text)
            total = sum(freq.values())
            entropy = -sum((count/total) * math.log2(count/total) for count in freq.values())
            
            return round(entropy, 3)
        except Exception:
            return 0.0
    
    def _count_keywords(self, text: str, keywords: List[str]) -> int:
        """Count occurrences of keywords in text."""
        count = 0
        for keyword in keywords:
            if keyword in text:
                count += 1
        return count
    
    def get_feature_names(self) -> List[str]:
        """Get list of feature names (60 features total)."""
        return [
            # Basic text statistics (10)
            'length', 'word_count', 'char_count', 'sentence_count',
            'avg_word_length', 'line_count', 'whitespace_ratio',
            
            # Pattern-based features (10)
            'has_url', 'url_count', 'has_email', 'email_count',
            'has_phone', 'phone_count', 'has_money', 'money_count',
            'has_time', 'has_ip',
            
            # Character features (10)
            'exclamation_count', 'question_count', 'uppercase_words', 'digit_count',
            'special_char_count', 'caps_ratio', 'digit_ratio', 'punctuation_density',
            'has_html_tags', 'has_encoded',
            
            # Keyword categories (10)
            'urgent_words', 'financial_words', 'security_words', 'threat_words',
            'request_words', 'scarcity_words', 'authority_words', 'reward_words',
            'total_suspicious_keywords', 'keyword_density',
            
            # Suspicious patterns (10)
            'has_click_here', 'has_verify', 'has_urgent', 'has_suspended',
            'has_winner', 'has_account', 'has_password', 'has_alert',
            'has_confirm', 'has_update',
            
            # Social engineering tactics (5)
            'uses_scarcity', 'uses_authority', 'uses_fear', 'uses_greed',
            'social_engineering_score',
            
            # Advanced linguistic features (5)
            'misspelling_indicators', 'grammar_issues', 'formality_score',
            'complexity_score', 'entropy'
        ]
