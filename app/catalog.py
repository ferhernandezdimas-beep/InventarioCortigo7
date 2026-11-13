import csv
import io
from decimal import Decimal

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.commerce_models import RecipeIngredient
from app.extensions import db
from app.forms import CategoryForm, IngredientForm, PresentationForm, SupplierForm
from app.models import AuditLog, Category, Ingredient, Lot, Movement, Presentation, Supplier, Unit
from app.permissions import permission_required
from app.services.queries import ingredient_choices, inventory_query

bp = Blueprint("catalog", __name__, url_prefix="/catalogos")


def _save(target, form, fields):
    for field in fields:
        value = getattr(form, field).data
        setattr(target, field, value.strip() or None if isinstance(value, str) else value)
    db.session.add(target)


def _commit(action, detail):
    db.session.add(AuditLog(user_id=current_user.id, action=action, detail=detail))
    try:
        db.session.commit()
        flash("Cambios guardados correctamente.", "success")
        return True
    except IntegrityError:
        db.session.rollback()
        flash("Ya existe un registro con ese nombre o código. Revisa los datos.", "danger")
        return False


def _ingredients_query():
    stmt = inventory_query()
    search = request.args.get("q", "").strip()[:150]
    if search:
        supplier_ids = select(Supplier.id).where(Supplier.name.ilike(f"%{search}%", escape="\\"))
        stmt = stmt.where(
            Ingredient.name.ilike(f"%{search}%")
            | Ingredient.code.ilike(f"%{search}%")
            | Ingredient.supplier_id.in_(supplier_ids)
        )
    if request.args.get("category", "").isdigit():
        stmt = stmt.where(Ingredient.category_id == int(request.args["category"]))
    if request.args.get("status") == "active":
        stmt = stmt.where(Ingredient.active.is_(True))
    elif request.args.get("status") == "inactive":
        stmt = stmt.where(Ingredient.active.is_(False))
    return stmt.order_by(Ingredient.name)


@bp.get("/ingredientes")
@permission_required("catalog.read")
def ingredients():
    page = max(1, request.args.get("page", 1, type=int))
    stmt = _ingredients_query()
    total = db.session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.session.execute(stmt.limit(25).offset((page - 1) * 25)).all()
    return render_template(
        "catalog/ingredients.html",
        rows=rows,
        page=page,
        total=total,
        categories=db.session.scalars(select(Category).order_by(Category.name)).all(),
    )


@bp.get("/ingredientes/exportar")
@permission_required("catalog.read")
def export_ingredients():
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(
        ["Ingrediente", "Código", "Categoría", "Disponible", "Unidad", "Mínimo", "Activo"]
    )

    def safe(value):
        text = str(value)
        return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text

    for row in db.session.execute(_ingredients_query()):
        i = row.Ingredient
        writer.writerow(
            [
                safe(i.name),
                safe(i.code or ""),
                safe(i.category.name),
                row.available,
                i.unit.symbol,
                i.minimum,
                "Sí" if i.active else "No",
            ]
        )
    return Response(
        "\ufeff" + stream.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=ingredientes.csv"},
    )


