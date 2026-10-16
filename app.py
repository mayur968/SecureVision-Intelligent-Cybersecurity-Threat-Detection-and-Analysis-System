"""
SecureVision - Intelligent Cybersecurity Threat Detection System
Main Flask Application
"""

import sys as _sys
import os as _os

def _check_venv():
    """Warn loudly if not running from the project venv."""
    venv_python = _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), 'venv', 'Scripts', 'python.exe'
    )
    running = _sys.executable.replace('\\', '/')
    expected = venv_python.replace('\\', '/')
    if running.lower() != expected.lower() and not _os.environ.get('SKIP_VENV_CHECK'):
        print(
            "\n" + "=" * 70 + "\n"
            "WARNING: You are NOT running from the project venv.\n"
            f"  Running:  {_sys.executable}\n"
            f"  Expected: {venv_python}\n"
            "  Some packages (playwright, tldextract, androguard) may be missing.\n"
            "  Run with:  .\\venv\\Scripts\\python.exe app.py\n"
            "  Or use:    .\\run.bat  (Windows CMD)  /  .\\run.ps1  (PowerShell)\n"
            + "=" * 70 + "\n",
            file=_sys.stderr
        )

_check_venv()
del _check_venv, _sys, _os

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from config import Config
from utils.logger import logger
from database.models import db, ScanHistory, seed_model_registry
import os
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# CORS — allow the Vite dev server to make credentialed requests
CORS(app, origins=['http://localhost:5173'], supports_credentials=True)

# Initialize database
db.init_app(app)

# Register blueprints
from database.auth import auth_bp  # noqa: E402
app.register_blueprint(auth_bp)

# In test environments (TESTING=true) create tables directly.
# In all other cases, run 'flask --app migrate_app db upgrade' separately.
if Config.TESTING or app.config.get('TESTING'):
    with app.app_context():
        db.create_all()
        logger.info("Test mode: database tables created via create_all()")
else:
    with app.app_context():
        seed_model_registry()
        logger.info("Database tables ready (migrations managed by Alembic)")


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
from database.ioc_extractor import extract_iocs

# Initialize services
url_detector = URLDetector()
message_detector = MessageDetector()
apk_detector = APKDetector()
risk_scorer = RiskScorer()
threat_explainer = ThreatExplainer()
recommendation_engine = RecommendationEngine()

# ── Live scan job store ──────────────────────────────────────────────────────
_job_store: dict = {}            # job_id -> {status, result, error, created_at, ip}
_job_store_lock = threading.Lock()
_live_executor = ThreadPoolExecutor(max_workers=int(os.environ.get('LIVE_SCAN_MAX_WORKERS', '2')))
_LIVE_SCAN_ENABLED = os.environ.get('LIVE_SCAN_ENABLED', 'true').lower() == 'true'
_JOB_TTL_SECONDS = 900           # 15 minutes
_IP_MAX_CONCURRENT = 2           # max concurrent live scans per IP


def _cleanup_old_jobs():
    """Remove expired jobs from the job store."""
    now = time.time()
    with _job_store_lock:
        expired = [k for k, v in _job_store.items() if now - v['created_at'] > _JOB_TTL_SECONDS]
        for k in expired:
            del _job_store[k]


def _count_ip_running(ip: str) -> int:
    """Count running/queued jobs for an IP."""
    with _job_store_lock:
        return sum(1 for v in _job_store.values() if v['ip'] == ip and v['status'] in ('queued', 'running'))


