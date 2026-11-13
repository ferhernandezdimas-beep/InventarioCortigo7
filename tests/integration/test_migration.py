import uuid

import pytest
from flask_migrate import downgrade, upgrade
from sqlalchemy import text

from app.extensions import db

pytestmark = pytest.mark.postgres


def test_upgrade_preserves_preexisting_user_and_inventory_history(app):
    with app.app_context():
        # Work only inside the test's new private schema; never downgrade a user's database.
        downgrade(revision="afbfed7dbf1a")
        op_id = uuid.uuid4()
        statements = [
            "INSERT INTO users (id,name,email,password_hash,role,active) VALUES (900,'Usuario previo','previous@example.com','test-hash','admin',true)",
            "INSERT INTO ingredient_categories (id,name) VALUES (900,'Categoría previa')",
            "INSERT INTO ingredients (id,name,category_id,unit_id,minimum,active,updated_by) SELECT 900,'Ingrediente previo',900,id,0,true,900 FROM measurement_units WHERE symbol='kg'",
        ]
        for statement in statements:
            db.session.execute(text(statement))
        db.session.execute(
            text(
                "INSERT INTO inventory_operations (id,idempotency_key,payload_hash,kind,reason,user_id,created_at) VALUES (:id,:key,:hash,'receipt','Recepción previa',900,now())"
            ),
            dict(id=op_id, key=uuid.uuid4(), hash="a" * 64),
        )
        db.session.execute(
            text(
                "INSERT INTO inventory_lots (id,ingredient_id,operation_id,original_quantity,remaining_quantity,unit_cost,received_at) VALUES (900,900,:op,12.5,12.5,20.125,now())"
            ),
            dict(op=op_id),
        )
        db.session.execute(
            text(
                "INSERT INTO inventory_movements (id,operation_id,ingredient_id,quantity,cost) VALUES (900,:op,900,12.5,251.5625)"
            ),
            dict(op=op_id),
        )
        db.session.execute(
            text(
                "INSERT INTO inventory_movement_allocations (movement_id,lot_id,quantity,unit_cost) VALUES (900,900,12.5,20.125)"
            )
        )
        db.session.commit()
        upgrade()
        assert db.session.scalar(text("SELECT count(*) FROM users WHERE id=900")) == 1
        assert (
            db.session.scalar(text("SELECT source FROM inventory_lots WHERE id=900")) == "receipt"
        )
        assert (
            str(
                db.session.scalar(
                    text("SELECT remaining_quantity FROM inventory_lots WHERE id=900")
                )
            )
            == "12.500000"
        )
        assert (
            db.session.scalar(
                text("SELECT count(*) FROM inventory_operations WHERE id=:op"), dict(op=op_id)
            )
            == 1
        )
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0
