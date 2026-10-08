"""
live-scanner/app.py — Minimal Flask service for live URL scanning.
Does NOT connect to the database. Returns results to the main ml-service.
"""
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=os.environ.get('LIVE_SCANNER_ORIGIN', 'http://ml-service:5000'))

# ── Job store ─────────────────────────────────────────────────────────────────
_job_store: dict = {}
_job_store_lock = threading.Lock()
_live_executor = ThreadPoolExecutor(
    max_workers=int(os.environ.get('LIVE_SCAN_MAX_WORKERS', '2'))
)
_LIVE_SCAN_ENABLED = os.environ.get('LIVE_SCAN_ENABLED', 'true').lower() == 'true'
_JOB_TTL_SECONDS = 900
_IP_MAX_CONCURRENT = 2


def _cleanup_old_jobs():
    now = time.time()
    with _job_store_lock:
        expired = [k for k, v in _job_store.items()
                   if now - v['created_at'] > _JOB_TTL_SECONDS]
        for k in expired:
            del _job_store[k]


def _count_ip_running(ip: str) -> int:
    with _job_store_lock:
        return sum(
            1 for v in _job_store.values()
            if v['ip'] == ip and v['status'] in ('queued', 'running')
        )


def _run_job(job_id: str, url: str):
    try:
        with _job_store_lock:
            _job_store[job_id]['status'] = 'running'

        from detection.live_scanner import scan_live
        timeout_ms = int(os.environ.get('LIVE_SCAN_TIMEOUT_MS', '15000'))
        result = scan_live(url, timeout_ms=timeout_ms)

        with _job_store_lock:
            _job_store[job_id]['status'] = 'done'
            _job_store[job_id]['result'] = result
    except Exception as e:
        with _job_store_lock:
            if job_id in _job_store:
                _job_store[job_id]['status'] = 'failed'
                _job_store[job_id]['error'] = str(e)[:500]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'live-scanner'})


@app.route('/api/scan/url/live', methods=['POST'])
def start_live_scan():
    if not _LIVE_SCAN_ENABLED:
        return jsonify({'success': False, 'error': 'Live scan is disabled'}), 503

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'success': False, 'error': 'URL parameter is required'}), 400

    url = data['url']
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc:
        return jsonify({'success': False, 'error': 'Invalid URL'}), 400

    client_ip = request.remote_addr or '0.0.0.0'
    if _count_ip_running(client_ip) >= _IP_MAX_CONCURRENT:
        return jsonify({'success': False, 'error': 'Too many concurrent scans'}), 429

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

    _live_executor.submit(_run_job, job_id, url)
    return jsonify({'job_id': job_id, 'status': 'queued'}), 202


@app.route('/api/scan/url/live/<job_id>', methods=['GET'])
def get_live_job(job_id):
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', '5001'))
    app.run(host='0.0.0.0', port=port, debug=False)
