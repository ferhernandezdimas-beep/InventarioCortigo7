import uuid

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select
from werkzeug.datastructures import MultiDict
from wtforms.fields.choices import SelectChoice

from app.commerce_forms import CountForm, WasteForm
from app.commerce_models import InventoryCount
from app.delivery_models import ReceiptDraft
from app.extensions import db
from app.forms import IssueForm, ReceiptForm, ReverseForm
from app.models import Allocation, Ingredient, Lot, Movement, Operation, Presentation, Supplier
from app.permissions import can, permission_required
from app.services.adjustments import record_count, record_waste
from app.services.inventory import issue, receive, reverse_issue
from app.services.numbers import DomainError, decimal_value
from app.services.queries import ingredient_choices, inventory_query
from app.services.receipts import confirm_draft, discard_draft, reverse_receipt, save_draft

bp = Blueprint("inventory", __name__, url_prefix="/inventario")


@bp.get("/")
@permission_required("inventory.read")
def index():
    statement = inventory_query().order_by(Ingredient.name)
    search = request.args.get("q", "").strip()[:150]
    status = request.args.get("status", "")
    if search:
        statement = statement.where(Ingredient.name.ilike(f"%{search}%"))
    if status == "low":
        statement = statement.where(
            Ingredient.active.is_(True), statement.selected_columns.available <= Ingredient.minimum
        )
    elif status == "out":
        statement = statement.where(
            Ingredient.active.is_(True), statement.selected_columns.available == 0
        )
    page = max(1, request.args.get("page", 1, type=int))
    total = db.session.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.session.execute(statement.limit(30).offset((page - 1) * 30)).all()
    return render_template(
        "inventory/index.html", rows=rows, total=total, page=page, more=page * 30 < total
    )


@bp.route("/entradas/nueva", methods=["GET", "POST"])
@bp.route("/entradas/borradores/<uuid:draft_id>/editar", methods=["GET", "POST"])
@permission_required("inventory.write")
def receipt(draft_id=None):
    draft = db.get_or_404(ReceiptDraft, draft_id) if draft_id else None
    if draft and draft.user_id != current_user.id and not can("inventory.reverse"):
        abort(403)
    if draft and draft.status == "confirmed":
        return redirect(url_for("inventory.operation", operation_id=draft.operation_id))
    if draft and draft.status == "discarded":
        flash("Este borrador está descartado.", "warning")
        return redirect(url_for("inventory.drafts"))
    form = (
        ReceiptForm(formdata=MultiDict(draft.payload))
        if draft and request.method == "GET"
        else ReceiptForm()
    )
    if request.method == "GET":
        form.key.data = str(draft.id if draft else uuid.uuid4())
        form.revision.data = str(draft.revision if draft else 0)
    form.supplier_id.choices = [(0, "Sin proveedor registrado")] + [
        (s.id, s.name)
        for s in db.session.scalars(
            select(Supplier).where(Supplier.active.is_(True)).order_by(Supplier.name)
        )
    ]
    choices = ingredient_choices()
    presentations = [(0, "Capturar en unidad base")] + [
        SelectChoice(
            str(p.id),
            f"{i.name}: {p.name} ({p.base_quantity} {i.unit.symbol})",
            render_kw={"data-ingredient": str(i.id)},
        )
        for p, i in db.session.execute(
            select(Presentation, Ingredient)
            .join(Ingredient, Presentation.ingredient_id == Ingredient.id)
            .order_by(Ingredient.name, Presentation.name)
        )
    ]
    for line in form.lines:
        line.ingredient_id.choices = choices
        line.presentation_id.choices = presentations
    if request.method == "POST" and request.form.get("action") == "draft":
        try:
            saved = save_draft(
                user_id=current_user.id,
                key=form.key.data,
                payload=request.form.to_dict(),
                expected_revision=form.revision.data or 0,
            )
            flash("Borrador guardado. No se ha modificado el inventario.", "success")
            return redirect(url_for("inventory.receipt", draft_id=saved))
        except DomainError as exc:
            flash(str(exc), "danger")
    elif form.validate_on_submit():
        try:
            if draft:
                op_id = confirm_draft(
                    user_id=current_user.id,
                    draft_id=draft.id,
                    payload=request.form.to_dict(),
                    expected_revision=form.revision.data,
                )
            else:
                op_id = receive(
                    key=form.key.data,
                    user_id=current_user.id,
                    lines=[line.data for line in form.lines],
                    reason=form.reason.data,
                    supplier_id=form.supplier_id.data or None,
                    reference=(form.reference.data or "").strip() or None,
                )
            flash("Recepción confirmada. Se registraron los lotes y sus movimientos.", "success")
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    return render_template(
        "inventory/receipt.html", form=form, has_ingredients=len(choices) > 1, draft=draft
    )


