import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier, Event
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import Allocation, Lot, Movement, Operation, Presentation
from app.services.inventory import issue, receive, reverse_issue
from app.services.numbers import DomainError

pytestmark = pytest.mark.postgres


def receipt(ids, quantity="10", cost="20", **extra):
    return receive(
        key=uuid.uuid4(),
        user_id=ids["user"],
        lines=[dict(ingredient_id=ids["ingredient"], quantity=quantity, unit_cost=cost, **extra)],
    )


def withdraw(ids, quantity, **extra):
    return issue(
        key=extra.pop("key", uuid.uuid4()),
        user_id=ids["user"],
        lines=[dict(ingredient_id=ids["ingredient"], quantity=quantity)],
        reason="Consumo de prueba",
        **extra,
    )


@pytest.mark.parametrize("requested,expected", [("3", "7"), ("10", "0")])
def test_single_lot_and_exact_consumption(app, seeded, requested, expected):
    with app.app_context():
        receipt(seeded)
        op = withdraw(seeded, requested)
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal(expected)
        assert (
            db.session.scalar(select(Movement.cost).where(Movement.operation_id == op))
            == Decimal(requested) * 20
        )
        assert (
            db.session.scalar(
                select(func.count(Allocation.id)).join(Movement).where(Movement.operation_id == op)
            )
            == 1
        )


def test_fifo_two_lots_historical_costs(app, seeded):
    with app.app_context():
        receipt(seeded, received_at=datetime.now(timezone.utc) - timedelta(days=2))
        receipt(seeded, quantity="15", cost="24")
        op = withdraw(seeded, "12")
        assert db.session.scalars(
            select(Lot.remaining_quantity).order_by(Lot.received_at, Lot.id)
        ).all() == [Decimal("0"), Decimal("13")]
        assert db.session.scalar(
            select(Movement.cost).where(Movement.operation_id == op)
        ) == Decimal("248")
        assert db.session.scalars(
            select(Allocation.quantity)
            .join(Movement)
            .where(Movement.operation_id == op)
            .order_by(Allocation.lot_id)
        ).all() == [Decimal("-10"), Decimal("-2")]


def test_tie_break_and_depleted_lots(app, seeded):
    with app.app_context():
        when = datetime.now(timezone.utc) - timedelta(days=1)
        receipt(seeded, quantity="1", cost="4", received_at=when)
        receipt(seeded, quantity="2", cost="5", received_at=when)
        withdraw(seeded, "1")
        op = withdraw(seeded, "1")
        assert db.session.scalars(select(Lot.remaining_quantity).order_by(Lot.id)).all() == [
            Decimal("0"),
            Decimal("1"),
        ]
        assert db.session.scalar(
            select(Movement.cost).where(Movement.operation_id == op)
        ) == Decimal("5")


def test_expired_lots_are_ineligible(app, seeded):
    with app.app_context():
        yesterday = datetime.now(ZoneInfo("America/Mexico_City")).date() - timedelta(days=1)
        receipt(seeded, expires_on=yesterday)
        with pytest.raises(DomainError, match="insuficiente"):
            withdraw(seeded, "1")
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10")
        assert db.session.scalar(select(func.count(Operation.id))) == 1


def test_multi_ingredient_failure_rolls_back_everything(app, seeded):
    with app.app_context():
        receipt(seeded)
        with pytest.raises(DomainError):
            issue(
                key=uuid.uuid4(),
                user_id=seeded["user"],
                reason="Fallo de prueba",
                lines=[
                    dict(ingredient_id=seeded["ingredient"], quantity="5"),
                    dict(ingredient_id=seeded["ingredient2"], quantity="1"),
                ],
            )
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10")
        assert db.session.scalar(select(func.count(Movement.id))) == 1
        assert db.session.scalar(select(func.count(Allocation.id))) == 1
        assert db.session.scalar(select(func.count(Operation.id))) == 1


def test_receipt_idempotency_and_conflicting_payload(app, seeded):
    with app.app_context():
        kwargs = dict(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="10")],
        )
        first = receive(**kwargs)
        assert receive(**kwargs) == first
        kwargs["lines"][0]["quantity"] = "11"
        with pytest.raises(DomainError, match="diferente"):
            receive(**kwargs)
        assert db.session.scalar(select(func.count(Lot.id))) == 1


def test_issue_idempotency_and_reversal(app, seeded):
    with app.app_context():
        receipt(seeded)
        key = uuid.uuid4()
        op = withdraw(seeded, "6", key=key)
        assert withdraw(seeded, "6", key=key) == op
        reverse_key = uuid.uuid4()
        reversal = reverse_issue(
            key=reverse_key, user_id=seeded["user"], operation_id=op, reason="Corrección de prueba"
        )
        assert (
            reverse_issue(
                key=reverse_key,
                user_id=seeded["user"],
                operation_id=op,
                reason="Corrección de prueba",
            )
            == reversal
        )
        with pytest.raises(DomainError, match="ya fue revertida"):
            reverse_issue(
                key=uuid.uuid4(), user_id=seeded["user"], operation_id=op, reason="Otra reversión"
            )
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10")
        assert db.session.scalar(select(func.sum(Movement.quantity))) == Decimal("10")
        assert db.session.scalar(select(func.sum(Allocation.quantity))) == Decimal("10")
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


