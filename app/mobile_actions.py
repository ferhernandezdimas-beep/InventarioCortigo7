"""Reviewed catalog tools and exact web exports for native clients."""

import base64
import hashlib
import json
import uuid
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify
from flask_login import login_user
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import HTTPException
from werkzeug.http import parse_options_header

from app.extensions import csrf, db
from app.forms import CategoryForm, IngredientForm, PresentationForm, SupplierForm
from app.mobile import authenticated, body, database_error, failure, http_error
from app.mobile_models import MobileAction
from app.models import AuditLog, Category, Ingredient, Presentation, Supplier, Unit, User, utcnow
from app.permissions import PERMISSIONS
from app.services.numbers import DomainError, decimal_value

bp = Blueprint("mobile_actions", __name__, url_prefix="/api/mobile/v1")
csrf.exempt(bp)
bp.register_error_handler(SQLAlchemyError, database_error)
bp.register_error_handler(HTTPException, http_error)
TOOLS = {
    "catalog.ingredient.create": (
        IngredientForm,
        Ingredient,
        [
            "name",
            "code",
            "description",
            "category_id",
            "unit_id",
            "supplier_id",
            "minimum",
            "maximum",
            "reference_cost",
            "active",
        ],
    ),
    "catalog.category.create": (CategoryForm, Category, ["name"]),
    "catalog.supplier.create": (
        SupplierForm,
        Supplier,
        ["name", "legal_name", "contact", "phone", "email", "address", "notes", "active"],
    ),
    "catalog.presentation.create": (
        PresentationForm,
        Presentation,
        ["ingredient_id", "name", "base_quantity"],
    ),
}


