import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.commerce_models import MenuItem, Sale, SaleCancellation
from app.delivery_models import ReceiptDraft
from app.extensions import db
from app.models import Allocation, AuditLog, Ingredient, Lot, Movement, Operation, Supplier, User
from app.services import demo
from app.services.numbers import DomainError
from app.services.presentation import normalize_presentation
from app.services.queries import inventory_query
from app.services.receipts import validated_form
from app.services.reconciliation import inventory_issues
from app.services.sales import confirm_sale
from tests.integration.test_web import login

pytestmark = pytest.mark.postgres


def counts():
    return {
        model.__tablename__: db.session.scalar(select(func.count()).select_from(model))
        for model in [
            User,
            Ingredient,
            Supplier,
            Lot,
            Movement,
            Allocation,
            Operation,
            MenuItem,
            Sale,
            AuditLog,
        ]
    }


def test_scenario_preserves_real_data_and_replays_without_duplicates(app, seeded, client):
    with app.app_context():
        actor = db.session.get(User, seeded["user"])
        password_hash = actor.password_hash
        actual = db.session.get(Ingredient, seeded["ingredient"])
        actual_name = actual.name
        supplier = Supplier(name="Proveedor real previo", notes="Conservar esta nota", active=True)
        db.session.add(supplier)
        db.session.commit()
        supplier_id = supplier.id
        result = demo.seed_demo(user_id=actor.id)
        assert result["ingredients"] == 46
        assert result["menu_items"] == 20
        assert result["sales"] == 74
        assert not result["already_loaded"]
        db.session.expire_all()
        assert db.session.get(User, actor.id).password_hash == password_hash
        assert db.session.get(Ingredient, seeded["ingredient"]).name == actual_name
        assert db.session.get(Supplier, supplier_id).notes == "Conservar esta nota"
        assert db.session.scalar(select(func.count()).select_from(Sale)) == 74
        assert db.session.scalar(select(func.count()).select_from(SaleCancellation)) == 2
        assert (
            db.session.scalar(
                select(func.count()).select_from(Lot).where(Lot.remaining_quantity < 0)
            )
            == 0
        )
        assert inventory_issues(db.engine) == []
        # Every consumed lot predates its synthetic sale; no time-travel consumption.
        assert not db.session.scalar(
            select(Allocation.id)
            .join(Movement)
            .join(Operation)
            .join(Lot, Lot.id == Allocation.lot_id)
            .where(Operation.kind == "sale", Lot.received_at > Operation.created_at)
            .limit(1)
        )
        assert not db.session.scalar(
            select(Sale.id).where(Sale.created_at > datetime.now(timezone.utc)).limit(1)
        )
        rows = db.session.execute(inventory_query().where(Ingredient.code.like("DEMO-I-%"))).all()
        assert any(row.available == 0 for row in rows)
        assert any(0 < row.available < row.Ingredient.minimum for row in rows)
        assert any(row.unknown > 0 for row in rows)
        assert all(
            sale.total > 0 and sale.cost is not None
            for sale in db.session.scalars(select(Sale)).unique()
        )
        draft = db.session.get(ReceiptDraft, demo.demo_key("draft-pending"))
        assert draft.status == "draft" and draft.operation_id is None
        form = validated_form(db.session, draft.payload)
        assert form.lines[0].quantity.data == Decimal("5")
        sample_ingredient = db.session.scalar(
            select(Ingredient.id).where(Ingredient.code == "DEMO-I-fresa")
        )
        sample_item = db.session.scalar(
            select(MenuItem.id).where(MenuItem.code == "DEMO-M-chilaquiles")
        )
        sample_sale = db.session.scalar(select(Sale.id).limit(1))
        sample_operation = db.session.scalar(select(Operation.id).limit(1))
        before = counts()
        replay = demo.seed_demo(user_id=actor.id)
        assert replay["already_loaded"]
        assert counts() == before
        additional_sale = confirm_sale(
            key=uuid.uuid4(),
            user_id=actor.id,
            lines=[dict(menu_item_id=sample_item, quantity=1)],
            method="card",
        )
        financial = list(
            db.session.execute(
                select(Movement.id, Movement.quantity, Movement.cost).order_by(Movement.id)
            )
        )
        balances = list(
            db.session.execute(
                select(
                    Lot.id, Lot.original_quantity, Lot.remaining_quantity, Lot.unit_cost
                ).order_by(Lot.id)
            )
        )
        claims = list(
            db.session.execute(
                select(Operation.id, Operation.idempotency_key, Operation.payload_hash).order_by(
                    Operation.id
                )
            )
        )
        original = db.session.get(Ingredient, seeded["ingredient"])
        original.name = "Jitomate saladet"
        db.session.commit()
        with pytest.raises(DomainError, match="otro ingrediente"):
            normalize_presentation()
        assert db.session.scalar(select(Ingredient.id).where(Ingredient.code == "DEMO-I-jitomate"))
        original.name = actual_name
        db.session.commit()
        presented = normalize_presentation()
        assert presented["ingredients"] == 46 and presented["products"] == 20
        assert (
            list(
                db.session.execute(
                    select(Movement.id, Movement.quantity, Movement.cost).order_by(Movement.id)
                )
            )
            == financial
        )
        assert (
            list(
                db.session.execute(
                    select(
                        Lot.id, Lot.original_quantity, Lot.remaining_quantity, Lot.unit_cost
                    ).order_by(Lot.id)
                )
            )
            == balances
        )
        assert (
            list(
                db.session.execute(
                    select(
                        Operation.id, Operation.idempotency_key, Operation.payload_hash
                    ).order_by(Operation.id)
                )
            )
            == claims
        )
        assert inventory_issues(db.engine) == []
        assert normalize_presentation()["already_applied"]
        assert demo.seed_demo()["already_loaded"]
    assert login(client).status_code == 302
    for path in [
        "/",
        "/catalogos/categorias",
        "/catalogos/presentaciones",
        "/inventario/lotes",
        "/inventario/lotes?status=expired",
        "/inventario/lotes?status=soon",
        f"/catalogos/ingredientes/{sample_ingredient}",
        "/inventario/movimientos",
        f"/inventario/operaciones/{sample_operation}",
        "/inventario/entradas/borradores",
        f"/inventario/entradas/borradores/{demo.demo_key('draft-pending')}/editar",
        "/operacion/platillos",
        f"/operacion/platillos/{sample_item}",
        "/ventas/punto-de-venta",
        "/ventas/",
        f"/ventas/{sample_sale}",
        f"/ventas/{additional_sale}",
        "/reportes/",
        *[
            f"/reportes/almacen?kind={kind}"
            for kind in ["inventory", "receipts", "issues", "lots", "waste", "costs"]
        ],
    ]:
        response = client.get(path, follow_redirects=True)
        assert response.status_code == 200, path
        assert "Datos de prueba cargados." not in response.text
        assert "(demo)" not in response.text
        assert "[DEMO]" not in response.text


