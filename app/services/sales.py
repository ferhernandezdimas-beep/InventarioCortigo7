import uuid
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.commerce_models import MenuItem, Sale, SaleCancellation, SaleIngredientSnapshot, SaleItem
from app.models import Allocation, AuditLog, Lot, Movement, Operation
from app.services.inventory import _authorize, _claim, _run, consume_fifo, restore_movements
from app.services.numbers import DomainError, cost_value, decimal_value
from app.services.recipes import latest_recipe, pesos, portion_quantity


def cart_lines(lines):
    if not lines or len(lines) > 60:
        raise DomainError("Agrega entre 1 y 60 productos a la venta.")
    totals = {}
    for line in lines:
        amount = decimal_value(line["quantity"], positive=True)
        if amount != amount.to_integral_value() or amount > 9999:
            raise DomainError("La cantidad de platillos debe ser un entero entre 1 y 9,999.")
        item_id = int(line["menu_item_id"])
        totals[item_id] = totals.get(item_id, 0) + int(amount)
        if totals[item_id] > 9999:
            raise DomainError("Demasiadas unidades del mismo platillo.")
    return totals


def quote_cart(session, lines):
    amounts = cart_lines(lines)
    items = session.scalars(
        select(MenuItem).where(MenuItem.id.in_(amounts)).order_by(MenuItem.id)
    ).all()
    if len(items) != len(amounts) or any(not item.active for item in items):
        raise DomainError("Uno de los productos ya no está disponible.")
    rows = [
        dict(item=item, quantity=amounts[item.id], subtotal=pesos(item.price * amounts[item.id]))
        for item in items
    ]
    return dict(rows=rows, total=pesos(sum((row["subtotal"] for row in rows), Decimal("0"))))


def confirm_sale(*, key, user_id, lines, method, received=None, expected_total=None):
    quantities = cart_lines(lines)
    if method not in {"cash", "card", "transfer"}:
        raise DomainError("Selecciona un método de pago válido.")
    received = None if received is None else pesos(received)
    expected_total = None if expected_total is None else pesos(expected_total)
    payload = dict(
        items=sorted(quantities.items()),
        method=method,
        received=received,
        expected_total=expected_total,
    )

    def command(session):
        _authorize(session, user_id, "sales.write")
        op_id, replay = _claim(session, key, "sale", payload, user_id, "Venta de mostrador")
        if replay:
            return session.scalar(select(Sale.id).where(Sale.operation_id == op_id))
        # Recipes are edited under the same menu-item locks. Then lock ingredients and lots.
        items = session.scalars(
            select(MenuItem)
            .where(MenuItem.id.in_(quantities))
            .order_by(MenuItem.id)
            .with_for_update()
        ).all()
        if len(items) != len(quantities) or any(not item.active for item in items):
            raise DomainError("Uno de los productos ya no está disponible.")
        total = pesos(sum((item.price * quantities[item.id] for item in items), Decimal("0")))
        if expected_total is not None and total != expected_total:
            raise DomainError("Los precios cambiaron. Actualiza el carrito antes de confirmar.")
        paid = total if method != "cash" else received
        if paid is None or paid < total:
            raise DomainError("El efectivo recibido no cubre el total de la venta.")
        sale = Sale(
            operation_id=op_id,
            user_id=user_id,
            total=total,
            received=paid,
            change=pesos(paid - total),
            method=method,
        )
        session.add(sale)
        session.flush()
        totals, snapshots = {}, []
        for item in items:
            recipe = latest_recipe(session, item.id)
            if recipe is None or not recipe.lines:
                raise DomainError(f"{item.name} necesita una receta antes de venderse.")
            sale_item = SaleItem(
                sale_id=sale.id,
                menu_item_id=item.id,
                recipe_version_id=recipe.id,
                name=item.name,
                quantity=quantities[item.id],
                unit_price=item.price,
                subtotal=pesos(item.price * quantities[item.id]),
            )
            session.add(sale_item)
            session.flush()
            for line in recipe.lines:
                # Use the rounded per-portion requirement consistently for one or many units.
                amount = decimal_value(
                    portion_quantity(line.quantity, recipe.yield_quantity) * quantities[item.id],
                    positive=True,
                )
                totals[line.ingredient_id] = decimal_value(
                    totals.get(line.ingredient_id, Decimal("0")) + amount, positive=True
                )
                snapshots.append((sale_item.id, line, amount))
        movements = {m.ingredient_id: m for m in consume_fifo(session, op_id, totals)}
        sale.cost = (
            None
            if any(m.cost is None for m in movements.values())
            else cost_value(sum((m.cost for m in movements.values()), Decimal("0")))
        )
        for sale_item_id, line, amount in snapshots:
            session.add(
                SaleIngredientSnapshot(
                    sale_item_id=sale_item_id,
                    ingredient_id=line.ingredient_id,
                    movement_id=movements[line.ingredient_id].id,
                    name=line.ingredient.name,
                    unit_symbol=line.unit_symbol,
                    quantity=amount,
                )
            )
        session.add(AuditLog(user_id=user_id, action="sale.confirm", detail=str(sale.id)))
        return sale.id

    return _run(command)


def cancel_sale(*, key, user_id, sale_id, reason, restock=False):
    reason = reason.strip()
    if not reason or len(reason) > 300:
        raise DomainError("Explica el motivo de la cancelación.")
    sale_id = uuid.UUID(str(sale_id))

    def command(session):
        _authorize(session, user_id, "sales.cancel")
        op_id, replay = _claim(
            session, key, "sale_cancel", dict(sale=str(sale_id), restock=restock), user_id, reason
        )
        if replay:
            return sale_id
        sale = session.scalar(select(Sale).where(Sale.id == sale_id).with_for_update(of=Sale))
        if not sale:
            raise DomainError("La venta no existe.")
        if session.scalar(select(SaleCancellation.id).where(SaleCancellation.sale_id == sale_id)):
            raise DomainError("La venta ya está cancelada.")
        if restock:
            # No physical recovery is assumed. An authorized user must explicitly attest it.
            today = datetime.now(ZoneInfo("America/Mexico_City")).date()
            expired = session.scalar(
                select(Lot.id)
                .join(Allocation, Allocation.lot_id == Lot.id)
                .join(Movement, Movement.id == Allocation.movement_id)
                .where(Movement.operation_id == sale.operation_id, Lot.expires_on < today)
                .limit(1)
            )
            if expired:
                raise DomainError(
                    "Hay lotes caducados. Cancela sin reincorporar inventario y registra la incidencia."
                )
            restore_movements(session, sale.operation_id, op_id)
            session.get(Operation, op_id).reverses_id = sale.operation_id
        session.add(
            SaleCancellation(
                sale_id=sale.id,
                operation_id=op_id,
                restocked=restock,
                reason=reason,
                user_id=user_id,
            )
        )
        session.add(
            AuditLog(
                user_id=user_id,
                action="sale.cancel",
                detail=f"{sale.id}; reincorporación={restock}",
            )
        )
        return sale.id

    return _run(command)
