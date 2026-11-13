import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.commerce_models import (
    InventoryCount,
    MenuItem,
    RecipeVersion,
    Sale,
    SaleCancellation,
    SaleIngredientSnapshot,
    SaleItem,
)
from app.extensions import db
from app.models import Lot, Movement, Operation, Unit
from app.services.adjustments import record_count, record_waste
from app.services.inventory import receive, reverse_issue
from app.services.numbers import DomainError
from app.services.recipes import estimate_recipe, latest_recipe, save_recipe
from app.services.sales import cancel_sale, confirm_sale

pytestmark = pytest.mark.postgres


def recipe_data(**overrides):
    data = dict(
        name="Platillo de prueba",
        code=None,
        category="Cocina de prueba",
        description=None,
        kind="prepared",
        active=True,
        price="100.00",
        yield_quantity="2",
        notes="Versión sintética",
    )
    data.update(overrides)
    return data


def recipe_lines(ids):
    return [
        dict(ingredient_id=ids["ingredient"], quantity="0.4", unit_id=ids["unit"]),
        dict(ingredient_id=ids["ingredient2"], quantity="0.2", unit_id=ids["unit"]),
    ]


@pytest.fixture
def prepared(app, seeded):
    with app.app_context():
        item_id = save_recipe(
            user_id=seeded["user"], item_id=None, data=recipe_data(), lines=recipe_lines(seeded)
        )
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[
                dict(ingredient_id=seeded["ingredient"], quantity="10", unit_cost="20"),
                dict(ingredient_id=seeded["ingredient2"], quantity="10", unit_cost="10"),
            ],
        )
        return {**seeded, "item": item_id}


def sell(ids, quantity=2, **overrides):
    kwargs = dict(
        key=uuid.uuid4(),
        user_id=ids["user"],
        lines=[dict(menu_item_id=ids["item"], quantity=quantity)],
        method="cash",
        received="1000.00",
    )
    kwargs.update(overrides)
    return confirm_sale(**kwargs)


def test_sale_consumes_recipe_quantities_and_keeps_snapshots(app, prepared):
    with app.app_context():
        sale_id = sell(prepared)
        sale = db.session.get(Sale, sale_id)
        assert sale.total == Decimal("200.00")
        assert sale.change == Decimal("800.00")
        assert sale.cost == Decimal("10")
        assert db.session.scalars(
            select(Lot.remaining_quantity).order_by(Lot.ingredient_id)
        ).all() == [Decimal("9.6"), Decimal("9.8")]
        assert db.session.scalars(
            select(SaleIngredientSnapshot.quantity).order_by(SaleIngredientSnapshot.ingredient_id)
        ).all() == [Decimal("0.4"), Decimal("0.2")]
        assert sale.items[0].unit_price == Decimal("100.00")
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


def test_sale_multiple_dishes_share_inventory_atomically(app, prepared):
    with app.app_context():
        another = save_recipe(
            user_id=prepared["user"],
            item_id=None,
            data=recipe_data(
                name="Producto directo de prueba", kind="direct", price="30.00", yield_quantity="1"
            ),
            lines=[
                dict(ingredient_id=prepared["ingredient"], quantity="0.1", unit_id=prepared["unit"])
            ],
        )
        sale_id = sell(
            prepared,
            lines=[
                dict(menu_item_id=prepared["item"], quantity=2),
                dict(menu_item_id=another, quantity=3),
            ],
        )
        sale = db.session.get(Sale, sale_id)
        assert sale.total == Decimal("290")
        assert sale.cost == Decimal("16")
        assert len(sale.items) == 2
        assert db.session.scalar(
            select(func.sum(Movement.quantity)).where(Movement.operation_id == sale.operation_id)
        ) == Decimal("-0.9")


def test_sale_failure_rolls_back_sale_items_payments_and_stock(app, seeded):
    with app.app_context():
        item = save_recipe(
            user_id=seeded["user"], item_id=None, data=recipe_data(), lines=recipe_lines(seeded)
        )
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="10")],
        )
        with pytest.raises(DomainError, match="insuficiente"):
            sell({**seeded, "item": item})
        for model in [Sale, SaleItem, SaleIngredientSnapshot]:
            assert db.session.scalar(select(func.count()).select_from(model)) == 0
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10")
        assert db.session.scalar(select(func.count(Operation.id))) == 1


@pytest.mark.parametrize("method,received", [("cash", "0.01"), ("unknown", "1000")])
def test_sale_rejects_invalid_payment(app, prepared, method, received):
    with app.app_context(), pytest.raises(DomainError):
        sell(prepared, method=method, received=received)


