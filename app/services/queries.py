from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select

from app.extensions import db
from app.models import Ingredient, Lot


def inventory_query():
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    eligible = (Lot.expires_on.is_(None)) | (Lot.expires_on >= today)
    balances = (
        select(
            Lot.ingredient_id,
            func.sum(Lot.remaining_quantity).label("physical"),
            func.sum(case((eligible, Lot.remaining_quantity), else_=0)).label("available"),
            func.sum(Lot.remaining_quantity * Lot.unit_cost).label("known_value"),
            func.sum(case((Lot.unit_cost.is_(None), Lot.remaining_quantity), else_=0)).label(
                "unknown"
            ),
        )
        .group_by(Lot.ingredient_id)
        .subquery()
    )
    return select(
        Ingredient,
        func.coalesce(balances.c.physical, Decimal("0")).label("physical"),
        func.coalesce(balances.c.available, Decimal("0")).label("available"),
        func.coalesce(balances.c.known_value, Decimal("0")).label("known_value"),
        func.coalesce(balances.c.unknown, Decimal("0")).label("unknown"),
    ).outerjoin(balances, Ingredient.id == balances.c.ingredient_id)


def ingredient_choices():
    return [(0, "Selecciona un ingrediente")] + [
        (i.id, f"{i.name} · {i.unit.symbol}")
        for i in db.session.scalars(
            select(Ingredient).where(Ingredient.active.is_(True)).order_by(Ingredient.name)
        )
    ]
