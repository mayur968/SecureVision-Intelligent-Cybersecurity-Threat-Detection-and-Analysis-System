"""Database models for SecureVision."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ScanHistory(db.Model):
    """Model for storing scan history."""
    
    __tablename__ = 'scan_history'
    
    id = db.Column(db.Integer, primary_key=True)
    scan_type = db.Column(db.String(20), nullable=False)  # APK, URL, MESSAGE
    input_value = db.Column(db.Text, nullable=False)  # URL, message text, or APK filename
    prediction = db.Column(db.String(20), nullable=False)  # SAFE, PHISHING, MALICIOUS
    confidence = db.Column(db.Float, nullable=False)  # 0.0 to 1.0
    risk_level = db.Column(db.String(20), nullable=False)  # LOW, MEDIUM, HIGH
    explanation = db.Column(db.Text, nullable=True)  # Why it was flagged
    recommendation = db.Column(db.Text, nullable=True)  # Security recommendations
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ScanHistory {self.id}: {self.scan_type} - {self.prediction}>'
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'scan_type': self.scan_type,
            'input_value': self.input_value[:100] + '...' if len(self.input_value) > 100 else self.input_value,
            'prediction': self.prediction,
            'confidence': round(self.confidence, 4),
            'risk_level': self.risk_level,
            'explanation': self.explanation,
            'recommendation': self.recommendation,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def get_statistics():
        """Get statistics for dashboard."""
        total_scans = ScanHistory.query.count()
        apk_scans = ScanHistory.query.filter_by(scan_type='APK').count()
        url_scans = ScanHistory.query.filter(
            ScanHistory.scan_type.in_(['URL', 'URL_LIVE'])
        ).count()
        message_scans = ScanHistory.query.filter_by(scan_type='MESSAGE').count()
        
        threats_detected = ScanHistory.query.filter(
            ScanHistory.prediction.in_(['PHISHING', 'MALICIOUS'])
        ).count()
        
        safe_results = ScanHistory.query.filter_by(prediction='SAFE').count()
        
        # Threat breakdown by type
        apk_threats = ScanHistory.query.filter_by(
            scan_type='APK', prediction='MALICIOUS'
        ).count()
        
        url_threats = ScanHistory.query.filter(
            ScanHistory.scan_type.in_(['URL', 'URL_LIVE']),
            ScanHistory.prediction == 'PHISHING'
        ).count()
        
        message_threats = ScanHistory.query.filter_by(
            scan_type='MESSAGE', prediction='PHISHING'
        ).count()
        
        return {
            'total_scans': total_scans,
            'apk_scans': apk_scans,
            'url_scans': url_scans,
            'message_scans': message_scans,
            'threats_detected': threats_detected,
            'safe_results': safe_results,
            'threat_breakdown': {
                'apk': apk_threats,
                'url': url_threats,
                'message': message_threats
            }
        }
    
    @staticmethod
    def get_recent_scans(limit=10):
        """Get recent scans."""
        return ScanHistory.query.order_by(
            ScanHistory.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def save_scan(scan_type, input_value, prediction, confidence, 
                  risk_level, explanation, recommendation):
        """
        Save a new scan to database.
        
        Args:
            scan_type: Type of scan (APK, URL, MESSAGE)
            input_value: Input that was scanned
            prediction: Prediction result (SAFE, PHISHING, MALICIOUS)
            confidence: Confidence score (0.0 to 1.0)
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            explanation: Explanation text
            recommendation: Recommendation text
            
        Returns:
            Saved ScanHistory object
        """
        scan = ScanHistory(
            scan_type=scan_type,
            input_value=input_value,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            explanation=explanation,
            recommendation=recommendation
        )
        
        db.session.add(scan)
        db.session.commit()
        
        return scan
