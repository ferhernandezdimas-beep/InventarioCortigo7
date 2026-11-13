import csv
import io

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_wtf.file import FileAllowed, FileField, FileRequired
from sqlalchemy import select
from sqlalchemy.orm import defer
from wtforms import BooleanField, SelectField, TextAreaField
from wtforms.validators import Length

from app.delivery_models import ImportJob
from app.extensions import db
from app.forms import SpanishForm
from app.models import Category
from app.permissions import permission_required
from app.services.imports import FIELDS, confirm_import, preview_book, upload_book, workbook_info
from app.services.numbers import DomainError
from app.services.xlsx import workbook_bytes

bp = Blueprint("imports", __name__, url_prefix="/importaciones")


class UploadForm(SpanishForm):
    file = FileField(
        "Archivo Excel (.xlsx)",
        validators=[
            FileRequired(message="Selecciona un archivo."),
            FileAllowed(["xlsx"], "Utiliza un archivo .xlsx."),
        ],
    )


class MapForm(SpanishForm):
    sheet = SelectField("Hoja del libro")
    mode = SelectField(
        "Tipo de importación",
        choices=lambda: {
            "catalog": "Solo catálogo: no cambia existencias",
            "opening": "Catálogo e inventario de apertura",
        },
    )
    default_category_id = SelectField("Categoría si no se mapea una columna", coerce=int)


for key, label in FIELDS.items():
    setattr(MapForm, key, SelectField(label, coerce=int))


class ConfirmForm(SpanishForm):
    reason = TextAreaField("Documento o motivo de la apertura", validators=[Length(max=300)])
    acknowledge = BooleanField(
        "Confirmo el saldo físico y acepto que la procedencia histórica no está verificada; PEPS lo ordenará desde la fecha de registro, sin inventar compras ni caducidades"
    )


@bp.route("/", methods=["GET", "POST"])
@permission_required("imports")
def index():
    form = UploadForm()
    if form.validate_on_submit():
        try:
            job_id = upload_book(
                user_id=current_user.id,
                filename=form.file.data.filename,
                content=form.file.data.read(2 * 1024 * 1024 + 1),
            )
            return redirect(url_for("imports.mapping", job_id=job_id))
        except DomainError as exc:
            flash(str(exc), "danger")
    jobs = db.session.scalars(
        select(ImportJob)
        .options(defer(ImportJob.content), defer(ImportJob.preview), defer(ImportJob.errors))
        .order_by(ImportJob.created_at.desc())
        .limit(50)
    ).all()
    return render_template("imports/index.html", form=form, jobs=jobs)


@bp.route("/<uuid:job_id>/columnas", methods=["GET", "POST"])
@permission_required("imports")
def mapping(job_id):
    job = db.get_or_404(ImportJob, job_id)
    if job.status == "confirmed":
        return redirect(url_for("imports.detail", job_id=job.id))
    try:
        sheets, selected, headers, automatic = workbook_info(job, request.values.get("sheet"))
    except DomainError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("imports.index"))
    form = MapForm()
    form.sheet.choices = [(name, name) for name in sheets]
    form.default_category_id.choices = [(0, "Usar la columna Categoría")] + [
        (category.id, category.name)
        for category in db.session.scalars(select(Category).order_by(Category.name))
    ]
    options = [(-1, "No importar esta columna")] + [
        (i, f"{i + 1}. {label or 'Sin encabezado'}") for i, label in enumerate(headers)
    ]
    for key in FIELDS:
        field = getattr(form, key)
        field.choices = options
        if request.method == "GET":
            field.data = (
                int(job.mapping["columns"].get(key, -1))
                if job.mapping and job.sheet == selected
                else int(automatic[key])
            )
    if request.method == "GET":
        form.sheet.data = selected
        form.mode.data = job.mode or "catalog"
        form.default_category_id.data = (
            job.mapping.get("default_category_id") or 0 if job.mapping else 0
        )
    if form.validate_on_submit():
        try:
            preview_book(
                user_id=current_user.id,
                job_id=job.id,
                sheet=form.sheet.data,
                mode=form.mode.data,
                mapping={key: getattr(form, key).data for key in FIELDS},
                default_category_id=form.default_category_id.data or None,
            )
            return redirect(url_for("imports.detail", job_id=job.id))
        except DomainError as exc:
            flash(str(exc), "danger")
    return render_template(
        "imports/mapping.html", job=job, form=form, fields=FIELDS, sheets=sheets, selected=selected
    )


@bp.route("/<uuid:job_id>", methods=["GET", "POST"])
@permission_required("imports")
def detail(job_id):
    job = db.get_or_404(ImportJob, job_id)
    form = ConfirmForm()
    if form.validate_on_submit():
        try:
            confirm_import(
                user_id=current_user.id,
                job_id=job.id,
                acknowledge=form.acknowledge.data,
                reason=form.reason.data or "",
            )
            flash("Importación confirmada. Consulta el resumen y el historial.", "success")
            return redirect(url_for("imports.detail", job_id=job.id))
        except DomainError as exc:
            flash(str(exc), "danger")
    if job.status == "uploaded":
        return redirect(url_for("imports.mapping", job_id=job.id))
    return render_template("imports/detail.html", job=job, form=form)


@bp.get("/<uuid:job_id>/errores.csv")
@permission_required("imports")
def errors(job_id):
    job = db.get_or_404(ImportJob, job_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fila", "Error"])
    for error in job.errors or []:
        writer.writerow([error["row"], error["message"]])
    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=errores-{job.id}.csv"},
    )


@bp.get("/plantilla.xlsx")
@permission_required("imports")
def template():
    content = workbook_bytes(
        [
            "Ingrediente",
            "Unidad base",
            "Categoría",
            "Proveedor",
            "Código",
            "Mínimo",
            "Máximo",
            "Costo de referencia",
            "Existencia de apertura",
            "Costo por unidad base de apertura",
        ],
        [],
        "Inventario",
    )
    return Response(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=plantilla-cortijo7.xlsx"},
    )
