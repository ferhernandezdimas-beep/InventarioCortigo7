from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select

from app.commerce_models import MenuItem, RecipeIngredient, RecipeVersion
from app.models import AuditLog, Lot, Unit
from app.services.inventory import _authorize, _lock_ingredients, _run
from app.services.numbers import DomainError, convert, cost_value, decimal_value


def pesos(value):
    amount = decimal_value(value)
    if amount < 0 or amount.as_tuple().exponent < -2:
        raise DomainError("El importe debe ser positivo o cero y tener como máximo dos decimales.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def portion_quantity(quantity, portions, count=1):
    result = (quantity * count / portions).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    return decimal_value(result, positive=True)


def save_recipe(*, user_id, item_id, data, lines, expected_version=0):
    if not lines or len(lines) > 60:
        raise DomainError("Agrega entre 1 y 60 ingredientes a la receta.")
    name, category = data["name"].strip(), data["category"].strip()
    if not name or len(name) > 150 or not category or len(category) > 80:
        raise DomainError("Captura el nombre y la categoría del platillo.")
    portions = decimal_value(data["yield_quantity"], positive=True)
    price = pesos(data["price"])
    if data["kind"] not in {"prepared", "direct"}:
        raise DomainError("Tipo de producto inválido.")
    ids = [int(line["ingredient_id"]) for line in lines]
    if len(ids) != len(set(ids)):
        raise DomainError(
            "Combina las cantidades repetidas del mismo ingrediente en un solo renglón."
        )
    if data["kind"] == "direct" and (len(lines) != 1 or portions != 1):
        raise DomainError("Un producto directo utiliza un ingrediente y rendimiento de una unidad.")

    def command(session):
        _authorize(session, user_id, "recipes.write")
        if item_id:
            item = session.scalar(select(MenuItem).where(MenuItem.id == item_id).with_for_update())
            if not item:
                raise DomainError("El platillo ya no existe.")
        else:
            item = MenuItem()
            session.add(item)
        if item_id:
            current = (
                session.scalar(
                    select(func.max(RecipeVersion.version)).where(
                        RecipeVersion.menu_item_id == item_id
                    )
                )
                or 0
            )
            if int(expected_version) != current:
                raise DomainError(
                    "La receta cambió mientras la editabas. Recarga y revisa la versión más reciente."
                )
        else:
            current = 0
        for field in ["name", "category", "description", "code", "kind", "active"]:
            value = data.get(field)
            setattr(item, field, (value.strip() or None) if isinstance(value, str) else value)
        item.price, item.updated_by = price, user_id
        # Do not autoflush a new item until required attributes have been assigned.
        session.flush()
        ingredients = {i.id: i for i in _lock_ingredients(session, ids)}
        recipe = RecipeVersion(
            menu_item_id=item.id,
            version=current + 1,
            yield_quantity=portions,
            notes=(data.get("notes") or "").strip() or None,
            user_id=user_id,
        )
        session.add(recipe)
        session.flush()
        for line in lines:
            ingredient = ingredients[int(line["ingredient_id"])]
            unit = session.get(Unit, int(line["unit_id"]))
            if not unit:
                raise DomainError("La unidad seleccionada no existe.")
            amount = convert(line["quantity"], unit, ingredient.unit)
            portion_quantity(amount, portions)
            session.add(
                RecipeIngredient(
                    recipe_version_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=amount,
                    unit_symbol=ingredient.unit.symbol,
                )
            )
        session.add(
            AuditLog(
                user_id=user_id,
                action="recipe.version",
                detail=f"Platillo {item.id}, versión {recipe.version}",
            )
        )
        return item.id

    return _run(command)


def latest_recipe(session, item_id):
    return session.scalar(
        select(RecipeVersion)
        .where(RecipeVersion.menu_item_id == item_id)
        .order_by(RecipeVersion.version.desc())
        .limit(1)
    )


def estimate_recipe(session, recipe):
    """Cost one portion against the next eligible FIFO lots, without reserving stock."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    total, complete, stock = Decimal("0"), True, True
    rows = []
    if recipe is None:
        return dict(total=None, known=total, complete=False, stock=False, rows=[])
    for line in recipe.lines:
        required = portion_quantity(line.quantity, recipe.yield_quantity)
        pending, known, unknown = required, Decimal("0"), False
        lots = session.scalars(
            select(Lot)
            .where(
                Lot.ingredient_id == line.ingredient_id,
                Lot.remaining_quantity > 0,
                (Lot.expires_on.is_(None)) | (Lot.expires_on >= today),
            )
            .order_by(Lot.received_at, Lot.id)
        ).all()
        for lot in lots:
            if not pending:
                break
            amount = min(pending, lot.remaining_quantity)
            pending -= amount
            if lot.unit_cost is None:
                unknown = True
            else:
                known += amount * lot.unit_cost
        ready = pending == 0 and line.ingredient.active
        reliable = ready and not unknown
        stock &= ready
        complete &= reliable
        total += known
        rows.append(
            dict(
                line=line,
                quantity=required,
                cost=cost_value(known) if reliable else None,
                ready=ready,
            )
        )
    return dict(
        total=cost_value(total) if complete else None,
        known=cost_value(total),
        complete=complete,
        stock=stock,
        rows=rows,
    )