def test_non_cash_records_declared_total_and_no_change(app, prepared):
    with app.app_context():
        sale = db.session.get(Sale, sell(prepared, method="card", received=None))
        assert sale.received == sale.total
        assert sale.change == 0


def test_sale_rejects_changed_prices(app, prepared):
    with app.app_context():
        with pytest.raises(DomainError, match="precios cambiaron"):
            sell(prepared, expected_total="199.99")
        assert db.session.scalar(select(func.count(Sale.id))) == 0


def test_recipe_update_does_not_change_historical_sale(app, prepared):
    with app.app_context():
        sale_id = sell(prepared)
        original_recipe_id = db.session.scalar(select(SaleItem.recipe_version_id))
        save_recipe(
            user_id=prepared["user"],
            item_id=prepared["item"],
            expected_version=1,
            data=recipe_data(name="Nombre nuevo", price="125.00"),
            lines=[
                dict(ingredient_id=prepared["ingredient"], quantity="0.8", unit_id=prepared["unit"])
            ],
        )
        sale = db.session.get(Sale, sale_id)
        assert sale.items[0].name == "Platillo de prueba"
        assert sale.total == Decimal("200") and sale.cost == Decimal("10")
        assert sale.items[0].recipe_version_id == original_recipe_id
        assert db.session.scalar(select(func.count(RecipeVersion.id))) == 2


def test_recipe_stale_version_is_rejected(app, prepared):
    with app.app_context(), pytest.raises(DomainError, match="cambió mientras"):
        save_recipe(
            user_id=prepared["user"],
            item_id=prepared["item"],
            expected_version=0,
            data=recipe_data(),
            lines=recipe_lines(prepared),
        )


def test_recipe_unit_conversion_and_dimension_validation(app, seeded):
    with app.app_context():
        gram = db.session.scalar(select(Unit.id).where(Unit.symbol == "g"))
        liter = db.session.scalar(select(Unit.id).where(Unit.symbol == "L"))
        item = save_recipe(
            user_id=seeded["user"],
            item_id=None,
            data=recipe_data(),
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="400", unit_id=gram)],
        )
        assert latest_recipe(db.session, item).lines[0].quantity == Decimal("0.4")
        with pytest.raises(DomainError, match="mezclar"):
            save_recipe(
                user_id=seeded["user"],
                item_id=None,
                data=recipe_data(name="Inválida"),
                lines=[dict(ingredient_id=seeded["ingredient"], quantity="1", unit_id=liter)],
            )
        assert db.session.scalar(select(func.count(MenuItem.id))) == 1


def test_estimate_is_fifo_and_does_not_reserve_stock(app, prepared):
    with app.app_context():
        estimate = estimate_recipe(db.session, latest_recipe(db.session, prepared["item"]))
        assert estimate["total"] == Decimal("5")
        assert estimate["complete"] is True
        assert db.session.scalar(select(func.sum(Lot.remaining_quantity))) == 20


def test_unknown_cost_is_not_presented_as_total(app, seeded):
    with app.app_context():
        item = save_recipe(
            user_id=seeded["user"], item_id=None, data=recipe_data(), lines=recipe_lines(seeded)
        )
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[
                dict(ingredient_id=seeded["ingredient"], quantity="10"),
                dict(ingredient_id=seeded["ingredient2"], quantity="10", unit_cost="10"),
            ],
        )
        assert estimate_recipe(db.session, latest_recipe(db.session, item))["total"] is None
        assert db.session.get(Sale, sell({**seeded, "item": item})).cost is None


def test_concurrent_sales_do_not_oversell(app, prepared):
    barrier = Barrier(2)

    def consumer(_):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return sell(prepared, quantity=35, received="5000.00")
            except DomainError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(consumer, range(2)))
    assert sum(result is not None for result in results) == 1
    with app.app_context():
        assert db.session.scalar(select(func.count(Sale.id))) == 1
        assert db.session.scalars(
            select(Lot.remaining_quantity).order_by(Lot.ingredient_id)
        ).all() == [Decimal("3"), Decimal("6.5")]


def test_concurrent_duplicate_sale_is_charged_once(app, prepared):
    barrier, key = Barrier(2), uuid.uuid4()

    def consumer(_):
        with app.app_context():
            barrier.wait(timeout=5)
            return sell(prepared, key=key)

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(consumer, range(2)))
    assert results[0] == results[1]
    with app.app_context():
        assert db.session.scalar(select(func.count(Sale.id))) == 1
        assert db.session.scalar(select(func.sum(Lot.remaining_quantity))) == Decimal("19.4")


