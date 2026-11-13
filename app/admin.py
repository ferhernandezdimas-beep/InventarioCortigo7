from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import select, text

from app.catalog import _commit, _save
from app.extensions import db
from app.forms import UserForm
from app.models import AuditLog, User
from app.permissions import permission_required

bp = Blueprint("admin", __name__, url_prefix="/administracion")


@bp.get("/usuarios")
@permission_required("users")
def users():
    items = db.session.scalars(select(User).order_by(User.name)).all()
    return render_template("admin/users.html", items=items)


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@bp.route("/usuarios/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("users")
def user_form(item_id=None):
    item = db.get_or_404(User, item_id) if item_id else User(active=True, role="warehouse")
    form = UserForm(obj=item)
    if form.validate_on_submit():
        # Serialize role changes so two admins cannot disable each other concurrently.
        db.session.execute(text("SELECT pg_advisory_xact_lock(7001001)"))
        actor = db.session.scalar(
            select(User).where(User.id == current_user.id).execution_options(populate_existing=True)
        )
        if not actor.active or actor.role != "admin":
            abort(403)
        if not item_id and not form.password.data:
            form.password.errors.append("La contraseña es obligatoria para una cuenta nueva.")
        elif item_id == current_user.id and (not form.active.data or form.role.data != "admin"):
            form.active.errors.append("Conserva tu cuenta activa y con rol de administrador.")
        else:
            _save(item, form, ["name", "email", "role", "active"])
            item.email = item.email.lower()
            if form.password.data:
                item.set_password(form.password.data)
            if _commit(
                "user.save", f"Cuenta: {item.email}; rol: {item.role}; activa: {item.active}"
            ):
                return redirect(url_for("admin.users"))
    return render_template(
        "form.html",
        form=form,
        title="Editar usuario" if item_id else "Nuevo usuario",
        eyebrow="ADMINISTRACIÓN",
        description="Los permisos se aplican en el servidor según el rol asignado.",
    )


@bp.get("/auditoria")
@permission_required("audit")
def audit():
    rows = db.session.execute(
        select(AuditLog, User.name)
        .outerjoin(User, User.id == AuditLog.user_id)
        .order_by(AuditLog.id.desc())
        .limit(200)
    ).all()
    return render_template("admin/audit.html", rows=rows)
