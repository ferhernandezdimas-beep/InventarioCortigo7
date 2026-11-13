"""Each command owns a fresh session and its complete database transaction.

Lock order: idempotency row -> ingredients ascending -> lots (received_at, id).
Never skip locked lots: doing so could violate FIFO.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import (
    Allocation,
    AuditLog,
    Ingredient,
    Lot,
    Movement,
    Operation,
    Presentation,
    Supplier,
    User,
)
from app.permissions import PERMISSIONS
from app.services.numbers import DomainError, cost_value, decimal_value


class ConcurrencyError(DomainError):
    pass


def _claim(session, key, kind, payload, user_id, reason, **extra):
    try:
        key = uuid.UUID(str(key))
    except (ValueError, TypeError, AttributeError):
        raise DomainError("La referencia de operación no es válida.") from None
    digest = hashlib.sha256(
        json.dumps(
            {"kind": kind, "payload": payload, "user": user_id, "reason": reason, **extra},
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    op_id = uuid.uuid4()
    inserted = session.scalar(
        insert(Operation)
        .values(
            id=op_id,
            idempotency_key=key,
            payload_hash=digest,
            kind=kind,
            user_id=user_id,
            reason=reason,
            created_at=datetime.now(timezone.utc),
            **extra,
        )
        .on_conflict_do_nothing(index_elements=[Operation.idempotency_key])
        .returning(Operation.id)
    )
    if inserted:
        return op_id, False
    existing = session.scalar(select(Operation).where(Operation.idempotency_key == key))
    if existing.payload_hash != digest:
        raise DomainError("Esta referencia ya se utilizó para una operación diferente.")
    return existing.id, True


def _authorize(session, user_id, permission):
    user = session.get(User, user_id)
    if not user or not user.active or permission not in PERMISSIONS.get(user.role, set()):
        raise DomainError("No tienes permiso para esta operación.")


def _lock_ingredients(session, ids):
    # of= avoids trying to lock nullable supplier joins from eager relationships.
    ingredients = list(
        session.scalars(
            select(Ingredient)
            .where(Ingredient.id.in_(ids))
            .order_by(Ingredient.id)
            .with_for_update(of=Ingredient)
            .execution_options(populate_existing=True)
        )
    )
    if len(ingredients) != len(set(ids)) or any(not i.active for i in ingredients):
        raise DomainError("Uno de los ingredientes no existe o está inactivo.")
    return ingredients


def _run(command):
    try:
        with (
            localcontext() as precision,
            Session(db.engine, expire_on_commit=False) as session,
            session.begin(),
        ):
            precision.prec = 50
            return command(session)
    except OperationalError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"40P01", "40001", "55P03", "57014"}:
            raise ConcurrencyError(
                "El inventario está ocupado. Reintenta con la misma referencia; no se guardó una operación parcial."
            ) from None
        raise


def normalize_receipt_lines(lines):
    if not lines or len(lines) > 100:
        raise DomainError("Captura entre 1 y 100 renglones.")
    normalized = []
    for line in lines:
        quantity = decimal_value(line["quantity"], positive=True)
        cost = None if line.get("unit_cost") is None else decimal_value(line["unit_cost"])
        if cost is not None and cost < 0:
            raise DomainError("El costo no puede ser negativo.")
        received_at = line.get("received_at")
        if received_at is not None and (
            received_at.tzinfo is None or received_at > datetime.now(timezone.utc)
        ):
            raise DomainError("La fecha de entrada debe tener zona horaria y no puede ser futura.")
        normalized.append(
            dict(
                ingredient_id=int(line["ingredient_id"]),
                quantity=str(quantity),
                unit_cost=None if cost is None else str(cost),
                code=line.get("code"),
                expires_on=line.get("expires_on"),
                received_at=received_at,
                presentation_id=int(line.get("presentation_id") or 0),
            )
        )

    return normalized


def record_receipt_lines(session, op_id, normalized):
    _lock_ingredients(session, [line["ingredient_id"] for line in normalized])
    for line in normalized:
        qty = Decimal(line["quantity"])
        cost = None if line["unit_cost"] is None else Decimal(line["unit_cost"])
        if line["presentation_id"]:
            presentation = session.get(Presentation, line["presentation_id"])
            if not presentation or presentation.ingredient_id != line["ingredient_id"]:
                raise DomainError("La presentación no corresponde al ingrediente seleccionado.")
            qty = decimal_value(qty * presentation.base_quantity, positive=True)
            cost = (
                None
                if cost is None
                else decimal_value(cost_value(cost / presentation.base_quantity))
            )
        lot = Lot(
            ingredient_id=line["ingredient_id"],
            operation_id=op_id,
            original_quantity=qty,
            remaining_quantity=qty,
            unit_cost=cost,
            code=line["code"],
            expires_on=line["expires_on"],
            received_at=line["received_at"] or datetime.now(timezone.utc),
        )
        movement = Movement(
            operation_id=op_id,
            ingredient_id=line["ingredient_id"],
            quantity=qty,
            cost=None if cost is None else cost_value(qty * cost),
        )
        session.add_all([lot, movement])
        session.flush()
        session.add(
            Allocation(movement_id=movement.id, lot_id=lot.id, quantity=qty, unit_cost=cost)
        )
    session.flush()


def receive(
    *, key, user_id, lines, reason="Recepción de mercancía", supplier_id=None, reference=None
):
    reason = reason.strip()
    if not reason or len(reason) > 300:
        raise DomainError("Captura un motivo de hasta 300 caracteres.")
    normalized = normalize_receipt_lines(lines)

    def command(session):
        _authorize(session, user_id, "inventory.write")
        op_id, replay = _claim(
            session,
            key,
            "receipt",
            normalized,
            user_id,
            reason,
            supplier_id=supplier_id,
            reference=reference,
        )
        if replay:
            return op_id
        if supplier_id and not session.scalar(
            select(Supplier.id).where(Supplier.id == supplier_id, Supplier.active.is_(True))
        ):
            raise DomainError("El proveedor no existe o está inactivo.")
        record_receipt_lines(session, op_id, normalized)
        session.add(AuditLog(user_id=user_id, action="inventory.receipt", detail=str(op_id)))
        return op_id

    return _run(command)


def consume_fifo(session, operation_id, totals, *, eligibility="usable", lock=True):
    """Join the caller transaction; never commit or open a nested session."""
    op_id = operation_id
    if lock:
        _lock_ingredients(session, sorted(totals))
    result = []
    today = datetime.now(ZoneInfo("America/Mexico_City")).date()
    for iid, requested in sorted(totals.items()):
        lots = list(
            session.scalars(
                select(Lot)
                .where(
                    Lot.ingredient_id == iid,
                    Lot.remaining_quantity > 0,
                    ((Lot.expires_on.is_(None)) | (Lot.expires_on >= today))
                    if eligibility == "usable"
                    else ((Lot.expires_on < today) if eligibility == "expired" else True),
                )
                .order_by(Lot.received_at, Lot.id)
                .with_for_update(of=Lot)
            )
        )
        if sum((lot.remaining_quantity for lot in lots), Decimal("0")) < requested:
            raise DomainError("Existencia elegible insuficiente. Revisa cantidades y caducidades.")
        movement = Movement(operation_id=op_id, ingredient_id=iid, quantity=-requested)
        session.add(movement)
        session.flush()
        pending, total, unknown = requested, Decimal("0"), False
        for lot in lots:
            if pending == 0:
                break
            consumed = min(pending, lot.remaining_quantity)
            lot.remaining_quantity -= consumed
            pending -= consumed
            unknown |= lot.unit_cost is None
            if lot.unit_cost is not None:
                total += consumed * lot.unit_cost
            session.add(
                Allocation(
                    movement_id=movement.id,
                    lot_id=lot.id,
                    quantity=-consumed,
                    unit_cost=lot.unit_cost,
                )
            )
        movement.cost = None if unknown else cost_value(total)
        result.append(movement)
    session.flush()
    return result


def issue(*, key, user_id, lines, reason):
    reason = reason.strip()
    if not reason or len(reason) > 300 or not lines or len(lines) > 100:
        raise DomainError("Captura un motivo y entre 1 y 100 renglones.")
    totals = {}
    for line in lines:
        iid = int(line["ingredient_id"])
        totals[iid] = decimal_value(
            totals.get(iid, Decimal("0")) + decimal_value(line["quantity"], positive=True),
            positive=True,
        )
    payload = [{"ingredient_id": iid, "quantity": str(qty)} for iid, qty in sorted(totals.items())]

    def command(session):
        _authorize(session, user_id, "inventory.write")
        op_id, replay = _claim(session, key, "issue", payload, user_id, reason)
        if replay:
            return op_id
        consume_fifo(session, op_id, totals)
        session.add(AuditLog(user_id=user_id, action="inventory.issue", detail=str(op_id)))
        return op_id

    return _run(command)


def restore_movements(session, operation_id, op_id):
    """Restore historical allocations inside the caller transaction."""
    movements = list(
        session.scalars(
            select(Movement)
            .where(Movement.operation_id == operation_id)
            .order_by(Movement.ingredient_id)
        )
    )
    ids = sorted({m.ingredient_id for m in movements})
    # Inactive ingredients can receive their original stock back.
    list(
        session.scalars(
            select(Ingredient)
            .where(Ingredient.id.in_(ids))
            .order_by(Ingredient.id)
            .with_for_update(of=Ingredient)
        )
    )
    if session.scalar(select(Operation.id).where(Operation.reverses_id == operation_id)):
        raise DomainError("Esta salida ya fue revertida.")
    for movement in movements:
        allocations = list(
            session.scalars(select(Allocation).where(Allocation.movement_id == movement.id))
        )
        lot_ids = [a.lot_id for a in allocations]
        lots = {
            lot.id: lot
            for lot in session.scalars(
                select(Lot)
                .where(Lot.id.in_(lot_ids))
                .order_by(Lot.received_at, Lot.id)
                .with_for_update(of=Lot)
            )
        }
        compensating = Movement(
            operation_id=op_id,
            ingredient_id=movement.ingredient_id,
            quantity=-movement.quantity,
            cost=movement.cost,
        )
        session.add(compensating)
        session.flush()
        for allocation in allocations:
            lots[allocation.lot_id].remaining_quantity -= allocation.quantity
            session.add(
                Allocation(
                    movement_id=compensating.id,
                    lot_id=allocation.lot_id,
                    quantity=-allocation.quantity,
                    unit_cost=allocation.unit_cost,
                )
            )
    session.flush()


def reverse_issue(*, key, user_id, operation_id, reason):
    if not reason.strip() or len(reason) > 300:
        raise DomainError("Explica el motivo de la reversión.")

    def command(session):
        _authorize(session, user_id, "inventory.reverse")
        op_id, replay = _claim(session, key, "reversal", str(operation_id), user_id, reason)
        if replay:
            return op_id
        original = session.get(Operation, operation_id)
        if not original or original.kind != "issue":
            raise DomainError("Solamente se pueden revertir salidas completas.")
        restore_movements(session, operation_id, op_id)
        if session.scalar(select(Operation.id).where(Operation.reverses_id == operation_id)):
            raise DomainError("Esta salida ya fue revertida.")
        session.get(Operation, op_id).reverses_id = operation_id
        session.add(
            AuditLog(
                user_id=user_id, action="inventory.reversal", detail=f"{op_id}: {operation_id}"
            )
        )
        return op_id

    return _run(command)