@pytest.mark.parametrize("restock,expected", [(False, "19.4"), (True, "20")])
def test_cancellation_is_auditable_and_idempotent(app, prepared, restock, expected):
    with app.app_context():
        sale_id = sell(prepared)
        kwargs = dict(
            key=uuid.uuid4(),
            user_id=prepared["user"],
            sale_id=sale_id,
            reason="Cancelación de prueba",
            restock=restock,
        )
        assert cancel_sale(**kwargs) == sale_id
        assert cancel_sale(**kwargs) == sale_id
        with pytest.raises(DomainError, match="ya está cancelada"):
            cancel_sale(**{**kwargs, "key": uuid.uuid4()})
        assert db.session.scalar(select(func.sum(Lot.remaining_quantity))) == Decimal(expected)
        assert db.session.scalar(select(func.count(SaleCancellation.id))) == 1
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


def test_expired_lots_cannot_be_restocked_on_cancellation(app, prepared):
    with app.app_context():
        sale_id = sell(prepared)
        yesterday = datetime.now(ZoneInfo("America/Mexico_City")).date() - timedelta(days=1)
        for lot in db.session.scalars(select(Lot)):
            lot.expires_on = yesterday
        db.session.commit()
        with pytest.raises(DomainError, match="caducados"):
            cancel_sale(
                key=uuid.uuid4(),
                user_id=prepared["user"],
                sale_id=sale_id,
                reason="Prueba",
                restock=True,
            )
        assert db.session.scalar(select(func.count(SaleCancellation.id))) == 0


def test_sale_operation_cannot_use_manual_issue_reversal(app, prepared):
    with app.app_context():
        sale = db.session.get(Sale, sell(prepared))
        with pytest.raises(DomainError, match="Solamente"):
            reverse_issue(
                key=uuid.uuid4(),
                user_id=prepared["user"],
                operation_id=sale.operation_id,
                reason="No autorizado por esta vía",
            )


@pytest.mark.parametrize("counted,expected", [("19", "19"), ("21", "21")])
def test_controlled_count_updates_balance_and_records_before_after(
    app, prepared, counted, expected
):
    with app.app_context():
        op = record_count(
            key=uuid.uuid4(),
            user_id=prepared["user"],
            ingredient_id=prepared["ingredient"],
            expected_quantity="10",
            counted_quantity=counted,
            reason="Conteo y procedencia documentados",
        )
        count = db.session.scalar(select(InventoryCount).where(InventoryCount.operation_id == op))
        assert count.before_quantity == 10 and count.counted_quantity == Decimal(expected)
        assert db.session.scalar(
            select(func.sum(Lot.remaining_quantity)).where(
                Lot.ingredient_id == prepared["ingredient"]
            )
        ) == Decimal(expected)
        recovered = db.session.scalar(select(Lot).where(Lot.source == "recovered"))
        assert recovered is not None and recovered.unit_cost is None
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


def test_negative_count_uses_physical_lots_and_stale_count_rejected(app, prepared):
    with app.app_context():
        record_count(
            key=uuid.uuid4(),
            user_id=prepared["user"],
            ingredient_id=prepared["ingredient"],
            expected_quantity="10",
            counted_quantity="8",
            reason="Diferencia observada",
        )
        assert (
            db.session.scalar(
                select(Lot.remaining_quantity).where(Lot.ingredient_id == prepared["ingredient"])
            )
            == 8
        )
        with pytest.raises(DomainError, match="cambió durante"):
            record_count(
                key=uuid.uuid4(),
                user_id=prepared["user"],
                ingredient_id=prepared["ingredient"],
                expected_quantity="10",
                counted_quantity="9",
                reason="Conteo anterior",
            )


def test_expired_waste_consumes_only_expired_lots(app, prepared):
    with app.app_context():
        lot = db.session.scalar(select(Lot).where(Lot.ingredient_id == prepared["ingredient"]))
        lot.expires_on = datetime.now(ZoneInfo("America/Mexico_City")).date() - timedelta(days=1)
        db.session.commit()
        record_waste(
            key=uuid.uuid4(),
            user_id=prepared["user"],
            ingredient_id=prepared["ingredient"],
            quantity="2",
            category="expired",
            reason="Caducidad verificada",
        )
        db.session.expire_all()
        assert lot.remaining_quantity == 8
        with pytest.raises(DomainError, match="insuficiente"):
            record_waste(
                key=uuid.uuid4(),
                user_id=prepared["user"],
                ingredient_id=prepared["ingredient2"],
                quantity="2",
                category="expired",
                reason="No debe usar lotes vigentes",
            )


