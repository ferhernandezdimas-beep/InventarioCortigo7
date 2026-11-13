import hashlib
import json
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.delivery_models import ImportJob
from app.models import (
    Allocation,
    AuditLog,
    Category,
    Ingredient,
    Lot,
    Movement,
    Supplier,
    Unit,
    utcnow,
)
from app.services.inventory import _authorize, _claim, _lock_ingredients, _run
from app.services.numbers import DomainError, cost_value
from app.services.xlsx import header_key, name_key, number_cell, read_book, sheet_rows

FIELDS = {
    "name": "Ingrediente",
    "unit": "Unidad base",
    "category": "Categoría",
    "supplier": "Proveedor",
    "code": "Código",
    "minimum": "Mínimo",
    "maximum": "Máximo",
    "reference_cost": "Costo de referencia",
    "quantity": "Existencia de apertura",
    "unit_cost": "Costo por unidad base de apertura",
}
ALIASES = {
    "name": ["ingrediente", "insumo", "nombre"],
    "unit": ["unidad", "unidad base", "unidad de medida"],
    "category": ["categoria", "catalogo"],
    "supplier": ["proveedor"],
    "code": ["codigo", "clave"],
    "minimum": ["minimo", "existencia minima"],
    "maximum": ["maximo", "existencia maxima"],
    "reference_cost": ["costo de referencia", "precio prom", "precio promedio"],
    "quantity": ["existencia de apertura", "inv final", "inventario inicial", "existencia inicial"],
    "unit_cost": ["costo unitario apertura", "costo por unidad base de apertura"],
}


def upload_book(*, user_id, filename, content):
    if not filename or not filename.lower().endswith(".xlsx"):
        raise DomainError("Selecciona un archivo .xlsx.")
    book = read_book(content)
    book.close()

    def command(session):
        _authorize(session, user_id, "imports")
        job = ImportJob(
            filename=filename.replace("\\", "/").split("/")[-1][:180],
            file_hash=hashlib.sha256(content).hexdigest(),
            content=content,
            user_id=user_id,
        )
        session.add(job)
        session.flush()
        session.add(AuditLog(user_id=user_id, action="import.upload", detail=str(job.id)))
        return job.id

    return _run(command)


def workbook_info(job, sheet=None):
    book = read_book(job.content)
    try:
        sheets = book.sheetnames
        selected = sheet or job.sheet or sheets[0]
        if selected not in sheets:
            raise DomainError("La hoja seleccionada no existe.")
        ws = book[selected]
        if (ws.max_column or 0) > 60:
            raise DomainError("Se permiten hasta 60 columnas por hoja.")
        headers = [str(cell.value or "").strip()[:150] for cell in next(ws.iter_rows(max_row=1))]
        automatic = {
            field: str(
                next((i for i, header in enumerate(headers) if header_key(header) in aliases), -1)
            )
            for field, aliases in ALIASES.items()
        }
        return sheets, selected, headers, automatic
    finally:
        book.close()


