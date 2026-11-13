import click
from flask import current_app
from sqlalchemy import select, text

from app.extensions import db
from app.models import AuditLog, User


def register_cli(app):
    @app.cli.command("prepare-presentation")
    def prepare_presentation_command():
        """Actualiza nombres visibles de la carga inicial; conserva sus importes e historia."""
        from app.services.numbers import DomainError
        from app.services.presentation import normalize_presentation

        try:
            result = normalize_presentation()
        except DomainError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            "Presentación ya actualizada."
            if result["already_applied"]
            else "Catálogo, lotes y comprobantes actualizados; importes e historia conservados."
        )

    @app.cli.command("seed-demo")
    @click.option("--user-id", type=int, help="Administrador existente que registra la carga.")
    def seed_demo_command(user_id):
        """Carga local, explícita y repetible de datos ficticios; conserva los registros existentes."""
        from app.services.demo import seed_demo
        from app.services.numbers import DomainError

        try:
            result = seed_demo(user_id=user_id, progress=click.echo)
        except DomainError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(
            "Escenario demo ya cargado; no se duplicaron registros."
            if result["already_loaded"]
            else "Escenario demo cargado correctamente."
        )
        click.echo(
            f"{result['ingredients']} ingredientes, {result['suppliers']} proveedores, {result['menu_items']} productos y {result['sales']} ventas de ejemplo ({result['cancellations']} canceladas)."
        )

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nombre", type=str)
    @click.option("--email", prompt="Correo electrónico", type=str)
    @click.password_option(prompt="Contraseña (mínimo 12 caracteres)")
    def create_admin(name, email, password):
        """Create the first administrator without public default credentials."""
        if len(password) < 12 or len(password) > 200:
            raise click.ClickException("La contraseña debe tener entre 12 y 200 caracteres.")
        if not name.strip() or len(name) > 100 or "@" not in email or len(email) > 254:
            raise click.ClickException("Nombre o correo inválidos.")
        db.session.execute(text("SELECT pg_advisory_xact_lock(7001001)"))
        if db.session.scalar(
            select(User.id).where(User.role == "admin", User.active.is_(True)).limit(1)
        ):
            raise click.ClickException(
                "Ya existe un administrador activo. Usa Administración → Usuarios."
            )
        user = User(name=name.strip(), email=email.strip().lower(), role="admin", active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(
            AuditLog(user_id=user.id, action="user.bootstrap", detail="Administrador inicial")
        )
        db.session.commit()
        click.echo("Administrador creado. No se cargaron datos de demostración.")

    @app.cli.command("reconcile-inventory")
    def reconcile_inventory():
        """Read-only comparison: lots, allocations and ingredient movements."""
        from app.services.reconciliation import inventory_issues

        issues = inventory_issues(db.engine)
        if issues:
            for issue in issues:
                click.echo(issue)
            raise click.ClickException("Se detectaron diferencias; no se modificaron datos.")
        click.echo("Conciliación correcta: lotes, asignaciones y movimientos coinciden.")

    @app.cli.command("verify-database")
    def verify_database():
        """Validate connectivity, engine major version and schema migration."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        version = int(db.session.scalar(text("SHOW server_version_num")))
        if version // 10000 != 17:
            raise click.ClickException("Se requiere PostgreSQL 17.")
        revision = db.session.scalar(text("SELECT version_num FROM alembic_version"))
        from pathlib import Path

        config = Config()
        config.set_main_option(
            "script_location", str(Path(current_app.root_path).parent / "migrations")
        )
        if revision != ScriptDirectory.from_config(config).get_current_head():
            raise click.ClickException(
                "La base no está en la última revisión. Ejecuta flask db upgrade."
            )
        click.echo(f"PostgreSQL 17 conectado. Migración: {revision}.")

    @app.cli.command("reset-password")
    @click.option("--email", prompt="Correo de la cuenta")
    @click.password_option(prompt="Contraseña nueva (mínimo 12 caracteres)")
    def reset_password(email, password):
        """Local administrator recovery; never prints or stores a clear-text password."""
        if not 12 <= len(password) <= 200:
            raise click.ClickException("La contraseña debe tener entre 12 y 200 caracteres.")
        user = db.session.scalar(select(User).where(User.email == email.strip().lower()))
        if not user:
            raise click.ClickException("No existe una cuenta con ese correo.")
        user.set_password(password)
        db.session.add(
            AuditLog(
                user_id=user.id,
                action="auth.local_reset",
                detail="Restablecimiento local; sesiones anteriores revocadas",
            )
        )
        db.session.commit()
        click.echo("Contraseña restablecida. Las sesiones anteriores ya no son válidas.")
