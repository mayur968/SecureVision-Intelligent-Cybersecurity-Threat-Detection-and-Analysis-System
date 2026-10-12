"""URL phishing detection service."""

import joblib
import numpy as np
from pathlib import Path
from typing import Dict, Optional
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from features.url_features import URLFeatureExtractor
from preprocessing.url_preprocessing import clean_url, normalize_url
from config import Config
from utils.logger import logger


# Registrable domains that are unconditionally safe (whitelist guard).
# Covers any subdomain: accounts.google.com -> google.com -> SAFE.
TRUSTED_DOMAINS = frozenset({
    'google.com', 'youtube.com', 'facebook.com', 'instagram.com', 'twitter.com',
    'linkedin.com', 'microsoft.com', 'apple.com', 'amazon.com', 'netflix.com',
    'paypal.com', 'ebay.com', 'wikipedia.org', 'reddit.com', 'github.com',
    'stackoverflow.com', 'dropbox.com', 'adobe.com', 'salesforce.com', 'ibm.com',
    'oracle.com', 'yahoo.com', 'outlook.com', 'live.com', 'office.com',
    'windows.com', 'bing.com', 'skype.com', 'xbox.com', 'azure.com',
    'icloud.com', 'bankofamerica.com', 'wellsfargo.com', 'chase.com',
    'citibank.com', 'americanexpress.com', 'discover.com', 'usbank.com',
    'tdbank.com', 'schwab.com', 'fidelity.com', 'vanguard.com', 'etrade.com',
    'visa.com', 'mastercard.com', 'mozilla.org', 'w3.org', 'python.org',
    'cloudflare.com', 'shopify.com', 'stripe.com', 'zoom.us', 'slack.com',
    'twilio.com', 'walmart.com', 'target.com', 'bestbuy.com', 'costco.com',
    'homedepot.com', 'lowes.com', 'etsy.com', 'aliexpress.com',
    'wix.com', 'wordpress.com', 'blogger.com', 'medium.com', 'substack.com',
    'quora.com', 'tumblr.com', 'flickr.com', 'vimeo.com', 'soundcloud.com',
    'spotify.com', 'pandora.com', 'hulu.com', 'disneyplus.com',
    'hbomax.com', 'primevideo.com', 'peacocktv.com', 'espn.com',
    'nfl.com', 'nba.com', 'cnn.com', 'bbc.com', 'nytimes.com',
    'washingtonpost.com', 'reuters.com', 'apnews.com', 'theguardian.com',
    'forbes.com', 'bloomberg.com', 'wsj.com', 'techcrunch.com', 'wired.com',
    'arstechnica.com', 'theverge.com', 'engadget.com', 'cnet.com',
    'pcmag.com', 'zdnet.com', 'nasa.gov', 'nih.gov', 'cdc.gov',
    'irs.gov', 'usa.gov', 'whitehouse.gov', 'mit.edu', 'stanford.edu',
    'harvard.edu', 'berkeley.edu', 'twitch.tv', 'discord.com',
    'telegram.org', 'whatsapp.com', 'signal.org', 'proton.me',
    'snapchat.com', 'tiktok.com', 'pinterest.com',
    'squarespace.com', 'booking.com', 'airbnb.com', 'expedia.com',
    'tripadvisor.com', 'indeed.com', 'glassdoor.com',
})


