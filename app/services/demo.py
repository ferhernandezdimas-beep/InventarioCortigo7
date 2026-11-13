"""Add an explicitly labelled, repeatable local scenario without clearing existing data.

Business operations use the ordinary transactional services. A persisted anchor and
stable idempotency keys allow interrupted runs to resume without duplicate stock/sales.
Only demo-owned history receives simulated dates; audit timestamps remain actual.
"""

import json
import random
import uuid
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from flask import current_app
from sqlalchemy import func, or_, select, text

from app.commerce_models import MenuItem, RecipeVersion, Sale, SaleCancellation
from app.extensions import db
from app.models import (
    AuditLog,
    Category,
    Ingredient,
    Lot,
    Operation,
    Presentation,
    Supplier,
    Unit,
    User,
)
from app.services.adjustments import record_count, record_waste
from app.services.demo_data import INGREDIENTS, MENU, SUPPLIERS
from app.services.inventory import _run, issue, receive
from app.services.numbers import DomainError
from app.services.receipts import reverse_receipt, save_draft
from app.services.recipes import save_recipe
from app.services.sales import cancel_sale, confirm_sale

NAMESPACE = uuid.UUID("e9cab43b-c4ab-43ad-acb8-2ef12114cdb4")
ZONE = ZoneInfo("America/Mexico_City")
SUFFIX = " (demo)"
START = "demo.v1.started"
COMPLETE = "demo.v1.completed"
LOCK = 7003001


def demo_key(value):
    return uuid.uuid5(NAMESPACE, value)


def _catalog(user_id, anchor):
    def command(session):
        if user_id is None:
            raise DomainError("Crea un administrador antes de cargar el escenario demo.")
        user = session.get(User, user_id)
        if not user or not user.active or user.role != "admin":
            raise DomainError("La carga demo requiere un administrador activo existente.")
        started = session.scalar(select(AuditLog).where(AuditLog.action == START))
        units = {unit.symbol: unit for unit in session.scalars(select(Unit))}
        for symbol, dimension, factor in [
            ("kg", "mass", 1000),
            ("L", "volume", 1000),
            ("pza", "count", 1),
        ]:
            unit = units.get(symbol)
            if not unit or unit.dimension != dimension or unit.factor != factor:
                raise DomainError(f"Revisa la unidad base {symbol} antes de cargar el escenario.")
        if not started:
            # Never adopt or overwrite an existing real record, even on a name/code collision.
            checks = [
                select(Ingredient.id).where(
                    or_(
                        Ingredient.code.in_([f"DEMO-I-{r[0]}" for r in INGREDIENTS]),
                        Ingredient.name.in_([r[1] + SUFFIX for r in INGREDIENTS]),
                    )
                ),
                select(MenuItem.id).where(
                    or_(
                        MenuItem.code.in_([f"DEMO-M-{r[0]}" for r in MENU]),
                        MenuItem.name.in_([r[1] + SUFFIX for r in MENU]),
                    )
                ),
                select(Supplier.id).where(
                    Supplier.name.in_([r[0] + SUFFIX for r in SUPPLIERS.values()])
                ),
                select(Category.id).where(Category.name.in_([r[2] + SUFFIX for r in INGREDIENTS])),
            ]
            if any(session.scalar(check.limit(1)) for check in checks):
                raise DomainError(
                    "Hay nombres/códigos demo previos sin manifiesto. No se modificó el catálogo; revisa la colisión."
                )
            session.add(
                AuditLog(
                    user_id=user_id,
                    action=START,
                    detail=json.dumps({"anchor": anchor.isoformat(), "user_id": user_id}),
                )
            )
        suppliers, categories, ingredients = {}, {}, {}
        for key, (name, contact, notes) in SUPPLIERS.items():
            supplier = session.scalar(select(Supplier).where(Supplier.name == name + SUFFIX))
            if not supplier:
                supplier = Supplier(
                    name=name + SUFFIX,
                    contact=contact + " (ficticio)",
                    email=f"{key}@example.com",
                    address="Proveedor ficticio · San Juan del Río, Querétaro",
                    notes="DATOS DE PRUEBA. " + notes,
                    active=True,
                )
                session.add(supplier)
                session.flush()
            suppliers[key] = supplier.id
        for (
            key,
            name,
            category,
            supplier,
            symbol,
            cost,
            minimum,
            first,
            second,
            expiry,
        ) in INGREDIENTS:
            if category not in categories:
                cat = session.scalar(select(Category).where(Category.name == category + SUFFIX))
                if not cat:
                    cat = Category(name=category + SUFFIX)
                    session.add(cat)
                    session.flush()
                categories[category] = cat.id
            ingredient = session.scalar(
                select(Ingredient).where(Ingredient.code == f"DEMO-I-{key}")
            )
            if not ingredient:
                ingredient = Ingredient(
                    code=f"DEMO-I-{key}",
                    name=name + SUFFIX,
                    description="DATOS DE PRUEBA · Escenario de restaurante. Cantidades y precios simulados.",
                    category_id=categories[category],
                    supplier_id=suppliers[supplier],
                    unit_id=units[symbol].id,
                    reference_cost=Decimal(cost) if cost is not None else None,
                    minimum=Decimal(minimum),
                    maximum=max(Decimal(minimum) * 4, (Decimal(first) + Decimal(second)) * 2),
                    active=True,
                    updated_by=user_id,
                )
                session.add(ingredient)
                session.flush()
            ingredients[key] = ingredient.id
            pack = {
                "kg": ("Bolsa de 1 kg", "1"),
                "L": ("Envase de 1 L", "1"),
                "pza": ("Caja de 24 piezas", "24"),
            }[symbol]
            if key == "huevo":
                pack = ("Charola de 30 huevos", "30")
            if not session.scalar(
                select(Presentation.id).where(
                    Presentation.ingredient_id == ingredient.id, Presentation.name == pack[0]
                )
            ):
                session.add(
                    Presentation(
                        ingredient_id=ingredient.id, name=pack[0], base_quantity=Decimal(pack[1])
                    )
                )
        return suppliers, ingredients, {key: unit.id for key, unit in units.items()}

    return _run(command)


