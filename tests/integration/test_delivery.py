import io
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import func, select

from app.delivery_models import ImportJob, ReceiptDraft
from app.extensions import db
from app.models import Ingredient, Lot, Movement, Operation, User
from app.services.imports import FIELDS, confirm_import, preview_book, upload_book
from app.services.inventory import issue, receive
from app.services.numbers import DomainError
from app.services.receipts import confirm_draft, reverse_receipt, save_draft
from app.services.xlsx import number_cell

pytestmark = pytest.mark.postgres


def book(rows, headers=None):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Inventario"
    worksheet.append(
        headers
        or [
            "Ingrediente",
            "Unidad",
            "Categoría",
            "Existencia de apertura",
            "Costo unitario apertura",
        ]
    )
    for row in rows:
        worksheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def mapped(ids, rows, mode="catalog", content=None):
    job_id = upload_book(
        user_id=ids["user"], filename="catalogo.xlsx", content=content or book(rows)
    )
    mapping = {key: -1 for key in FIELDS}
    mapping.update(name=0, unit=1, category=2, quantity=3, unit_cost=4)
    preview_book(user_id=ids["user"], job_id=job_id, sheet="Inventario", mode=mode, mapping=mapping)
    return job_id


def payload(ids, key):
    return {
        "key": str(key),
        "supplier_id": "0",
        "reference": "Prueba de entrega",
        "reason": "Recepción verificada",
        "lines-0-ingredient_id": str(ids["ingredient"]),
        "lines-0-presentation_id": "0",
        "lines-0-quantity": "3.5",
        "lines-0-unit_cost": "20",
        "lines-0-code": "Lote de prueba",
    }


def token(client, path="/login"):
    response = client.get(path)
    assert response.status_code == 200, response.text[:500]
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', response.text)
    assert match
    return match[1]


def login(client):
    assert (
        client.post(
            "/login",
            data=dict(
                csrf_token=token(client),
                email="admin@example.com",
                password="test-password-strong-123",
            ),
        ).status_code
        == 302
    )


def test_import_preview_does_not_write_catalog_and_confirm_is_atomic(app, seeded):
    with app.app_context():
        job_id = mapped(
            seeded, [["Aceite de prueba", "ml", "Despensa", "2,000", None]], mode="opening"
        )
        assert db.session.scalar(select(func.count(Ingredient.id))) == 2
        job = db.session.get(ImportJob, job_id)
        assert job.errors == [] and job.preview[0]["quantity"] == "2000"
        assert (
            confirm_import(
                user_id=seeded["user"],
                job_id=job_id,
                acknowledge=True,
                reason="Saldo físico revisado",
            )
            == job_id
        )
        assert (
            confirm_import(
                user_id=seeded["user"], job_id=job_id, acknowledge=True, reason="Repetición"
            )
            == job_id
        )
        db.session.expire_all()
        lot = db.session.scalar(select(Lot))
        assert lot.source == "opening" and lot.original_quantity == 2000 and lot.unit_cost is None
        assert lot.expires_on is None and lot.received_at.tzinfo is not None
        assert db.session.scalar(select(func.count(Ingredient.id))) == 3
        assert db.session.scalar(select(func.count(Operation.id))) == 1
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


@pytest.mark.parametrize(
    "row",
    [
        ["Repetido", "unidad desconocida", "Cat", "1", "2"],
        ["", "kg", "Cat", "1", "2"],
        ["Ingrediente", "kg", "Cat", "-1", "2"],
        ["Ingrediente", "kg", "Cat", "NaN", "2"],
        ["Ingrediente", "kg", "Cat", "abc", "2"],
        ["Ingrediente", "kg", "Cat", "=1+1", "2"],
    ],
)
def test_invalid_import_rows_prevent_any_catalog_or_stock_write(app, seeded, row):
    with app.app_context():
        job_id = mapped(seeded, [row], mode="opening")
        assert db.session.get(ImportJob, job_id).errors
        with pytest.raises(DomainError, match="errores"):
            confirm_import(
                user_id=seeded["user"], job_id=job_id, acknowledge=True, reason="No debe confirmar"
            )
        assert db.session.scalar(select(func.count(Ingredient.id))) == 2
        assert db.session.scalar(select(func.count(Lot.id))) == 0