def preview_book(*, user_id, job_id, sheet, mode, mapping, default_category_id=None):
    if mode not in {"catalog", "opening"}:
        raise DomainError("Selecciona catálogo o inventario de apertura.")

    def command(session):
        _authorize(session, user_id, "imports")
        job = session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job or job.status == "confirmed":
            raise DomainError("La importación no existe o ya fue confirmada.")
        rows = sheet_rows(job.content, sheet)
        width = len(rows[0])
        selected = {}
        for field in FIELDS:
            try:
                index = int(mapping.get(field, -1))
            except (TypeError, ValueError):
                raise DomainError("El mapeo de columnas no es válido.") from None
            if index < -1 or index >= width:
                raise DomainError("Una columna seleccionada no existe.")
            selected[field] = index
        if any(selected[field] < 0 for field in ["name", "unit"]):
            raise DomainError("Mapea las columnas Ingrediente y Unidad base.")
        default_category = (
            session.get(Category, default_category_id) if default_category_id else None
        )
        if selected["category"] < 0 and default_category is None:
            raise DomainError("Mapea una categoría o selecciona una categoría predeterminada.")
        if mode == "opening" and selected["quantity"] < 0:
            raise DomainError("Mapea la existencia de apertura antes de continuar.")
        unit_map = {}
        synonyms = {
            "kg": ["kg", "kilogramo", "kilogramos", "kilo", "kilos"],
            "g": ["g", "gr", "gramo", "gramos"],
            "L": ["l", "lt", "litro", "litros"],
            "ml": ["ml", "mililitro", "mililitros"],
            "pza": ["pza", "pz", "pieza", "piezas"],
        }
        for unit in session.scalars(select(Unit)):
            for alias in synonyms.get(unit.symbol, [unit.symbol]):
                unit_map[name_key(alias)] = unit
        existing = {name_key(item.name): item for item in session.scalars(select(Ingredient))}
        seen, preview, errors = set(), [], []

        def value(row, field):
            index = selected[field]
            if index < 0:
                return None
            cell = row[index]
            if cell.data_type == "f":
                raise DomainError(
                    f"{FIELDS[field]} contiene una fórmula. Sustitúyela por su valor verificado."
                )
            return cell.value

        for number, row in enumerate(rows[1:], start=2):
            if all(
                cell.value is None or (isinstance(cell.value, str) and not cell.value.strip())
                for cell in row
            ):
                continue
            try:
                name = " ".join(str(value(row, "name") or "").split())
                category = " ".join(
                    str(
                        value(row, "category")
                        or (default_category.name if default_category else "")
                    ).split()
                )
                supplier = " ".join(str(value(row, "supplier") or "").split())
                code = str(value(row, "code") or "").strip() or None
                if (
                    not name
                    or len(name) > 150
                    or not category
                    or len(category) > 100
                    or len(supplier) > 150
                    or (code and len(code) > 50)
                ):
                    raise DomainError(
                        "Falta el ingrediente/categoría o un texto excede la longitud permitida."
                    )
                key = name_key(name)
                if key in seen:
                    raise DomainError("El ingrediente está repetido en la hoja.")
                seen.add(key)
                unit = unit_map.get(name_key(value(row, "unit")))
                if not unit:
                    raise DomainError("Unidad desconocida. Utiliza kg, g, L, ml o pza.")
                old = existing.get(key)
                if old and (not old.active or old.unit_id != unit.id):
                    raise DomainError(
                        "El ingrediente existente está inactivo o utiliza otra unidad base."
                    )
                minimum = number_cell(value(row, "minimum"), optional=True)
                maximum = number_cell(value(row, "maximum"), optional=True)
                reference_cost = number_cell(value(row, "reference_cost"), optional=True)
                quantity = (
                    number_cell(value(row, "quantity")) if mode == "opening" else Decimal("0")
                )
                unit_cost = (
                    number_cell(value(row, "unit_cost"), optional=True)
                    if mode == "opening"
                    else None
                )
                minimum = Decimal("0") if minimum is None else minimum
                if any(
                    amount is not None and amount < 0
                    for amount in [minimum, maximum, reference_cost, quantity, unit_cost]
                ):
                    raise DomainError("No se permiten cantidades ni costos negativos.")
                if maximum is not None and maximum < minimum:
                    raise DomainError("El máximo es menor que el mínimo.")
                if (
                    old
                    and mode == "opening"
                    and session.scalar(select(Lot.id).where(Lot.ingredient_id == old.id).limit(1))
                ):
                    raise DomainError(
                        "Este ingrediente ya tiene historia de inventario. No puede volver a abrirse."
                    )
                preview.append(
                    dict(
                        row=number,
                        name=name,
                        category=category,
                        supplier=supplier,
                        code=code,
                        unit_id=unit.id,
                        unit=unit.symbol,
                        minimum=str(minimum),
                        maximum=None if maximum is None else str(maximum),
                        reference_cost=None if reference_cost is None else str(reference_cost),
                        quantity=str(quantity),
                        unit_cost=None if unit_cost is None else str(unit_cost),
                        action="existing" if old else "new",
                    )
                )
            except DomainError as exc:
                errors.append(dict(row=number, message=str(exc)))
        if not preview and not errors:
            errors.append(dict(row=0, message="La hoja no contiene registros."))
        job.mode, job.sheet, job.mapping = (
            mode,
            sheet,
            dict(columns=selected, default_category_id=default_category_id),
        )
        job.preview, job.errors, job.status = preview, errors, "preview"
        return job.id

    return _run(command)


