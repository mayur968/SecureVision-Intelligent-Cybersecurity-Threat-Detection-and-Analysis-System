"""Configuration settings for SecureVision application."""

import os
from datetime import timedelta
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Application configuration."""

    # Flask settings — read from env so SESSION_COOKIE_SECURE resolves correctly
    # at startup rather than being hard-wired to False at class-parse time.
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

    # Database settings
    # DATABASE_URL env-var enables Postgres (or any other backend).
    # Falls back to the local SQLite file for development.
    _db_url = os.environ.get('DATABASE_URL')
    if _db_url:
        # SQLAlchemy 2.x requires "postgresql+psycopg2://" not "postgres://"
        if _db_url.startswith('postgres://'):
            _db_url = _db_url.replace('postgres://', 'postgresql+psycopg2://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{BASE_DIR / "securevision.db"}'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'apk'}

    # Model paths
    MODELS_DIR = BASE_DIR / 'models'
    URL_MODEL_PATH = MODELS_DIR / 'url_model.pkl'
    URL_VECTORIZER_PATH = MODELS_DIR / 'url_vectorizer.pkl'
    MESSAGE_MODEL_PATH = MODELS_DIR / 'message_model.pkl'
    MESSAGE_VECTORIZER_PATH = MODELS_DIR / 'message_vectorizer.pkl'
    APK_MODEL_PATH = MODELS_DIR / 'apk_model.pkl'

    # Data paths
    DATA_DIR = BASE_DIR / 'data'
    URL_DATA_PATH = DATA_DIR / 'urls' / 'sample_urls.csv'
    MESSAGE_DATA_PATH = DATA_DIR / 'messages' / 'sample_messages.csv'
    APK_DATA_PATH = DATA_DIR / 'apk' / 'sample_apk_features.csv'

    # Logging
    LOG_FILE = BASE_DIR / 'securevision.log'
    LOG_LEVEL = 'INFO'

    # Security settings
    SAFE_FILENAME_LENGTH = 100
    TEMP_FILE_CLEANUP = True

    # Testing flag — used by test suite to skip Alembic and use create_all()
    TESTING = os.environ.get('TESTING', '').lower() == 'true'

    # Google OAuth 2.0 settings
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', None)
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', None)
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

    # Session / secret key
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE   = not DEBUG        # False in dev, True when DEBUG=False
    SESSION_COOKIE_HTTPONLY = True
    # Explicit lifetime — avoids relying on Flask's implicit 31-day default.
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # Feature flag: expose legacy scan rows (no owner) to all visitors
    SHOW_LEGACY_TO_ALL = os.environ.get('SHOW_LEGACY_TO_ALL', 'true').lower() == 'true'

    @property
    def GOOGLE_ENABLED(self) -> bool:
        """True only when both Google OAuth credentials are configured."""
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)

    @staticmethod
    def init_app(app):
        """Initialize application configuration.

        NOTE: Database migrations are NOT run here.
        Run 'flask db upgrade' as a separate step before starting the app.
        In test environments (TESTING=true) the test suite calls db.create_all().
        """
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        Config.MODELS_DIR.mkdir(exist_ok=True)
        Config.DATA_DIR.mkdir(exist_ok=True)

        # Guard against the well-known default SECRET_KEY being used in
        # production.  A visible default value allows an attacker to forge
        # signed Flask session cookies with arbitrary user_id values.
        _debug = app.config.get('DEBUG', False)
        _secret = app.config.get('SECRET_KEY', '')
        if not _debug and _secret == 'dev-secret-change-me':
            raise RuntimeError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Set the SECRET_KEY environment variable before starting the app."
            )
