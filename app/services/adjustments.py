from sqlalchemy import func, select

from app.commerce_models import InventoryCount
from app.models import Allocation, AuditLog, Lot, Movement
from app.services.inventory import _authorize, _claim, _lock_ingredients, _run, consume_fifo
from app.services.numbers import DomainError, decimal_value


def record_waste(*, key, user_id, ingredient_id, quantity, category, reason):
    if category not in {"waste", "damaged", "expired"} or not reason.strip() or len(reason) > 250:
        raise DomainError("Selecciona el tipo y explica el motivo de la baja.")
    amount = decimal_value(quantity, positive=True)

    def command(session):
        _authorize(session, user_id, "inventory.waste")
        labels = {"waste": "Merma", "damaged": "Daño", "expired": "Caducidad"}
        op_id, replay = _claim(
            session,
            key,
            "waste",
            dict(ingredient_id=ingredient_id, quantity=str(amount), category=category),
            user_id,
            f"{labels[category]}: {reason.strip()}",
        )
        if replay:
            return op_id
        consume_fifo(
            session,
            op_id,
            {ingredient_id: amount},
            eligibility="expired" if category == "expired" else "all",
        )
        session.add(AuditLog(user_id=user_id, action="inventory.waste", detail=str(op_id)))
        return op_id

    return _run(command)


def record_count(*, key, user_id, ingredient_id, expected_quantity, counted_quantity, reason):
    before = decimal_value(expected_quantity)
    counted = decimal_value(counted_quantity)
    if min(before, counted) < 0 or not reason.strip() or len(reason) > 300:
        raise DomainError("Captura un conteo válido y documenta el motivo de la diferencia.")

    def command(session):
        _authorize(session, user_id, "inventory.adjust")
        op_id, replay = _claim(
            session,
            key,
            "adjustment",
            dict(ingredient_id=ingredient_id, before=str(before), counted=str(counted)),
            user_id,
            reason.strip(),
        )
        if replay:
            return op_id
        _lock_ingredients(session, [ingredient_id])
        physical = session.scalar(
            select(func.coalesce(func.sum(Lot.remaining_quantity), 0)).where(
                Lot.ingredient_id == ingredient_id
            )
        )
        if physical != before:
            raise DomainError(
                "El inventario cambió durante el conteo. Actualiza la existencia y vuelve a contar antes de confirmar."
            )
        difference = counted - physical
        if difference == 0:
            raise DomainError("El conteo coincide. No es necesario generar un ajuste.")
        if difference < 0:
            consume_fifo(
                session, op_id, {ingredient_id: -difference}, eligibility="all", lock=False
            )
        else:
            # This is recovered stock, never a fabricated purchase or backdated receipt.
            lot = Lot(
                ingredient_id=ingredient_id,
                operation_id=op_id,
                code="Ajuste positivo documentado",
                source="recovered",
                original_quantity=difference,
                remaining_quantity=difference,
                unit_cost=None,
                expires_on=None,
            )
            movement = Movement(
                operation_id=op_id, ingredient_id=ingredient_id, quantity=difference, cost=None
            )
            session.add_all([lot, movement])
            session.flush()
            session.add(
                Allocation(
                    movement_id=movement.id, lot_id=lot.id, quantity=difference, unit_cost=None
                )
            )
        session.add(
            InventoryCount(
                operation_id=op_id,
                ingredient_id=ingredient_id,
                before_quantity=physical,
                counted_quantity=counted,
            )
        )
        session.add(
            AuditLog(
                user_id=user_id, action="inventory.count", detail=f"{op_id}: {physical} → {counted}"
            )
        )
        return op_id

    return _run(command)