class URLDetector:
    """URL phishing detector using trained ML model."""
    
    # Expose for tests / external access
    TRUSTED_DOMAINS = TRUSTED_DOMAINS

    def __init__(self):
        """Initialize URL detector."""
        self.feature_extractor = URLFeatureExtractor()
        self.model = None
        self.model_loaded = False
        
        # Try to load model
        self._load_model()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_base_domain(self, url: str) -> str:
        """Return the registrable domain (domain + public suffix) for *url*.

        Uses tldextract when available (most accurate), falls back to a simple
        two-label split that works for the vast majority of .com/.org/.net/etc.
        """
        try:
            fe = self.feature_extractor
            if fe.tldextract_available:
                from urllib.parse import urlparse
                parsed = urlparse(url if '://' in url else 'https://' + url)
                host = parsed.netloc.split(':')[0].lower()
                ext = fe.tldextract.extract(host)
                if ext.domain and ext.suffix:
                    return f"{ext.domain}.{ext.suffix}"
                return host
            else:
                from urllib.parse import urlparse
                parsed = urlparse(url if '://' in url else 'https://' + url)
                host = parsed.netloc.lower().split(':')[0]
                if host.startswith('www.'):
                    host = host[4:]
                parts = host.split('.')
                if len(parts) >= 2:
                    return '.'.join(parts[-2:])
                return host
        except Exception:
            return ''
    
    def _load_model(self):
        """Load trained model from disk."""
        try:
            if Config.URL_MODEL_PATH.exists():
                self.model = joblib.load(Config.URL_MODEL_PATH)
                self.model_loaded = True
                logger.info("URL detection model loaded successfully")
            else:
                logger.warning(f"URL model not found at {Config.URL_MODEL_PATH}")
                logger.warning("Please train the model first by running: python training/train_url_model.py")
        except Exception as e:
            logger.error(f"Error loading URL model: {str(e)}")
            self.model_loaded = False
    
    def predict(self, url: str) -> Dict:
        """
        Predict if a URL is phishing or safe.
        
        Args:
            url: URL string to analyze
            
        Returns:
            Dictionary containing:
                - prediction: 'SAFE' or 'PHISHING'
                - confidence: float between 0 and 1
                - features: dict of extracted features
                - model_available: bool
        """
        if not self.model_loaded:
            return {
                'prediction': 'UNKNOWN',
                'confidence': 0.0,
                'features': {},
                'model_available': False,
                'error': 'Model not loaded. Please train the model first.'
            }
        
        try:
            # Preprocess URL
            url_clean = normalize_url(url)

            # ── Whitelist guard ──────────────────────────────────────────────
            base_domain = self._extract_base_domain(url_clean)
            if base_domain and base_domain in TRUSTED_DOMAINS:
                logger.info(f"URL whitelisted: {base_domain} -> SAFE")
                return {
                    'prediction': 'SAFE',
                    'confidence': 0.99,
                    'features': {},
                    'important_features': {},
                    'model_available': self.model_loaded,
                    'url_analyzed': url_clean,
                    'whitelisted': True,
                    'whitelisted_domain': base_domain,
                }
            # ────────────────────────────────────────────────────────────────
            
            # Extract features
            features = self.feature_extractor.extract_features(url_clean)
            feature_vector = np.array(list(features.values())).reshape(1, -1)
            
            # Predict
            prediction_numeric = self.model.predict(feature_vector)[0]
            
            # Get probability if available
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(feature_vector)[0]
                confidence = float(probabilities[prediction_numeric])
            else:
                # For models without predict_proba, use decision function or default
                if hasattr(self.model, 'decision_function'):
                    decision = self.model.decision_function(feature_vector)[0]
                    # Convert decision function to probability-like score
                    confidence = float(1 / (1 + np.exp(-decision)))
                    if prediction_numeric == 0:
                        confidence = 1 - confidence
                else:
                    confidence = 0.8  # Default confidence
            
            # Convert numeric prediction to label
            prediction_label = 'PHISHING' if prediction_numeric == 1 else 'SAFE'
            
            # Get important features (top suspicious indicators)
            important_features = self._get_important_features(features)
            
            result = {
                'prediction': prediction_label,
                'confidence': confidence,
                'features': features,
                'important_features': important_features,
                'model_available': True,
                'url_analyzed': url_clean
            }
            
            logger.info(f"URL analyzed: {url_clean[:50]}... -> {prediction_label} ({confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting URL: {str(e)}")
            return {
                'prediction': 'ERROR',
                'confidence': 0.0,
                'features': {},
                'model_available': True,
                'error': str(e)
            }
    
    def _get_important_features(self, features: Dict) -> Dict:
        """
        Identify important/suspicious features.
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            Dictionary of important features and their values
        """
        important = {}
        
        # Long URL
        if features.get('url_length', 0) > 100:
            important['long_url'] = features['url_length']
        
        # No HTTPS
        if features.get('is_https', 0) == 0:
            important['no_https'] = True
        
        # IP address in URL
        if features.get('has_ip', 0) == 1:
            important['has_ip_address'] = True
        
        # Multiple subdomains
        if features.get('num_subdomains', 0) >= 2:
            important['multiple_subdomains'] = features['num_subdomains']
        
        # Suspicious keywords
        if features.get('suspicious_keywords', 0) > 0:
            important['suspicious_keywords_count'] = features['suspicious_keywords']
        
        # @ symbol (credential phishing)
        if features.get('num_at', 0) > 0:
            important['at_symbol_present'] = True
        
        # Many hyphens
        if features.get('num_hyphens', 0) > 3:
            important['many_hyphens'] = features['num_hyphens']
        
        # Digits in domain
        if features.get('domain_has_digits', 0) == 1:
            important['domain_has_digits'] = True
        
        return important
