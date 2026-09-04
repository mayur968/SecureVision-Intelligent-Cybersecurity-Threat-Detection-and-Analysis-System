"""Email/SMS phishing detection service."""

import joblib
import numpy as np
from pathlib import Path
from typing import Dict, List
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from preprocessing.text_preprocessing import TextPreprocessor
from features.text_features import TextFeatureExtractor
from config import Config
from utils.logger import logger


class MessageDetector:
    """Email/SMS phishing detector using trained ML model."""
    
    def __init__(self):
        """Initialize message detector."""
        self.preprocessor = TextPreprocessor()
        self.feature_extractor = TextFeatureExtractor()
        self.model = None
        self.vectorizer = None
        self.model_loaded = False
        
        # Try to load model
        self._load_model()
    
    def _load_model(self):
        """Load trained model and vectorizer from disk."""
        try:
            if Config.MESSAGE_MODEL_PATH.exists() and Config.MESSAGE_VECTORIZER_PATH.exists():
                self.model = joblib.load(Config.MESSAGE_MODEL_PATH)
                self.vectorizer = joblib.load(Config.MESSAGE_VECTORIZER_PATH)
                self.model_loaded = True
                logger.info("Message detection model loaded successfully")
            else:
                logger.warning(f"Message model not found")
                logger.warning("Please train the model first by running: python training/train_message_model.py")
        except Exception as e:
            logger.error(f"Error loading message model: {str(e)}")
            self.model_loaded = False
    
    def predict(self, message: str) -> Dict:
        """
        Predict if a message is phishing or safe.
        
        Args:
            message: Message text to analyze
            
        Returns:
            Dictionary containing:
                - prediction: 'SAFE' or 'PHISHING'
                - confidence: float between 0 and 1
                - indicators: list of detected indicators
                - model_available: bool
        """
        if not self.model_loaded:
            return {
                'prediction': 'UNKNOWN',
                'confidence': 0.0,
                'indicators': [],
                'model_available': False,
                'error': 'Model not loaded. Please train the model first.'
            }
        
        try:
            # Preprocess message
            message_clean = self.preprocessor.preprocess(message)
            
            # Extract manual features for analysis
            manual_features = self.feature_extractor.extract_features(message)
            
            # Transform with TF-IDF vectorizer
            message_tfidf = self.vectorizer.transform([message_clean])
            
            # Predict
            prediction_numeric = self.model.predict(message_tfidf)[0]
            
            # Get probability
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(message_tfidf)[0]
                confidence = float(probabilities[prediction_numeric])
            else:
                confidence = 0.8  # Default confidence
            
            # Convert numeric prediction to label
            prediction_label = 'PHISHING' if prediction_numeric == 1 else 'SAFE'
            
            # Get detected indicators
            indicators = self._get_indicators(message, manual_features)
            
            result = {
                'prediction': prediction_label,
                'confidence': confidence,
                'indicators': indicators,
                'features': manual_features,
                'model_available': True,
                'message_preview': message[:100] + '...' if len(message) > 100 else message
            }
            
            logger.info(f"Message analyzed: {len(message)} chars -> {prediction_label} ({confidence:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error predicting message: {str(e)}")
            return {
                'prediction': 'ERROR',
                'confidence': 0.0,
                'indicators': [],
                'model_available': True,
                'error': str(e)
            }
    
    def _get_indicators(self, original_message: str, features: Dict) -> List[str]:
        """
        Get list of detected phishing indicators.
        
        Args:
            original_message: Original message text
            features: Extracted features
            
        Returns:
            List of indicator strings
        """
        indicators = []
        message_lower = original_message.lower()
        
        # URL presence
        if features.get('has_url', 0) == 1:
            indicators.append('Contains URL/link')
        
        # Urgency
        if features.get('urgent_words', 0) > 0 or features.get('has_urgent', 0) == 1:
            indicators.append('Urgent language detected')
        
        # Financial keywords
        if features.get('financial_words', 0) > 0:
            indicators.append('Financial/monetary keywords')
        
        # Security/verification requests
        if features.get('security_words', 0) > 0 or features.get('has_verify', 0) == 1:
            indicators.append('Security/verification request')
        
        # Threats
        if features.get('threat_words', 0) > 0 or features.get('has_suspended', 0) == 1:
            indicators.append('Threatening language')
        
        # Action requests
        if features.get('request_words', 0) > 0 or features.get('has_click_here', 0) == 1:
            indicators.append('Requests immediate action')
        
        # Excessive punctuation
        if features.get('exclamation_count', 0) > 2:
            indicators.append('Excessive exclamation marks')
        
        # Phone/contact info
        if features.get('has_phone', 0) == 1:
            indicators.append('Contains phone number')
        
        # Suspicious patterns
        if 'click here' in message_lower or 'click link' in message_lower:
            indicators.append('"Click here" pattern')
        
        if 'verify' in message_lower and 'account' in message_lower:
            indicators.append('Account verification request')
        
        if 'suspend' in message_lower or 'locked' in message_lower:
            indicators.append('Account suspension threat')
        
        if 'winner' in message_lower or 'prize' in message_lower or 'won' in message_lower:
            indicators.append('Prize/lottery claim')
        
        return indicators if indicators else ['No specific indicators detected']
