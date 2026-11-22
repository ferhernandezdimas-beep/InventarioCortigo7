"""Native mobile API: bearer authentication, scoped snapshots, atomic commands.

Cookie sessions are deliberately not accepted. CSRF exemption applies only here;
all web forms retain Flask-WTF protection. Native clients need no CORS wildcard.
"""

import hashlib
import secrets
import uuid
from datetime import date, timedelta
from functools import wraps

from flask import Blueprint, g, jsonify, redirect, request, session
from flask_login import login_user
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash

from app.auth import DUMMY_HASH, allow_attempt
from app.commerce_models import MenuItem, RecipeVersion, Sale
from app.extensions import csrf, db
from app.mobile_models import MobileSession
from app.models import (
    AuditLog,
    Category,
    Lot,
    Operation,
    Presentation,
    Supplier,
    Unit,
    User,
    utcnow,
)
from app.permissions import PERMISSIONS, ROLES
from app.services.inventory import ConcurrencyError, issue, receive
from app.services.numbers import DomainError, decimal_value
from app.services.queries import inventory_query
from app.services.recipes import portion_quantity
from app.services.sales import confirm_sale
from app.settings import expiry_days

bp = Blueprint("mobile", __name__, url_prefix="/api/mobile/v1")
csrf.exempt(bp)


def failure(message, code, status):
    return jsonify(error=dict(message=message, code=code)), status


@bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.errorhandler(HTTPException)
def http_error(error):
    return failure("La solicitud no es válida.", "invalid_request", error.code)


@bp.errorhandler(SQLAlchemyError)
def database_error(error):
    db.session.rollback()
    return failure(
        "Servicio temporalmente ocupado. Conserva la referencia y reintenta.", "unavailable", 503
    )


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise DomainError("Envía un objeto JSON válido.")
    return data


def string(data, key, limit, *, required=True):
    value = data.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise DomainError(f"Revisa el campo {key}.")
    return value.strip()


