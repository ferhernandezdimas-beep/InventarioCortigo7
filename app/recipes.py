from decimal import Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.commerce_forms import RecipeForm
from app.commerce_models import MenuItem, RecipeVersion
from app.extensions import db
from app.models import Unit
from app.permissions import permission_required
from app.services.numbers import DomainError
from app.services.queries import ingredient_choices
from app.services.recipes import estimate_recipe, latest_recipe, save_recipe

bp = Blueprint("recipes", __name__, url_prefix="/operacion")


@bp.get("/platillos")
@permission_required("recipes.read")
def index():
    statement = select(MenuItem).order_by(MenuItem.name)
    search = request.args.get("q", "").strip()[:150]
    if search:
        statement = statement.where(MenuItem.name.ilike(f"%{search}%"))
    items = db.session.scalars(statement).all()
    rows = [(item, latest_recipe(db.session, item.id)) for item in items]
    return render_template("recipes/index.html", rows=rows)


@bp.route("/platillos/nuevo", methods=["GET", "POST"])
@bp.route("/platillos/<int:item_id>/editar", methods=["GET", "POST"])
@permission_required("recipes.write")
def edit(item_id=None):
    item = db.get_or_404(MenuItem, item_id) if item_id else None
    recipe = latest_recipe(db.session, item_id) if item_id else None
    initial = dict(yield_quantity=Decimal("1"), expected_version="0", active=True)
    if recipe:
        initial.update(
            yield_quantity=recipe.yield_quantity,
            expected_version=str(recipe.version),
            lines=[
                dict(
                    ingredient_id=line.ingredient_id,
                    quantity=line.quantity,
                    unit_id=line.ingredient.unit_id,
                )
                for line in recipe.lines
            ],
        )
    form = RecipeForm(obj=item, data=initial) if request.method == "GET" else RecipeForm()
    choices = ingredient_choices()
    units = [
        (unit.id, f"{unit.name} ({unit.symbol})")
        for unit in db.session.scalars(select(Unit).order_by(Unit.id))
    ]
    for line in form.lines:
        line.ingredient_id.choices = choices
        line.unit_id.choices = units
    if form.validate_on_submit():
        try:
            saved = save_recipe(
                user_id=current_user.id,
                item_id=item_id,
                data=form.data,
                lines=[line.data for line in form.lines],
                expected_version=form.expected_version.data or 0,
            )
            flash(
                "Receta guardada como una nueva versión. El historial anterior se conserva.",
                "success",
            )
            return redirect(url_for("recipes.detail", item_id=saved))
        except DomainError as exc:
            flash(str(exc), "danger")
        except IntegrityError:
            flash("Ya existe un platillo con ese nombre o código.", "danger")
    return render_template(
        "recipes/edit.html", form=form, item=item, recipe=recipe, has_ingredients=len(choices) > 1
    )


@bp.get("/platillos/<int:item_id>")
@permission_required("recipes.read")
def detail(item_id):
    item = db.get_or_404(MenuItem, item_id)
    versions = db.session.scalars(
        select(RecipeVersion)
        .where(RecipeVersion.menu_item_id == item.id)
        .order_by(RecipeVersion.version.desc())
    ).all()
    recipe = next(
        (
            version
            for version in versions
            if version.version == request.args.get("version", type=int)
        ),
        versions[0] if versions else None,
    )
    estimate = estimate_recipe(db.session, recipe)
    return render_template(
        "recipes/detail.html", item=item, recipe=recipe, versions=versions, estimate=estimate
    )