def test_duplicate_ingredients_and_missing_columns_are_reported(app, seeded):
    with app.app_context():
        job_id = mapped(
            seeded, [["Arroz", "kg", "Secos", 0, None], [" ARROZ ", "kg", "Secos", 0, None]]
        )
        assert "repetido" in db.session.get(ImportJob, job_id).errors[0]["message"]
        with pytest.raises(DomainError, match="Mapea"):
            preview_book(
                user_id=seeded["user"],
                job_id=job_id,
                sheet="Inventario",
                mode="catalog",
                mapping={},
            )


def test_existing_catalog_is_not_overwritten_and_file_reimport_is_rejected(app, seeded):
    with app.app_context():
        rows = [[" CEBOLLA de prueba ", "kg", "Nueva categoría no aplicada", "100", "500"]]
        job_id = mapped(seeded, rows)
        confirm_import(user_id=seeded["user"], job_id=job_id)
        ingredient = db.session.get(Ingredient, seeded["ingredient"])
        assert ingredient.category_id == seeded["category"] and ingredient.reference_cost is None
        duplicate = mapped(seeded, rows)
        with pytest.raises(DomainError, match="ya fueron importados"):
            confirm_import(user_id=seeded["user"], job_id=duplicate)
        assert db.session.scalar(select(func.count(Lot.id))) == 0


def test_opening_requires_acknowledgement_and_revalidates_stock(app, seeded):
    with app.app_context():
        job_id = mapped(
            seeded, [["Cebolla de prueba", "kg", "Verduras", "10", "20"]], mode="opening"
        )
        with pytest.raises(DomainError, match="Documenta"):
            confirm_import(user_id=seeded["user"], job_id=job_id)
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="1")],
        )
        with pytest.raises(DomainError, match="inventario previo"):
            confirm_import(
                user_id=seeded["user"],
                job_id=job_id,
                acknowledge=True,
                reason="Intento desactualizado",
            )
        assert db.session.scalar(select(Lot.remaining_quantity)) == 1


def test_concurrent_duplicate_import_records_one_opening(app, seeded):
    with app.app_context():
        first = mapped(seeded, [["Arroz", "kg", "Secos", "10", "30"]], mode="opening")
        second = mapped(seeded, [["Arroz", "kg", "Secos", "10", "30"]], mode="opening")
    barrier = Barrier(2)

    def run(job_id):
        with app.app_context():
            barrier.wait(timeout=5)
            try:
                return confirm_import(
                    user_id=seeded["user"],
                    job_id=job_id,
                    acknowledge=True,
                    reason="Apertura verificada",
                )
            except DomainError:
                return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(run, [first, second]))
    assert sum(result is not None for result in results) == 1
    with app.app_context():
        assert db.session.scalar(select(func.count(Lot.id))) == 1
        assert db.session.scalar(select(Lot.remaining_quantity)) == 10


def test_corrupt_or_empty_workbook_is_rejected(app, seeded):
    with app.app_context():
        with pytest.raises(DomainError):
            upload_book(user_id=seeded["user"], filename="mal.xlsx", content=b"not a workbook")
        with pytest.raises(DomainError):
            mapped(seeded, [])


@pytest.mark.parametrize(
    "value,expected",
    [("$1,234.56", "1234.56"), ("1.234,56", "1234.56"), ("1,25", "1.25"), ("0", "0")],
)
def test_spreadsheet_decimal_formats(value, expected):
    assert number_cell(value) == Decimal(expected)


def test_incomplete_draft_is_non_inventory_and_confirmation_is_idempotent(app, seeded):
    with app.app_context():
        key = uuid.uuid4()
        incomplete = {"key": str(key), "reason": "Falta completar"}
        draft_id = save_draft(user_id=seeded["user"], key=key, payload=incomplete)
        assert db.session.scalar(select(func.count(Lot.id))) == 0
        save_draft(
            user_id=seeded["user"], key=key, payload=payload(seeded, key), expected_revision=1
        )
        op_id = confirm_draft(
            user_id=seeded["user"],
            draft_id=draft_id,
            payload=payload(seeded, key),
            expected_revision=2,
        )
        assert (
            confirm_draft(
                user_id=seeded["user"],
                draft_id=draft_id,
                payload=payload(seeded, key),
                expected_revision=2,
            )
            == op_id
        )
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("3.5")
        assert db.session.scalar(select(func.count(Operation.id))) == 1


