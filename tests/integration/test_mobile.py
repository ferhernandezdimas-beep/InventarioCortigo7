import hashlib
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.commerce_models import RecipeVersion, Sale
from app.extensions import db
from app.mobile_models import MobileSession
from app.models import Lot, Operation, User, utcnow
from app.services.inventory import receive
from app.services.recipes import save_recipe

pytestmark = pytest.mark.postgres
BASE = "/api/mobile/v1"


def login(client):
    return client.post(
        BASE + "/auth/login",
        json={
            "email": "admin@example.com",
            "password": "test-password-strong-123",
            "device_name": "Teléfono",
        },
    )


@pytest.fixture
def mobile(client, seeded):
    response = login(client)
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json["token"]}


def test_login_uses_existing_user_and_stores_only_digest(app, client, seeded):
    response = login(client)
    assert response.status_code == 200
    assert response.json["user"]["id"] == seeded["user"]
    assert "Set-Cookie" not in response.headers
    with app.app_context():
        device = db.session.scalar(select(MobileSession))
        assert device.token_hash == hashlib.sha256(response.json["token"].encode()).hexdigest()
        assert device.token_hash != response.json["token"]
    assert client.get(BASE + "/snapshot").status_code == 401


def test_cookie_session_does_not_authenticate_mobile(client, seeded):
    with client.session_transaction() as session:
        session["_user_id"] = f"{seeded['user']}:1"
    assert client.get(BASE + "/snapshot").status_code == 401


def test_session_logout_revokes_token(client, mobile):
    assert client.get(BASE + "/auth/me", headers=mobile).status_code == 200
    assert client.post(BASE + "/auth/logout", headers=mobile, json={}).status_code == 200
    assert client.get(BASE + "/snapshot", headers=mobile).status_code == 401


@pytest.mark.parametrize("change", ["inactive", "password", "expiry"])
def test_revocation_from_web_and_expiry(app, client, seeded, mobile, change):
    with app.app_context():
        user = db.session.get(User, seeded["user"])
        if change == "inactive":
            user.active = False
        elif change == "password":
            user.set_password("changed-strong-password")
        else:
            device = db.session.scalar(select(MobileSession))
            device.created_at = utcnow() - timedelta(days=9)
            device.expires_at = utcnow() - timedelta(days=1)
        db.session.commit()
    assert client.get(BASE + "/snapshot", headers=mobile).status_code == 401


def test_snapshot_decimal_strings_and_role_scoping(app, client, seeded, mobile):
    data = client.get(BASE + "/snapshot", headers=mobile)
    assert data.status_code == 200
    assert data.headers["Cache-Control"] == "no-store"
    assert isinstance(data.json["ingredients"][0]["available"], str)
    with app.app_context():
        db.session.get(User, seeded["user"]).role = "cashier"
        db.session.commit()
    data = client.get(BASE + "/snapshot", headers=mobile).json
    assert data["ingredients"] == data["lots"] == data["operations"] == []
    assert "inventory.write" not in data["user"]["permissions"]
    assert (
        client.post(BASE + "/operations", headers=mobile, json={"kind": "issue"}).status_code == 403
    )


def receipt_payload(seeded, key=None):
    return dict(
        key=key or str(uuid.uuid4()),
        kind="receipt",
        reason="Compra de cocina",
        lines=[
            dict(
                ingredient_id=seeded["ingredient"],
                quantity="10.500000",
                unit_cost="20.25",
                expires_on="2099-12-31",
            ),
        ],
    )


def test_receipt_replay_and_content_collision(app, client, seeded, mobile):
    payload = receipt_payload(seeded)
    first = client.post(BASE + "/operations", headers=mobile, json=payload)
    assert first.status_code == 200
    again = client.post(BASE + "/operations", headers=mobile, json=payload)
    assert again.json["id"] == first.json["id"]
    payload["lines"][0]["quantity"] = "11"
    assert client.post(BASE + "/operations", headers=mobile, json=payload).status_code == 422
    with app.app_context():
        assert db.session.scalar(select(func.count(Operation.id))) == 1
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10.5")


def test_acknowledgement_recovery_survives_role_change(app, client, seeded, mobile):
    payload = receipt_payload(seeded)
    first = client.post(BASE + "/operations", headers=mobile, json=payload)
    with app.app_context():
        db.session.get(User, seeded["user"]).role = "cashier"
        db.session.commit()
    result = client.get(BASE + "/operations/" + payload["key"], headers=mobile)
    assert result.status_code == 200
    assert result.json["id"] == first.json["id"]
    assert client.post(BASE + "/operations", headers=mobile, json=payload).status_code == 403
    assert client.get(BASE + "/operations/" + str(uuid.uuid4()), headers=mobile).status_code == 404


