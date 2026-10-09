"""Minimal Flask application for running Flask-Migrate / Alembic CLI commands.

Usage:
    flask --app migrate_app db init       (first time only — already done)
    flask --app migrate_app db upgrade
    flask --app migrate_app db downgrade
    flask --app migrate_app db current
    flask --app migrate_app db history
"""
from flask import Flask
from flask_migrate import Migrate

from config import Config
from database.models import db


def create_migrate_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    Migrate(app, db, render_as_batch=True)
    return app


app = create_migrate_app()
