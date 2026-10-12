"""
SecureVision — Python ML Microservice
JSON-only API (no HTML rendering).
Consumed by the Node.js/Express gateway.
"""

import sys as _sys
import os as _os

def _check_venv():
    """Warn loudly if not running from the project venv."""
    venv_python = _os.path.normpath(_os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)), '..', 'venv', 'Scripts', 'python.exe'
    ))
    running = _sys.executable.replace('\\', '/')
    expected = venv_python.replace('\\', '/')
    if running.lower() != expected.lower() and not _os.environ.get('SKIP_VENV_CHECK'):
        print(
            "\n" + "=" * 70 + "\n"
            "WARNING: You are NOT running from the project venv.\n"
            f"  Running:  {_sys.executable}\n"
            f"  Expected: {venv_python}\n"
            "  Some packages (playwright, tldextract, androguard) may be missing.\n"
            "  Run with:  .\\venv\\Scripts\\python.exe ml-service\\app.py\n"
            "  Or use:    .\\run.bat  (Windows CMD)  /  .\\run.ps1  (PowerShell)\n"
            + "=" * 70 + "\n",
            file=_sys.stderr
        )

_check_venv()
del _check_venv, _sys, _os

from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from utils.logger import logger
from database.models import db, ScanHistory, seed_model_registry
import os

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app(app)

# CORS scoped to Node gateway only (override via ML_ALLOWED_ORIGIN env var)
_allowed_origin = os.environ.get("ML_ALLOWED_ORIGIN", "http://localhost:4000")
CORS(app, origins=[_allowed_origin], supports_credentials=False)

db.init_app(app)
# In test mode create tables directly; otherwise expect 'flask db upgrade' to have run.
if Config.TESTING or app.config.get('TESTING'):
    with app.app_context():
        db.create_all()
        logger.info("ML microservice (test mode): tables created via create_all()")
else:
    with app.app_context():
        seed_model_registry()
        logger.info("ML microservice: database tables ready")

# ── Lazy-load detectors once at startup ─────────────────────────────────────
from detection.url_detector import URLDetector
from detection.message_detector import MessageDetector
from detection.apk_detector import APKDetector
from explanation.risk_score import RiskScorer
from explanation.threat_explainer import ThreatExplainer
from explanation.recommendations import RecommendationEngine
from utils.validators import validate_url, validate_message
from utils.file_security import generate_secure_filename, safe_file_cleanup
from database.ioc_extractor import extract_iocs

url_detector        = URLDetector()
message_detector    = MessageDetector()
apk_detector        = APKDetector()
risk_scorer         = RiskScorer()
threat_explainer    = ThreatExplainer()
recommendation_engine = RecommendationEngine()

logger.info("ML microservice: all detectors initialised")


# ── Health ───────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health probe for the Node.js gateway."""
    return jsonify({
        "status": "ok",
        "service": "securevision-ml",
        "models": {
            "url":     url_detector.model_loaded,
            "message": message_detector.model_loaded,
            "apk":     apk_detector.model_loaded,
        }
    })


# ── URL scan ─────────────────────────────────────────────────────────────────

