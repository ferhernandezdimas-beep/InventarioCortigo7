import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.commerce_models import MenuItem
from app.models import Ingredient, Lot, Movement, Operation
from app.services.numbers import DomainError
from app.services.queries import inventory_query
from app.services.recipes import estimate_recipe, latest_recipe
from app.services.xlsx import workbook_bytes

REPORTS = {
    "inventory": "Inventario actual",
    "receipts": "Entradas",
    "issues": "Salidas y consumos",
    "lots": "Lotes y caducidades",
    "waste": "Mermas y bajas",
    "costs": "Costos de recetas",
}
MAX_EXPORT = 10000


def export_response(headers, rows, filename, format):
    if format == "xlsx":
        return Response(
            workbook_bytes(headers, rows),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(
            [
                "'" + value
                if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
                for value in row
            ]
        )
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
    )


def warehouse_report(session, *, kind, since, until, search="", status="", expiry_days=7):
    zone = ZoneInfo("America/Mexico_City")
    today = datetime.now(zone).date()
    if kind == "inventory":
        statement = inventory_query().order_by(Ingredient.name)
        if search:
            statement = statement.where(Ingredient.name.ilike(f"%{search}%"))
        source = session.execute(statement.limit(MAX_EXPORT + 1)).all()
        headers = [
            "Ingrediente",
            "Categoría",
            "Unidad",
            "Existencia física",
            "Disponible",
            "Mínimo",
            "Valor conocido MXN",
            "Costos pendientes",
            "Estado",
        ]
        rows = []
        for row in source:
            item = row.Ingredient
            state = (
                "Inactivo"
                if not item.active
                else "Agotado"
                if row.available == 0
                else "Existencia baja"
                if row.available <= item.minimum
                else "Disponible"
            )
            if status == "low" and not (item.active and row.available <= item.minimum):
                continue
            rows.append(
                [
                    item.name,
                    item.category.name,
                    item.unit.symbol,
                    row.physical,
                    row.available,
                    item.minimum,
                    row.known_value,
                    "Sí" if row.unknown else "No",
                    state,
                ]
            )
    elif kind == "lots":
        statement = select(Lot).order_by(Lot.received_at, Lot.id)
        if search:
            statement = statement.join(Ingredient, Ingredient.id == Lot.ingredient_id).where(
                Ingredient.name.ilike(f"%{search}%")
            )
        if status == "expired":
            statement = statement.where(Lot.expires_on < today, Lot.remaining_quantity > 0)
        elif status == "soon":
            statement = statement.where(
                Lot.expires_on >= today,
                Lot.expires_on <= today + timedelta(days=expiry_days),
                Lot.remaining_quantity > 0,
            )
        elif status == "active":
            statement = statement.where(Lot.remaining_quantity > 0)
        source = session.scalars(statement.limit(MAX_EXPORT + 1)).all()
        headers = [
            "Ingrediente",
            "Lote",
            "Unidad",
            "Entrada local",
            "Caducidad",
            "Saldo",
            "Costo unitario MXN",
            "Origen",
            "Estado",
        ]
        origins = {
            "receipt": "Recepción",
            "recovered": "Recuperado; origen no verificado",
            "opening": "Apertura; historia no verificada",
        }
        rows = [
            [
                lot.ingredient.name,
                lot.code or f"Lote #{lot.id}",
                lot.ingredient.unit.symbol,
                lot.received_at.astimezone(zone).strftime("%d/%m/%Y %H:%M"),
                lot.expires_on.strftime("%d/%m/%Y") if lot.expires_on else "Sin fecha",
                lot.remaining_quantity,
                lot.unit_cost if lot.unit_cost is not None else "Pendiente",
                origins[lot.source],
                "Agotado"
                if lot.remaining_quantity == 0
                else "Caducado"
                if lot.expires_on and lot.expires_on < today
                else "Activo",
            ]
            for lot in source
        ]
    elif kind == "costs":
        statement = select(MenuItem).order_by(MenuItem.name)
        if search:
            statement = statement.where(MenuItem.name.ilike(f"%{search}%"))
        source = session.scalars(statement.limit(1001)).all()
        if len(source) > 1000:
            raise DomainError("Filtra el menú para consultar hasta 1,000 recetas por reporte.")
        headers = [
            "Platillo",
            "Categoría",
            "Precio MXN",
            "Costo estimado por porción MXN",
            "Margen bruto estimado MXN",
            "Disponibilidad para una porción",
        ]
        rows = []
        for item in source:
            estimate = estimate_recipe(session, latest_recipe(session, item.id))
            rows.append(
                [
                    item.name,
                    item.category,
                    item.price,
                    estimate["total"] if estimate["complete"] else "Incompleto",
                    item.price - estimate["total"] if estimate["complete"] else "Incompleto",
                    "Disponible" if estimate["stock"] else "Insuficiente",
                ]
            )
    else:
        kinds = {
            "receipts": ["receipt", "opening", "receipt_reversal"],
            "issues": ["issue", "sale", "reversal", "sale_cancel"],
            "waste": ["waste"],
        }[kind]
        statement = (
            select(Movement)
            .join(Operation, Operation.id == Movement.operation_id)
            .where(
                Operation.kind.in_(kinds),
                Operation.created_at >= since,
                Operation.created_at < until,
            )
            .options(joinedload(Movement.operation).joinedload(Operation.user))
            .order_by(Operation.created_at.desc(), Movement.id.desc())
        )
        if search:
            statement = statement.join(Ingredient, Ingredient.id == Movement.ingredient_id).where(
                Ingredient.name.ilike(f"%{search}%")
            )
        source = session.scalars(statement.limit(MAX_EXPORT + 1)).all()
        headers = [
            "Fecha local",
            "Ingrediente",
            "Unidad",
            "Cantidad firmada",
            "Costo histórico MXN",
            "Operación",
            "Responsable",
            "Motivo",
            "Folio",
        ]
        labels = {
            "receipt": "Entrada",
            "opening": "Apertura",
            "receipt_reversal": "Reversión de recepción",
            "issue": "Salida",
            "sale": "Venta",
            "reversal": "Reversión de salida",
            "sale_cancel": "Cancelación de venta",
            "waste": "Merma / baja",
        }
        rows = [
            [
                movement.operation.created_at.astimezone(zone).strftime("%d/%m/%Y %H:%M"),
                movement.ingredient.name,
                movement.ingredient.unit.symbol,
                movement.quantity,
                movement.cost if movement.cost is not None else "Pendiente",
                labels[movement.operation.kind],
                movement.operation.user.name,
                movement.operation.reason,
                str(movement.operation_id),
            ]
            for movement in source
        ]
    if len(source) > MAX_EXPORT:
        raise DomainError(
            "El reporte excede 10,000 registros. Reduce el periodo o filtra por nombre."
        )
    return headers, rows
