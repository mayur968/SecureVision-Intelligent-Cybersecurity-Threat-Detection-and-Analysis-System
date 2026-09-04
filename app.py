"""
SecureVision - Intelligent Cybersecurity Threat Detection System
Main Flask Application
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from config import Config
from utils.logger import logger
from database.models import db, ScanHistory
import os

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created successfully")


# ============================================
# ROUTES - Dashboard
# ============================================

@app.route('/')
def index():
    """Render dashboard homepage."""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return "Error loading dashboard", 500


@app.route('/dashboard')
def dashboard():
    """Dashboard with statistics."""
    return redirect(url_for('index'))


# ============================================
# ROUTES - Scanners (HTML Pages)
# ============================================

@app.route('/scan/url')
def url_scanner_page():
    """Render URL scanner page."""
    try:
        return render_template('url_scanner.html')
    except Exception as e:
        logger.error(f"Error rendering URL scanner: {str(e)}")
        return "Error loading URL scanner", 500


@app.route('/scan/message')
def message_scanner_page():
    """Render message scanner page."""
    try:
        return render_template('message_scanner.html')
    except Exception as e:
        logger.error(f"Error rendering message scanner: {str(e)}")
        return "Error loading message scanner", 500


@app.route('/scan/apk')
def apk_scanner_page():
    """Render APK scanner page."""
    try:
        return render_template('apk_scanner.html')
    except Exception as e:
        logger.error(f"Error rendering APK scanner: {str(e)}")
        return "Error loading APK scanner", 500


@app.route('/history')
def history_page():
    """Render scan history page."""
    try:
        return render_template('history.html')
    except Exception as e:
        logger.error(f"Error rendering history: {str(e)}")
        return "Error loading history", 500


# ============================================
# API ROUTES - Detection Services
# ============================================

# Initialize detectors and services
from detection.url_detector import URLDetector
from detection.message_detector import MessageDetector
from detection.apk_detector import APKDetector
from explanation.risk_score import RiskScorer
from explanation.threat_explainer import ThreatExplainer
from explanation.recommendations import RecommendationEngine
from utils.validators import validate_url, validate_message
from utils.file_security import generate_secure_filename, safe_file_cleanup
from werkzeug.utils import secure_filename

# Initialize services
url_detector = URLDetector()
message_detector = MessageDetector()
apk_detector = APKDetector()
risk_scorer = RiskScorer()
threat_explainer = ThreatExplainer()
recommendation_engine = RecommendationEngine()


@app.route('/api/scan/url', methods=['POST'])
def api_scan_url():
    """API endpoint for URL scanning."""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                'success': False,
                'error': 'URL parameter is required'
            }), 400
        
        url = data['url']
        
        # Validate URL
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Detect
        detection_result = url_detector.predict(url)
        
        if 'error' in detection_result:
            return jsonify({
                'success': False,
                'error': detection_result['error']
            }), 500
        
        # Calculate risk
        risk_result = risk_scorer.calculate_risk_score(
            detection_result['prediction'],
            detection_result['confidence'],
            'URL',
            detection_result
        )
        
        # Generate explanation
        explanation = threat_explainer.explain(
            detection_result['prediction'],
            detection_result['confidence'],
            'URL',
            detection_result
        )
        
        # Get recommendations
        recommendations = recommendation_engine.get_recommendations(
            detection_result['prediction'],
            'URL',
            risk_result['risk_level'],
            detection_result
        )
        
        # Save to database
        ScanHistory.save_scan(
            scan_type='URL',
            input_value=url,
            prediction=detection_result['prediction'],
            confidence=detection_result['confidence'],
            risk_level=risk_result['risk_level'],
            explanation=explanation,
            recommendation='\n'.join(recommendations)
        )
        
        return jsonify({
            'success': True,
            'prediction': detection_result['prediction'],
            'confidence': round(detection_result['confidence'], 4),
            'risk_score': risk_result['risk_score'],
            'risk_level': risk_result['risk_level'],
            'explanation': explanation,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logger.error(f"Error in URL scan API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/scan/message', methods=['POST'])
def api_scan_message():
    """API endpoint for message scanning."""
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message parameter is required'
            }), 400
        
        message = data['message']
        
        # Validate message
        is_valid, error_msg = validate_message(message)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Detect
        detection_result = message_detector.predict(message)
        
        if 'error' in detection_result:
            return jsonify({
                'success': False,
                'error': detection_result['error']
            }), 500
        
        # Calculate risk
        risk_result = risk_scorer.calculate_risk_score(
            detection_result['prediction'],
            detection_result['confidence'],
            'MESSAGE',
            detection_result
        )
        
        # Generate explanation
        explanation = threat_explainer.explain(
            detection_result['prediction'],
            detection_result['confidence'],
            'MESSAGE',
            detection_result
        )
        
        # Get recommendations
        recommendations = recommendation_engine.get_recommendations(
            detection_result['prediction'],
            'MESSAGE',
            risk_result['risk_level'],
            detection_result
        )
        
        # Save to database (truncate message for storage)
        message_preview = message[:500] if len(message) > 500 else message
        ScanHistory.save_scan(
            scan_type='MESSAGE',
            input_value=message_preview,
            prediction=detection_result['prediction'],
            confidence=detection_result['confidence'],
            risk_level=risk_result['risk_level'],
            explanation=explanation,
            recommendation='\n'.join(recommendations)
        )
        
        return jsonify({
            'success': True,
            'prediction': detection_result['prediction'],
            'confidence': round(detection_result['confidence'], 4),
            'risk_score': risk_result['risk_score'],
            'risk_level': risk_result['risk_level'],
            'explanation': explanation,
            'recommendations': recommendations,
            'indicators': detection_result.get('indicators', [])
        })
        
    except Exception as e:
        logger.error(f"Error in message scan API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/scan/apk', methods=['POST'])
def api_scan_apk():
    """API endpoint for APK scanning."""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Check file extension
        if not file.filename.endswith('.apk'):
            return jsonify({
                'success': False,
                'error': 'Only APK files are allowed'
            }), 400
        
        # Generate secure filename
        secure_name = generate_secure_filename(file.filename)
        file_path = Config.UPLOAD_FOLDER / secure_name
        
        # Save file temporarily
        file.save(str(file_path))
        
        try:
            # Analyze APK
            detection_result = apk_detector.analyze(file_path)
            
            if 'error' in detection_result:
                return jsonify({
                    'success': False,
                    'error': detection_result['error']
                }), 400
            
            # Calculate risk
            risk_result = risk_scorer.calculate_risk_score(
                detection_result['prediction'],
                detection_result['confidence'],
                'APK',
                detection_result.get('features', {})
            )
            
            # Generate explanation
            explanation = threat_explainer.explain(
                detection_result['prediction'],
                detection_result['confidence'],
                'APK',
                detection_result.get('features', {})
            )
            
            # Get recommendations
            recommendations = recommendation_engine.get_recommendations(
                detection_result['prediction'],
                'APK',
                risk_result['risk_level'],
                detection_result.get('features', {})
            )
            
            # Save to database
            file_info = detection_result.get('file_info', {})
            apk_filename = file_info.get('filename', file.filename)
            
            ScanHistory.save_scan(
                scan_type='APK',
                input_value=apk_filename,
                prediction=detection_result['prediction'],
                confidence=detection_result['confidence'],
                risk_level=risk_result['risk_level'],
                explanation=explanation,
                recommendation='\n'.join(recommendations)
            )
            
            return jsonify({
                'success': True,
                'filename': apk_filename,
                'file_size': file_info.get('size_mb', 0),
                'prediction': detection_result['prediction'],
                'confidence': round(detection_result['confidence'], 4),
                'risk_score': risk_result['risk_score'],
                'risk_level': risk_result['risk_level'],
                'explanation': explanation,
                'recommendations': recommendations,
                'indicators': detection_result.get('indicators', []),
                'analysis_note': detection_result.get('analysis_note', '')
            })
            
        finally:
            # Clean up uploaded file
            safe_file_cleanup(file_path)
        
    except Exception as e:
        logger.error(f"Error in APK scan API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """API endpoint to get scan history."""
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Maximum 100 records
        
        scans = ScanHistory.get_recent_scans(limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(scans),
            'scans': [scan.to_dict() for scan in scans]
        })
        
    except Exception as e:
        logger.error(f"Error in history API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@app.route('/api/statistics', methods=['GET'])
def api_get_statistics():
    """API endpoint to get statistics."""
    try:
        stats = ScanHistory.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error in statistics API: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Endpoint not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {str(error)}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return "Internal server error", 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large errors."""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'File too large'}), 413
    return "File too large", 413


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    logger.info("Starting SecureVision application...")
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
