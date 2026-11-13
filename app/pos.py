import json
import uuid

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from app.commerce_forms import CancellationForm, SaleForm
from app.commerce_models import MenuItem, Sale
from app.extensions import db
from app.permissions import can, permission_required
from app.services.numbers import DomainError
from app.services.recipes import estimate_recipe, latest_recipe
from app.services.sales import cancel_sale, confirm_sale, quote_cart

bp = Blueprint("pos", __name__, url_prefix="/ventas")


@bp.route("/punto-de-venta", methods=["GET", "POST"])
@permission_required("sales.write")
def index():
    form = SaleForm()
    if request.method == "GET":
        form.key.data = str(uuid.uuid4())
    if form.validate_on_submit():
        try:
            lines = json.loads(form.cart.data)
            sale_id = confirm_sale(
                key=form.key.data,
                user_id=current_user.id,
                lines=lines,
                method=form.method.data,
                received=form.received.data,
                expected_total=form.expected_total.data,
            )
            flash("Venta confirmada. Los ingredientes se descontaron de forma atómica.", "success")
            return redirect(url_for("pos.detail", sale_id=sale_id))
        except (DomainError, ValueError, KeyError, TypeError) as exc:
            flash(
                str(exc)
                if isinstance(exc, DomainError)
                else "El carrito no es válido. Actualízalo e intenta de nuevo.",
                "danger",
            )
    items = db.session.scalars(
        select(MenuItem).where(MenuItem.active.is_(True)).order_by(MenuItem.category, MenuItem.name)
    ).all()
    items = [item for item in items if latest_recipe(db.session, item.id)]
    return render_template(
        "pos/index.html",
        form=form,
        items=items,
        categories=sorted({item.category for item in items}),
        availability={
            item.id: estimate_recipe(db.session, latest_recipe(db.session, item.id))["stock"]
            for item in items
        },
    )


@bp.post("/cotizar")
@permission_required("sales.write")
def quote():
    data = request.get_json(silent=True)
    try:
        quote = quote_cart(db.session, data["lines"])
    except (DomainError, KeyError, TypeError, ValueError) as exc:
        return jsonify(
            error=str(exc) if isinstance(exc, DomainError) else "El carrito no es válido."
        ), 400
    return jsonify(
        total=str(quote["total"]),
        rows=[
            dict(
                id=row["item"].id,
                name=row["item"].name,
                quantity=row["quantity"],
                unit_price=str(row["item"].price),
                subtotal=str(row["subtotal"]),
            )
            for row in quote["rows"]
        ],
    )


@bp.get("/")
@permission_required("sales.read")
def sales():
    page = max(1, request.args.get("page", 1, type=int))
    statement = select(Sale).order_by(Sale.created_at.desc())
    if not can("sales.cancel"):
        statement = statement.where(Sale.user_id == current_user.id)
    items = db.session.scalars(statement.offset((page - 1) * 30).limit(31)).all()
    return render_template("pos/sales.html", items=items[:30], page=page, more=len(items) > 30)


@bp.get("/<uuid:sale_id>")
@permission_required("sales.read")
def detail(sale_id):
    sale = db.get_or_404(Sale, sale_id)
    if not can("sales.cancel") and sale.user_id != current_user.id:
        abort(403)
    form = CancellationForm(key=str(uuid.uuid4()))
    return render_template("pos/detail.html", sale=sale, form=form)


@bp.post("/<uuid:sale_id>/cancelar")
@permission_required("sales.cancel")
def cancel(sale_id):
    form = CancellationForm()
    if form.validate_on_submit():
        try:
            cancel_sale(
                key=form.key.data,
                user_id=current_user.id,
                sale_id=sale_id,
                reason=form.reason.data,
                restock=form.restock.data,
            )
            flash("Cancelación interna registrada y auditada.", "success")
        except DomainError as exc:
            flash(str(exc), "danger")
    else:
        flash("Captura un motivo válido para cancelar.", "danger")
    return redirect(url_for("pos.detail", sale_id=sale_id))