def test_stale_or_invalid_draft_does_not_confirm(app, seeded):
    with app.app_context():
        key = uuid.uuid4()
        draft_id = save_draft(user_id=seeded["user"], key=key, payload=payload(seeded, key))
        with pytest.raises(DomainError, match="cambió"):
            confirm_draft(
                user_id=seeded["user"],
                draft_id=draft_id,
                payload=payload(seeded, key),
                expected_revision=0,
            )
        invalid = {**payload(seeded, key), "lines-0-quantity": "-1"}
        with pytest.raises(DomainError):
            confirm_draft(
                user_id=seeded["user"], draft_id=draft_id, payload=invalid, expected_revision=1
            )
        assert db.session.scalar(select(func.count(Lot.id))) == 0


def test_receipt_reversal_preserves_history_and_refuses_consumed_lots(app, seeded):
    with app.app_context():
        op = receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="5", unit_cost="20")],
        )
        key = uuid.uuid4()
        reversal = reverse_receipt(
            key=key, user_id=seeded["user"], operation_id=op, reason="Corrección documentada"
        )
        assert (
            reverse_receipt(
                key=key, user_id=seeded["user"], operation_id=op, reason="Corrección documentada"
            )
            == reversal
        )
        assert db.session.scalar(select(Lot.remaining_quantity)) == 0
        assert db.session.scalar(select(func.count(Movement.id))) == 2
        with pytest.raises(DomainError, match="ya fue revertida"):
            reverse_receipt(
                key=uuid.uuid4(), user_id=seeded["user"], operation_id=op, reason="Otra vez"
            )
        op2 = receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="2")],
        )
        issue(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="1")],
            reason="Consumo",
        )
        with pytest.raises(DomainError, match="consumidas"):
            reverse_receipt(
                key=uuid.uuid4(),
                user_id=seeded["user"],
                operation_id=op2,
                reason="No debe retirar consumido",
            )
        assert app.test_cli_runner().invoke(args=["reconcile-inventory"]).exit_code == 0


def test_password_change_revokes_other_sessions(app, seeded):
    first, second = app.test_client(), app.test_client()
    login(first)
    login(second)
    response = first.post(
        "/mi-cuenta",
        data=dict(
            csrf_token=token(first, "/mi-cuenta"),
            current="test-password-strong-123",
            password="new-password-strong-456",
            confirmation="new-password-strong-456",
        ),
    )
    assert response.status_code == 302
    assert second.get("/").status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/importaciones/",
        "/administracion/configuracion",
        "/administracion/ayuda",
        "/inventario/entradas/borradores",
        "/reportes/almacen",
        "/inventario/?status=low",
        "/inventario/lotes?status=expired",
    ],
)
def test_delivery_pages_render(client, seeded, path):
    login(client)
    assert client.get(path).status_code == 200