@bp.route("/salidas/nueva", methods=["GET", "POST"])
@permission_required("inventory.write")
def withdrawal():
    form = IssueForm()
    if request.method == "GET":
        form.key.data = str(uuid.uuid4())
    form.ingredient_id.choices = ingredient_choices()
    if form.validate_on_submit():
        try:
            op_id = issue(
                key=form.key.data,
                user_id=current_user.id,
                lines=[dict(ingredient_id=form.ingredient_id.data, quantity=form.quantity.data)],
                reason=form.reason.data,
            )
            flash("Salida confirmada mediante PEPS.", "success")
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    return render_template(
        "inventory/issue.html",
        form=form,
        has_ingredients=len(form.ingredient_id.choices) > 1,
        title="Registrar salida",
        eyebrow="CONTROL DE ALMACÉN",
        description="Consumo manual en unidad base. PEPS asigna primero los lotes más antiguos y excluye los caducados. Toda la operación se confirma o se revierte.",
    )


@bp.get("/peps/<int:ingredient_id>")
@permission_required("inventory.write")
def preview(ingredient_id):
    from datetime import datetime
    from decimal import Decimal
    from zoneinfo import ZoneInfo

    try:
        pending = decimal_value(request.args.get("quantity", ""), positive=True)
    except DomainError as exc:
        return jsonify(error=str(exc)), 400
    ingredient = db.get_or_404(Ingredient, ingredient_id)
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    lots = db.session.scalars(
        select(Lot)
        .where(
            Lot.ingredient_id == ingredient_id,
            Lot.remaining_quantity > 0,
            (Lot.expires_on.is_(None)) | (Lot.expires_on >= today),
        )
        .order_by(Lot.received_at, Lot.id)
    ).all()
    allocations = []
    for lot in lots:
        if pending == Decimal("0"):
            break
        amount = min(pending, lot.remaining_quantity)
        pending -= amount
        allocations.append(
            dict(
                lot=lot.code or f"Lote #{lot.id}", quantity=str(amount), unit=ingredient.unit.symbol
            )
        )
    return jsonify(
        sufficient=pending == 0,
        allocations=allocations,
        note="Vista previa informativa. Al confirmar se bloquean los lotes y se valida de nuevo la disponibilidad.",
    )


@bp.get("/lotes")
@permission_required("inventory.read")
def lots():
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    from app.settings import expiry_days

    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    statement = select(Lot).order_by(Lot.received_at, Lot.id)
    search = request.args.get("q", "").strip()[:150]
    if search:
        statement = statement.join(Ingredient, Ingredient.id == Lot.ingredient_id).where(
            Ingredient.name.ilike(f"%{search}%")
        )
    status = request.args.get("status", "")
    if status == "expired":
        statement = statement.where(Lot.expires_on < today, Lot.remaining_quantity > 0)
    elif status == "soon":
        statement = statement.where(
            Lot.expires_on >= today,
            Lot.expires_on <= today + timedelta(days=expiry_days(db.session)),
            Lot.remaining_quantity > 0,
        )
    elif status == "active":
        statement = statement.where(Lot.remaining_quantity > 0)
    page = max(1, request.args.get("page", 1, type=int))
    total = db.session.scalar(select(func.count()).select_from(statement.subquery()))
    items = db.session.scalars(statement.offset((page - 1) * 30).limit(30)).all()
    return render_template(
        "inventory/lots.html", items=items, page=page, total=total, more=page * 30 < total
    )


@bp.get("/movimientos")
@permission_required("inventory.read")
def movements():
    page = max(1, request.args.get("page", 1, type=int))
    items = db.session.scalars(
        select(Movement).order_by(Movement.id.desc()).offset((page - 1) * 50).limit(51)
    ).all()
    return render_template(
        "inventory/movements.html", items=items[:50], more=len(items) > 50, page=page
    )