def _stamp(op_id, token, stamp, *, sale_id=None):
    def command(session):
        operation = session.get(Operation, op_id)
        if operation.idempotency_key != demo_key(token):
            raise DomainError("La operación no pertenece a esta carga demo.")
        operation.created_at = stamp
        operation.reason = "[DEMO] " + operation.reason.removeprefix("[DEMO] ")
        operation.reference = "DEMO-" + token
        if sale_id:
            session.get(Sale, sale_id).created_at = stamp
        cancellation = session.scalar(
            select(SaleCancellation).where(SaleCancellation.operation_id == op_id)
        )
        if cancellation:
            cancellation.created_at = stamp

    _run(command)


def _scenario(user_id, anchor, progress):
    suppliers, ingredients, units = _catalog(user_id, anchor)
    today = anchor.astimezone(ZONE).date()

    def moment(days, hour=8):
        return min(
            datetime.combine(today + timedelta(days=days), time(hour), ZONE), anchor
        ).astimezone(timezone.utc)

    progress("Catálogos y presentaciones listos. Registrando recepciones por proveedor…")
    for batch, days in enumerate([-9, -8]):
        for supplier in SUPPLIERS:
            lines = []
            for row in INGREDIENTS:
                key, _, _, source, _, cost, _, first, second, expiry = row
                quantity = [first, second][batch]
                if source != supplier or Decimal(quantity) == 0:
                    continue
                lines.append(
                    dict(
                        ingredient_id=ingredients[key],
                        quantity=quantity,
                        unit_cost=None
                        if cost is None
                        else str(
                            (
                                Decimal(cost) * (Decimal("1") if batch == 0 else Decimal("1.03"))
                            ).quantize(Decimal("0.000001"))
                        ),
                        code=f"DEMO-{today:%Y%m%d}-{key}-{batch + 1}",
                        received_at=moment(days),
                        expires_on=today + timedelta(days=expiry + batch * 5),
                    )
                )
            token = f"receipt-{supplier}-{batch}"
            op_id = receive(
                key=demo_key(token),
                user_id=user_id,
                supplier_id=suppliers[supplier],
                reference="DEMO-" + token,
                reason="[DEMO] Abastecimiento simulado por proveedor",
                lines=lines,
            )
            _stamp(op_id, token, moment(days))

    # Separate overdue lots make expiry and waste views useful without affecting usable stock.
    token = "receipt-expired"
    op_id = receive(
        key=demo_key(token),
        user_id=user_id,
        reason="[DEMO] Lotes de ejemplo para control de caducidades",
        reference="DEMO-" + token,
        supplier_id=suppliers["huerta"],
        lines=[
            dict(
                ingredient_id=ingredients[key],
                quantity=qty,
                unit_cost=cost,
                code="DEMO-CADUCADO-" + key,
                received_at=moment(-10),
                expires_on=today - timedelta(days=1),
            )
            for key, qty, cost in [("fresa", "0.8", "85"), ("lechuga", "0.5", "35")]
        ],
    )
    _stamp(op_id, token, moment(-10))

    progress("Creando platillos y recetas con cantidades por porción…")
    menu, prices = {}, {}
    ingredient_units = {r[0]: units[r[4]] for r in INGREDIENTS}
    for key, name, category, price, recipe in MENU:

        def existing(session):
            return session.scalar(select(MenuItem.id).where(MenuItem.code == f"DEMO-M-{key}"))

        item_id = _run(existing)
        if item_id is None:
            item_id = save_recipe(
                user_id=user_id,
                item_id=None,
                data=dict(
                    code=f"DEMO-M-{key}",
                    name=name + SUFFIX,
                    category=category,
                    description="DATOS DE PRUEBA · Precio y receta de ejemplo, no representan la carta oficial.",
                    kind="direct" if key in {"refresco", "agua", "mineral", "pan"} else "prepared",
                    price=price,
                    yield_quantity="1",
                    active=True,
                    notes="Receta sintética por porción; revisar rendimientos antes de uso real.",
                ),
                lines=[
                    dict(ingredient_id=ingredients[i], quantity=q, unit_id=ingredient_units[i])
                    for i, q in recipe.items()
                ],
            )

            def date_recipe(session):
                item = session.get(MenuItem, item_id)
                item.created_at = moment(-8, 10)
                version = session.scalar(
                    select(RecipeVersion).where(RecipeVersion.menu_item_id == item_id)
                )
                version.created_at = moment(-8, 10)

            _run(date_recipe)
        menu[key], prices[key] = item_id, Decimal(price)

    progress("Registrando tickets de la última semana con consumo PEPS…")
    rng = random.Random(7)
    sales = []
    for day, count in enumerate([8, 10, 9, 11, 12, 14, 10]):
        start = moment(day - 6, 9)
        end = min(moment(day - 6, 20), anchor)
        for ticket in range(count):
            choices = [r[0] for r in MENU[:12]]
            main = choices[(day * 3 + ticket) % len(choices)]
            drink = rng.choice(
                ["cafe", "jamaica", "licuado", "naranjada", "refresco", "agua", "mineral"]
            )
            portions = rng.choice([1, 1, 2, 2, 3])
            lines = [
                dict(menu_item_id=menu[main], quantity=portions),
                dict(menu_item_id=menu[drink], quantity=portions),
            ]
            total = (prices[main] + prices[drink]) * portions
            if ticket % 4 == 0:
                lines.append(dict(menu_item_id=menu["pan"], quantity=1))
                total += prices["pan"]
            method = ["cash", "card", "cash", "transfer", "card"][ticket % 5]
            paid = (
                ((total / 100).to_integral_value(rounding="ROUND_CEILING") * 100)
                if method == "cash"
                else None
            )
            token = f"sale-{day}-{ticket}"
            sale_id = confirm_sale(
                key=demo_key(token),
                user_id=user_id,
                lines=lines,
                method=method,
                received=paid,
                expected_total=total,
            )
            op_id = _run(lambda session: session.get(Sale, sale_id).operation_id)
            stamp = start + (end - start) * (ticket + 1) / (count + 1)
            _stamp(op_id, token, stamp, sale_id=sale_id)
            sales.append((sale_id, stamp))
            index = len(sales) - 1
            if index in {12, 45}:
                restock = index == 12
                token = f"cancel-{index}"
                cancel_sale(
                    key=demo_key(token),
                    user_id=user_id,
                    sale_id=sale_id,
                    reason="[DEMO] Ticket duplicado; pedido sin preparar"
                    if restock
                    else "[DEMO] Pedido preparado cancelado; no se recuperan insumos",
                    restock=restock,
                )
                op_id = _run(
                    lambda session: session.scalar(
                        select(SaleCancellation.operation_id).where(
                            SaleCancellation.sale_id == sale_id
                        )
                    )
                )
                _stamp(op_id, token, stamp + timedelta(minutes=4))

    progress("Agregando mermas, correcciones y un borrador de recepción…")
    token = "issue-kitchen"
    op_id = issue(
        key=demo_key(token),
        user_id=user_id,
        reason="[DEMO] Degustación interna del menú y capacitación de cocina",
        lines=[
            dict(ingredient_id=ingredients["pollo"], quantity="0.45"),
            dict(ingredient_id=ingredients["arroz"], quantity="0.25"),
            dict(ingredient_id=ingredients["aceite"], quantity="0.05"),
        ],
    )
    _stamp(op_id, token, anchor)
    for token, key, qty, category, reason in [
        (
            "waste-fresa",
            "fresa",
            "0.3",
            "expired",
            "Retiro parcial del lote vencido; resto pendiente de revisión",
        ),
        (
            "waste-cilantro",
            "cilantro",
            "0.12",
            "waste",
            "Hojas y tallos no aprovechables durante limpieza",
        ),
    ]:
        op_id = record_waste(
            key=demo_key(token),
            user_id=user_id,
            ingredient_id=ingredients[key],
            quantity=qty,
            category=category,
            reason="[DEMO] " + reason,
        )
        _stamp(op_id, token, anchor)
    token = "count-salt"

    # Compute the expected balance once and persist the command's original payload on replay.
    def count_values(session):
        existing = session.scalar(
            select(Operation).where(Operation.idempotency_key == demo_key(token))
        )
        if existing:
            from app.commerce_models import InventoryCount

            count = session.scalar(
                select(InventoryCount).where(InventoryCount.operation_id == existing.id)
            )
            return count.before_quantity, count.counted_quantity
        balance = session.scalar(
            select(func.sum(Lot.remaining_quantity)).where(Lot.ingredient_id == ingredients["sal"])
        )
        return balance, balance - Decimal("0.05")

    before, counted = _run(count_values)
    op_id = record_count(
        key=demo_key(token),
        user_id=user_id,
        ingredient_id=ingredients["sal"],
        expected_quantity=before,
        counted_quantity=counted,
        reason="[DEMO] Diferencia de 50 g en revisión de sal; ajuste documentado",
    )
    _stamp(op_id, token, anchor)
    # A fully reversible receipt illustrates correction without deleting history.
    token = "receipt-correction"
    op_id = receive(
        key=demo_key(token),
        user_id=user_id,
        reason="[DEMO] Captura duplicada detectada antes de utilizar mercancía",
        reference="DEMO-" + token,
        supplier_id=suppliers["bebidas"],
        lines=[
            dict(
                ingredient_id=ingredients["mineral"],
                quantity="12",
                unit_cost="13",
                code="DEMO-RECEPCION-CORREGIDA",
                received_at=anchor,
                expires_on=today + timedelta(days=180),
            )
        ],
    )
    _stamp(op_id, token, anchor)
    correction = reverse_receipt(
        key=demo_key("reverse-receipt"),
        user_id=user_id,
        operation_id=op_id,
        reason="[DEMO] Corrección de recepción duplicada; no se recibió mercancía adicional",
    )
    _stamp(correction, "reverse-receipt", anchor)
    draft_id = demo_key("draft-pending")
    from app.delivery_models import ReceiptDraft

    if not _run(lambda session: session.get(ReceiptDraft, draft_id) is not None):
        save_draft(
            user_id=user_id,
            key=draft_id,
            payload={
                "key": str(draft_id),
                "supplier_id": str(suppliers["huerta"]),
                "reference": "DEMO-PEDIDO-PENDIENTE",
                "reason": "[DEMO] Pedido de verduras pendiente de recepción; no afecta existencias",
                "lines-0-ingredient_id": str(ingredients["aguacate"]),
                "lines-0-quantity": "5",
                "lines-0-unit_cost": "78",
                "lines-0-code": "DEMO-PENDIENTE",
                "lines-0-expires_on": "",
                "lines-0-presentation_id": "0",
            },
        )