def test_unknown_cost_preserved(app, seeded):
    with app.app_context():
        receipt(seeded, cost=None)
        op = withdraw(seeded, "1")
        assert db.session.scalar(select(Movement.cost).where(Movement.operation_id == op)) is None


def test_database_prevents_negative_stock(app, seeded):
    with app.app_context():
        receipt(seeded)
        lot = db.session.scalar(select(Lot))
        lot.remaining_quantity = Decimal("-1")
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_concurrent_consumption_cannot_oversell(app, seeded):
    with app.app_context():
        receipt(seeded)
    barrier = Barrier(2)

    def consumer():
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return withdraw(seeded, "7")
            except DomainError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: consumer(), range(2)))
    assert sum(result is not None for result in results) == 1
    with app.app_context():
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("3")
        assert (
            db.session.scalar(select(func.count(Operation.id)).where(Operation.kind == "issue"))
            == 1
        )


def test_concurrent_duplicate_request_records_once(app, seeded):
    with app.app_context():
        receipt(seeded)
    barrier = Barrier(2)
    key = uuid.uuid4()

    def consumer():
        with app.app_context():
            barrier.wait(timeout=5)
            return withdraw(seeded, "3", key=key)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: consumer(), range(2)))
    assert results[0] == results[1]
    with app.app_context():
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("7")


def test_locked_oldest_lot_is_not_skipped(app, seeded):
    with app.app_context():
        receipt(
            seeded,
            quantity="2",
            cost="10",
            received_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        receipt(seeded, quantity="2", cost="20")
        engine = db.engine
        oldest = db.session.scalar(select(Lot.id).order_by(Lot.received_at, Lot.id).limit(1))
    started = Event()
    finished = Event()

    def consume():
        with app.app_context():
            started.set()
            result = withdraw(seeded, "1")
            finished.set()
            return result

    with Session(engine) as holder, holder.begin():
        holder.scalar(select(Lot).where(Lot.id == oldest).with_for_update(of=Lot))
        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(consume)
            assert started.wait(timeout=5)
            assert not finished.wait(timeout=0.3)
            holder.commit()
            op = future.result(timeout=10)
    with app.app_context():
        assert db.session.scalar(
            select(Movement.cost).where(Movement.operation_id == op)
        ) == Decimal("10")


def test_timezone_aware_persistence(app, seeded):
    with app.app_context():
        op_id = receipt(seeded)
        operation = db.session.get(Operation, op_id)
        assert operation.created_at.utcoffset() == timedelta(0)


def test_presentation_quantity_and_price_are_converted_on_server(app, seeded):
    with app.app_context():
        presentation = Presentation(
            ingredient_id=seeded["ingredient"], name="Costal de prueba", base_quantity=Decimal("25")
        )
        db.session.add(presentation)
        db.session.commit()
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[
                dict(
                    ingredient_id=seeded["ingredient"],
                    presentation_id=presentation.id,
                    quantity="2",
                    unit_cost="750",
                )
            ],
        )
        lot = db.session.scalar(select(Lot))
        assert lot.original_quantity == Decimal("50")
        assert lot.unit_cost == Decimal("30")
        assert db.session.scalar(select(Movement.cost)) == Decimal("1500")


def test_wrong_ingredient_presentation_rolls_back(app, seeded):
    with app.app_context():
        presentation = Presentation(
            ingredient_id=seeded["ingredient2"],
            name="Otra presentación",
            base_quantity=Decimal("10"),
        )
        db.session.add(presentation)
        db.session.commit()
        with pytest.raises(DomainError, match="no corresponde"):
            receive(
                key=uuid.uuid4(),
                user_id=seeded["user"],
                lines=[
                    dict(
                        ingredient_id=seeded["ingredient"],
                        presentation_id=presentation.id,
                        quantity="1",
                        unit_cost="10",
                    )
                ],
            )
        assert db.session.scalar(select(func.count(Lot.id))) == 0
        assert db.session.scalar(select(func.count(Operation.id))) == 0


def test_multi_ingredient_concurrent_order_is_consistent(app, seeded):
    with app.app_context():
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[
                dict(ingredient_id=seeded["ingredient"], quantity="10"),
                dict(ingredient_id=seeded["ingredient2"], quantity="10"),
            ],
        )
    barrier = Barrier(2)
    ids = [seeded["ingredient"], seeded["ingredient2"]]

    def consumer(order):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return issue(
                    key=uuid.uuid4(),
                    user_id=seeded["user"],
                    reason="Consumo simultáneo",
                    lines=[dict(ingredient_id=iid, quantity="7") for iid in order],
                )
            except DomainError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(consumer, [ids, list(reversed(ids))]))
    assert sum(result is not None for result in results) == 1
    with app.app_context():
        assert db.session.scalars(select(Lot.remaining_quantity).order_by(Lot.id)).all() == [
            Decimal("3"),
            Decimal("3"),
        ]


def test_concurrent_receipt_duplicate_records_one_lot(app, seeded):
    barrier = Barrier(2)
    key = uuid.uuid4()

    def receiver(_):
        with app.app_context():
            barrier.wait(timeout=5)
            return receive(
                key=key,
                user_id=seeded["user"],
                lines=[dict(ingredient_id=seeded["ingredient"], quantity="4", unit_cost="10")],
            )

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(receiver, range(2)))
    assert results[0] == results[1]
    with app.app_context():
        assert db.session.scalar(select(func.count(Lot.id))) == 1
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("4")