@bp.get("/operaciones/<uuid:operation_id>")
@permission_required("inventory.read")
def operation(operation_id):
    item = db.get_or_404(Operation, operation_id)
    rows = db.session.execute(
        select(Movement, Allocation, Lot)
        .join(Allocation, Allocation.movement_id == Movement.id)
        .join(Lot, Lot.id == Allocation.lot_id)
        .where(Movement.operation_id == item.id)
        .order_by(Movement.id, Lot.received_at, Lot.id)
    ).all()
    form = ReverseForm(key=str(uuid.uuid4()))
    reversed_by = db.session.scalar(select(Operation).where(Operation.reverses_id == item.id))
    return render_template(
        "inventory/operation.html",
        item=item,
        rows=rows,
        form=form,
        reversed_by=reversed_by,
        count=db.session.scalar(
            select(InventoryCount).where(InventoryCount.operation_id == item.id)
        ),
    )


@bp.post("/operaciones/<uuid:operation_id>/revertir")
@permission_required("inventory.reverse")
def reverse(operation_id):
    form = ReverseForm()
    if form.validate_on_submit():
        try:
            op_id = reverse_issue(
                key=form.key.data,
                user_id=current_user.id,
                operation_id=operation_id,
                reason=form.reason.data,
            )
            flash("Salida revertida con movimientos compensatorios.", "success")
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    else:
        flash("Captura un motivo válido para revertir la salida.", "danger")
    return redirect(url_for("inventory.operation", operation_id=operation_id))


@bp.route("/mermas/nueva", methods=["GET", "POST"])
@permission_required("inventory.waste")
def waste():
    form = WasteForm()
    if request.method == "GET":
        form.key.data = str(uuid.uuid4())
    form.ingredient_id.choices = ingredient_choices()
    if form.validate_on_submit():
        try:
            op_id = record_waste(
                key=form.key.data,
                user_id=current_user.id,
                ingredient_id=form.ingredient_id.data,
                quantity=form.quantity.data,
                category=form.category.data,
                reason=form.reason.data,
            )
            flash("Baja registrada con asignación de lotes y costo histórico.", "success")
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    return render_template(
        "inventory/control.html",
        form=form,
        mode="waste",
        rows=[],
        has_ingredients=len(form.ingredient_id.choices) > 1,
    )


@bp.route("/conteos", methods=["GET", "POST"])
@permission_required("inventory.adjust")
def counts():
    form = CountForm()
    if request.method == "GET":
        form.key.data = str(uuid.uuid4())
    form.ingredient_id.choices = ingredient_choices()
    if form.validate_on_submit():
        try:
            op_id = record_count(
                key=form.key.data,
                user_id=current_user.id,
                ingredient_id=form.ingredient_id.data,
                expected_quantity=form.expected_quantity.data,
                counted_quantity=form.counted_quantity.data,
                reason=form.reason.data,
            )
            flash("Conteo y diferencia registrados de manera atómica.", "success")
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    rows = db.session.execute(
        inventory_query().where(Ingredient.active.is_(True)).order_by(Ingredient.name)
    ).all()
    return render_template(
        "inventory/control.html",
        form=form,
        mode="count",
        rows=rows,
        has_ingredients=len(form.ingredient_id.choices) > 1,
    )


@bp.get("/entradas/borradores")
@permission_required("inventory.write")
def drafts():
    statement = select(ReceiptDraft).order_by(ReceiptDraft.updated_at.desc())
    if not can("inventory.reverse"):
        statement = statement.where(ReceiptDraft.user_id == current_user.id)
    items = db.session.scalars(statement.limit(100)).all()
    return render_template("inventory/drafts.html", items=items)


@bp.post("/entradas/borradores/<uuid:draft_id>/descartar")
@permission_required("inventory.write")
def discard(draft_id):
    try:
        discard_draft(user_id=current_user.id, draft_id=draft_id)
        flash("Borrador descartado; se conserva el historial.", "success")
    except DomainError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("inventory.drafts"))


@bp.post("/operaciones/<uuid:operation_id>/revertir-recepcion")
@permission_required("inventory.reverse")
def receipt_reverse(operation_id):
    form = ReverseForm()
    if form.validate_on_submit():
        try:
            op_id = reverse_receipt(
                key=form.key.data,
                user_id=current_user.id,
                operation_id=operation_id,
                reason=form.reason.data,
            )
            flash(
                "Recepción revertida con evidencia. Puedes registrar la entrada corregida.",
                "success",
            )
            return redirect(url_for("inventory.operation", operation_id=op_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    else:
        flash("Captura un motivo válido de corrección.", "danger")
    return redirect(url_for("inventory.operation", operation_id=operation_id))