def seed_demo(*, user_id=None, progress=lambda message: None):
    if current_app.config["APP_ENV"] == "production":
        raise DomainError("La carga de prueba solo está habilitada en el entorno local.")
    # This lock spans the per-operation transactions; a crashed process releases it.
    with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        if not connection.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": LOCK}):
            raise DomainError("Otra carga demo está en curso. Espera a que termine.")
        try:

            def manifest(session):
                complete = session.scalar(select(AuditLog).where(AuditLog.action == COMPLETE))
                if complete:
                    return json.loads(complete.detail), None, None
                started = session.scalar(select(AuditLog).where(AuditLog.action == START))
                if started:
                    info = json.loads(started.detail)
                    if user_id is not None and user_id != info["user_id"]:
                        raise DomainError(
                            "La carga iniciada pertenece a otro administrador; usa el mismo responsable."
                        )
                    return None, info["user_id"], datetime.fromisoformat(info["anchor"])
                actor = user_id or session.scalar(
                    select(User.id)
                    .where(User.active.is_(True), User.role == "admin")
                    .order_by(User.id)
                    .limit(1)
                )
                return None, actor, datetime.now(timezone.utc)

            complete, actor, anchor = _run(manifest)
            if complete:
                return dict(complete, already_loaded=True)
            _scenario(actor, anchor, progress)

            def finish(session):
                counts = dict(
                    ingredients=session.scalar(
                        select(func.count())
                        .select_from(Ingredient)
                        .where(Ingredient.code.like("DEMO-I-%"))
                    ),
                    menu_items=session.scalar(
                        select(func.count())
                        .select_from(MenuItem)
                        .where(MenuItem.code.like("DEMO-M-%"))
                    ),
                    suppliers=len(SUPPLIERS),
                    categories=len({r[2] for r in INGREDIENTS}),
                    presentations=len(INGREDIENTS),
                    sales=74,
                    cancellations=2,
                    anchor=anchor.isoformat(),
                )
                session.add(AuditLog(user_id=actor, action=COMPLETE, detail=json.dumps(counts)))
                return counts

            return dict(_run(finish), already_loaded=False)
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": LOCK})