@bp.route("/ingredientes/nuevo", methods=["GET", "POST"])
@bp.route("/ingredientes/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("catalog.write")
def ingredient_form(item_id=None):
    item = (
        db.get_or_404(Ingredient, item_id)
        if item_id
        else Ingredient(minimum=Decimal("0"), active=True)
    )
    form = IngredientForm(obj=item)
    form.category_id.choices = [
        (c.id, c.name) for c in db.session.scalars(select(Category).order_by(Category.name))
    ]
    form.unit_id.choices = [
        (u.id, f"{u.name} ({u.symbol})") for u in db.session.scalars(select(Unit).order_by(Unit.id))
    ]
    form.supplier_id.choices = [(0, "Sin proveedor principal")] + [
        (s.id, s.name)
        for s in db.session.scalars(
            select(Supplier)
            .where(Supplier.active.is_(True) | (Supplier.id == item.supplier_id))
            .order_by(Supplier.name)
        )
    ]
    if form.validate_on_submit():
        if item_id:
            item = db.session.scalar(
                select(Ingredient)
                .where(Ingredient.id == item_id)
                .with_for_update(of=Ingredient)
                .execution_options(populate_existing=True)
            )
        has_history = item_id and db.session.scalar(
            select(Lot.id).where(Lot.ingredient_id == item_id).limit(1)
        )
        has_history = has_history or (
            item_id
            and db.session.scalar(
                select(RecipeIngredient.id)
                .where(RecipeIngredient.ingredient_id == item_id)
                .limit(1)
            )
        )
        if has_history and form.unit_id.data != item.unit_id:
            form.unit_id.errors.append(
                "La unidad base no puede cambiar después de registrar movimientos o recetas."
            )
        else:
            _save(
                item,
                form,
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
            )
            item.supplier_id = item.supplier_id or None
            item.updated_by = current_user.id
            if _commit("ingredient.save", f"Ingrediente: {item.name}"):
                return redirect(url_for("catalog.ingredients"))
    return render_template(
        "form.html",
        form=form,
        title="Editar ingrediente" if item_id else "Nuevo ingrediente",
        eyebrow="CATÁLOGO DE INSUMOS",
        description="Define la unidad base y los niveles de control. Las existencias se obtienen de los lotes; nunca se editan aquí.",
    )


@bp.get("/ingredientes/<int:item_id>")
@permission_required("catalog.read")
def ingredient_detail(item_id):
    item = db.get_or_404(Ingredient, item_id)
    lots = db.session.scalars(
        select(Lot).where(Lot.ingredient_id == item_id).order_by(Lot.received_at, Lot.id)
    ).all()
    movements = db.session.scalars(
        select(Movement)
        .where(Movement.ingredient_id == item_id)
        .order_by(Movement.id.desc())
        .limit(100)
    ).all()
    return render_template("catalog/detail.html", item=item, lots=lots, movements=movements)


@bp.route("/categorias", methods=["GET", "POST"])
@bp.route("/categorias/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("catalog.write")
def categories(item_id=None):
    item = db.get_or_404(Category, item_id) if item_id else Category()
    form = CategoryForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data.strip()
        db.session.add(item)
        if _commit("category.save", form.name.data.strip()):
            return redirect(url_for("catalog.categories"))
    items = db.session.execute(
        select(Category, func.count(Ingredient.id))
        .outerjoin(Ingredient, Ingredient.category_id == Category.id)
        .group_by(Category.id)
        .order_by(Category.name)
    ).all()
    rows = [(category.name, count) for category, count in items]
    return render_template(
        "catalog/workbench.html",
        title="Categorías",
        description="Organiza los insumos según la operación de tu almacén.",
        form=form,
        headers=["Categoría", "Ingredientes"],
        rows=rows,
        edit_links=[
            url_for("catalog.categories", item_id=category.id) for category, count in items
        ],
        editing=bool(item_id),
        list_url=url_for("catalog.categories"),
        kind="categories",
        ready=True,
    )


@bp.get("/proveedores")
@permission_required("catalog.read")
def suppliers():
    items = db.session.scalars(select(Supplier).order_by(Supplier.name)).all()
    return render_template("catalog/suppliers.html", items=items)


@bp.route("/proveedores/nuevo", methods=["GET", "POST"])
@bp.route("/proveedores/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("catalog.write")
def supplier_form(item_id=None):
    item = db.get_or_404(Supplier, item_id) if item_id else Supplier(active=True)
    form = SupplierForm(obj=item)
    if form.validate_on_submit():
        _save(
            item,
            form,
            ["name", "legal_name", "contact", "phone", "email", "address", "notes", "active"],
        )
        if _commit("supplier.save", f"Proveedor: {item.name}"):
            return redirect(url_for("catalog.suppliers"))
    return render_template(
        "form.html",
        form=form,
        title="Editar proveedor" if item_id else "Nuevo proveedor",
        eyebrow="RELACIONES COMERCIALES",
        description="Solo el nombre comercial es obligatorio. Completa los demás datos cuando los tengas disponibles.",
    )


@bp.get("/unidades")
@permission_required("catalog.read")
def units():
    labels = {"mass": "Masa", "volume": "Volumen", "count": "Conteo"}
    rows = [
        (u.name, u.symbol, labels[u.dimension], u.factor)
        for u in db.session.scalars(select(Unit).order_by(Unit.id))
    ]
    return render_template(
        "catalog/simple.html",
        title="Unidades de medida",
        description="Conversiones exactas dentro de la misma dimensión. Las equivalencias por presentación son explícitas.",
        headers=["Unidad", "Símbolo", "Dimensión", "Factor base"],
        rows=rows,
    )


@bp.route("/presentaciones", methods=["GET", "POST"])
@bp.route("/presentaciones/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("catalog.write")
def presentations(item_id=None):
    item = db.get_or_404(Presentation, item_id) if item_id else Presentation()
    form = PresentationForm(obj=item)
    form.ingredient_id.choices = ingredient_choices()
    if form.validate_on_submit():
        _save(item, form, ["ingredient_id", "name", "base_quantity"])
        if _commit("presentation.create", form.name.data.strip()):
            return redirect(url_for("catalog.presentations"))
    items = db.session.execute(
        select(Presentation, Ingredient.name, Unit.symbol)
        .join(Ingredient, Presentation.ingredient_id == Ingredient.id)
        .join(Unit, Ingredient.unit_id == Unit.id)
        .order_by(Ingredient.name)
    ).all()
    rows = [
        (presentation.name, name, presentation.base_quantity, symbol)
        for presentation, name, symbol in items
    ]
    return render_template(
        "catalog/workbench.html",
        title="Presentaciones de compra",
        description="Define cuántas unidades base contiene cada empaque; por ejemplo, una botella de 1 L equivale a 1,000 ml.",
        form=form,
        headers=["Presentación", "Ingrediente", "Contenido base", "Unidad"],
        rows=rows,
        edit_links=[
            url_for("catalog.presentations", item_id=presentation.id)
            for presentation, name, symbol in items
        ],
        editing=bool(item_id),
        list_url=url_for("catalog.presentations"),
        kind="presentations",
        ready=len(form.ingredient_id.choices) > 1,
    )


@bp.get("/proveedores/<int:item_id>")
@permission_required("catalog.read")
def supplier_detail(item_id):
    from app.models import Operation

    item = db.get_or_404(Supplier, item_id)
    operations = db.session.scalars(
        select(Operation)
        .where(Operation.supplier_id == item_id)
        .order_by(Operation.created_at.desc())
        .limit(100)
    ).all()
    return render_template("catalog/supplier_detail.html", item=item, operations=operations)
