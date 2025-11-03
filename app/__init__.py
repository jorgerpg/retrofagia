import os

from flask import Flask, url_for
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@db:5432/retrofagia",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # 4MB por arquivo
    app.config["UPLOAD_FOLDER"] = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(app.root_path, "static", "uploads")
    )

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    from . import models  # noqa: F401
    from .auth import auth_bp
    from .main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    @app.before_request
    def ensure_tables_exist():
        # Lazy table creation keeps setup simple in development containers.
        if not getattr(app, "_tables_created", False):
            db.create_all()
            app._tables_created = True

    @app.template_filter("image_url")
    def image_url_filter(value: str):
        if not value:
            return ""
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return url_for("static", filename=value)

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app


__all__ = ["create_app", "db", "login_manager"]
