import base64
import hashlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.mobile_models import MobileAction, MobileSession
from app.models import AuditLog, Ingredient, User, utcnow

pytestmark = pytest.mark.postgres
BASE = "/api/mobile/v1"


@pytest.fixture
def token(client, seeded):
    response = client.post(
        BASE + "/auth/login",
        json={"email": "admin@example.com", "password": "test-password-strong-123"},
    )
    return response.json["token"]


def headers(token):
    return {"Authorization": "Bearer " + token}


def command(seeded, **values):
    return dict(
        key=str(uuid.uuid4()),
        kind="catalog.ingredient.create",
        data=dict(
            name="Aguacate Hass",
            category_id=seeded["category"],
            unit_id=seeded["unit"],
            minimum="2.500000",
            active=True,
            **values,
        ),
    )


def test_web_bootstrap_uses_existing_user_and_does_not_leak_token(client, seeded, token):
    result = client.post(BASE + "/web-session", data={"access_token": token})
    assert result.status_code == 303 and result.location == "/"
    assert token not in result.text and token not in result.location
    assert "HttpOnly" in result.headers["Set-Cookie"]
    assert client.get("/catalogos/ingredientes").status_code == 200
    with client.session_transaction() as session:
        assert session["mobile_device"] == hashlib.sha256(token.encode()).hexdigest()


@pytest.mark.parametrize("change", ["revoke", "expire", "password", "inactive"])
def test_web_cookie_keeps_device_revocation_and_account_checks(app, client, seeded, token, change):
    client.post(BASE + "/web-session", data={"access_token": token})
    with app.app_context():
        device = db.session.get(MobileSession, hashlib.sha256(token.encode()).hexdigest())
        user = db.session.get(User, seeded["user"])
        if change == "revoke":
            device.revoked_at = utcnow()
        elif change == "expire":
            device.created_at = utcnow() - timedelta(days=9)
            device.expires_at = utcnow() - timedelta(days=1)
        elif change == "password":
            user.set_password("a-new-secure-password")
        else:
            user.active = False
        db.session.commit()
    assert client.get("/catalogos/ingredientes").status_code == 302


@pytest.mark.parametrize(
    "role,allowed,forbidden",
    [
        (
            "admin",
            [
                "/administracion/usuarios",
                "/administracion/configuracion",
                "/importaciones/",
                "/reportes/",
            ],
            [],
        ),
        (
            "manager",
            ["/importaciones/", "/reportes/", "/catalogos/ingredientes"],
            ["/administracion/usuarios", "/administracion/configuracion"],
        ),
        (
            "warehouse",
            ["/inventario/", "/catalogos/ingredientes"],
            ["/reportes/", "/administracion/usuarios", "/ventas/punto-de-venta"],
        ),
        (
            "cashier",
            ["/ventas/punto-de-venta", "/ventas/"],
            ["/catalogos/ingredientes", "/inventario/", "/administracion/usuarios"],
        ),
    ],
)
def test_full_web_preserves_role_permissions(app, client, seeded, token, role, allowed, forbidden):
    with app.app_context():
        db.session.get(User, seeded["user"]).role = role
        db.session.commit()
    assert client.post(BASE + "/web-session", data={"access_token": token}).status_code == 303
    for path in allowed:
        assert client.get(path).status_code == 200, path
    for path in forbidden:
        assert client.get(path).status_code == 403, path


def test_no_token_or_query_token_cannot_create_a_web_session(client, seeded, token):
    assert client.post(BASE + "/web-session").status_code == 401
    assert client.post(BASE + "/web-session?access_token=" + token).status_code == 401
    assert client.get(BASE + "/web-session").status_code == 405


