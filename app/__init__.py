from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import configuration
from app.extensions import csrf, db, login_manager, migrate


def create_app(overrides=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(configuration(overrides))
    if app.config["TRUST_PROXY"]:
        # Only enable behind the single trusted Nginx proxy; web has no host port.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    db.init_app(app)
    migrate.init_app(app, db, compare_type=True)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."

    from app import (
        admin,
        auth,
        catalog,
        dashboard,
        imports,
        inventory,
        pos,
        recipes,
        reports,
        settings,
    )
    from app.cli import register_cli
    from app.models import User
    from app.permissions import ROLES, can

    for module in [
        auth,
        dashboard,
        catalog,
        inventory,
        admin,
        recipes,
        pos,
        reports,
        imports,
        settings,
    ]:
        app.register_blueprint(module.bp)
    register_cli(app)

    @login_manager.user_loader
    def load_user(user_id):
        if not isinstance(user_id, str) or ":" not in user_id:
            return None
        identity, version = user_id.split(":", 1)
        if not identity.isdigit() or not version.isdigit():
            return None
        return db.session.scalar(
            select(User).where(
                User.id == int(identity), User.auth_version == int(version), User.active.is_(True)
            )
        )

    @app.context_processor
    def context():
        now = datetime.now(ZoneInfo("America/Mexico_City"))
        return dict(
            can=can,
            roles=ROLES,
            now=now,
            today=now.date(),
            audit_labels={
                "demo.v1.started": "Carga inicial iniciada",
                "demo.v1.completed": "Carga inicial completada",
                "dataset.presentation.v1": "Actualización de presentación del catálogo",
                "dataset.snapshot_names.v1": "Actualización de nombres en comprobantes",
            },
            operation_labels={
                "receipt": "Entrada",
                "issue": "Salida",
                "reversal": "Reversión",
                "waste": "Merma / baja",
                "adjustment": "Ajuste por conteo",
                "sale": "Venta",
                "sale_cancel": "Cancelación de venta",
                "opening": "Inventario de apertura",
                "receipt_reversal": "Reversión de recepción",
            },
            payment_labels={"cash": "Efectivo", "card": "Tarjeta", "transfer": "Transferencia"},
        )

    @app.template_filter("money")
    def money(value):
        return "Costo pendiente" if value is None else f"${Decimal(value):,.2f}"

    @app.template_filter("quantity")
    def quantity(value):
        result = f"{Decimal(value):,.6f}".rstrip("0").rstrip(".")
        return result if result else "0"

    @app.template_filter("localtime")
    def localtime(value):
        return value.astimezone(ZoneInfo("America/Mexico_City")).strftime("%d/%m/%Y · %H:%M")

    @app.get("/health/ready")
    def health():
        try:
            from pathlib import Path

            from alembic.config import Config
            from alembic.script import ScriptDirectory

            config = Config()
            config.set_main_option(
                "script_location", str(Path(app.root_path).parent / "migrations")
            )
            head = ScriptDirectory.from_config(config).get_current_head()
            version = int(db.session.scalar(text("SHOW server_version_num")))
            revision = db.session.scalar(text("SELECT version_num FROM alembic_version"))
            if version // 10000 != 17 or revision != head:
                return jsonify(status="unavailable"), 503
            return jsonify(status="ok")
        except SQLAlchemyError:
            db.session.rollback()
            return jsonify(status="unavailable"), 503

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
        if current_user.is_authenticated or request.endpoint == "auth.login":
            response.headers["Cache-Control"] = "no-store"
        if app.config["APP_ENV"] == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return render_template(
            "error.html",
            code=400,
            message="La sesión del formulario expiró. Recarga la página e intenta de nuevo.",
        ), 400

    for code, message in [
        (400, "La solicitud no es válida. Revisa los datos e intenta de nuevo."),
        (403, "No tienes permiso para acceder a esta sección."),
        (404, "No encontramos la página solicitada."),
        (
            405,
            "Esta operación no está disponible mediante ese método. Utiliza el formulario de la aplicación.",
        ),
        (413, "El archivo o formulario excede el tamaño permitido."),
    ]:
        app.register_error_handler(
            code,
            lambda error, c=code, m=message: (render_template("error.html", code=c, message=m), c),
        )

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template(
            "error.html",
            code=500,
            message="No se pudo completar la operación. Intenta de nuevo; si persiste, contacta al administrador.",
        ), 500

    return app
