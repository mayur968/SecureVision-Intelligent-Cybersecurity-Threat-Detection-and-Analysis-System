"""Configuration settings for SecureVision application."""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

class Config:
    """Application configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = True
    
    # Database settings
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
    
    @staticmethod
    def init_app(app):
        """Initialize application configuration."""
        # Create necessary directories
        Config.UPLOAD_FOLDER.mkdir(exist_ok=True)
        Config.MODELS_DIR.mkdir(exist_ok=True)
        Config.DATA_DIR.mkdir(exist_ok=True)