@app.route("/api/scan/url", methods=["POST"])
def api_scan_url():
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"success": False, "error": "url field required"}), 400

        url = data["url"]
        is_valid, err = validate_url(url)
        if not is_valid:
            return jsonify({"success": False, "error": err}), 400

        det   = url_detector.predict(url)
        if "error" in det:
            return jsonify({"success": False, "error": det["error"]}), 500

        risk  = risk_scorer.calculate_risk_score(det["prediction"], det["confidence"], "URL", det)
        expl  = threat_explainer.explain(det["prediction"], det["confidence"], "URL", det)
        recs  = recommendation_engine.get_recommendations(det["prediction"], "URL", risk["risk_level"], det)

        ScanHistory.save_scan(
            scan_type="URL", input_value=url,
            prediction=det["prediction"], confidence=det["confidence"],
            risk_level=risk["risk_level"], explanation=expl,
            recommendation="\n".join(recs),
            risk_score=risk["risk_score"],
            model_version="url_lr_v1.0",
            ioc_list=extract_iocs("URL", url, det),
        )

        return jsonify({
            "success": True,
            "prediction":    det["prediction"],
            "confidence":    round(det["confidence"], 4),
            "risk_score":    risk["risk_score"],
            "risk_level":    risk["risk_level"],
            "explanation":   expl,
            "recommendations": recs,
            "features":      det.get("important_features", {}),
        })
    except Exception as e:
        logger.error(f"URL scan error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── Message scan ─────────────────────────────────────────────────────────────

@app.route("/api/scan/message", methods=["POST"])
def api_scan_message():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"success": False, "error": "message field required"}), 400

        message = data["message"]
        is_valid, err = validate_message(message)
        if not is_valid:
            return jsonify({"success": False, "error": err}), 400

        det   = message_detector.predict(message)
        if "error" in det:
            return jsonify({"success": False, "error": det["error"]}), 500

        risk  = risk_scorer.calculate_risk_score(det["prediction"], det["confidence"], "MESSAGE", det)
        expl  = threat_explainer.explain(det["prediction"], det["confidence"], "MESSAGE", det)
        recs  = recommendation_engine.get_recommendations(det["prediction"], "MESSAGE", risk["risk_level"], det)

        ScanHistory.save_scan(
            scan_type="MESSAGE",
            input_value=message[:500],
            prediction=det["prediction"], confidence=det["confidence"],
            risk_level=risk["risk_level"], explanation=expl,
            recommendation="\n".join(recs),
            risk_score=risk["risk_score"],
            model_version="message_lr_v1.0",
            ioc_list=extract_iocs("MESSAGE", message, det),
        )

        return jsonify({
            "success": True,
            "prediction":    det["prediction"],
            "confidence":    round(det["confidence"], 4),
            "risk_score":    risk["risk_score"],
            "risk_level":    risk["risk_level"],
            "explanation":   expl,
            "recommendations": recs,
            "indicators":    det.get("indicators", []),
        })
    except Exception as e:
        logger.error(f"Message scan error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── APK scan ─────────────────────────────────────────────────────────────────

@app.route("/api/scan/apk", methods=["POST"])
def api_scan_apk():
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files["file"]
        if not file.filename:
            return jsonify({"success": False, "error": "No file selected"}), 400
        if not file.filename.lower().endswith(".apk"):
            return jsonify({"success": False, "error": "Only .apk files accepted"}), 400

        secure_name = generate_secure_filename(file.filename)
        file_path   = Config.UPLOAD_FOLDER / secure_name
        file.save(str(file_path))

        try:
            det = apk_detector.analyze(file_path)
            if "error" in det:
                return jsonify({"success": False, "error": det["error"]}), 400

            feats = det.get("features", {})
            risk  = risk_scorer.calculate_risk_score(det["prediction"], det["confidence"], "APK", feats)
            expl  = threat_explainer.explain(det["prediction"], det["confidence"], "APK", feats)
            recs  = recommendation_engine.get_recommendations(det["prediction"], "APK", risk["risk_level"], feats)

            file_info    = det.get("file_info", {})
            apk_filename = file_info.get("filename", file.filename)

            ScanHistory.save_scan(
                scan_type="APK", input_value=apk_filename,
                prediction=det["prediction"], confidence=det["confidence"],
                risk_level=risk["risk_level"], explanation=expl,
                recommendation="\n".join(recs),
                risk_score=risk["risk_score"],
                model_version="apk_lr_v1.0",
                ioc_list=extract_iocs("APK", apk_filename, det, apk_file_path=file_path),
            )

            return jsonify({
                "success": True,
                "filename":      apk_filename,
                "file_size":     file_info.get("size_mb", 0),
                "prediction":    det["prediction"],
                "confidence":    round(det["confidence"], 4),
                "risk_score":    risk["risk_score"],
                "risk_level":    risk["risk_level"],
                "explanation":   expl,
                "recommendations": recs,
                "indicators":    det.get("indicators", []),
                "analysis_note": det.get("analysis_note", ""),
            })
        finally:
            safe_file_cleanup(file_path)

    except Exception as e:
        logger.error(f"APK scan error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── History & Statistics ─────────────────────────────────────────────────────

@app.route("/api/history", methods=["GET"])
def api_get_history():
    try:
        limit = min(request.args.get("limit", 50, type=int), 100)
        scans = ScanHistory.get_recent_scans(limit=limit)
        return jsonify({"success": True, "count": len(scans), "scans": [s.to_dict() for s in scans]})
    except Exception as e:
        logger.error(f"History error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@app.route("/api/statistics", methods=["GET"])
def api_get_statistics():
    try:
        return jsonify({"success": True, "statistics": ScanHistory.get_statistics()})
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# ── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Unhandled 500: {e}")
    return jsonify({"success": False, "error": "Internal server error"}), 500

@app.errorhandler(413)
def too_large(_):
    return jsonify({"success": False, "error": "File too large (max 50 MB)"}), 413


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("ML_PORT", 5000))
    logger.info(f"Starting ML microservice on port {port}")
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=port)
