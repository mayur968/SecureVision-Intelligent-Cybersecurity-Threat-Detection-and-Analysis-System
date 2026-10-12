"""URL feature extraction for phishing detection with advanced analysis."""

import re
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Tuple, Optional
import numpy as np
from datetime import datetime
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import logger


class URLFeatureExtractor:
    """Extract advanced features from URLs for phishing detection."""
    
    # Suspicious keywords commonly found in phishing URLs
    SUSPICIOUS_KEYWORDS = [
        'login', 'verify', 'account', 'secure', 'update', 'password',
        'bank', 'signin', 'confirm', 'security', 'suspend', 'verify',
        'verification', 'authenticate', 'wallet', 'paypal', 'ebay',
        'amazon', 'apple', 'microsoft', 'alert', 'urgent', 'unlock',
        'validate', 'restore', 'limit', 'support', 'service'
    ]
    
    # Popular brand domains for typosquatting detection
    POPULAR_BRANDS = [
        'google.com', 'facebook.com', 'amazon.com', 'apple.com', 'microsoft.com',
        'paypal.com', 'netflix.com', 'instagram.com', 'twitter.com', 'linkedin.com',
        'ebay.com', 'walmart.com', 'chase.com', 'bankofamerica.com', 'wellsfargo.com',
        'citibank.com', 'yahoo.com', 'outlook.com', 'gmail.com', 'dropbox.com'
    ]

    # Known brand domains — keywords in these are NOT suspicious
    KNOWN_BRAND_DOMAINS = [
        'google.com', 'facebook.com', 'amazon.com', 'apple.com', 'microsoft.com',
        'paypal.com', 'netflix.com', 'instagram.com', 'twitter.com', 'linkedin.com',
        'ebay.com', 'walmart.com', 'chase.com', 'bankofamerica.com', 'wellsfargo.com',
        'yahoo.com', 'outlook.com', 'gmail.com', 'dropbox.com', 'icloud.com',
        'adobe.com', 'salesforce.com', 'zoom.us', 'slack.com', 'github.com',
        'stackoverflow.com', 'reddit.com', 'youtube.com', 'wikipedia.org',
        'citibank.com', 'americanexpress.com', 'discover.com', 'usbank.com',
        'tdbank.com', 'schwab.com', 'fidelity.com', 'vanguard.com',
        'target.com', 'bestbuy.com', 'costco.com', 'etsy.com',
        'live.com', 'office.com', 'windows.com', 'azure.com',
        'mozilla.org', 'w3.org', 'python.org', 'cloudflare.com',
        'shopify.com', 'stripe.com', 'ibm.com', 'oracle.com',
    ]
    
    # Suspicious TLDs commonly used in phishing
    SUSPICIOUS_TLDS = [
        '.tk', '.ml', '.ga', '.cf', '.gq',  # Free TLDs
        '.xyz', '.top', '.work', '.click', '.link',
        '.download', '.stream', '.racing', '.loan'
    ]
    
    def __init__(self, skip_whois: bool = False):
        """Initialize feature extractor with optional WHOIS support.
        
        Args:
            skip_whois: Set True during training/batch processing to avoid
                        network lookups that slow down feature extraction.
        """
        self.whois_available = False
        self.tldextract_available = False
        self._skip_whois = skip_whois
        
        # Try to import WHOIS (disabled during training)
        if not skip_whois:
            try:
                import whois
                self.whois = whois
                self.whois_available = True
                logger.info("WHOIS library available for domain age analysis")
            except ImportError:
                logger.warning("python-whois not available. Domain age features will be disabled.")
                self.whois = None
        else:
            self.whois = None
            logger.info("WHOIS disabled (skip_whois=True)")
        
        # Try to import tldextract
        try:
            import tldextract
            self.tldextract = tldextract
            self.tldextract_available = True
            logger.info("tldextract available for domain parsing")
        except ImportError:
            logger.warning("tldextract not available. Advanced domain parsing disabled.")
            self.tldextract = None
        
        # Try to import Levenshtein for typosquatting detection
        try:
            import Levenshtein
            self.Levenshtein = Levenshtein
            self.levenshtein_available = True
            logger.info("Levenshtein available for typosquatting detection")
        except ImportError:
            logger.warning("Levenshtein not available. Typosquatting detection will be basic.")
            self.Levenshtein = None
            self.levenshtein_available = False
        
        # In-memory cache for WHOIS lookups (avoid rate limiting)
        self._whois_cache = {}
        self._cache_max_age = 3600  # 1 hour
    
    def extract_features(self, url: str) -> Dict[str, float]:
        """
        Extract comprehensive numerical features from a URL.
        
        Args:
            url: URL string to analyze
            
        Returns:
            Dictionary of feature names and values (35+ features)
        """
        try:
            parsed = urlparse(url)
            url_lower = url.lower()
            
            # 1. BASIC LEXICAL FEATURES (existing 20 features)
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
                'suspicious_keywords': self._count_suspicious_keywords(url_lower),
                'domain_has_digits': 1 if any(c.isdigit() for c in parsed.netloc) else 0,
                'path_length': len(parsed.path),
                'query_length': len(parsed.query) if parsed.query else 0,
                'has_port': 1 if ':' in parsed.netloc and not parsed.netloc.startswith('[') else 0,
            }
            
            # 2. ADVANCED DOMAIN FEATURES (8 new features)
            domain_features = self._extract_domain_features(parsed.netloc)
            features.update(domain_features)
            
            # 3. TYPOSQUATTING DETECTION (3 new features)
            typo_features = self._detect_typosquatting(parsed.netloc)
            features.update(typo_features)
            
            # 4. URL STRUCTURE FEATURES (5 new features)
            structure_features = self._analyze_url_structure(url, parsed)
            features.update(structure_features)
            
            # 5. WHOIS / DOMAIN AGE (3 new features)
            whois_features = self._get_whois_features(parsed.netloc)
            features.update(whois_features)
            
            # 6. TLD ANALYSIS (2 new features)
            tld_features = self._analyze_tld(parsed.netloc)
            features.update(tld_features)
            
            # 7. REDIRECT & SHORTENER DETECTION (2 new features)
            redirect_features = self._check_redirects_shorteners(parsed.netloc)
            features.update(redirect_features)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting URL features: {e}")
            return self._get_default_features()
    
    def _extract_domain_features(self, domain: str) -> Dict[str, float]:
        """Extract advanced domain-specific features."""
        features = {}
        
        try:
            # Remove port if present
            domain = domain.split(':')[0]
            
            if self.tldextract_available:
                extracted = self.tldextract.extract(domain)
                
                features['tld_length'] = len(extracted.suffix) if extracted.suffix else 0
                features['domain_token_count'] = len(extracted.domain.split('-')) if extracted.domain else 1
                features['subdomain_length'] = len(extracted.subdomain) if extracted.subdomain else 0
                
                # Check for numeric subdomain
                features['subdomain_has_digits'] = 1 if extracted.subdomain and any(c.isdigit() for c in extracted.subdomain) else 0
                
                # Vowel ratio (legitimate domains have ~40% vowels)
                full_domain = extracted.domain if extracted.domain else domain
                vowel_count = sum(1 for c in full_domain.lower() if c in 'aeiou')
                features['vowel_ratio'] = vowel_count / max(len(full_domain), 1)
                
                # Consonant clusters (suspicious if too many)
                features['max_consonant_cluster'] = self._max_consonant_cluster(full_domain)
            else:
                # Fallback without tldextract
                parts = domain.split('.')
                features['tld_length'] = len(parts[-1]) if parts else 0
                features['domain_token_count'] = len(parts[-2].split('-')) if len(parts) >= 2 else 1
                features['subdomain_length'] = len('.'.join(parts[:-2])) if len(parts) > 2 else 0
                features['subdomain_has_digits'] = 1 if len(parts) > 2 and any(c.isdigit() for c in parts[0]) else 0
                
                main_domain = parts[-2] if len(parts) >= 2 else domain
                vowel_count = sum(1 for c in main_domain.lower() if c in 'aeiou')
                features['vowel_ratio'] = vowel_count / max(len(main_domain), 1)
                features['max_consonant_cluster'] = self._max_consonant_cluster(main_domain)
            
            # Entropy of domain (randomness metric)
            features['domain_entropy'] = self._calculate_entropy(domain)
            
            # Length ratio (domain length / TLD length) - phishing often have long domains
            features['domain_tld_ratio'] = len(domain) / max(features['tld_length'], 1)
        
        except Exception as e:
            logger.debug(f"Error in domain feature extraction: {e}")
            features = {
                'tld_length': 0, 'domain_token_count': 1, 'subdomain_length': 0,
                'subdomain_has_digits': 0, 'vowel_ratio': 0.4, 'max_consonant_cluster': 0,
                'domain_entropy': 0, 'domain_tld_ratio': 1
            }
        
        return features
    
    def _detect_typosquatting(self, domain: str) -> Dict[str, float]:
        """Detect typosquatting attempts against popular brands."""
        features = {
            'min_brand_distance': 100,  # Minimum Levenshtein distance to known brands
            'is_homograph': 0,  # Uses lookalike characters (e.g., paypa1.com)
            'typosquat_score': 0  # Combined typosquatting risk score
        }
        
        try:
            domain = domain.split(':')[0].lower()
            
            # Extract main domain without TLD
            if self.tldextract_available:
                extracted = self.tldextract.extract(domain)
                main_domain = extracted.domain
            else:
                parts = domain.split('.')
                main_domain = parts[-2] if len(parts) >= 2 else domain
            
            # Calculate minimum Levenshtein distance to popular brands
            if self.levenshtein_available and main_domain:
                distances = []
                for brand in self.POPULAR_BRANDS:
                    brand_domain = brand.split('.')[0]
                    distance = self.Levenshtein.distance(main_domain, brand_domain)
                    distances.append(distance)
                
                features['min_brand_distance'] = min(distances) if distances else 100
                
                # If very close to a brand (distance 1-3), likely typosquatting
                if features['min_brand_distance'] <= 3:
                    features['typosquat_score'] = 1 - (features['min_brand_distance'] / 4)
            else:
                # Basic check without Levenshtein: exact substring match
                for brand in self.POPULAR_BRANDS:
                    brand_domain = brand.split('.')[0]
                    if brand_domain in main_domain and brand_domain != main_domain:
                        features['typosquat_score'] = 0.7
                        features['min_brand_distance'] = 2
                        break
            
            # Check for homograph attacks (lookalike characters)
            homograph_patterns = {
                '0': 'o', '1': 'l', '3': 'e', '5': 's',
                'vv': 'w', 'rn': 'm'
            }
            
            for fake, real in homograph_patterns.items():
                if fake in main_domain:
                    # Check if replacing fake with real matches a brand
                    potential = main_domain.replace(fake, real)
                    if any(potential in brand for brand in self.POPULAR_BRANDS):
                        features['is_homograph'] = 1
                        features['typosquat_score'] = max(features['typosquat_score'], 0.8)
                        break
        
        except Exception as e:
            logger.debug(f"Error in typosquatting detection: {e}")
        
        return features
    
    def _analyze_url_structure(self, url: str, parsed) -> Dict[str, float]:
        """Analyze URL structure for suspicious patterns."""
        features = {}
        
        try:
            # Double slashes in path (http://example.com//path)
            features['has_double_slash'] = 1 if '//' in parsed.path else 0
            
            # Prefix/suffix pattern (http://paypal-security.com)
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) >= 2:
                main_part = domain_parts[-2]
                features['has_prefix_suffix'] = 1 if '-' in main_part else 0
            else:
                features['has_prefix_suffix'] = 0
            
            # Abnormally long path (>50 chars)
            features['long_path'] = 1 if len(parsed.path) > 50 else 0
            
            # Many parameters (>5)
            param_count = len(parse_qs(parsed.query))
            features['many_params'] = 1 if param_count > 5 else 0
            
            # Encoded characters (%)
            features['url_encoded_chars'] = url.count('%')
        
        except Exception as e:
            logger.debug(f"Error in URL structure analysis: {e}")
            features = {
                'has_double_slash': 0, 'has_prefix_suffix': 0,
                'long_path': 0, 'many_params': 0, 'url_encoded_chars': 0
            }
        
        return features
    
    def _get_whois_features(self, domain: str) -> Dict[str, float]:
        """Get WHOIS information (domain age, registration).
        
        Note: WHOIS lookups are rate-limited and cached.
        """
        features = {
            'domain_age_days': 365,  # Default: 1 year
            'is_newly_registered': 0,  # <30 days
            'whois_available': 0
        }
        
        if not self.whois_available:
            return features
        
        try:
            domain = domain.split(':')[0].lower()
            
            # Check cache first
            if domain in self._whois_cache:
                cached_time, cached_features = self._whois_cache[domain]
                if (datetime.now().timestamp() - cached_time) < self._cache_max_age:
                    return cached_features
            
            # Perform WHOIS lookup (with timeout)
            try:
                w = self.whois.whois(domain)
                
                if w and hasattr(w, 'creation_date'):
                    creation_date = w.creation_date
                    
                    # Handle list of dates (some WHOIS return multiple)
                    if isinstance(creation_date, list):
                        creation_date = creation_date[0]
                    
                    if creation_date:
                        age = (datetime.now() - creation_date).days
                        features['domain_age_days'] = max(age, 0)
                        features['is_newly_registered'] = 1 if age < 30 else 0
                        features['whois_available'] = 1
                
                # Cache result
                self._whois_cache[domain] = (datetime.now().timestamp(), features)
            
            except Exception as whois_error:
                logger.debug(f"WHOIS lookup failed for {domain}: {whois_error}")
                # Cache negative result to avoid repeated failures
                self._whois_cache[domain] = (datetime.now().timestamp(), features)
        
        except Exception as e:
            logger.debug(f"Error in WHOIS feature extraction: {e}")
        
        return features
    
    def _analyze_tld(self, domain: str) -> Dict[str, float]:
        """Analyze Top-Level Domain for suspicious patterns."""
        features = {
            'has_suspicious_tld': 0,
            'is_known_tld': 1
        }
        
        try:
            domain = domain.split(':')[0].lower()
            
            # Check for suspicious TLDs
            for sus_tld in self.SUSPICIOUS_TLDS:
                if domain.endswith(sus_tld):
                    features['has_suspicious_tld'] = 1
                    break
            
            # Check if it's a recognized TLD
            if self.tldextract_available:
                extracted = self.tldextract.extract(domain)
                features['is_known_tld'] = 1 if extracted.suffix else 0
            else:
                # Basic check: has at least one dot and TLD length 2-10
                parts = domain.split('.')
                if len(parts) >= 2:
                    tld_len = len(parts[-1])
                    features['is_known_tld'] = 1 if 2 <= tld_len <= 10 else 0
                else:
                    features['is_known_tld'] = 0
        
        except Exception as e:
            logger.debug(f"Error in TLD analysis: {e}")
        
        return features
    
    def _check_redirects_shorteners(self, domain: str) -> Dict[str, float]:
        """Check for URL shorteners and redirect services."""
        # Common URL shorteners and redirect services
        shorteners = [
            'bit.ly', 'goo.gl', 'tinyurl.com', 't.co', 'ow.ly',
            'is.gd', 'buff.ly', 'adf.ly', 'short.link', 'tiny.cc',
            'rebrand.ly', 'cutt.ly', 'bl.ink', 'shorte.st'
        ]
        
        features = {
            'is_shortener': 0,
            'redirect_risk': 0
        }
        
        try:
            domain = domain.split(':')[0].lower()
            
            for shortener in shorteners:
                if shortener in domain:
                    features['is_shortener'] = 1
                    features['redirect_risk'] = 0.8  # High risk
                    break
        
        except Exception as e:
            logger.debug(f"Error checking shorteners: {e}")
        
        return features
    
    def _max_consonant_cluster(self, text: str) -> int:
        """Calculate maximum consonant cluster length."""
        try:
            consonants = 'bcdfghjklmnpqrstvwxyz'
            max_cluster = 0
            current_cluster = 0
            
            for char in text.lower():
                if char in consonants:
                    current_cluster += 1
                    max_cluster = max(max_cluster, current_cluster)
                else:
                    current_cluster = 0
            
            return max_cluster
        except Exception:
            return 0
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text (randomness metric)."""
        try:
            import math
            from collections import Counter
            
            if not text:
                return 0.0
            
            freq = Counter(text.lower())
            total = sum(freq.values())
            entropy = -sum((count/total) * math.log2(count/total) for count in freq.values())
            
            return round(entropy, 3)
        except Exception:
            return 0.0
    
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
        """Get list of feature names in order (43 features total)."""
        return [
            # Basic lexical features (20)
            'url_length', 'domain_length', 'num_dots', 'num_hyphens',
            'num_underscores', 'num_slashes', 'num_questionmarks', 'num_equals',
            'num_at', 'num_ampersand', 'num_digits', 'num_params',
            'is_https', 'has_ip', 'num_subdomains', 'suspicious_keywords',
            'domain_has_digits', 'path_length', 'query_length', 'has_port',
            
            # Advanced domain features (8)
            'tld_length', 'domain_token_count', 'subdomain_length',
            'subdomain_has_digits', 'vowel_ratio', 'max_consonant_cluster',
            'domain_entropy', 'domain_tld_ratio',
            
            # Typosquatting features (3)
            'min_brand_distance', 'is_homograph', 'typosquat_score',
            
            # URL structure features (5)
            'has_double_slash', 'has_prefix_suffix', 'long_path',
            'many_params', 'url_encoded_chars',
            
            # WHOIS features (3)
            'domain_age_days', 'is_newly_registered', 'whois_available',
            
            # TLD features (2)
            'has_suspicious_tld', 'is_known_tld',
            
            # Redirect features (2)
            'is_shortener', 'redirect_risk'
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
        """Count suspicious keywords only in the domain portion, skip known brands."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_lower if '://' in url_lower else 'https://' + url_lower)
            netloc = parsed.netloc.split(':')[0]  # strip port

            # Extract registrable domain using tldextract if available
            if self.tldextract_available:
                ext = self.tldextract.extract(netloc)
                reg_domain = f"{ext.domain}.{ext.suffix}" if ext.suffix else netloc
            else:
                parts = netloc.split('.')
                reg_domain = '.'.join(parts[-2:]) if len(parts) >= 2 else netloc

            # If it's a known brand, never count keywords as suspicious
            if reg_domain in [b.lower() for b in self.KNOWN_BRAND_DOMAINS]:
                return 0

            # Count keywords in domain only (not path/query)
            count = 0
            for keyword in self.SUSPICIOUS_KEYWORDS:
                if keyword in netloc:
                    count += 1
            return count
        except Exception:
            # Fallback: original behaviour
            count = 0
            for keyword in self.SUSPICIOUS_KEYWORDS:
                if keyword in url_lower:
                    count += 1
            return count
    
    def _get_default_features(self) -> Dict[str, float]:
        """Get default feature values (43 features)."""
        return {name: 0.0 for name in self.get_feature_names()}