def test_interrupted_scenario_resumes_with_same_anchor(app, seeded, monkeypatch):
    with app.app_context():
        original = demo.confirm_sale
        calls = 0

        def interrupted(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("Interrupción simulada de la carga")
            return original(**kwargs)

        monkeypatch.setattr(demo, "confirm_sale", interrupted)
        with pytest.raises(RuntimeError, match="Interrupción"):
            demo.seed_demo(user_id=seeded["user"])
        assert db.session.scalar(select(func.count()).select_from(Sale)) == 1
        anchor = db.session.scalar(select(AuditLog.detail).where(AuditLog.action == demo.START))
        monkeypatch.setattr(demo, "confirm_sale", original)
        result = demo.seed_demo(user_id=seeded["user"])
        assert result["sales"] == 74
        assert db.session.scalar(select(func.count()).select_from(Sale)) == 74
        assert (
            db.session.scalar(select(AuditLog.detail).where(AuditLog.action == demo.START))
            == anchor
        )
        assert inventory_issues(db.engine) == []


def test_demo_refuses_collisions_without_overwriting_existing_rows(app, seeded):
    with app.app_context():
        actual = db.session.get(Ingredient, seeded["ingredient"])
        actual.code = "DEMO-I-jitomate"
        db.session.commit()
        before = counts()
        with pytest.raises(DomainError, match="colisión"):
            demo.seed_demo(user_id=seeded["user"])
        assert counts() == before


def test_demo_refuses_production_and_non_admin(app, seeded):
    with app.app_context():
        app.config["APP_ENV"] = "production"
        with pytest.raises(DomainError, match="local"):
            demo.seed_demo(user_id=seeded["user"])
        app.config["APP_ENV"] = "development"
        actor = db.session.get(User, seeded["user"])
        actor.role = "cashier"
        db.session.commit()
        before = counts()
        with pytest.raises(DomainError, match="administrador"):
            demo.seed_demo(user_id=actor.id)
        assert counts() == before
