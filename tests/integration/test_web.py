import re
import uuid

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Ingredient, User
from app.services.inventory import receive

pytestmark = pytest.mark.postgres


def csrf(client, path="/login"):
    response = client.get(path)
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', response.data)
    assert match, response.data.decode()[:2000]
    return match.group(1).decode()


def login(client):
    return client.post(
        "/login",
        data={
            "csrf_token": csrf(client),
            "email": "admin@example.com",
            "password": "test-password-strong-123",
        },
    )


def test_login_logout_and_csrf(app, client, seeded):
    assert client.get("/").status_code == 302
    assert (
        client.post("/login", data={"email": "admin@example.com", "password": "wrong"}).status_code
        == 400
    )
    assert login(client).status_code == 302
    assert client.get("/").status_code == 200
    assert client.get("/logout").status_code == 405
    assert (
        client.post("/logout", data={"csrf_token": csrf(client, "/mi-cuenta")}).status_code == 302
    )
    assert client.get("/").status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/catalogos/ingredientes",
        "/catalogos/ingredientes/nuevo",
        "/catalogos/categorias",
        "/catalogos/proveedores",
        "/catalogos/proveedores/nuevo",
        "/catalogos/unidades",
        "/catalogos/presentaciones",
        "/inventario/",
        "/inventario/entradas/nueva",
        "/inventario/salidas/nueva",
        "/inventario/lotes",
        "/inventario/movimientos",
        "/administracion/usuarios",
        "/administracion/usuarios/nuevo",
        "/administracion/auditoria",
        "/mi-cuenta",
    ],
)
def test_authorized_pages_render(client, seeded, path):
    login(client)
    assert client.get(path).status_code == 200


def test_catalog_validation_and_persistence(app, client, seeded):
    login(client)
    data = dict(
        csrf_token=csrf(client, "/catalogos/ingredientes/nuevo"),
        name="Arroz de prueba",
        code="A1",
        category_id=seeded["category"],
        unit_id=seeded["unit"],
        supplier_id=0,
        minimum="2",
        maximum="10",
        active="y",
    )
    assert client.post("/catalogos/ingredientes/nuevo", data=data).status_code == 302
    assert "Arroz de prueba" in client.get("/catalogos/ingredientes?q=Arroz").text
    with app.app_context():
        assert db.session.scalar(select(Ingredient).where(Ingredient.code == "A1")) is not None
    data["maximum"] = "1"
    assert "mayor o igual" in client.post("/catalogos/ingredientes/nuevo", data=data).text


def test_receipt_form_issue_and_detail(client, seeded):
    login(client)
    data = {
        "csrf_token": csrf(client, "/inventario/entradas/nueva"),
        "key": str(uuid.uuid4()),
        "supplier_id": "0",
        "reason": "Recepción de prueba",
        "lines-0-ingredient_id": seeded["ingredient"],
        "lines-0-quantity": "3",
        "lines-0-unit_cost": "20",
    }
    response = client.post("/inventario/entradas/nueva", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert "Operación confirmada".lower() in response.text.lower()
    response = client.post(
        "/inventario/salidas/nueva",
        data={
            "csrf_token": csrf(client, "/inventario/salidas/nueva"),
            "key": str(uuid.uuid4()),
            "ingredient_id": seeded["ingredient"],
            "quantity": "1",
            "reason": "Preparación",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Salida de inventario" in response.text


def test_permissions_and_inactive_user(app, client, seeded):
    login(client)
    with app.app_context():
        db.session.get(User, seeded["user"]).role = "cashier"
        db.session.commit()
    assert client.get("/catalogos/ingredientes").status_code == 403
    assert client.get("/administracion/usuarios").status_code == 403
    assert client.get("/").status_code == 200
    assert "Cebolla de prueba" not in client.get("/").text
    with app.app_context():
        db.session.get(User, seeded["user"]).active = False
        db.session.commit()
    assert client.get("/").status_code == 302


def test_unit_cannot_change_after_receipt(app, client, seeded):
    with app.app_context():
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="2")],
        )
    login(client)
    path = f"/catalogos/ingredientes/{seeded['ingredient']}/editar"
    response = client.post(
        path,
        data=dict(
            csrf_token=csrf(client, path),
            name="Cebolla de prueba",
            category_id=seeded["category"],
            unit_id=seeded["unit"] + 1,
            supplier_id=0,
            minimum="1",
            active="y",
        ),
    )
    assert "unidad base no puede cambiar" in response.text


def test_login_throttling_shared_in_database(client, seeded):
    for _ in range(10):
        response = client.post(
            "/login",
            data=dict(csrf_token=csrf(client), email="admin@example.com", password="invalid"),
        )
        assert response.status_code == 200
    assert (
        client.post(
            "/login",
            data=dict(csrf_token=csrf(client), email="admin@example.com", password="invalid"),
        ).status_code
        == 429
    )


@pytest.mark.parametrize("value", ["NaN", "Infinity", "1.0000001", "-1"])
def test_reject_unsafe_decimal_form_values(client, seeded, value):
    login(client)
    response = client.post(
        "/inventario/salidas/nueva",
        data=dict(
            csrf_token=csrf(client, "/inventario/salidas/nueva"),
            key=str(uuid.uuid4()),
            ingredient_id=seeded["ingredient"],
            quantity=value,
            reason="Prueba",
        ),
    )
    assert response.status_code == 200
    assert "Salida confirmada" not in response.text


def test_fifo_preview_does_not_reserve_inventory(app, client, seeded):
    with app.app_context():
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="2")],
        )
    login(client)
    response = client.get(f"/inventario/peps/{seeded['ingredient']}?quantity=1")
    assert response.status_code == 200
    assert response.json["sufficient"] is True
    assert response.json["allocations"][0]["quantity"] == "1"
    assert (
        client.get(f"/inventario/peps/{seeded['ingredient']}?quantity=3").json["sufficient"]
        is False
    )
    with app.app_context():
        from app.models import Lot

        assert db.session.scalar(select(Lot.remaining_quantity)) == 2


def test_initial_admin_cli_has_no_default_password(app):
    runner = app.test_cli_runner()
    assert (
        runner.invoke(
            args=[
                "create-admin",
                "--name",
                "Admin",
                "--email",
                "bootstrap@example.com",
                "--password",
                "short",
            ]
        ).exit_code
        != 0
    )
    assert (
        runner.invoke(
            args=[
                "create-admin",
                "--name",
                "Admin",
                "--email",
                "bootstrap@example.com",
                "--password",
                "bootstrap-test-password",
            ]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            args=[
                "create-admin",
                "--name",
                "Otro",
                "--email",
                "another@example.com",
                "--password",
                "bootstrap-test-password",
            ]
        ).exit_code
        != 0
    )


def test_database_verification_cli(app):
    result = app.test_cli_runner().invoke(args=["verify-database"])
    assert result.exit_code == 0, result.output
    assert "PostgreSQL 17 conectado" in result.output
