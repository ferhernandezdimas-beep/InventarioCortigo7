from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import text
from wtforms import IntegerField
from wtforms.validators import InputRequired, NumberRange

from app.delivery_models import SystemSettings
from app.extensions import db
from app.forms import SpanishForm
from app.models import AuditLog
from app.permissions import PERMISSIONS, ROLES, permission_required

bp = Blueprint("settings", __name__, url_prefix="/administracion")


def expiry_days(session):
    settings = session.get(SystemSettings, 1)
    return settings.expiry_alert_days if settings else current_app.config["EXPIRY_ALERT_DAYS"]


class SettingsForm(SpanishForm):
    expiry_alert_days = IntegerField(
        "Anticipación de alertas de caducidad · días",
        validators=[InputRequired(), NumberRange(min=1, max=90)],
    )


@bp.route("/configuracion", methods=["GET", "POST"])
@permission_required("settings")
def index():
    item = db.session.get(SystemSettings, 1)
    form = SettingsForm(
        obj=item, data=dict(expiry_alert_days=current_app.config["EXPIRY_ALERT_DAYS"])
    )
    if form.validate_on_submit():
        db.session.execute(text("SELECT pg_advisory_xact_lock(7003001)"))
        item = db.session.get(SystemSettings, 1) or SystemSettings(id=1)
        item.expiry_alert_days, item.updated_by = form.expiry_alert_days.data, current_user.id
        db.session.add(item)
        db.session.add(
            AuditLog(
                user_id=current_user.id,
                action="settings.update",
                detail=f"Alerta de caducidad: {item.expiry_alert_days} días",
            )
        )
        db.session.commit()
        flash("Configuración guardada.", "success")
        return redirect(url_for("settings.index"))
    return render_template("settings.html", form=form, permissions=PERMISSIONS, roles=ROLES)


@bp.get("/ayuda")
@login_required
def help():
    return render_template("help.html")
