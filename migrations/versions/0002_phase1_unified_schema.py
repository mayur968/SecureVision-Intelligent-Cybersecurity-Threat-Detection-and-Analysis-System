"""0002 – Phase 1: unified threat model and data layer.

Changes:
  scan_history  – add 5 nullable/defaulted columns
  model_registry – new table
  ioc            – new table
  scan_ioc       – new join table
  seed model_registry with 3 rows (idempotent)

Revision ID: 0002_phase1_unified_schema
Revises:     0001_baseline
Create Date: 2026-10-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime, timezone

revision      = '0002_phase1_unified_schema'
down_revision = '0001_baseline'
branch_labels = None
depends_on    = None


# ── upgrade ────────────────────────────────────────────────────────────────────

def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {'t': table_name}
    ).first()
    return result is not None


def _column_exists(conn, table_name: str, col_name: str) -> bool:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return any(r[1] == col_name for r in rows)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. model_registry ─────────────────────────────────────────────────────
    if not _table_exists(conn, 'model_registry'):
        op.create_table(
            'model_registry',
            sa.Column('id',               sa.String(50),  nullable=False),
            sa.Column('detector_type',    sa.String(20),  nullable=False),
            sa.Column('version',          sa.String(20),  nullable=False),
            sa.Column('algorithm',        sa.String(50),  nullable=False),
            sa.Column('training_date',    sa.DateTime,    nullable=True),
            sa.Column('dataset_name',     sa.String(100), nullable=False),
            sa.Column('dataset_size',     sa.Integer,     nullable=True),
            sa.Column('is_synthetic_data',sa.Boolean,     nullable=False, server_default='1'),
            sa.Column('accuracy',         sa.Float,       nullable=True),
            sa.Column('precision_score',  sa.Float,       nullable=True),
            sa.Column('recall',           sa.Float,       nullable=True),
            sa.Column('f1_score',         sa.Float,       nullable=True),
            sa.Column('roc_auc',          sa.Float,       nullable=True),
            sa.Column('notes',            sa.Text,        nullable=True),
            sa.Column('status',           sa.String(20),  nullable=False, server_default='active'),
            sa.Column('created_at',       sa.DateTime,    nullable=False,
                      server_default=sa.func.now()),
            sa.PrimaryKeyConstraint('id'),
        )

    # 2. ioc ────────────────────────────────────────────────────────────────
    if not _table_exists(conn, 'ioc'):
        op.create_table(
            'ioc',
            sa.Column('id',         sa.Integer,     nullable=False,  autoincrement=True),
            sa.Column('ioc_type',   sa.String(20),  nullable=False),
            sa.Column('value',      sa.String(512), nullable=False),
            sa.Column('first_seen', sa.DateTime,    nullable=False, server_default=sa.func.now()),
            sa.Column('last_seen',  sa.DateTime,    nullable=False, server_default=sa.func.now()),
            sa.Column('seen_count', sa.Integer,     nullable=False, server_default='1'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ioc_type', 'value', name='uq_ioc_type_value'),
        )

    # 3. scan_ioc (join table) ───────────────────────────────────────────────
    if not _table_exists(conn, 'scan_ioc'):
        op.create_table(
            'scan_ioc',
            sa.Column('scan_id', sa.Integer, sa.ForeignKey('scan_history.id', ondelete='CASCADE'),
                      nullable=False),
            sa.Column('ioc_id',  sa.Integer, sa.ForeignKey('ioc.id',          ondelete='CASCADE'),
                      nullable=False),
            sa.PrimaryKeyConstraint('scan_id', 'ioc_id'),
        )

    # 4. scan_history – add 5 columns using batch for SQLite compatibility ──
    new_cols = {
        'risk_score':    sa.Column('risk_score',    sa.Integer,    nullable=True),
        'duration_ms':   sa.Column('duration_ms',   sa.Integer,    nullable=True),
        'status':        sa.Column('status',        sa.String(20), nullable=True,   server_default='completed'),
        'model_version': sa.Column('model_version', sa.String(50), nullable=True),
        'is_demo_data':  sa.Column('is_demo_data',  sa.Boolean,    nullable=False,  server_default='0'),
    }
    missing = [name for name in new_cols if not _column_exists(conn, 'scan_history', name)]
    if missing:
        with op.batch_alter_table('scan_history', schema=None) as batch_op:
            for name in missing:
                batch_op.add_column(new_cols[name])

    # 5. Seed model_registry (idempotent INSERT OR IGNORE) ──────────────────
    _seed_model_registry()


def _seed_model_registry() -> None:
    """Insert initial model registry rows.

    Algorithm names are read from the saved .pkl files at migration time.
    Accuracy metrics are left NULL — not yet evaluated on a real test set.
    Training dates are set from model file mtimes.
    is_synthetic_data = 1 (True) for all three.
    """
    import pathlib, joblib

    base = pathlib.Path(__file__).parent.parent.parent  # project root

    MODELS = [
        {
            'id':            'url_lr_v1.0',
            'detector_type': 'url',
            'version':       'v1.0',
            'pkl':           'models/url_model.pkl',
            'dataset_name':  'Synthetic URL dataset (100 samples)',
            'dataset_size':  100,
            'notes':         (
                'Trained on 100-sample synthetic dataset (50 benign / 50 phishing). '
                'is_synthetic_data=True. Metrics NULL — not evaluated on real held-out set. '
                '43 lexical + WHOIS + typosquatting features.'
            ),
        },
        {
            'id':            'message_lr_v1.0',
            'detector_type': 'message',
            'version':       'v1.0',
            'pkl':           'models/message_model.pkl',
            'dataset_name':  'Demo message corpus (99 samples)',
            'dataset_size':  99,
            'notes':         (
                'Trained on 99-sample demo corpus (40 safe / 59 phishing). '
                'is_synthetic_data=True. Metrics NULL — not evaluated on real held-out set. '
                'TF-IDF (1000 features, unigrams+bigrams) + Logistic Regression.'
            ),
        },
        {
            'id':            'apk_lr_v1.0',
            'detector_type': 'apk',
            'version':       'v1.0',
            'pkl':           'models/apk_model.pkl',
            'dataset_name':  'Synthetic APK feature dataset (400 samples)',
            'dataset_size':  400,
            'notes':         (
                'Trained on 400-sample synthetic APK feature dataset '
                '(200 benign / 200 malicious). '
                'is_synthetic_data=True. Metrics NULL — not evaluated on real held-out set. '
                'Pipeline: StandardScaler + Logistic Regression, 44 static-analysis features.'
            ),
        },
    ]

    conn = op.get_bind()

    for entry in MODELS:
        # Skip if already present (idempotent)
        existing = conn.execute(
            text("SELECT id FROM model_registry WHERE id = :id"),
            {'id': entry['id']}
        ).first()
        if existing:
            continue

        algorithm = 'LogisticRegression'
        training_date = None
        pkl_path = base / entry['pkl']

        try:
            m = joblib.load(pkl_path)
            clf = m
            if hasattr(m, 'steps'):
                clf = m.steps[-1][1]
            algorithm = type(clf).__name__
        except Exception:
            pass

        try:
            mtime = pkl_path.stat().st_mtime
            training_date = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            training_date = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

        conn.execute(
            text("""
                INSERT OR IGNORE INTO model_registry
                  (id, detector_type, version, algorithm, training_date,
                   dataset_name, dataset_size, is_synthetic_data,
                   accuracy, precision_score, recall, f1_score, roc_auc,
                   notes, status, created_at)
                VALUES
                  (:id, :detector_type, :version, :algorithm, :training_date,
                   :dataset_name, :dataset_size, 1,
                   NULL, NULL, NULL, NULL, NULL,
                   :notes, 'active', :created_at)
            """),
            {
                'id':            entry['id'],
                'detector_type': entry['detector_type'],
                'version':       entry['version'],
                'algorithm':     algorithm,
                'training_date': training_date,
                'dataset_name':  entry['dataset_name'],
                'dataset_size':  entry['dataset_size'],
                'notes':         entry['notes'],
                'created_at':    datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            }
        )


# ── downgrade ──────────────────────────────────────────────────────────────────

def downgrade() -> None:
    # Remove Phase 1 additions from scan_history
    with op.batch_alter_table('scan_history', schema=None) as batch_op:
        batch_op.drop_column('is_demo_data')
        batch_op.drop_column('model_version')
        batch_op.drop_column('status')
        batch_op.drop_column('duration_ms')
        batch_op.drop_column('risk_score')

    op.drop_table('scan_ioc')
    op.drop_table('ioc')
    op.drop_table('model_registry')