def confirm_import(*, user_id, job_id, acknowledge=False, reason=""):
    def command(session):
        _authorize(session, user_id, "imports")
        job = session.scalar(select(ImportJob).where(ImportJob.id == job_id).with_for_update())
        if not job:
            raise DomainError("No existe la importación.")
        if job.status == "confirmed":
            return job.id
        if job.status != "preview" or job.errors or not job.preview:
            raise DomainError("Primero genera una vista previa y corrige todos los errores.")
        if job.mode == "opening" and (not acknowledge or not reason.strip() or len(reason) > 300):
            raise DomainError(
                "Documenta la apertura y confirma su procedencia no verificada y el orden de consumo."
            )
        # One consistent lock also serializes catalog creation by competing imports.
        session.execute(text("SELECT pg_advisory_xact_lock(7002001)"))
        fingerprint = hashlib.sha256(
            json.dumps([job.file_hash, job.sheet, job.mode, job.mapping], sort_keys=True).encode()
        ).hexdigest()
        if session.scalar(select(ImportJob.id).where(ImportJob.fingerprint == fingerprint)):
            raise DomainError(
                "Este archivo, hoja y mapeo ya fueron importados. Consulta el historial."
            )
        categories = {name_key(c.name): c for c in session.scalars(select(Category))}
        suppliers = {name_key(s.name): s for s in session.scalars(select(Supplier))}
        ingredients = {name_key(i.name): i for i in session.scalars(select(Ingredient))}
        targets, created, skipped = [], 0, 0
        for row in job.preview:
            existing_ingredient = ingredients.get(name_key(row["name"]))
            if existing_ingredient is not None:
                skipped += 1
                targets.append((existing_ingredient, row))
                continue
            category = categories.get(name_key(row["category"]))
            if category is None:
                category = Category(name=row["category"])
                session.add(category)
                session.flush()
                categories[name_key(category.name)] = category
            supplier = suppliers.get(name_key(row["supplier"])) if row["supplier"] else None
            if row["supplier"] and supplier is None:
                supplier = Supplier(name=row["supplier"], active=True)
                session.add(supplier)
                session.flush()
                suppliers[name_key(supplier.name)] = supplier
            ingredient = ingredients.get(name_key(row["name"]))
            if ingredient is None:
                ingredient = Ingredient(
                    name=row["name"],
                    code=row["code"],
                    category_id=category.id,
                    supplier_id=supplier.id if supplier else None,
                    unit_id=row["unit_id"],
                    minimum=Decimal(row["minimum"]),
                    maximum=None if row["maximum"] is None else Decimal(row["maximum"]),
                    reference_cost=None
                    if row["reference_cost"] is None
                    else Decimal(row["reference_cost"]),
                    active=True,
                    updated_by=user_id,
                )
                session.add(ingredient)
                session.flush()
                ingredients[name_key(ingredient.name)] = ingredient
                created += 1
            else:
                skipped += 1  # Existing catalog fields are never overwritten by an import.
            targets.append((ingredient, row))
        _lock_ingredients(session, [ingredient.id for ingredient, row in targets])
        # Re-read locked records: a catalog edit may have happened since the preview.
        session.expire_all()
        if any(
            not ingredient.active or ingredient.unit_id != row["unit_id"]
            for ingredient, row in targets
        ):
            raise DomainError(
                "Una unidad cambió desde la vista previa. Vuelve a validar el archivo."
            )
        if job.mode == "opening":
            ids = [ingredient.id for ingredient, row in targets]
            if session.scalar(select(Lot.id).where(Lot.ingredient_id.in_(ids)).limit(1)):
                raise DomainError(
                    "Hay inventario previo. La apertura se revirtió completa para evitar duplicaciones."
                )
            op_id, _ = _claim(session, job.id, "opening", job.preview, user_id, reason.strip())
            for ingredient, row in targets:
                quantity = Decimal(row["quantity"])
                if quantity == 0:
                    continue
                cost = None if row["unit_cost"] is None else Decimal(row["unit_cost"])
                lot = Lot(
                    ingredient_id=ingredient.id,
                    operation_id=op_id,
                    source="opening",
                    code="Apertura · origen histórico no verificado",
                    original_quantity=quantity,
                    remaining_quantity=quantity,
                    unit_cost=cost,
                    expires_on=None,
                )
                movement = Movement(
                    operation_id=op_id,
                    ingredient_id=ingredient.id,
                    quantity=quantity,
                    cost=None if cost is None else cost_value(quantity * cost),
                )
                session.add_all([lot, movement])
                session.flush()
                session.add(
                    Allocation(
                        movement_id=movement.id, lot_id=lot.id, quantity=quantity, unit_cost=cost
                    )
                )
            job.operation_id = op_id
        job.status, job.fingerprint, job.confirmed_at, job.confirmed_by = (
            "confirmed",
            fingerprint,
            utcnow(),
            user_id,
        )
        job.result = dict(created=created, existing=skipped, rows=len(targets), mode=job.mode)
        session.add(
            AuditLog(
                user_id=user_id,
                action="import.confirm",
                detail=f"{job.id}: {len(targets)} registros",
            )
        )
        return job.id

    try:
        return _run(command)
    except IntegrityError:
        raise DomainError(
            "Un nombre o código ya existe. No se guardó ninguna parte de la importación; revisa la vista previa."
        ) from None
