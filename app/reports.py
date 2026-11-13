from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, flash, render_template, request
from sqlalchemy import case, func, select
from sqlalchemy.orm import lazyload

from app.commerce_models import Sale, SaleCancellation
from app.extensions import db
from app.models import Movement, Operation
from app.permissions import permission_required
from app.services.numbers import DomainError
from app.services.reporting import MAX_EXPORT, REPORTS, export_response, warehouse_report
from app.settings import expiry_days

bp = Blueprint("reports", __name__, url_prefix="/reportes")


def period():
    zone = ZoneInfo("America/Mexico_City")
    today = datetime.now(zone).date()
    try:
        start = datetime.strptime(
            request.args.get("start", today.replace(day=1).isoformat()), "%Y-%m-%d"
        ).date()
        end = datetime.strptime(request.args.get("end", today.isoformat()), "%Y-%m-%d").date()
        if end < start or (end - start).days > 366 or start.year < 1900 or end.year > 2100:
            raise ValueError()
    except ValueError:
        flash("Selecciona un periodo válido de hasta 366 días.", "danger")
        start, end = today.replace(day=1), today
    return (
        start,
        end,
        datetime.combine(start, time.min, tzinfo=zone),
        datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone),
    )


@bp.get("/")
@permission_required("reports")
def index():
    start, end, since, until = period()
    base = select(Sale).where(Sale.created_at >= since, Sale.created_at < until)
    total_rows = db.session.scalar(select(func.count()).select_from(base.subquery()))
    page = max(1, request.args.get("page", 1, type=int))
    valid = SaleCancellation.id.is_(None)
    totals = db.session.execute(
        select(
            func.coalesce(func.sum(case((valid, Sale.total), else_=0)), 0).label("total"),
            func.coalesce(func.sum(case((valid, Sale.cost), else_=0)), 0).label("known"),
            func.count(case((valid, 1))).label("confirmed"),
            func.count(case((valid & Sale.cost.is_(None), 1))).label("unknown"),
        )
        .outerjoin(SaleCancellation, SaleCancellation.sale_id == Sale.id)
        .where(Sale.created_at >= since, Sale.created_at < until)
    ).one()
    waste = db.session.scalar(
        select(func.coalesce(func.sum(Movement.cost), 0))
        .join(Operation)
        .where(
            Operation.kind == "waste", Operation.created_at >= since, Operation.created_at < until
        )
    )
    format = request.args.get("format")
    if format in {"csv", "xlsx"}:
        if total_rows > MAX_EXPORT:
            return render_template(
                "error.html",
                code=400,
                message="Reduce el periodo para exportar hasta 10,000 ventas.",
            ), 400
        sales = db.session.scalars(
            base.options(lazyload(Sale.items)).order_by(Sale.created_at.desc())
        ).all()
        labels = {"cash": "Efectivo", "card": "Tarjeta", "transfer": "Transferencia"}
        rows = [
            [
                str(sale.id),
                sale.created_at.astimezone(ZoneInfo("America/Mexico_City")).strftime(
                    "%d/%m/%Y %H:%M"
                ),
                "Cancelada" if sale.cancellation else "Confirmada",
                labels[sale.method],
                sale.total,
                sale.cost if sale.cost is not None else "Pendiente",
            ]
            for sale in sales
        ]
        return export_response(
            ["Folio", "Fecha local", "Estado", "Método", "Total MXN", "Costo histórico MXN"],
            rows,
            "ventas",
            format,
        )
    sales = db.session.scalars(
        base.options(lazyload(Sale.items))
        .order_by(Sale.created_at.desc())
        .offset((page - 1) * 50)
        .limit(50)
    ).all()
    return render_template(
        "reports/index.html",
        sales=sales,
        total=totals.total,
        known=totals.known,
        unknown=totals.unknown,
        waste=waste,
        confirmed=totals.confirmed,
        start=start,
        end=end,
        page=page,
        more=page * 50 < total_rows,
        total_rows=total_rows,
        report_types=REPORTS,
    )


@bp.get("/almacen")
@permission_required("reports")
def warehouse():
    start, end, since, until = period()
    kind = request.args.get("kind", "inventory")
    if kind not in REPORTS:
        kind = "inventory"
    search = request.args.get("q", "").strip()[:150]
    status = request.args.get("status", "")
    page = max(1, request.args.get("page", 1, type=int))
    try:
        headers, rows = warehouse_report(
            db.session,
            kind=kind,
            since=since,
            until=until,
            search=search,
            status=status,
            expiry_days=expiry_days(db.session),
        )
    except DomainError as exc:
        return render_template("error.html", code=400, message=str(exc)), 400
    if request.args.get("format") in {"csv", "xlsx"}:
        return export_response(headers, rows, kind, request.args["format"])
    return render_template(
        "reports/warehouse.html",
        headers=headers,
        rows=rows[(page - 1) * 50 : page * 50],
        total_rows=len(rows),
        page=page,
        more=page * 50 < len(rows),
        kind=kind,
        report_types=REPORTS,
        start=start,
        end=end,
        search=search,
        status=status,
    )
