"""APK malware detection service (static analysis only)."""

import joblib
import numpy as np
from pathlib import Path
from typing import Dict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from features.apk_features import APKFeatureExtractor
from preprocessing.apk_preprocessing import APKPreprocessor
from config import Config
from utils.logger import logger


class APKDetector:
    """APK malware detector using static analysis."""
    
    def __init__(self):
        """Initialize APK detector."""
        self.feature_extractor = APKFeatureExtractor()
        self.preprocessor = APKPreprocessor()
        self.model = None
        self.model_loaded = False
        
        # Try to load model
        self._load_model()
    
    def _load_model(self):
        """Load trained model from disk."""
        try:
            if Config.APK_MODEL_PATH.exists():
                self.model = joblib.load(Config.APK_MODEL_PATH)
                self.model_loaded = True
                logger.info("APK detection model loaded successfully")
            else:
                logger.warning(f"APK model not found at {Config.APK_MODEL_PATH}")
                logger.warning("APK detection will use rule-based heuristics only")
        except Exception as e:
            logger.error(f"Error loading APK model: {str(e)}")
            self.model_loaded = False
    
    def analyze(self, apk_path: Path) -> Dict:
        """
        Analyze APK file for malware (static analysis only).
        
        IMPORTANT: This method does NOT execute the APK file.
        Analysis is performed through static inspection only.
        
        Args:
            apk_path: Path to APK file
            
        Returns:
            Dictionary containing:
                - prediction: 'SAFE' or 'MALICIOUS'
                - confidence: float between 0 and 1
                - features: dict of extracted features
                - indicators: list of suspicious indicators
                - file_info: basic file information
        """
        # Validate APK
        is_valid, error = self.preprocessor.validate_apk(apk_path)
        if not is_valid:
            return {
                'prediction': 'ERROR',
                'confidence': 0.0,
                'error': error,
                'features': {},
                'indicators': []
            }
        
        try:
            # Get file info
            file_info = self.preprocessor.get_file_info(apk_path)
            
            # Extract features (static analysis only)
            features = self.feature_extractor.extract_features(apk_path)
            
            # If model is loaded, use ML prediction
            if self.model_loaded and features.get('analysis_method') == 'androguard':
                prediction_result = self._ml_prediction(features)
            else:
                # Use rule-based heuristics
                prediction_result = self._heuristic_prediction(features)
            
            # Get suspicious indicators
            indicators = self._get_indicators(features)
            
            result = {
                'prediction': prediction_result['prediction'],
                'confidence': prediction_result['confidence'],
                'features': features,
                'indicators': indicators,
                'file_info': file_info,
                'analysis_note': 'Static analysis only. APK was not executed.',
                'model_available': self.model_loaded
            }
            
            logger.info(f"APK analyzed: {apk_path.name} -> {result['prediction']} ({result['confidence']:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing APK: {str(e)}")
            return {
                'prediction': 'ERROR',
                'confidence': 0.0,
                'error': str(e),
                'features': {},
                'indicators': []
            }
    
    def _ml_prediction(self, features: Dict) -> Dict:
        """Make prediction using ML model."""
        try:
            feature_vector = np.array(
                self.feature_extractor.get_feature_vector(features)
            ).reshape(1, -1)
            
            prediction_numeric = self.model.predict(feature_vector)[0]
            
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(feature_vector)[0]
                confidence = float(probabilities[prediction_numeric])
            else:
                confidence = 0.75
            
            prediction_label = 'MALICIOUS' if prediction_numeric == 1 else 'SAFE'
            
            return {
                'prediction': prediction_label,
                'confidence': confidence
            }
        except Exception as e:
            logger.error(f"ML prediction failed: {str(e)}")
            return self._heuristic_prediction(features)
    
    def _heuristic_prediction(self, features: Dict) -> Dict:
        """
        Make prediction using rule-based heuristics.
        This is used when ML model is not available or as fallback.
        """
        risk_score = 0
        max_score = 100
        
        # Dangerous permissions (high weight)
        dangerous_count = features.get('dangerous_permission_count', 0)
        if dangerous_count > 10:
            risk_score += 40
        elif dangerous_count > 5:
            risk_score += 25
        elif dangerous_count > 0:
            risk_score += 10
        
        # Total permissions (medium weight)
        permission_count = features.get('permission_count', 0)
        if permission_count > 30:
            risk_score += 20
        elif permission_count > 20:
            risk_score += 10
        
        # Component count (low weight)
        component_count = features.get('component_count', 0)
        if component_count > 50:
            risk_score += 15
        elif component_count > 30:
            risk_score += 10
        
        # Multiple DEX files (medium weight - can indicate obfuscation)
        dex_count = features.get('dex_count', 1)
        if dex_count > 3:
            risk_score += 15
        elif dex_count > 1:
            risk_score += 5
        
        # Normalize to 0-1
        confidence = min(risk_score / max_score, 1.0)
        
        # Threshold for malicious classification
        if risk_score > 50:
            prediction = 'MALICIOUS'
        else:
            prediction = 'SAFE'
            confidence = 1.0 - confidence  # Invert for safe prediction
        
        return {
            'prediction': prediction,
            'confidence': max(confidence, 0.6)  # Minimum confidence for heuristics
        }
    
    def _get_indicators(self, features: Dict) -> list:
        """Get list of suspicious indicators."""
        indicators = []
        
        # Dangerous permissions
        dangerous_count = features.get('dangerous_permission_count', 0)
        if dangerous_count > 0:
            indicators.append(f'{dangerous_count} dangerous permissions detected')
        
        # Excessive permissions
        permission_count = features.get('permission_count', 0)
        if permission_count > 20:
            indicators.append(f'High permission count ({permission_count})')
        
        # Many components
        component_count = features.get('component_count', 0)
        if component_count > 30:
            indicators.append(f'Many components ({component_count})')
        
        # Multiple DEX files
        dex_count = features.get('dex_count', 0)
        if dex_count > 1:
            indicators.append(f'Multiple DEX files ({dex_count}) - possible obfuscation')
        
        # Native libraries
        if features.get('has_native_libs'):
            indicators.append('Contains native libraries')
        
        # Check specific dangerous permissions
        permissions = features.get('permissions', [])
        critical_perms = ['SEND_SMS', 'READ_SMS', 'CALL_PHONE', 'INSTALL_PACKAGES', 'WRITE_SETTINGS']
        for perm in permissions:
            for critical in critical_perms:
                if critical in perm:
                    indicators.append(f'Critical permission: {critical}')
        
        if not indicators:
            indicators.append('No significant threats detected in static analysis')
        
        return indicators
