import hashlib
from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.forms import LoginForm, PasswordForm
from app.models import AuditLog, LoginThrottle, User, utcnow

bp = Blueprint("auth", __name__)
DUMMY_HASH = generate_password_hash("no-account-password-not-for-login")


def allow_attempt(email, address):
    """Database upserts make throttling consistent across Gunicorn workers."""
    now = utcnow()
    allowed = True
    with Session(db.engine) as transaction, transaction.begin():
        for source, limit in [(f"ip:{address}", 100), (f"account:{address}:{email}", 10)]:
            key = hashlib.sha256(source.encode()).hexdigest()
            expired = LoginThrottle.window_start < now - timedelta(minutes=15)
            attempts = transaction.scalar(
                insert(LoginThrottle)
                .values(
                    key=key,
                    attempts=1,
                    window_start=now,
                )
                .on_conflict_do_update(
                    index_elements=[LoginThrottle.key],
                    set_={
                        "attempts": case((expired, 1), else_=LoginThrottle.attempts + 1),
                        "window_start": case((expired, now), else_=LoginThrottle.window_start),
                    },
                )
                .returning(LoginThrottle.attempts)
            )
            allowed &= attempts <= limit
    return allowed


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if not allow_attempt(email, request.remote_addr or "unknown"):
            return render_template("auth/login.html", form=form, throttle=True), 429
        user = db.session.scalar(select(User).where(User.email == email))
        valid = check_password_hash(user.password_hash if user else DUMMY_HASH, form.password.data)
        if user and user.active and valid:
            session.clear()
            login_user(user)
            session.permanent = True
            db.session.add(
                AuditLog(user_id=user.id, action="auth.login", detail="Inicio de sesión")
            )
            db.session.commit()
            return redirect(url_for("dashboard.index"))
        db.session.add(AuditLog(action="auth.failed", detail="Intento de acceso fallido"))
        db.session.commit()
        flash("Correo o contraseña incorrectos, o cuenta inactiva.", "danger")
    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/mi-cuenta", methods=["GET", "POST"])
@login_required
def password():
    form = PasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current.data):
            form.current.errors.append("La contraseña actual no es correcta.")
        else:
            current_user.set_password(form.password.data)
            db.session.add(
                AuditLog(
                    user_id=current_user.id, action="auth.password", detail="Cambio de contraseña"
                )
            )
            db.session.commit()
            logout_user()
            session.clear()
            flash(
                "Contraseña actualizada. Inicia sesión nuevamente con tu contraseña nueva.",
                "success",
            )
            return redirect(url_for("auth.login"))
    return render_template(
        "form.html",
        form=form,
        title="Mi cuenta",
        eyebrow="SEGURIDAD",
        description="Actualiza tu contraseña de acceso.",
    )
