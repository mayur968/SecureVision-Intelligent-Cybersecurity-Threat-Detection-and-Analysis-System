"""Database models for SecureVision — Phase 1 unified schema + Stage 2 auth."""

from datetime import datetime, timezone
from typing import Optional
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ── Users ──────────────────────────────────────────────────────────────────────
class User(db.Model):
    """Authenticated user — created on first Google sign-in, updated on each login."""
    __tablename__ = 'users'

    id          = db.Column(db.Integer,     primary_key=True, autoincrement=True)
    google_sub  = db.Column(db.String(255), unique=True, nullable=False)
    email       = db.Column(db.String(255), nullable=True)
    name        = db.Column(db.String(255), nullable=True)
    picture     = db.Column(db.String(500), nullable=True)
    created_at  = db.Column(db.DateTime,    nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    last_login  = db.Column(db.DateTime,    nullable=True)

    # Scans belonging to this user
    scans = db.relationship('ScanHistory', back_populates='owner', lazy='dynamic',
                            foreign_keys='ScanHistory.user_id')

    def to_dict(self):
        return {
            'id':      self.id,
            'name':    self.name,
            'email':   self.email,
            'picture': self.picture,
        }

    def __repr__(self):
        return f'<User {self.id}: {self.email}>'


# ── Association table: scan_history ↔ ioc (many-to-many) ──────────────────────
scan_ioc = db.Table(
    'scan_ioc',
    db.Column('scan_id', db.Integer, db.ForeignKey('scan_history.id', ondelete='CASCADE'),
              primary_key=True),
    db.Column('ioc_id',  db.Integer, db.ForeignKey('ioc.id',          ondelete='CASCADE'),
              primary_key=True),
)


# ── Model registry ─────────────────────────────────────────────────────────────
class ModelRegistry(db.Model):
    """Registry of all trained ML models used by the detectors.

    Accuracy/precision/recall/f1/roc_auc are NULL unless they come from a
    real evaluation run against a held-out test set.
    """
    __tablename__ = 'model_registry'

    id               = db.Column(db.String(50),  primary_key=True)
    detector_type    = db.Column(db.String(20),  nullable=False)   # url|message|apk
    version          = db.Column(db.String(20),  nullable=False)
    algorithm        = db.Column(db.String(50),  nullable=False)
    training_date    = db.Column(db.DateTime,    nullable=True)
    dataset_name     = db.Column(db.String(100), nullable=False)
    dataset_size     = db.Column(db.Integer,     nullable=True)
    is_synthetic_data = db.Column(db.Boolean,    nullable=False, default=True)
    # Metrics — NULL unless from a real evaluation run
    accuracy         = db.Column(db.Float, nullable=True)
    precision_score  = db.Column(db.Float, nullable=True)
    recall           = db.Column(db.Float, nullable=True)
    f1_score         = db.Column(db.Float, nullable=True)
    roc_auc          = db.Column(db.Float, nullable=True)
    notes            = db.Column(db.Text,  nullable=True)
    status           = db.Column(db.String(20), nullable=False, default='active')  # active|retired
    created_at       = db.Column(db.DateTime,   nullable=False,
                                 default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id':               self.id,
            'detector_type':    self.detector_type,
            'version':          self.version,
            'algorithm':        self.algorithm,
            'training_date':    self.training_date.isoformat() if self.training_date else None,
            'dataset_name':     self.dataset_name,
            'dataset_size':     self.dataset_size,
            'is_synthetic_data': self.is_synthetic_data,
            'accuracy':         self.accuracy,
            'precision_score':  self.precision_score,
            'recall':           self.recall,
            'f1_score':         self.f1_score,
            'roc_auc':          self.roc_auc,
            'notes':            self.notes,
            'status':           self.status,
            'created_at':       self.created_at.isoformat() if self.created_at else None,
        }


# ── IOC ────────────────────────────────────────────────────────────────────────
class IOC(db.Model):
    """Indicators of Compromise, normalised and deduplicated across scans.

    ioc_type values: domain | ip | url | hash_sha256 | hash_md5 |
                     email  | phone | permission
    """
    __tablename__ = 'ioc'
    __table_args__ = (
        db.UniqueConstraint('ioc_type', 'value', name='uq_ioc_type_value'),
    )

    id         = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    ioc_type   = db.Column(db.String(20),   nullable=False)
    value      = db.Column(db.String(512),  nullable=False)
    first_seen = db.Column(db.DateTime,     nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    last_seen  = db.Column(db.DateTime,     nullable=False,
                           default=lambda: datetime.now(timezone.utc))
    seen_count = db.Column(db.Integer,      nullable=False, default=1)

    scans      = db.relationship('ScanHistory', secondary=scan_ioc, back_populates='iocs',
                                 lazy='dynamic')

    def to_dict(self):
        return {
            'id':         self.id,
            'ioc_type':   self.ioc_type,
            'value':      self.value,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen':  self.last_seen.isoformat()  if self.last_seen  else None,
            'seen_count': self.seen_count,
        }


# ── Scan history ───────────────────────────────────────────────────────────────
class ScanHistory(db.Model):
    """Scan history — extended in Phase 1 with additive columns.

    All new columns are nullable or carry defaults so existing SQLite rows
    remain valid with no data loss.
    """
    __tablename__ = 'scan_history'

    # ── Original columns (do not remove or rename) ──────────────────────────
    id             = db.Column(db.Integer,      primary_key=True)
    scan_type      = db.Column(db.String(20),   nullable=False)
    input_value    = db.Column(db.Text,         nullable=False)
    prediction     = db.Column(db.String(20),   nullable=False)
    confidence     = db.Column(db.Float,        nullable=False)
    risk_level     = db.Column(db.String(20),   nullable=False)
    explanation    = db.Column(db.Text,         nullable=True)
    recommendation = db.Column(db.Text,         nullable=True)
    created_at     = db.Column(db.DateTime,     nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    # ── Phase 1 additions ───────────────────────────────────────────────────
    risk_score     = db.Column(db.Integer,      nullable=True)   # 0-100
    duration_ms    = db.Column(db.Integer,      nullable=True)
    status         = db.Column(db.String(20),   nullable=True,   default='completed')
    # FK to model_registry; NULL for pre-Phase-1 rows ("legacy" in UI)
    model_version  = db.Column(db.String(50),
                                db.ForeignKey('model_registry.id', ondelete='SET NULL'),
                                nullable=True)
    is_demo_data   = db.Column(db.Boolean,      nullable=False,  default=False)

    # ── Stage 2 additions ───────────────────────────────────────────────────
    # NULL = legacy row (pre-auth). Set when user is signed in.
    user_id        = db.Column(db.Integer,
                                db.ForeignKey('users.id', ondelete='SET NULL'),
                                nullable=True)
    # Set for anonymous (guest) sessions so rows are queryable by session.
    anon_session_id = db.Column(db.String(64),  nullable=True)

    # Relationships
    iocs           = db.relationship('IOC', secondary=scan_ioc, back_populates='scans',
                                     lazy='select')
    model          = db.relationship('ModelRegistry', foreign_keys=[model_version], lazy='select')
    owner          = db.relationship('User', foreign_keys=[user_id], back_populates='scans',
                                     lazy='select')

    def __repr__(self):
        return f'<ScanHistory {self.id}: {self.scan_type} - {self.prediction}>'

    def to_dict(self):
        """Serialize for JSON API.

        Additive only — all original keys are preserved unchanged.
        New keys are always present (null when not set).
        """
        base = self.input_value
        truncated = base[:100] + '...' if len(base) > 100 else base

        return {
            # ── Original keys (unchanged shape) ──────────────────────────
            'id':             self.id,
            'scan_type':      self.scan_type,
            'input_value':    truncated,
            'prediction':     self.prediction,
            'confidence':     round(self.confidence, 4),
            'risk_level':     self.risk_level,
            'explanation':    self.explanation,
            'recommendation': self.recommendation,
            'created_at':     self.created_at.isoformat() if self.created_at else None,
            # ── Phase 1 additions ─────────────────────────────────────────
            'risk_score':     self.risk_score,
            'duration_ms':    self.duration_ms,
            'status':         self.status or 'completed',
            'model_version':  self.model_version or 'legacy',
            'is_demo_data':   bool(self.is_demo_data),
            'ioc_count':      len(self.iocs),
            # ── Stage 2 additions ─────────────────────────────────────────
            'user_id':        self.user_id,
            # True when both user_id and anon_session_id are NULL (pre-auth legacy row)
            'is_legacy':      (self.user_id is None and self.anon_session_id is None),
        }

    # ── Queries ────────────────────────────────────────────────────────────────

    @staticmethod
    def get_statistics():
        """Aggregate statistics for dashboard. Unchanged shape, URL_LIVE counted."""
        total_scans    = ScanHistory.query.count()
        apk_scans      = ScanHistory.query.filter_by(scan_type='APK').count()
        url_scans      = ScanHistory.query.filter(
            ScanHistory.scan_type.in_(['URL', 'URL_LIVE'])
        ).count()
        message_scans  = ScanHistory.query.filter_by(scan_type='MESSAGE').count()

        threats_detected = ScanHistory.query.filter(
            ScanHistory.prediction.in_(['PHISHING', 'MALICIOUS'])
        ).count()
        safe_results   = ScanHistory.query.filter_by(prediction='SAFE').count()

        apk_threats    = ScanHistory.query.filter_by(
            scan_type='APK', prediction='MALICIOUS').count()
        url_threats    = ScanHistory.query.filter(
            ScanHistory.scan_type.in_(['URL', 'URL_LIVE']),
            ScanHistory.prediction == 'PHISHING',
        ).count()
        message_threats = ScanHistory.query.filter_by(
            scan_type='MESSAGE', prediction='PHISHING').count()

        return {
            'total_scans':      total_scans,
            'apk_scans':        apk_scans,
            'url_scans':        url_scans,
            'message_scans':    message_scans,
            'threats_detected': threats_detected,
            'safe_results':     safe_results,
            'threat_breakdown': {
                'apk':     apk_threats,
                'url':     url_threats,
                'message': message_threats,
            },
        }

    @staticmethod
    def get_recent_scans(limit=10, user_id=None, anon_session_id=None, show_legacy=True):
        """Return recent scans filtered by ownership.

        - user_id set:        return that user's scans only.
        - anon_session_id set: return that guest session's scans + legacy rows (when show_legacy).
        - Neither set:        return legacy rows (when show_legacy) or nothing.
        - show_legacy=True:   always include rows where both user_id IS NULL and
                              anon_session_id IS NULL (pre-auth rows).
        """
        from sqlalchemy import or_, and_

        if user_id is not None:
            return ScanHistory.query.filter_by(user_id=user_id).order_by(
                ScanHistory.created_at.desc()
            ).limit(limit).all()

        # Guest or unauthenticated caller
        filters = []
        if anon_session_id is not None:
            filters.append(ScanHistory.anon_session_id == anon_session_id)
        if show_legacy:
            filters.append(
                and_(ScanHistory.user_id.is_(None),
                     ScanHistory.anon_session_id.is_(None))
            )

        if filters:
            return ScanHistory.query.filter(or_(*filters)).order_by(
                ScanHistory.created_at.desc()
            ).limit(limit).all()

        # No filters match → return empty list
        return []

    @staticmethod
    def save_scan(scan_type, input_value, prediction, confidence,
                  risk_level, explanation, recommendation,
                  risk_score=None, duration_ms=None, model_version=None,
                  is_demo_data=False, ioc_list=None,
                  user_id=None, anon_session_id=None):
        """Create and persist a scan record, then attach extracted IOCs.

        ioc_list: optional list of dicts [{ioc_type, value}, ...] already
                  extracted by ioc_extractor.  If None, no IOCs are attached.

        Returns the saved ScanHistory object.
        """
        scan = ScanHistory(
            scan_type=scan_type,
            input_value=input_value,
            prediction=prediction,
            confidence=confidence,
            risk_level=risk_level,
            explanation=explanation,
            recommendation=recommendation,
            risk_score=risk_score,
            duration_ms=duration_ms,
            status='completed',
            model_version=model_version,
            is_demo_data=is_demo_data,
            user_id=user_id,
            anon_session_id=anon_session_id,
        )
        db.session.add(scan)
        db.session.flush()   # get scan.id before committing

        if ioc_list:
            _attach_iocs(scan, ioc_list)

        db.session.commit()
        return scan


# ── IOC upsert helper ──────────────────────────────────────────────────────────

def _attach_iocs(scan: ScanHistory, ioc_list: list) -> None:
    """Upsert IOC records and attach them to a scan.

    Called inside an open transaction (after flush, before commit).
    Handles unique-constraint races gracefully.
    Capped at 50 IOCs per scan.
    """
    from sqlalchemy.exc import IntegrityError
    from datetime import timezone as _tz

    now = datetime.now(timezone.utc)
    seen = set()

    for raw in ioc_list[:50]:
        if not isinstance(raw, dict):
            continue
        ioc_type = (raw.get('ioc_type') or '').strip().lower()
        value    = (raw.get('value')    or '').strip()
        if not ioc_type or not value:
            continue

        # Normalise domains to lowercase; deduplicate within this scan
        key = (ioc_type, value)
        if key in seen:
            continue
        seen.add(key)

        try:
            existing = IOC.query.filter_by(ioc_type=ioc_type, value=value).with_for_update().first()
            if existing:
                existing.seen_count += 1
                existing.last_seen   = now
                scan.iocs.append(existing)
            else:
                new_ioc = IOC(ioc_type=ioc_type, value=value,
                              first_seen=now, last_seen=now, seen_count=1)
                db.session.add(new_ioc)
                db.session.flush()
                scan.iocs.append(new_ioc)
        except IntegrityError:
            db.session.rollback()
            # Race: another request inserted the same IOC just now; re-fetch
            try:
                db.session.begin_nested()
                existing = IOC.query.filter_by(ioc_type=ioc_type, value=value).first()
                if existing:
                    existing.seen_count += 1
                    existing.last_seen   = now
                    scan.iocs.append(existing)
            except Exception:
                pass   # IOC failure must never fail the scan
        except Exception:
            pass        # idem


# ── Model registry seed ────────────────────────────────────────────────────────

def seed_model_registry() -> None:
    """Idempotently seed the three initial model registry entries.

    Algorithm names and feature counts are read from the actual .pkl files.
    Accuracy metrics are left NULL — they have not been evaluated on a
    real held-out test set.  is_synthetic_data is True.
    """
    import pathlib, sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

    SEED_MODELS = [
        {
            'id':               'url_lr_v1.0',
            'detector_type':    'url',
            'version':          'v1.0',
            'pkl_path':         'models/url_model.pkl',
            'dataset_name':     'Synthetic URL dataset (197 samples)',
            'dataset_size':     197,
            'notes':            (
                'RandomForestClassifier trained on 197-row synthetic URL dataset '
                '(~100 safe / ~97 phishing). '
                'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
                '43 lexical + WHOIS + typosquatting features. '
                'Whitelist guard bypasses model for top-100 trusted domains.'
            ),
        },
        {
            'id':               'message_lr_v1.0',
            'detector_type':    'message',
            'version':          'v1.0',
            'pkl_path':         'models/message_model.pkl',
            'dataset_name':     'Demo message corpus (99 samples)',
            'dataset_size':     99,
            'notes':            (
                'LogisticRegression trained on 99-row demo message corpus '
                '(~40 safe / ~59 phishing). '
                'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
                'TF-IDF vectorizer (1000 features, unigrams+bigrams), 110 input features.'
            ),
        },
        {
            'id':               'apk_lr_v1.0',
            'detector_type':    'apk',
            'version':          'v1.0',
            'pkl_path':         'models/apk_model.pkl',
            'dataset_name':     'Synthetic APK feature dataset (50 samples)',
            'dataset_size':     50,
            'notes':            (
                'LogisticRegression trained on 50-row synthetic APK feature dataset '
                '(25 benign / 25 malicious). '
                'is_synthetic_data=True. Metrics not evaluated on a real held-out set. '
                '44 static-analysis features (permissions, DEX count, components). '
                'No dynamic execution or code analysis.'
            ),
        },
    ]

    base = pathlib.Path(__file__).parent.parent

    for entry in SEED_MODELS:
        if db.session.get(ModelRegistry, entry['id']) is not None:
            continue   # already seeded — idempotent

        # Read algorithm from the actual saved model
        algorithm = 'LogisticRegression'  # fallback
        try:
            import joblib
            m = joblib.load(base / entry['pkl_path'])
            clf = m
            if hasattr(m, 'steps'):       # sklearn Pipeline
                clf = m.steps[-1][1]
            algorithm = type(clf).__name__
        except Exception:
            pass

        # Use model file mtime as training date proxy
        training_date = None
        try:
            mtime = (base / entry['pkl_path']).stat().st_mtime
            training_date = datetime.fromtimestamp(mtime, tz=timezone.utc)
        except Exception:
            pass

        record = ModelRegistry(
            id=entry['id'],
            detector_type=entry['detector_type'],
            version=entry['version'],
            algorithm=algorithm,
            training_date=training_date,
            dataset_name=entry['dataset_name'],
            dataset_size=entry['dataset_size'],
            is_synthetic_data=True,
            accuracy=None,
            precision_score=None,
            recall=None,
            f1_score=None,
            roc_auc=None,
            notes=entry['notes'],
            status='active',
        )
        db.session.add(record)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