@bp.after_request
def private(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/actions/<uuid:key>")
@authenticated()
def action_status(key):
    item = db.session.get(MobileAction, key)
    if not item or item.user_id != g.mobile_user.id:
        return failure("No hay una acción confirmada con esta referencia.", "not_found", 404)
    return jsonify(key=str(key), kind=item.kind, status="confirmed", **item.result)


@bp.post("/actions")
@authenticated("catalog.write")
def execute_action():
    try:
        payload = body()
        key = uuid.UUID(str(payload.get("key", "")))
        kind = payload.get("kind")
        if not isinstance(kind, str) or kind not in TOOLS:
            raise DomainError("Selecciona una herramienta de catálogo válida.")
        data = payload.get("data")
        form_type, model, fields = TOOLS[kind]
        if not isinstance(data, dict) or set(data) - set(fields):
            raise DomainError("La acción incluye campos desconocidos; no se ejecutó ningún cambio.")
        for name, value in data.items():
            if name in {"minimum", "maximum", "reference_cost", "base_quantity"} and value not in (
                None,
                "",
            ):
                if not isinstance(value, str):
                    raise DomainError("Las cantidades deben enviarse como texto decimal exacto.")
                decimal_value(value)
            elif name.endswith("_id"):
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise DomainError("Selecciona identificadores válidos del catálogo descargado.")
            elif name == "active":
                if not isinstance(value, bool):
                    raise DomainError("Revisa el estado activo.")
            elif value is not None and (not isinstance(value, str) or len(value) > 2000):
                raise DomainError("Revisa los campos de texto.")
        actor = db.session.scalar(
            select(User)
            .where(User.id == g.mobile_user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if not actor.active or "catalog.write" not in PERMISSIONS.get(actor.role, set()):
            db.session.rollback()
            return failure("Tu cuenta no puede modificar catálogos.", "forbidden", 403)
        digest = hashlib.sha256(
            json.dumps(
                dict(user=actor.id, kind=kind, data=data), sort_keys=True, ensure_ascii=False
            ).encode()
        ).hexdigest()
        inserted = db.session.scalar(
            insert(MobileAction)
            .values(
                key=key,
                user_id=actor.id,
                kind=kind,
                payload_hash=digest,
                result={},
                created_at=utcnow(),
            )
            .on_conflict_do_nothing(index_elements=[MobileAction.key])
            .returning(MobileAction.key)
        )
        record = db.session.get(MobileAction, key)
        if not inserted:
            if record.user_id != actor.id or record.payload_hash != digest:
                raise DomainError("La referencia corresponde a una acción distinta.")
            return jsonify(key=str(key), kind=kind, status="confirmed", **record.result)
        values = dict(data)
        if model is Ingredient:
            values.setdefault("minimum", "0")
            values.setdefault("supplier_id", 0)
            values.setdefault("active", True)
        elif model is Supplier:
            values.setdefault("active", True)
        formdata = MultiDict(
            {
                name: ("y" if value else "")
                if isinstance(value, bool)
                else str(value)
                if value is not None
                else ""
                for name, value in values.items()
            }
        )
        form = form_type(formdata=formdata, meta={"csrf": False})
        if model is Ingredient:
            form.category_id.choices = [
                (c.id, c.name) for c in db.session.scalars(select(Category).order_by(Category.name))
            ]
            form.unit_id.choices = [
                (u.id, u.symbol) for u in db.session.scalars(select(Unit).order_by(Unit.id))
            ]
            form.supplier_id.choices = [(0, "Sin proveedor")] + [
                (s.id, s.name)
                for s in db.session.scalars(select(Supplier).where(Supplier.active.is_(True)))
            ]
        elif model is Presentation:
            form.ingredient_id.choices = [
                (i.id, i.name)
                for i in db.session.scalars(select(Ingredient).where(Ingredient.active.is_(True)))
            ]
        if not form.validate():
            messages = [
                f"{getattr(form, name).label.text}: {' '.join(errors)}"
                for name, errors in form.errors.items()
            ]
            raise DomainError("\n".join(messages))
        item = model()
        for name in fields:
            value = getattr(form, name).data
            setattr(item, name, value.strip() or None if isinstance(value, str) else value)
        if model is Ingredient:
            item.supplier_id = item.supplier_id or None
            item.updated_by = actor.id
        db.session.add(item)
        db.session.flush()
        result = dict(id=str(item.id), name=item.name)
        record.result = result
        db.session.add(
            AuditLog(
                user_id=actor.id,
                action="assistant." + kind,
                detail=f"{item.id}: {item.name}; referencia {key}",
            )
        )
        db.session.commit()
        return jsonify(key=str(key), kind=kind, status="confirmed", **result)
    except (DomainError, ValueError, TypeError) as error:
        db.session.rollback()
        return failure(
            str(error)
            if isinstance(error, DomainError)
            else "Revisa la referencia y los datos de la acción.",
            "conflict",
            422,
        )
    except IntegrityError:
        db.session.rollback()
        return failure(
            "Ya existe un registro con ese nombre o código. No se duplicó el catálogo.",
            "conflict",
            422,
        )


EXPORT_ENDPOINTS = {
    "catalog.export_ingredients",
    "imports.template",
    "imports.errors",
    "reports.index",
    "reports.warehouse",
}


@bp.post("/documents")
@authenticated()
def export_document():
    try:
        data = body()
    except DomainError as error:
        return failure(str(error), "validation", 422)
    path = data.get("path")
    if not isinstance(path, str) or len(path) > 2000:
        return failure("La dirección del documento no es válida.", "validation", 400)
    parsed = urlsplit(path)
    if (
        parsed.scheme
        or parsed.netloc
        or not parsed.path.startswith("/")
        or path.startswith("//")
        or "\\" in path
    ):
        return failure("Solo se permiten documentos del restaurante.", "forbidden", 403)
    app = current_app._get_current_object()
    try:
        endpoint, _ = app.url_map.bind("localhost").match(parsed.path, method="GET")
    except HTTPException:
        return failure("El documento no existe.", "not_found", 404)
    if endpoint not in EXPORT_ENDPOINTS:
        return failure("Esta dirección no es una exportación permitida.", "forbidden", 403)
    actor_id = g.mobile_user.id
    # Execute the existing GET export, with its unchanged permission decorators,
    # in a separate request/app context. No cookies or internal headers are returned.
    with app.app_context(), app.test_request_context(path, method="GET"):
        actor = db.session.get(User, actor_id)
        if not actor or not actor.active:
            return failure("La cuenta está inactiva.", "unauthorized", 401)
        login_user(actor)
        response = app.full_dispatch_request()
        if response.status_code != 200:
            return failure(
                "No tienes permiso o los filtros no son válidos.", "forbidden", response.status_code
            )
        disposition, options = parse_options_header(response.headers.get("Content-Disposition", ""))
        if disposition != "attachment":
            return failure("Selecciona una exportación CSV o Excel.", "validation", 422)
        response.direct_passthrough = False
        content = response.get_data()
        if len(content) > 12 * 1024 * 1024:
            return failure(
                "Reduce los filtros para exportar un archivo más pequeño.", "too_large", 413
            )
        return jsonify(
            filename=options.get("filename", "reporte.bin"),
            mime=response.mimetype,
            content=base64.b64encode(content).decode(),
        )
