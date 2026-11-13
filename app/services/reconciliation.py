"""Read-only reconciliation against one consistent PostgreSQL snapshot."""

from sqlalchemy import case, func, select, text
from sqlalchemy.orm import Session

from app.models import Allocation, Lot, Movement


def inventory_issues(engine):
    issues = []
    with (
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection,
        connection.begin(),
        Session(bind=connection) as session,
    ):
        session.execute(text("SET TRANSACTION READ ONLY"))
        by_lot = (
            select(Allocation.lot_id, func.sum(Allocation.quantity).label("quantity"))
            .group_by(Allocation.lot_id)
            .subquery()
        )
        invalid_lots = session.execute(
            select(Lot.id, Lot.remaining_quantity, func.coalesce(by_lot.c.quantity, 0))
            .outerjoin(by_lot, by_lot.c.lot_id == Lot.id)
            .where(Lot.remaining_quantity != func.coalesce(by_lot.c.quantity, 0))
        ).all()
        for lot_id, balance, allocated in invalid_lots:
            issues.append(f"Lote {lot_id}: saldo {balance}, asignaciones {allocated}")
        by_movement = (
            select(
                Allocation.movement_id,
                func.sum(Allocation.quantity).label("quantity"),
                func.count(case((Allocation.unit_cost.is_(None), 1))).label("unknown"),
                func.round(func.sum(func.abs(Allocation.quantity) * Allocation.unit_cost), 6).label(
                    "cost"
                ),
            )
            .group_by(Allocation.movement_id)
            .subquery()
        )
        expected_cost = case((by_movement.c.unknown > 0, None), else_=by_movement.c.cost)
        invalid_movements = session.execute(
            select(Movement.id)
            .outerjoin(by_movement, by_movement.c.movement_id == Movement.id)
            .where(
                (Movement.quantity != func.coalesce(by_movement.c.quantity, 0))
                | Movement.cost.is_distinct_from(expected_cost)
            )
        ).all()
        for (movement_id,) in invalid_movements:
            issues.append(
                f"Movimiento {movement_id}: cantidad o costo no coincide con sus asignaciones"
            )
        mismatched = session.execute(
            select(Allocation.id)
            .join(Movement, Movement.id == Allocation.movement_id)
            .join(Lot, Lot.id == Allocation.lot_id)
            .where(Movement.ingredient_id != Lot.ingredient_id)
        ).all()
        for (allocation_id,) in mismatched:
            issues.append(f"Asignación {allocation_id}: el ingrediente no coincide con el lote")
        lots = (
            select(Lot.ingredient_id, func.sum(Lot.remaining_quantity).label("quantity"))
            .group_by(Lot.ingredient_id)
            .subquery()
        )
        movements = (
            select(Movement.ingredient_id, func.sum(Movement.quantity).label("quantity"))
            .group_by(Movement.ingredient_id)
            .subquery()
        )
        for row in session.execute(
            select(func.coalesce(lots.c.ingredient_id, movements.c.ingredient_id))
            .select_from(
                lots.join(movements, lots.c.ingredient_id == movements.c.ingredient_id, full=True)
            )
            .where(func.coalesce(lots.c.quantity, 0) != func.coalesce(movements.c.quantity, 0))
        ):
            issues.append(f"Ingrediente {row[0]}: saldos de lotes y movimientos no coinciden")
    return issues