def _run_live_scan_job(job_id: str, url: str, user_id=None, anon_session_id=None):
    """Background worker: runs live scan, combines with ML score, saves to DB."""
    try:
        with _job_store_lock:
            _job_store[job_id]['status'] = 'running'

        # Import here to avoid circular imports and graceful failure if playwright missing
        from detection.live_scanner import scan_live

        timeout_ms = int(os.environ.get('LIVE_SCAN_TIMEOUT_MS', '15000'))
        live_result = scan_live(url, timeout_ms=timeout_ms)

        # ML prediction
        ml_result = url_detector.predict(url)
        ml_prediction = ml_result.get('prediction', 'UNKNOWN')
        ml_confidence = ml_result.get('confidence', 0.5)
        ml_phishing_prob = ml_confidence if ml_prediction == 'PHISHING' else (1.0 - ml_confidence)

        live_verdict = live_result.get('verdict', 'COULD_NOT_VERIFY')
        live_score = live_result.get('live_score', 0)
        ml_fallback = False

        if live_verdict == 'COULD_NOT_VERIFY':
            combined_score = ml_phishing_prob * 100
            ml_fallback = True
        else:
            combined_score = 0.6 * live_score + 0.4 * (ml_phishing_prob * 100)

        combined_score = min(100, max(0, combined_score))

        # Map combined score to prediction for risk scorer
        if combined_score >= 60:
            combined_prediction = 'PHISHING'
        elif combined_score >= 30:
            combined_prediction = 'SUSPICIOUS'
        else:
            combined_prediction = 'SAFE'

        combined_confidence = combined_score / 100.0

        # Build feature dict for explanation pipeline (include live evidence)
        live_features = {
            'important_features': ml_result.get('important_features', {}),
            'live_evidence': live_result.get('evidence', []),
            'live_verdict': live_verdict,
            'ml_fallback': ml_fallback,
        }

        # Risk scoring
        risk_result = risk_scorer.calculate_risk_score(
            combined_prediction,
            combined_confidence,
            'URL',
            live_features
        )

        # Explanation: prepend live evidence bullets
        base_explanation = threat_explainer.explain(
            combined_prediction,
            combined_confidence,
            'URL',
            live_features
        )
        if live_result.get('evidence'):
            evidence_bullets = '\n'.join(f'• {e}' for e in live_result['evidence'])
            full_explanation = f'Live browser evidence:\n{evidence_bullets}\n\n{base_explanation}'
        else:
            full_explanation = base_explanation

        recommendations = recommendation_engine.get_recommendations(
            combined_prediction,
            'URL',
            risk_result['risk_level'],
            live_features
        )

        # Save to database (no screenshot)
        live_ioc_list = extract_iocs('URL_LIVE', url, live_result)
        with app.app_context():
            ScanHistory.save_scan(
                scan_type='URL_LIVE',
                input_value=url,
                prediction=combined_prediction,
                confidence=combined_confidence,
                risk_level=risk_result['risk_level'],
                explanation=full_explanation[:2000],
                recommendation='\n'.join(recommendations),
                risk_score=risk_result['risk_score'],
                model_version='url_lr_v1.0',
                ioc_list=live_ioc_list,
                user_id=user_id,
                anon_session_id=anon_session_id,
            )

        result_payload = {
            'verdict': live_verdict,
            'live_score': round(live_score, 1),
            'combined_score': round(combined_score, 1),
            'final_url': live_result.get('final_url', url),
            'redirect_chain': live_result.get('redirect_chain', []),
            'title': live_result.get('title', ''),
            'evidence': live_result.get('evidence', []),
            'screenshot_b64': live_result.get('screenshot_b64'),
            'load_time_ms': live_result.get('load_time_ms', 0),
            'ml_fallback': ml_fallback,
            'prediction': combined_prediction,
            'confidence': round(combined_confidence, 4),
            'risk_score': risk_result['risk_score'],
            'risk_level': risk_result['risk_level'],
            'explanation': full_explanation,
            'recommendations': recommendations,
        }

        with _job_store_lock:
            _job_store[job_id]['status'] = 'done'
            _job_store[job_id]['result'] = result_payload

    except Exception as e:
        logger.error(f'Live scan job {job_id} failed: {str(e)}')
        with _job_store_lock:
            if job_id in _job_store:
                _job_store[job_id]['status'] = 'failed'
                _job_store[job_id]['error'] = str(e)[:500]


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
        
        # Assign anon session id for guests
        user_id = session.get('user_id')
        if not user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = secrets.token_hex(32)
        anon_id = session.get('anon_session_id') if not user_id else None

        # Save to database
        ioc_list = extract_iocs('URL', url, detection_result)
        ScanHistory.save_scan(
            scan_type='URL',
            input_value=url,
            prediction=detection_result['prediction'],
            confidence=detection_result['confidence'],
            risk_level=risk_result['risk_level'],
            explanation=explanation,
            recommendation='\n'.join(recommendations),
            risk_score=risk_result['risk_score'],
            model_version='url_lr_v1.0',
            ioc_list=ioc_list,
            user_id=user_id,
            anon_session_id=anon_id,
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
        ioc_list = extract_iocs('MESSAGE', message, detection_result)

        # Assign anon session id for guests
        user_id = session.get('user_id')
        if not user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = secrets.token_hex(32)
        anon_id = session.get('anon_session_id') if not user_id else None

        ScanHistory.save_scan(
            scan_type='MESSAGE',
            input_value=message_preview,
            prediction=detection_result['prediction'],
            confidence=detection_result['confidence'],
            risk_level=risk_result['risk_level'],
            explanation=explanation,
            recommendation='\n'.join(recommendations),
            risk_score=risk_result['risk_score'],
            model_version='message_lr_v1.0',
            ioc_list=ioc_list,
            user_id=user_id,
            anon_session_id=anon_id,
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
            ioc_list = extract_iocs('APK', apk_filename, detection_result,
                                     apk_file_path=file_path)

            # Assign anon session id for guests
            user_id = session.get('user_id')
            if not user_id and 'anon_session_id' not in session:
                session['anon_session_id'] = secrets.token_hex(32)
            anon_id = session.get('anon_session_id') if not user_id else None

            ScanHistory.save_scan(
                scan_type='APK',
                input_value=apk_filename,
                prediction=detection_result['prediction'],
                confidence=detection_result['confidence'],
                risk_level=risk_result['risk_level'],
                explanation=explanation,
                recommendation='\n'.join(recommendations),
                risk_score=risk_result['risk_score'],
                model_version='apk_lr_v1.0',
                ioc_list=ioc_list,
                user_id=user_id,
                anon_session_id=anon_id,
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


@app.route('/api/scan/url/live', methods=['POST'])
def api_scan_url_live():
    """Start a live URL scan job. Returns job_id with HTTP 202."""
    try:
        if not _LIVE_SCAN_ENABLED:
            return jsonify({'success': False, 'error': 'Live scan is disabled'}), 503

        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'success': False, 'error': 'URL parameter is required'}), 400

        url = data['url']

        # Validate URL with existing validator
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400

        # Per-IP concurrency check
        client_ip = request.remote_addr or '0.0.0.0'
        if _count_ip_running(client_ip) >= _IP_MAX_CONCURRENT:
            return jsonify({'success': False, 'error': 'Too many concurrent scans. Please wait.'}), 429

        # Cleanup expired jobs
        _cleanup_old_jobs()

        job_id = str(uuid.uuid4())
        with _job_store_lock:
            _job_store[job_id] = {
                'status': 'queued',
                'result': None,
                'error': None,
                'created_at': time.time(),
                'ip': client_ip,
            }

        # Capture ownership from session before passing to background thread
        live_user_id = session.get('user_id')
        if not live_user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = secrets.token_hex(32)
        live_anon_id = session.get('anon_session_id') if not live_user_id else None

        _live_executor.submit(_run_live_scan_job, job_id, url, live_user_id, live_anon_id)

        logger.info(f'Live scan job queued: {job_id} for {url[:80]}')
        return jsonify({'job_id': job_id, 'status': 'queued'}), 202

    except Exception as e:
        logger.error(f'Error starting live scan job: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@app.route('/api/scan/url/live/<job_id>', methods=['GET'])
def api_get_live_job(job_id):
    """Get status and result of a live scan job."""
    with _job_store_lock:
        job = _job_store.get(job_id)

    if not job:
        return jsonify({'success': False, 'error': 'Job not found'}), 404

    response = {'status': job['status']}
    if job['status'] == 'done' and job.get('result'):
        response['result'] = job['result']
    if job['status'] == 'failed' and job.get('error'):
        response['error'] = job['error']

    return jsonify(response)


@app.route('/api/scan/email/upload', methods=['POST'])
def scan_email_upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    f = request.files['file']
    if not f.filename or not f.filename.lower().endswith('.eml'):
        return jsonify({'success': False, 'error': 'Only .eml files are accepted'}), 400
    data = f.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
        return jsonify({'success': False, 'error': 'File too large (max 5 MB)'}), 413
    try:
        from detection.email_scanner import scan_eml
        result = scan_eml(data)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f'Email scan error: {e}')
        return jsonify({'success': False, 'error': 'Internal scan error'}), 500
    try:
        input_val = f"{result['sender']['from_domain']}:{result['subject_snippet']}"[:200]
        user_id = session.get('user_id')
        if not user_id and 'anon_session_id' not in session:
            session['anon_session_id'] = secrets.token_hex(32)
        anon_id = session.get('anon_session_id') if not user_id else None
        scan = ScanHistory(
            scan_type='EMAIL',
            input_value=input_val,
            prediction=result['prediction'],
            confidence=result['confidence'],
            risk_score=result['risk_score'],
            risk_level=result['risk_level'],
            explanation='; '.join(result['evidence'][:3]) if result['evidence'] else '',
            recommendation='Review sender, do not click links.',
            status='completed',
            model_version=None,
            anon_session_id=anon_id,
            user_id=user_id,
        )
        db.session.add(scan)
        db.session.commit()
    except Exception as e:
        logger.error(f'Failed to save email scan to history: {e}')
    return jsonify(result), 200


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'service': 'securevision-ml'})


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """API endpoint to get scan history with ownership filtering."""
    try:
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Maximum 100 records

        user_id = session.get('user_id')
        show_legacy = app.config.get('SHOW_LEGACY_TO_ALL', True)

        if user_id:
            # Signed-in user: see only their own scans
            scans = ScanHistory.get_recent_scans(limit=limit, user_id=user_id)
        else:
            # Guest: see their anon session scans + legacy rows when enabled
            anon_id = session.get('anon_session_id')
            scans = ScanHistory.get_recent_scans(
                limit=limit,
                anon_session_id=anon_id,
                show_legacy=show_legacy,
            )

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
        email_scans = ScanHistory.query.filter_by(scan_type='EMAIL').count()
        stats['email_scans'] = email_scans

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
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000, use_reloader=False)
