"""
Idempotent script to update model_registry rows with accurate metadata
read from the actual .pkl files and training CSVs.

Run with:
    venv\Scripts\python.exe scripts/update_model_registry.py

Safe to re-run: only updates fields that have changed; never touches metrics.
"""
import sys, pathlib, datetime, joblib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import os
os.environ.setdefault('SKIP_VENV_CHECK', '1')
os.environ.setdefault('SECRET_KEY', 'update-script-key')

from app import app
from database.models import db, ModelRegistry

BASE = pathlib.Path(__file__).parent.parent

MODELS = [
    {
        'id':           'url_lr_v1.0',   # keep existing id (lr = initial name; not worth changing)
        'detector_type': 'url',
        'version':      'v1.0',
        'pkl_path':     'models/url_model.pkl',
        'csv_path':     'data/urls/sample_urls.csv',
        'notes': (
            'RandomForestClassifier trained on 197-row synthetic URL dataset '
            '(~100 safe / ~97 phishing). '
            'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
            '43 lexical + WHOIS + typosquatting features. '
            'Whitelist guard bypasses model for top-100 trusted domains.'
        ),
    },
    {
        'id':           'message_lr_v1.0',
        'detector_type': 'message',
        'version':      'v1.0',
        'pkl_path':     'models/message_model.pkl',
        'csv_path':     'data/messages/sample_messages.csv',
        'notes': (
            'LogisticRegression trained on 99-row demo message corpus '
            '(~40 safe / ~59 phishing). '
            'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
            'TF-IDF vectorizer (1000 features, unigrams+bigrams), 110 input features.'
        ),
    },
    {
        'id':           'apk_lr_v1.0',
        'detector_type': 'apk',
        'version':      'v1.0',
        'pkl_path':     'models/apk_model.pkl',
        'csv_path':     'data/apk/sample_apk_features.csv',
        'notes': (
            'LogisticRegression trained on 50-row synthetic APK feature dataset '
            '(25 benign / 25 malicious). '
            'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
            '44 static-analysis features (permissions, DEX count, components). '
            'No dynamic execution or code analysis.'
        ),
    },
]

def _get_algo(pkl_path):
    try:
        m = joblib.load(BASE / pkl_path)
        clf = m.steps[-1][1] if hasattr(m, 'steps') else m
        return type(clf).__name__
    except Exception as e:
        print(f"  WARNING: could not load {pkl_path}: {e}")
        return None

def _get_mtime(pkl_path):
    try:
        mtime = (BASE / pkl_path).stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc)
    except Exception:
        return None

def _get_csv_size(csv_path):
    try:
        import csv
        with open(BASE / csv_path) as f:
            return sum(1 for _ in csv.reader(f)) - 1  # subtract header
    except Exception:
        return None

def run():
    with app.app_context():
        for entry in MODELS:
            row = db.session.get(ModelRegistry, entry['id'])
            if row is None:
                print(f"  SKIP {entry['id']}: row not found in DB (run flask db upgrade first)")
                continue

            algo    = _get_algo(entry['pkl_path'])
            mtime   = _get_mtime(entry['pkl_path'])
            ds_size = _get_csv_size(entry['csv_path'])

            changed = []
            if algo and row.algorithm != algo:
                changed.append(f"algorithm {row.algorithm!r} -> {algo!r}")
                row.algorithm = algo
            if mtime and row.training_date != mtime:
                changed.append(f"training_date -> {mtime.date()}")
                row.training_date = mtime
            if ds_size and row.dataset_size != ds_size:
                changed.append(f"dataset_size {row.dataset_size} -> {ds_size}")
                row.dataset_size = ds_size
            if row.notes != entry['notes']:
                changed.append("notes updated")
                row.notes = entry['notes']

            if changed:
                print(f"  UPDATED {entry['id']}: {', '.join(changed)}")
            else:
                print(f"  OK      {entry['id']}: no changes needed")

        db.session.commit()
        print("Done.")

if __name__ == '__main__':
    run()