def integer(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 2147483647:
        raise DomainError("El identificador no es válido.")
    return value


def profile(user):
    return dict(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        role_label=ROLES[user.role],
        permissions=sorted(PERMISSIONS.get(user.role, set())),
    )


def authenticated(permission=None):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            authorization = request.headers.get("Authorization", "")
            if not authorization and request.endpoint == "mobile.web_session":
                token = request.form.get("access_token", "")
                authorization = "Bearer " + token if token else ""
            if not authorization.startswith("Bearer ") or len(authorization) > 256:
                return failure("Inicia sesión con tu cuenta del restaurante.", "unauthorized", 401)
            digest = hashlib.sha256(authorization[7:].encode()).hexdigest()
            row = db.session.execute(
                select(MobileSession, User)
                .join(User, User.id == MobileSession.user_id)
                .where(MobileSession.token_hash == digest)
            ).first()
            if not row:
                return failure("La sesión ya no es válida.", "unauthorized", 401)
            device, user = row
            if (
                device.revoked_at
                or device.expires_at <= utcnow()
                or not user.active
                or device.auth_version != user.auth_version
            ):
                return failure(
                    "La sesión venció o fue revocada. Vuelve a iniciar sesión.", "unauthorized", 401
                )
            if permission and permission not in PERMISSIONS.get(user.role, set()):
                return failure("Tu cuenta no tiene permiso para esta operación.", "forbidden", 403)
            g.mobile_user, g.mobile_session = user, device
            return fn(*args, **kwargs)

        return wrapped

    return decorator


@bp.post("/auth/login")
def login():
    try:
        data = body()
        email = string(data, "email", 254).lower()
        password = data.get("password")
        if not isinstance(password, str) or not 1 <= len(password) <= 1024:
            raise DomainError("Captura tu contraseña.")
        device_name = string(data, "device_name", 100, required=False) or "Cortijo 7 móvil"
    except DomainError as error:
        return failure(str(error), "validation", 400)
    if not allow_attempt(email, request.remote_addr or "unknown"):
        return failure("Demasiados intentos. Espera 15 minutos.", "throttled", 429)
    user = db.session.scalar(select(User).where(User.email == email))
    valid = check_password_hash(user.password_hash if user else DUMMY_HASH, password)
    if not user or not user.active or not valid:
        db.session.add(
            AuditLog(action="mobile.auth.failed", detail="Intento de acceso móvil fallido")
        )
        db.session.commit()
        return failure("Correo o contraseña incorrectos, o cuenta inactiva.", "unauthorized", 401)
    token = secrets.token_urlsafe(48)
    now = utcnow()
    expires = now + timedelta(days=7)
    db.session.add(
        MobileSession(
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            user_id=user.id,
            auth_version=user.auth_version,
            device_name=device_name,
            created_at=now,
            expires_at=expires,
        )
    )
    db.session.add(AuditLog(user_id=user.id, action="mobile.auth.login", detail=device_name))
    result = dict(token=token, expires_at=expires.isoformat(), user=profile(user))
    db.session.commit()
    return jsonify(result)


@bp.get("/auth/me")
@authenticated()
def me():
    return jsonify(user=profile(g.mobile_user), expires_at=g.mobile_session.expires_at.isoformat())


@bp.post("/web-session")
@authenticated()
def web_session():
    """Native POST bootstrap: no tokens in URLs, HTML or JavaScript injection."""
    actor, device = g.mobile_user, g.mobile_session
    session.clear()
    login_user(actor)
    session.permanent = True
    session["mobile_device"] = device.token_hash
    return redirect("/", code=303)


@bp.post("/auth/logout")
@authenticated()
def logout():
    g.mobile_session.revoked_at = utcnow()
    db.session.add(
        AuditLog(
            user_id=g.mobile_user.id, action="mobile.auth.logout", detail="Cierre de sesión móvil"
        )
    )
    db.session.commit()
    return jsonify(ok=True)


def snapshot(session, user):
    permissions = PERMISSIONS.get(user.role, set())
    result = dict(
        schema_version=1,
        server_time=utcnow().isoformat(),
        user=profile(user),
        expiry_alert_days=expiry_days(session),
        ingredients=[],
        lots=[],
        suppliers=[],
        presentations=[],
        products=[],
        operations=[],
        sales=[],
        categories=[],
        units=[],
    )
    if "catalog.read" in permissions:
        result["categories"] = [
            dict(id=c.id, name=c.name)
            for c in session.scalars(select(Category).order_by(Category.name))
        ]
        result["units"] = [
            dict(id=u.id, name=u.name, symbol=u.symbol)
            for u in session.scalars(select(Unit).order_by(Unit.id))
        ]
    if "inventory.read" in permissions:
        for row in session.execute(inventory_query().order_by(text("ingredients.name"))):
            item = row.Ingredient
            if not item.active:
                continue
            result["ingredients"].append(
                dict(
                    id=item.id,
                    name=item.name,
                    code=item.code,
                    category=item.category.name,
                    unit=item.unit.symbol,
                    minimum=str(item.minimum),
                    maximum=None if item.maximum is None else str(item.maximum),
                    physical=str(row.physical),
                    available=str(row.available),
                    known_value=str(row.known_value),
                    unknown=str(row.unknown),
                    supplier_id=item.supplier_id,
                )
            )
        result["lots"] = [
            dict(
                id=lot.id,
                ingredient_id=lot.ingredient_id,
                code=lot.code,
                quantity=str(lot.remaining_quantity),
                received_at=lot.received_at.isoformat(),
                expires_on=None if lot.expires_on is None else lot.expires_on.isoformat(),
            )
            for lot in session.scalars(
                select(Lot).where(Lot.remaining_quantity > 0).order_by(Lot.received_at, Lot.id)
            )
        ]
        result["suppliers"] = [
            dict(id=s.id, name=s.name)
            for s in session.scalars(
                select(Supplier).where(Supplier.active.is_(True)).order_by(Supplier.name)
            )
        ]
        result["presentations"] = [
            dict(
                id=p.id,
                ingredient_id=p.ingredient_id,
                name=p.name,
                base_quantity=str(p.base_quantity),
            )
            for p in session.scalars(select(Presentation).order_by(Presentation.id))
        ]
        result["operations"] = [
            dict(
                id=str(op.id), kind=op.kind, reason=op.reason, created_at=op.created_at.isoformat()
            )
            for op in session.scalars(
                select(Operation).order_by(Operation.created_at.desc(), Operation.id).limit(100)
            )
        ]
    if "sales.write" in permissions or "recipes.read" in permissions:
        recipes = {}
        for recipe in session.scalars(
            select(RecipeVersion).order_by(RecipeVersion.menu_item_id, RecipeVersion.version)
        ):
            recipes[recipe.menu_item_id] = recipe
        for item in session.scalars(
            select(MenuItem)
            .where(MenuItem.active.is_(True))
            .order_by(MenuItem.category, MenuItem.name)
        ):
            recipe = recipes.get(item.id)
            if not recipe or not recipe.lines:
                continue
            product = dict(
                id=item.id,
                name=item.name,
                category=item.category,
                price=str(item.price),
                code=item.code,
                recipe_version=recipe.version,
                requirements=[],
            )
            if "recipes.read" in permissions:
                product["requirements"] = [
                    dict(
                        ingredient_id=line.ingredient_id,
                        quantity=str(portion_quantity(line.quantity, recipe.yield_quantity)),
                    )
                    for line in recipe.lines
                ]
            result["products"].append(product)
    if "sales.read" in permissions:
        statement = select(Sale).order_by(Sale.created_at.desc(), Sale.id).limit(100)
        if "sales.cancel" not in permissions:
            statement = statement.where(Sale.user_id == user.id)
        result["sales"] = [
            dict(
                id=str(s.id),
                total=str(s.total),
                method=s.method,
                created_at=s.created_at.isoformat(),
                cancelled=s.cancellation is not None,
                items=[
                    dict(name=i.name, quantity=i.quantity, unit_price=str(i.unit_price))
                    for i in s.items
                ],
            )
            for s in session.scalars(statement).unique()
        ]
    return result


@bp.get("/snapshot")
@authenticated()
def download_snapshot():
    # A complete snapshot is replaced on the device only after the response is saved.
    with Session(db.engine) as session, session.begin():
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        user = session.get(User, g.mobile_user.id)
        return jsonify(snapshot(session, user))


@bp.get("/operations/<uuid:key>")
@authenticated()
def operation_status(key):
    # Recover an acknowledgement even if the role changed after the original commit.
    operation = db.session.scalar(
        select(Operation).where(
            Operation.idempotency_key == key, Operation.user_id == g.mobile_user.id
        )
    )
    if not operation:
        return failure("Aún no hay una operación confirmada con esta referencia.", "not_found", 404)
    result_id = operation.id
    if operation.kind == "sale":
        result_id = db.session.scalar(select(Sale.id).where(Sale.operation_id == operation.id))
    return jsonify(key=str(key), kind=operation.kind, id=str(result_id), status="confirmed")


@bp.post("/operations")
@authenticated()
def sync_operation():
    try:
        data = body()
        kind = string(data, "kind", 20)
        permission = "sales.write" if kind == "sale" else "inventory.write"
        if permission not in PERMISSIONS.get(g.mobile_user.role, set()):
            return failure("No tienes permiso para esta operación.", "forbidden", 403)
        key = str(uuid.UUID(string(data, "key", 36)))
        lines = data.get("lines")
        if not isinstance(lines, list) or not 1 <= len(lines) <= (60 if kind == "sale" else 100):
            raise DomainError("Agrega renglones válidos a la operación.")
        normalized = []
        for line in lines:
            if not isinstance(line, dict):
                raise DomainError("Uno de los renglones no es válido.")
            id_field = "menu_item_id" if kind == "sale" else "ingredient_id"
            iid = integer(line.get(id_field))
            quantity = string(line, "quantity", 30)
            decimal_value(quantity, positive=True)
            entry = {id_field: iid, "quantity": quantity}
            if kind == "receipt":
                cost = string(line, "unit_cost", 30, required=False)
                entry.update(
                    unit_cost=cost or None, code=string(line, "code", 100, required=False) or None
                )
                expires = string(line, "expires_on", 10, required=False)
                entry["expires_on"] = date.fromisoformat(expires) if expires else None
                pid = line.get("presentation_id")
                entry["presentation_id"] = integer(pid) if pid else 0
            normalized.append(entry)
        if kind == "sale":
            versions = data.get("expected_recipes")
            if not isinstance(versions, dict) or set(versions) != {
                str(line["menu_item_id"]) for line in normalized
            }:
                raise DomainError("Actualiza el catálogo de recetas antes de vender.")
            for value in versions.values():
                integer(value)
            result_id = confirm_sale(
                key=key,
                user_id=g.mobile_user.id,
                lines=normalized,
                method=string(data, "method", 20),
                received=string(data, "received", 30, required=False),
                expected_total=string(data, "expected_total", 30),
                expected_recipes=versions,
            )
        elif kind == "receipt":
            sid = data.get("supplier_id")
            result_id = receive(
                key=key,
                user_id=g.mobile_user.id,
                lines=normalized,
                reason=string(data, "reason", 300),
                supplier_id=integer(sid) if sid else None,
                reference=string(data, "reference", 100, required=False) or None,
            )
        elif kind == "issue":
            result_id = issue(
                key=key,
                user_id=g.mobile_user.id,
                lines=normalized,
                reason=string(data, "reason", 300),
            )
        else:
            raise DomainError("El tipo de operación no está disponible en móvil.")
        return jsonify(key=key, kind=kind, id=str(result_id), status="confirmed")
    except ConcurrencyError as error:
        return failure(str(error), "busy", 409)
    except (DomainError, ValueError, TypeError, KeyError) as error:
        if (
            isinstance(error, DomainError)
            and str(error) == "No tienes permiso para esta operación."
        ):
            return failure(str(error), "forbidden", 403)
        return failure(
            str(error) if isinstance(error, DomainError) else "Revisa los campos de la operación.",
            "conflict",
            422,
        )
