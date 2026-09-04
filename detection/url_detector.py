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


class URLDetector:
    """URL phishing detector using trained ML model."""
    
    def __init__(self):
        """Initialize URL detector."""
        self.feature_extractor = URLFeatureExtractor()
        self.model = None
        self.model_loaded = False
        
        # Try to load model
        self._load_model()
    
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
