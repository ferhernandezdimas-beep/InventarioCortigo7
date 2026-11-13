"""Normalize the explicitly requested presentation of the existing seeded dataset.

Provenance stays in the audit manifest and technical documentation. Financial values,
dates, original snapshots' amounts, allocations, IDs and idempotency hashes stay intact.
"""

import json

from sqlalchemy import select, text

from app.commerce_models import (
    MenuItem,
    RecipeVersion,
    Sale,
    SaleCancellation,
    SaleItem,
)
from app.delivery_models import ReceiptDraft
from app.models import AuditLog, Category, Ingredient, Lot, Operation, Supplier
from app.services.demo import COMPLETE, START, SUFFIX, demo_key
from app.services.demo_data import INGREDIENTS, MENU, SUPPLIERS
from app.services.inventory import _run
from app.services.numbers import DomainError

PRESENTED = "dataset.presentation.v1"


def normalize_presentation():
    def command(session):
        session.execute(text("SELECT pg_advisory_xact_lock(7003001)"))
        previous = session.scalar(select(AuditLog).where(AuditLog.action == PRESENTED))
        if previous:
            return dict(json.loads(previous.detail), already_applied=True)
        completed = session.scalar(select(AuditLog).where(AuditLog.action == COMPLETE))
        started = session.scalar(select(AuditLog).where(AuditLog.action == START))
        if not completed or not started:
            raise DomainError(
                "Primero debe finalizar la carga inicial; no se modificaron registros."
            )
        actor = json.loads(started.detail)["user_id"]
        ingredient_ids, item_ids, supplier_ids = [], [], []
        for key, name, category, *_ in INGREDIENTS:
            ingredient = session.scalar(
                select(Ingredient).where(Ingredient.code == f"DEMO-I-{key}")
            )
            if not ingredient:
                raise DomainError(
                    "El catálogo inicial fue modificado. Revisa los códigos antes de continuar."
                )
            if session.scalar(
                select(Ingredient.id).where(
                    Ingredient.id != ingredient.id, Ingredient.name.ilike(name)
                )
            ):
                raise DomainError(
                    f"Ya existe otro ingrediente llamado {name}; no se combinaron registros."
                )
            if session.scalar(select(Ingredient.id).where(Ingredient.code == f"INS-{key.upper()}")):
                raise DomainError("Existe un código de ingrediente en conflicto.")
            ingredient_ids.append(ingredient.id)
            ingredient.name = ingredient.name.removesuffix(SUFFIX)
            ingredient.code = f"INS-{key.upper()}"
            ingredient.description = f"{name}. Control de existencias en {ingredient.unit.symbol}."
            cat = session.scalar(select(Category).where(Category.id == ingredient.category_id))
            if cat.name.endswith(SUFFIX):
                new_name = cat.name.removesuffix(SUFFIX)
                if session.scalar(
                    select(Category.id).where(Category.id != cat.id, Category.name == new_name)
                ):
                    raise DomainError(
                        "Existe una categoría en conflicto; no se combinaron registros."
                    )
                cat.name = new_name
        for name, contact, notes in SUPPLIERS.values():
            supplier = session.scalar(select(Supplier).where(Supplier.name == name + SUFFIX))
            if not supplier:
                raise DomainError("Revisa los proveedores de la carga inicial.")
            if session.scalar(
                select(Supplier.id).where(Supplier.id != supplier.id, Supplier.name == name)
            ):
                raise DomainError("Existe un proveedor en conflicto; no se combinaron registros.")
            supplier_ids.append(supplier.id)
            supplier.name, supplier.contact, supplier.notes = name, contact, notes
            supplier.address = "San Juan del Río, Querétaro"
            supplier.email = None
        for key, name, _, _, _ in MENU:
            item = session.scalar(select(MenuItem).where(MenuItem.code == f"DEMO-M-{key}"))
            if not item:
                raise DomainError("Revisa los productos de la carga inicial.")
            if session.scalar(
                select(MenuItem.id).where(MenuItem.id != item.id, MenuItem.name == name)
            ) or session.scalar(select(MenuItem.id).where(MenuItem.code == f"PLT-{key.upper()}")):
                raise DomainError(
                    "Existe un producto/código en conflicto; no se combinaron registros."
                )
            item_ids.append(item.id)
            item.name, item.code = name, f"PLT-{key.upper()}"
            item.description = (
                name + ". Preparado al momento."
                if item.kind == "prepared"
                else name + ". Venta por unidad."
            )
            for version in session.scalars(
                select(RecipeVersion).where(RecipeVersion.menu_item_id == item.id)
            ):
                if (
                    version.notes
                    == "Receta sintética por porción; revisar rendimientos antes de uso real."
                ):
                    version.notes = "Receta estándar por porción."
        tokens = [f"receipt-{supplier}-{batch}" for supplier in SUPPLIERS for batch in range(2)]
        tokens += [
            f"sale-{day}-{ticket}"
            for day, count in enumerate([8, 10, 9, 11, 12, 14, 10])
            for ticket in range(count)
        ]
        tokens += [
            "receipt-expired",
            "cancel-12",
            "cancel-45",
            "issue-kitchen",
            "waste-fresa",
            "waste-cilantro",
            "count-salt",
            "receipt-correction",
            "reverse-receipt",
        ]
        operations = session.scalars(
            select(Operation)
            .where(Operation.idempotency_key.in_([demo_key(token) for token in tokens]))
            .order_by(Operation.created_at, Operation.id)
        ).all()
        prefixes = {
            "receipt": "REC",
            "issue": "SAL",
            "sale": "VTA",
            "sale_cancel": "CAN",
            "waste": "MER",
            "adjustment": "AJU",
            "receipt_reversal": "COR",
        }
        for index, operation in enumerate(operations, 1):
            operation.reason = (
                operation.reason.replace("[DEMO] ", "")
                .replace("Abastecimiento simulado por proveedor", "Abastecimiento de almacén")
                .replace(
                    "Lotes de ejemplo para control de caducidades",
                    "Revisión de caducidades en almacén",
                )
            )
            operation.reference = (
                f"{prefixes[operation.kind]}-{operation.created_at:%Y%m%d}-{index:04d}"
            )
        op_ids = [operation.id for operation in operations]
        for lot in session.scalars(select(Lot).where(Lot.operation_id.in_(op_ids))):
            if lot.code and lot.code.startswith("DEMO-"):
                lot.code = "LT-" + lot.code.removeprefix("DEMO-")
        sale_ids = list(session.scalars(select(Sale.id).where(Sale.operation_id.in_(op_ids))))
        for line in session.scalars(select(SaleItem).where(SaleItem.sale_id.in_(sale_ids))):
            line.name = line.name.removesuffix(SUFFIX)
            for snapshot in line.ingredients:
                snapshot.name = snapshot.name.removesuffix(SUFFIX)
        for cancellation in session.scalars(
            select(SaleCancellation).where(SaleCancellation.sale_id.in_(sale_ids))
        ):
            cancellation.reason = cancellation.reason.removeprefix("[DEMO] ")
        for draft in session.scalars(
            select(ReceiptDraft).where(
                ReceiptDraft.payload["reference"].astext == "DEMO-PEDIDO-PENDIENTE"
            )
        ):
            payload = dict(draft.payload)
            payload["reference"] = "PEDIDO-VERDURAS-PENDIENTE"
            payload["reason"] = "Pedido de verduras pendiente de recepción"
            payload["lines-0-code"] = "LOTE-PENDIENTE"
            draft.payload = payload
        result = dict(
            ingredients=len(ingredient_ids),
            products=len(item_ids),
            suppliers=len(supplier_ids),
            operations=len(operations),
        )
        session.add(AuditLog(user_id=actor, action=PRESENTED, detail=json.dumps(result)))
        return dict(result, already_applied=False)

    return _run(command)