def test_acknowledgement_is_not_visible_to_another_user(app, client, seeded, mobile):
    payload = receipt_payload(seeded)
    client.post(BASE + "/operations", headers=mobile, json=payload)
    with app.app_context():
        other = User(name="Otro usuario", email="other@example.com", role="admin", active=True)
        other.set_password("other-secure-password")
        db.session.add(other)
        db.session.commit()
    response = client.post(
        BASE + "/auth/login", json=dict(email="other@example.com", password="other-secure-password")
    )
    headers = {"Authorization": "Bearer " + response.json["token"]}
    assert client.get(BASE + "/operations/" + payload["key"], headers=headers).status_code == 404


def test_web_device_revocation_keeps_csrf_protection(app, client, seeded, mobile):
    with app.app_context():
        user = db.session.get(User, seeded["user"])
        identity = user.get_id()
        device = db.session.scalar(select(MobileSession)).token_hash
    with client.session_transaction() as session:
        session["_user_id"] = identity
        session["_fresh"] = True
    page = client.get("/mi-cuenta/dispositivos")
    assert page.status_code == 200
    assert b"Tel" in page.data
    assert client.post("/mi-cuenta/dispositivos", data={"device": device}).status_code == 400
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.text).group(1)
    response = client.post("/mi-cuenta/dispositivos", data={"device": device, "csrf_token": token})
    assert response.status_code == 302
    assert client.get(BASE + "/auth/me", headers=mobile).status_code == 401


def test_fifo_conflict_rolls_back_and_valid_operation_is_visible_on_web(
    app, client, seeded, mobile
):
    client.post(BASE + "/operations", headers=mobile, json=receipt_payload(seeded))
    payload = dict(
        key=str(uuid.uuid4()),
        kind="issue",
        reason="Cocina",
        lines=[
            dict(ingredient_id=seeded["ingredient"], quantity="11"),
        ],
    )
    assert client.post(BASE + "/operations", headers=mobile, json=payload).status_code == 422
    with app.app_context():
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("10.5")
    payload["lines"][0]["quantity"] = "2"
    assert client.post(BASE + "/operations", headers=mobile, json=payload).status_code == 200
    data = client.get(BASE + "/snapshot", headers=mobile).json
    assert Decimal(data["ingredients"][0]["available"]) == Decimal("8.5")


def test_concurrent_mobile_replays_do_not_duplicate(app, client, seeded, mobile):
    payload = receipt_payload(seeded)

    def send(_):
        with app.test_client() as connection:
            return connection.post(BASE + "/operations", headers=mobile, json=payload)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, range(2)))
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].json["id"] == results[1].json["id"]
    with app.app_context():
        assert db.session.scalar(select(func.count(Lot.id))) == 1


@pytest.mark.parametrize("payload", [None, [], {"email": 123}, {"email": "x", "password": []}])
def test_invalid_login_json_is_rejected(client, seeded, payload):
    assert client.post(BASE + "/auth/login", json=payload).status_code == 400


@pytest.mark.parametrize(
    "mutation", ["float", "negative", "boolean_id", "invalid_date", "huge_code", "missing_lines"]
)
def test_invalid_operations_are_json_errors(client, seeded, mobile, mutation):
    payload = receipt_payload(seeded)
    line = payload["lines"][0]
    if mutation == "float":
        line["quantity"] = 0.2
    elif mutation == "negative":
        line["quantity"] = "-2"
    elif mutation == "boolean_id":
        line["ingredient_id"] = True
    elif mutation == "invalid_date":
        line["expires_on"] = "2026-99-99"
    elif mutation == "huge_code":
        line["code"] = "x" * 101
    else:
        del payload["lines"]
    response = client.post(BASE + "/operations", headers=mobile, json=payload)
    assert response.status_code == 422
    assert response.json["error"]["code"] == "conflict"


def test_mobile_sale_rejects_changed_recipe_and_preserves_replay(app, client, seeded, mobile):
    with app.app_context():
        item = save_recipe(
            user_id=seeded["user"],
            item_id=None,
            data=dict(
                name="Ensalada",
                category="Cocina",
                price="45.00",
                yield_quantity="1",
                kind="prepared",
                active=True,
            ),
            lines=[
                dict(ingredient_id=seeded["ingredient"], quantity="0.2", unit_id=seeded["unit"])
            ],
        )
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="10")],
        )
    snapshot = client.get(BASE + "/snapshot", headers=mobile).json
    assert snapshot["products"][0]["recipe_version"] == 1
    payload = dict(
        key=str(uuid.uuid4()),
        kind="sale",
        lines=[dict(menu_item_id=item, quantity="1")],
        method="cash",
        received="50.00",
        expected_total="45.00",
        expected_recipes={str(item): 1},
    )
    first = client.post(BASE + "/operations", headers=mobile, json=payload)
    assert first.status_code == 200
    with app.app_context():
        recipe = db.session.scalar(select(RecipeVersion))
        recipe.version = 2
        db.session.commit()
    assert (
        client.post(BASE + "/operations", headers=mobile, json=payload).json["id"]
        == first.json["id"]
    )
    payload["key"] = str(uuid.uuid4())
    assert client.post(BASE + "/operations", headers=mobile, json=payload).status_code == 422
    with app.app_context():
        assert db.session.scalar(select(func.count(Sale.id))) == 1
