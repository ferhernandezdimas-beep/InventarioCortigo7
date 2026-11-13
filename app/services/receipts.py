import re
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from werkzeug.datastructures import MultiDict

from app.delivery_models import ReceiptDraft
from app.forms import ReceiptForm
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
    utcnow,
)
from app.permissions import PERMISSIONS
from app.services.inventory import (
    _authorize,
    _claim,
    _run,
    normalize_receipt_lines,
    record_receipt_lines,
)
from app.services.numbers import DomainError


def _allowed(session, draft, user_id):
    user = session.get(User, user_id)
    if draft.user_id != user_id and "inventory.reverse" not in PERMISSIONS[user.role]:
        raise DomainError("Este borrador pertenece a otra persona.")


def clean_payload(payload):
    allowed = {"key", "supplier_id", "reference", "reason"}
    result = {}
    for key, value in payload.items():
        match = re.fullmatch(
            r"lines-(\d+)-(ingredient_id|presentation_id|quantity|unit_cost|code|expires_on)", key
        )
        if key in allowed or (match and int(match[1]) < 30):
            if len(str(value)) > 500:
                raise DomainError("Un campo del borrador excede la longitud permitida.")
            result[key] = str(value)
    return result


def validated_form(session, payload):
    form = ReceiptForm(formdata=MultiDict(payload), meta={"csrf": False})
    form.supplier_id.choices = [(0, "Sin proveedor")] + [
        (s.id, s.name) for s in session.scalars(select(Supplier).where(Supplier.active.is_(True)))
    ]
    ingredients = [(0, "Seleccionar")] + [
        (i.id, i.name)
        for i in session.scalars(select(Ingredient).where(Ingredient.active.is_(True)))
    ]
    presentations = [(0, "Unidad base")] + [
        (p.id, p.name) for p in session.scalars(select(Presentation))
    ]
    for line in form.lines:
        line.ingredient_id.choices = ingredients
        line.presentation_id.choices = presentations
    if not form.validate():
        raise DomainError(
            "Completa el proveedor válido, motivo e ingredientes del borrador; revisa cantidades, costos y fechas."
        )
    return form


def save_draft(*, user_id, key, payload, expected_revision=0):
    try:
        draft_id = uuid.UUID(str(key))
        revision = int(expected_revision)
    except (ValueError, TypeError):
        raise DomainError("La referencia del borrador no es válida.") from None
    payload = clean_payload(payload)

    def command(session):
        _authorize(session, user_id, "inventory.write")
        created = session.scalar(
            insert(ReceiptDraft)
            .values(id=draft_id, payload=payload, revision=1, status="draft", user_id=user_id)
            .on_conflict_do_nothing(index_elements=[ReceiptDraft.id])
            .returning(ReceiptDraft.id)
        )
        draft = session.scalar(
            select(ReceiptDraft).where(ReceiptDraft.id == draft_id).with_for_update()
        )
        _allowed(session, draft, user_id)
        if draft.status != "draft":
            raise DomainError("El borrador ya se confirmó o descartó.")
        if not created:
            if revision != draft.revision:
                raise DomainError("Otra persona modificó el borrador. Recarga antes de guardar.")
            draft.payload, draft.revision, draft.updated_at = payload, draft.revision + 1, utcnow()
        session.add(AuditLog(user_id=user_id, action="receipt.draft", detail=str(draft.id)))
        return draft.id

    return _run(command)


