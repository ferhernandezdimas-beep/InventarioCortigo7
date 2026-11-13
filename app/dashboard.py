from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import Blueprint, render_template
from flask_login import current_user
from sqlalchemy import case, func, select

from app.commerce_models import Sale, SaleCancellation
from app.extensions import db
from app.models import Lot, Movement, Operation
from app.permissions import can, permission_required
from app.services.queries import inventory_query
from app.settings import expiry_days

bp = Blueprint("dashboard", __name__)


@bp.get("/")
@permission_required("dashboard")
def index():
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    sale_date = func.date(func.timezone("America/Mexico_City", Sale.created_at))
    sales_query = (
        select(Sale)
        .outerjoin(SaleCancellation, SaleCancellation.sale_id == Sale.id)
        .where(sale_date == today, SaleCancellation.id.is_(None))
    )
    if not can("sales.cancel"):
        sales_query = sales_query.where(Sale.user_id == current_user.id)
    sales_today = db.session.scalars(sales_query).all() if can("sales.read") else []
    sales_total = sum((sale.total for sale in sales_today), Decimal("0"))
    if not can("inventory.read"):
        return render_template(
            "dashboard.html", restricted=True, sales_total=sales_total, sales_count=len(sales_today)
        )
    rows = db.session.execute(inventory_query()).all()
    active = [r for r in rows if r.Ingredient.active]
    low = [r for r in active if r.available <= r.Ingredient.minimum]
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    expiring = db.session.scalar(
        select(func.count(Lot.id)).where(
            Lot.remaining_quantity > 0,
            Lot.expires_on >= today,
            Lot.expires_on <= today + timedelta(days=expiry_days(db.session)),
        )
    )
    recent = db.session.scalars(
        select(Operation).order_by(Operation.created_at.desc()).limit(6)
    ).all()
    start = today - timedelta(days=6)
    local_date = func.date(func.timezone("America/Mexico_City", Operation.created_at))
    counts = dict(
        db.session.execute(
            select(local_date, func.count()).where(local_date >= start).group_by(local_date)
        ).all()
    )
    chart = {
        "labels": [(start + timedelta(days=i)).strftime("%d/%m") for i in range(7)],
        "values": [counts.get(start + timedelta(days=i), 0) for i in range(7)],
    }
    consumed = db.session.scalar(
        select(
            func.coalesce(
                func.sum(case((Movement.quantity < 0, Movement.cost), else_=-Movement.cost)), 0
            )
        )
        .join(Operation)
        .where(
            Operation.kind.in_(["issue", "sale", "waste", "reversal", "sale_cancel"]),
            local_date == today,
        )
    )
    return render_template(
        "dashboard.html",
        active=active,
        low=low,
        expiring=expiring,
        expiry_days=expiry_days(db.session),
        value=sum((r.known_value for r in active), Decimal("0")),
        unknown=sum(r.unknown > 0 for r in active),
        recent=recent,
        chart=chart,
        consumed=consumed,
        sales_total=sales_total,
        sales_count=len(sales_today),
    )