def web_csrf(client, path="/login"):
    response = client.get(path)
    assert response.status_code == 200, response.text[:800]
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text).group(1)


def web_login(client):
    assert (
        client.post(
            "/login",
            data=dict(
                csrf_token=web_csrf(client),
                email="admin@example.com",
                password="test-password-strong-123",
            ),
        ).status_code
        == 302
    )


@pytest.mark.parametrize(
    "path",
    [
        "/operacion/platillos",
        "/operacion/platillos/nuevo",
        "/ventas/punto-de-venta",
        "/ventas/",
        "/reportes/",
        "/inventario/mermas/nueva",
        "/inventario/conteos",
    ],
)
def test_new_pages_render_with_real_permissions_and_csrf(client, seeded, path):
    web_login(client)
    response = client.get(path)
    assert response.status_code == 200
    assert "Punto de venta" in response.text


def test_recipe_sale_receipt_and_cancel_end_to_end(app, client, prepared):
    web_login(client)
    assert client.get(f"/operacion/platillos/{prepared['item']}").status_code == 200
    assert client.get(f"/operacion/platillos/{prepared['item']}/editar").status_code == 200
    token = web_csrf(client, "/ventas/punto-de-venta")
    lines = [dict(menu_item_id=prepared["item"], quantity=2)]
    quote = client.post("/ventas/cotizar", json={"lines": lines}, headers={"X-CSRFToken": token})
    assert quote.status_code == 200 and quote.json["total"] == "200.00"
    response = client.post(
        "/ventas/punto-de-venta",
        data=dict(
            csrf_token=token,
            key=str(uuid.uuid4()),
            cart=json.dumps(lines),
            expected_total=quote.json["total"],
            method="cash",
            received="500.00",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "No es una factura fiscal" in response.text
    assert "$300.00" in response.text
    with app.app_context():
        sale = db.session.scalar(select(Sale))
        sale_id = sale.id
    report = client.get("/reportes/")
    assert report.status_code == 200 and "$200.00" in report.text
    assert client.get("/reportes/?format=csv").status_code == 200
    token = web_csrf(client, f"/ventas/{sale_id}")
    response = client.post(
        f"/ventas/{sale_id}/cancelar",
        data=dict(
            csrf_token=token,
            key=str(uuid.uuid4()),
            reason="Cancelación sintética por prueba",
            restock="y",
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200 and "Venta cancelada" in response.text


def test_recipe_form_persists_version_and_validates_decimal_units(app, client, seeded):
    web_login(client)
    token = web_csrf(client, "/operacion/platillos/nuevo")
    response = client.post(
        "/operacion/platillos/nuevo",
        data={
            "csrf_token": token,
            "expected_version": "0",
            "name": "Platillo desde formulario",
            "category": "Pruebas",
            "price": "95.00",
            "kind": "prepared",
            "yield_quantity": "1",
            "active": "y",
            "lines-0-ingredient_id": seeded["ingredient"],
            "lines-0-quantity": "0.2",
            "lines-0-unit_id": seeded["unit"],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200 and "Versión 1" in response.text
    with app.app_context():
        assert db.session.scalar(select(MenuItem.price)) == Decimal("95.00")


def test_cashier_only_sees_own_sales_and_cannot_cancel(app, client, prepared):
    from app.models import User

    with app.app_context():
        sale_id = sell(prepared)
        cashier = User(
            name="Caja de prueba", email="cashier@example.com", role="cashier", active=True
        )
        cashier.set_password("cashier-test-password")
        db.session.add(cashier)
        db.session.commit()
    token = web_csrf(client)
    assert (
        client.post(
            "/login",
            data=dict(
                csrf_token=token, email="cashier@example.com", password="cashier-test-password"
            ),
        ).status_code
        == 302
    )
    assert client.get("/ventas/punto-de-venta").status_code == 200
    assert client.get(f"/ventas/{sale_id}").status_code == 403
    assert client.get("/operacion/platillos").status_code == 403
    assert client.get("/reportes/").status_code == 403
    assert str(sale_id) not in client.get("/ventas/").text


def test_empty_catalog_explains_prerequisite_instead_of_blank_select(app, client):
    from app.models import User

    with app.app_context():
        user = User(name="Admin vacío", email="admin@example.com", role="admin", active=True)
        user.set_password("test-password-strong-123")
        db.session.add(user)
        db.session.commit()
    web_login(client)
    for path in [
        "/inventario/entradas/nueva",
        "/inventario/salidas/nueva",
        "/catalogos/presentaciones",
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert "Crear ingrediente" in response.text
