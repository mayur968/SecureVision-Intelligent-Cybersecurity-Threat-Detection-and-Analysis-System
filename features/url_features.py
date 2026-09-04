"""URL feature extraction for phishing detection."""

import re
from urllib.parse import urlparse
from typing import Dict
import numpy as np


class URLFeatureExtractor:
    """Extract features from URLs for phishing detection."""
    
    # Suspicious keywords commonly found in phishing URLs
    SUSPICIOUS_KEYWORDS = [
        'login', 'verify', 'account', 'secure', 'update', 'password',
        'bank', 'signin', 'confirm', 'security', 'suspend', 'verify',
        'verification', 'authenticate', 'wallet', 'paypal', 'ebay',
        'amazon', 'apple', 'microsoft', 'alert', 'urgent', 'unlock'
    ]
    
    def __init__(self):
        """Initialize feature extractor."""
        pass
    
    def extract_features(self, url: str) -> Dict[str, float]:
        """
        Extract numerical features from a URL.
        
        Args:
            url: URL string to analyze
            
        Returns:
            Dictionary of feature names and values
        """
        try:
            parsed = urlparse(url)
            
            features = {
                'url_length': len(url),
                'domain_length': len(parsed.netloc),
                'num_dots': url.count('.'),
                'num_hyphens': url.count('-'),
                'num_underscores': url.count('_'),
                'num_slashes': url.count('/'),
                'num_questionmarks': url.count('?'),
                'num_equals': url.count('='),
                'num_at': url.count('@'),
                'num_ampersand': url.count('&'),
                'num_digits': sum(c.isdigit() for c in url),
                'num_params': len(parsed.query.split('&')) if parsed.query else 0,
                'is_https': 1 if parsed.scheme == 'https' else 0,
                'has_ip': self._has_ip_address(parsed.netloc),
                'num_subdomains': self._count_subdomains(parsed.netloc),
                'suspicious_keywords': self._count_suspicious_keywords(url.lower()),
                'domain_has_digits': 1 if any(c.isdigit() for c in parsed.netloc) else 0,
                'path_length': len(parsed.path),
                'query_length': len(parsed.query) if parsed.query else 0,
                'has_port': 1 if ':' in parsed.netloc and not parsed.netloc.startswith('[') else 0,
            }
            
            return features
            
        except Exception as e:
            # Return default features on error
            return self._get_default_features()
    
    def extract_feature_vector(self, url: str) -> np.ndarray:
        """
        Extract features as numpy array for model prediction.
        
        Args:
            url: URL string to analyze
            
        Returns:
            NumPy array of features
        """
        features = self.extract_features(url)
        return np.array(list(features.values())).reshape(1, -1)
    
    def get_feature_names(self) -> list:
        """Get list of feature names in order."""
        return [
            'url_length', 'domain_length', 'num_dots', 'num_hyphens',
            'num_underscores', 'num_slashes', 'num_questionmarks', 'num_equals',
            'num_at', 'num_ampersand', 'num_digits', 'num_params',
            'is_https', 'has_ip', 'num_subdomains', 'suspicious_keywords',
            'domain_has_digits', 'path_length', 'query_length', 'has_port'
        ]
    
    def _has_ip_address(self, domain: str) -> int:
        """Check if domain contains an IP address."""
        ip_pattern = re.compile(
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        )
        return 1 if ip_pattern.match(domain) else 0
    
    def _count_subdomains(self, domain: str) -> int:
        """Count number of subdomains."""
        # Remove port if present
        domain = domain.split(':')[0]
        
        # Split by dots and count
        parts = domain.split('.')
        
        # Typical domain has 2 parts (example.com)
        # Subdomains add more parts (www.example.com has 1 subdomain)
        if len(parts) <= 2:
            return 0
        return len(parts) - 2
    
    def _count_suspicious_keywords(self, url_lower: str) -> int:
        """Count suspicious keywords in URL."""
        count = 0
        for keyword in self.SUSPICIOUS_KEYWORDS:
            if keyword in url_lower:
                count += 1
        return count
    
    def _get_default_features(self) -> Dict[str, float]:
        """Get default feature values."""
        return {name: 0.0 for name in self.get_feature_names()}