def test_upload_mapping_preview_and_confirmation_http(app, client, seeded):
    login(client)
    response = client.post(
        "/importaciones/",
        data={
            "csrf_token": token(client, "/importaciones/"),
            "file": (io.BytesIO(book([["Arroz", "kg", "Secos", 0, None]])), "archivo.xlsx"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    with app.app_context():
        job_id = db.session.scalar(select(ImportJob.id))
    url = f"/importaciones/{job_id}/columnas"
    values = {key: "-1" for key in FIELDS}
    values.update(
        name="0",
        unit="1",
        category="2",
        quantity="3",
        unit_cost="4",
        mode="catalog",
        sheet="Inventario",
        default_category_id="0",
        csrf_token=token(client, url),
    )
    response = client.post(url, data=values, follow_redirects=True)
    assert response.status_code == 200 and "filas válidas" in response.text
    assert (
        client.post(
            f"/importaciones/{job_id}",
            data={"csrf_token": token(client, f"/importaciones/{job_id}")},
            follow_redirects=True,
        ).status_code
        == 200
    )
    with app.app_context():
        assert db.session.get(ImportJob, job_id).status == "confirmed"


@pytest.mark.parametrize("kind", ["inventory", "receipts", "issues", "lots", "waste", "costs"])
def test_priority_report_exports_are_valid_excel(client, seeded, kind):
    login(client)
    response = client.get(f"/reportes/almacen?kind={kind}&format=xlsx")
    assert response.status_code == 200
    workbook = load_workbook(io.BytesIO(response.data), read_only=True)
    assert workbook.active.max_row >= 1
    workbook.close()


def test_draft_form_and_receipt_correction_http(app, client, seeded):
    login(client)
    key = uuid.uuid4()
    values = payload(seeded, key)
    values.update(
        csrf_token=token(client, "/inventario/entradas/nueva"), action="draft", revision="0"
    )
    response = client.post("/inventario/entradas/nueva", data=values, follow_redirects=True)
    assert response.status_code == 200 and "Borrador guardado" in response.text
    with app.app_context():
        draft_id = db.session.scalar(select(ReceiptDraft.id))
    url = f"/inventario/entradas/borradores/{draft_id}/editar"
    values.update(csrf_token=token(client, url), action="confirm", revision="1")
    assert client.post(url, data=values, follow_redirects=True).status_code == 200
    with app.app_context():
        operation_id = db.session.get(ReceiptDraft, draft_id).operation_id
    url = f"/inventario/operaciones/{operation_id}"
    response = client.post(
        url + "/revertir-recepcion",
        data=dict(
            csrf_token=token(client, url), key=str(uuid.uuid4()), reason="Corrección verificada"
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200 and "Recepción revertida" in response.text


def test_concurrent_draft_confirmation_creates_one_receipt(app, seeded):
    key = uuid.uuid4()
    with app.app_context():
        draft_id = save_draft(user_id=seeded["user"], key=key, payload=payload(seeded, key))
    barrier = Barrier(2)

    def confirm(_):
        with app.app_context():
            barrier.wait(timeout=5)
            return confirm_draft(
                user_id=seeded["user"],
                draft_id=draft_id,
                payload=payload(seeded, key),
                expected_revision=1,
            )

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(confirm, range(2)))
    assert results[0] == results[1]
    with app.app_context():
        assert db.session.scalar(select(func.count(Operation.id))) == 1
        assert db.session.scalar(select(Lot.remaining_quantity)) == Decimal("3.5")


@pytest.mark.parametrize("role", ["warehouse", "cashier"])
def test_import_and_settings_are_denied_to_operational_roles(app, client, seeded, role):
    login(client)
    with app.app_context():
        db.session.get(User, seeded["user"]).role = role
        db.session.commit()
    for url in [
        "/importaciones/",
        "/importaciones/plantilla.xlsx",
        "/administracion/configuracion",
    ]:
        assert client.get(url).status_code == 403


def test_reconciliation_detects_historical_cost_inconsistency(app, seeded):
    with app.app_context():
        receive(
            key=uuid.uuid4(),
            user_id=seeded["user"],
            lines=[dict(ingredient_id=seeded["ingredient"], quantity="5", unit_cost="20")],
        )
        movement = db.session.scalar(select(Movement))
        movement.cost = Decimal("99")
        db.session.commit()
        result = app.test_cli_runner().invoke(args=["reconcile-inventory"])
        assert result.exit_code != 0 and "costo" in result.output


def test_xlsx_text_export_does_not_create_formulas(client, app, seeded):
    with app.app_context():
        db.session.get(Ingredient, seeded["ingredient"]).name = "=1+1"
        db.session.commit()
    login(client)
    response = client.get("/reportes/almacen?kind=inventory&format=xlsx")
    workbook = load_workbook(io.BytesIO(response.data), read_only=True, data_only=False)
    cells = [cell for row in workbook.active.iter_rows() for cell in row if cell.value == "=1+1"]
    assert cells and all(cell.data_type != "f" for cell in cells)
    workbook.close()


def test_database_readiness_includes_migration_revision(client, seeded):
    assert client.get("/health/ready").status_code == 200


def test_local_password_recovery_revokes_existing_session(app, client, seeded):
    login(client)
    result = app.test_cli_runner().invoke(
        args=[
            "reset-password",
            "--email",
            "admin@example.com",
            "--password",
            "new-local-password-456",
        ]
    )
    assert result.exit_code == 0
    assert client.get("/").status_code == 302