def test_assistant_creates_exact_catalog_once_and_keeps_audit(app, client, seeded, token):
    payload = command(seeded)
    first = client.post(BASE + "/actions", headers=headers(token), json=payload)
    assert first.status_code == 200, first.json
    replay = client.post(BASE + "/actions", headers=headers(token), json=payload)
    assert replay.json["id"] == first.json["id"]
    with app.app_context():
        assert (
            db.session.scalar(
                select(func.count(Ingredient.id)).where(Ingredient.name == "Aguacate Hass")
            )
            == 1
        )
        row = db.session.get(Ingredient, int(first.json["id"]))
        assert str(row.minimum) == "2.500000" and row.updated_by == seeded["user"]
        assert db.session.scalar(select(func.count(MobileAction.key))) == 1
        assert (
            db.session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.action == "assistant.catalog.ingredient.create"
                )
            )
            == 1
        )
    payload["data"]["name"] = "Otro ingrediente"
    assert client.post(BASE + "/actions", headers=headers(token), json=payload).status_code == 422


def test_assistant_concurrent_replays_do_not_duplicate(app, client, seeded, token):
    payload = command(seeded)

    def send(_):
        with app.test_client() as c:
            return c.post(BASE + "/actions", headers=headers(token), json=payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, range(2)))
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json["id"] == results[1].json["id"]


@pytest.mark.parametrize(
    "mutation", ["role", "unknown_field", "invalid_unit", "float", "max_below_min", "missing_name"]
)
def test_assistant_denies_invalid_actions_atomically(app, client, seeded, token, mutation):
    payload = command(seeded)
    if mutation == "role":
        with app.app_context():
            db.session.get(User, seeded["user"]).role = "cashier"
            db.session.commit()
    elif mutation == "unknown_field":
        payload["data"]["stock"] = "100"
    elif mutation == "invalid_unit":
        payload["data"]["unit_id"] = 999999
    elif mutation == "float":
        payload["data"]["minimum"] = 0.1
    elif mutation == "max_below_min":
        payload["data"]["maximum"] = "1"
    else:
        payload["data"]["name"] = "   "
    response = client.post(BASE + "/actions", headers=headers(token), json=payload)
    assert response.status_code == (403 if mutation == "role" else 422), response.json
    with app.app_context():
        assert db.session.scalar(select(func.count(MobileAction.key))) == 0


def test_assistant_all_catalog_tools_and_metadata(client, seeded, token):
    metadata = client.get(BASE + "/snapshot", headers=headers(token)).json
    assert metadata["categories"] and metadata["units"]
    for kind, data in [
        ("catalog.category.create", {"name": "Refrigerados"}),
        (
            "catalog.supplier.create",
            {"name": "Huerta San Juan", "email": "ventas@example.com", "active": True},
        ),
        (
            "catalog.presentation.create",
            {
                "name": "Caja de 5 kg",
                "ingredient_id": seeded["ingredient"],
                "base_quantity": "5.000000",
            },
        ),
    ]:
        response = client.post(
            BASE + "/actions",
            headers=headers(token),
            json=dict(key=str(uuid.uuid4()), kind=kind, data=data),
        )
        assert response.status_code == 200, response.json


def test_native_exports_use_the_same_web_permissions(app, client, seeded, token):
    response = client.post(
        BASE + "/documents",
        headers=headers(token),
        json={"path": "/catalogos/ingredientes/exportar"},
    )
    assert response.status_code == 200, response.json
    assert "Cebolla" in base64.b64decode(response.json["content"]).decode("utf-8-sig")
    for path in [
        "https://example.com/x",
        "//example.com",
        "/administracion/usuarios",
        "/api/mobile/v1/auth/me",
        "/catalogos/ingredientes/nuevo",
    ]:
        assert (
            client.post(
                BASE + "/documents", headers=headers(token), json={"path": path}
            ).status_code
            == 403
        )
    with app.app_context():
        db.session.get(User, seeded["user"]).role = "cashier"
        db.session.commit()
    assert (
        client.post(
            BASE + "/documents",
            headers=headers(token),
            json={"path": "/catalogos/ingredientes/exportar"},
        ).status_code
        == 403
    )


def test_export_rejects_non_object_json(client, token):
    response = client.post(BASE + "/documents", json=["invalid"], headers=headers(token))
    assert response.status_code == 422
    assert response.json["error"]