def confirm_draft(*, user_id, draft_id, payload, expected_revision):
    payload = clean_payload(payload)

    def command(session):
        _authorize(session, user_id, "inventory.write")
        draft = session.scalar(
            select(ReceiptDraft).where(ReceiptDraft.id == draft_id).with_for_update()
        )
        if not draft:
            raise DomainError("No existe el borrador.")
        _allowed(session, draft, user_id)
        if draft.status == "confirmed":
            return draft.operation_id
        if draft.status != "draft" or str(draft.revision) != str(expected_revision):
            raise DomainError("El borrador cambió o se descartó. Recarga antes de confirmar.")
        form = validated_form(session, payload)
        normalized = normalize_receipt_lines([line.data for line in form.lines])
        op_id, replay = _claim(
            session,
            draft.id,
            "receipt",
            normalized,
            user_id,
            form.reason.data.strip(),
            supplier_id=form.supplier_id.data or None,
            reference=(form.reference.data or "").strip() or None,
        )
        if not replay:
            record_receipt_lines(session, op_id, normalized)
        draft.status, draft.operation_id, draft.payload = "confirmed", op_id, payload
        draft.revision += 1
        session.add(AuditLog(user_id=user_id, action="receipt.confirm_draft", detail=str(op_id)))
        return op_id

    return _run(command)


def discard_draft(*, user_id, draft_id):
    def command(session):
        _authorize(session, user_id, "inventory.write")
        draft = session.scalar(
            select(ReceiptDraft).where(ReceiptDraft.id == draft_id).with_for_update()
        )
        if not draft:
            raise DomainError("No existe el borrador.")
        _allowed(session, draft, user_id)
        if draft.status == "confirmed":
            raise DomainError(
                "Una recepción confirmada se corrige mediante reversión, no descartando el borrador."
            )
        draft.status = "discarded"
        session.add(AuditLog(user_id=user_id, action="receipt.discard_draft", detail=str(draft.id)))
        return draft.id

    return _run(command)


def reverse_receipt(*, key, user_id, operation_id, reason):
    if not reason.strip() or len(reason) > 300:
        raise DomainError("Documenta el motivo de la corrección.")

    def command(session):
        _authorize(session, user_id, "inventory.reverse")
        op_id, replay = _claim(
            session, key, "receipt_reversal", str(operation_id), user_id, reason.strip()
        )
        if replay:
            return op_id
        original = session.scalar(
            select(Operation).where(Operation.id == operation_id).with_for_update()
        )
        if not original or original.kind != "receipt":
            raise DomainError("Solo se pueden revertir recepciones de mercancía.")
        if session.scalar(select(Operation.id).where(Operation.reverses_id == original.id)):
            raise DomainError("La recepción ya fue revertida.")
        lots = session.scalars(
            select(Lot).where(Lot.operation_id == original.id).order_by(Lot.ingredient_id, Lot.id)
        ).all()
        ids = sorted({lot.ingredient_id for lot in lots})
        list(
            session.scalars(
                select(Ingredient)
                .where(Ingredient.id.in_(ids))
                .order_by(Ingredient.id)
                .with_for_update(of=Ingredient)
            )
        )
        lots = session.scalars(
            select(Lot)
            .where(Lot.operation_id == original.id)
            .order_by(Lot.ingredient_id, Lot.received_at, Lot.id)
            .with_for_update(of=Lot)
            .execution_options(populate_existing=True)
        ).all()
        if not lots or any(lot.remaining_quantity != lot.original_quantity for lot in lots):
            raise DomainError(
                "Hay cantidades ya consumidas. La recepción se conserva; documenta un ajuste autorizado para corregir diferencias."
            )
        for lot in lots:
            quantity = lot.remaining_quantity
            original_movement = session.scalar(
                select(Movement)
                .join(Allocation, Allocation.movement_id == Movement.id)
                .where(Allocation.lot_id == lot.id, Movement.operation_id == original.id)
            )
            movement = Movement(
                operation_id=op_id,
                ingredient_id=lot.ingredient_id,
                quantity=-quantity,
                cost=original_movement.cost,
            )
            session.add(movement)
            session.flush()
            session.add(
                Allocation(
                    movement_id=movement.id,
                    lot_id=lot.id,
                    quantity=-quantity,
                    unit_cost=lot.unit_cost,
                )
            )
            lot.remaining_quantity = 0
        session.get(Operation, op_id).reverses_id = original.id
        session.add(
            AuditLog(user_id=user_id, action="receipt.reverse", detail=f"{op_id}: {original.id}")
        )
        return op_id

    return _run(command)
