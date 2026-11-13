"""Bounded XLSX reading and formula-safe exports, without filesystem uploads."""

import io
import re
import unicodedata
import zipfile
from decimal import Decimal

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from app.services.numbers import DomainError, decimal_value

MAX_ROWS, MAX_COLUMNS = 2000, 60


def name_key(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def header_key(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", name_key(value)) if not unicodedata.combining(c)
    ).replace(".", "")


def read_book(content):
    if not content or len(content) > 2 * 1024 * 1024:
        raise DomainError("El archivo debe contener datos y pesar como máximo 2 MB.")
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries) > 200 or sum(e.file_size for e in entries) > 20 * 1024 * 1024:
                raise DomainError("El libro excede los límites de lectura segura.")
            if any("vbaproject" in e.filename.lower() for e in entries):
                raise DomainError("No se permiten libros con macros.")
        return load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
    except DomainError:
        raise
    except Exception:
        raise DomainError(
            "No se pudo abrir el archivo. Utiliza un libro .xlsx válido, sin contraseña."
        ) from None


def sheet_rows(content, sheet):
    book = read_book(content)
    try:
        if sheet not in book.sheetnames:
            raise DomainError("La hoja seleccionada no existe.")
        ws = book[sheet]
        if (ws.max_row or 0) > MAX_ROWS + 1 or (ws.max_column or 0) > MAX_COLUMNS:
            raise DomainError(
                f"Se permiten hasta {MAX_ROWS} filas y {MAX_COLUMNS} columnas por hoja."
            )
        result = list(
            ws.iter_rows(max_row=MAX_ROWS + 2, max_col=min(ws.max_column or 1, MAX_COLUMNS))
        )
        while result and all(cell.value is None for cell in result[-1]):
            result.pop()
        if len(result) < 2 or not any(cell.value is not None for row in result[1:] for cell in row):
            raise DomainError("La hoja no contiene registros para importar.")
        if len(result) > MAX_ROWS + 1:
            raise DomainError("La hoja tiene demasiadas filas.")
        return result
    finally:
        book.close()


def number_cell(value, *, optional=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        if optional:
            return None
        raise DomainError("Falta una cantidad obligatoria.")
    if isinstance(value, bool):
        raise DomainError("Un valor lógico no es una cantidad.")
    text = str(value).strip().replace("$", "").replace("MXN", "").replace(" ", "")
    if "," in text and "." in text:
        text = (
            text.replace(",", "")
            if text.rfind(".") > text.rfind(",")
            else text.replace(".", "").replace(",", ".")
        )
    elif "," in text:
        text = (
            text.replace(",", "")
            if re.fullmatch(r"-?\d{1,3}(,\d{3})+", text)
            else text.replace(",", ".")
        )
    return decimal_value(text)


def workbook_bytes(headers, rows, title="Datos"):
    book = Workbook()
    sheet = book.active
    sheet.title = title[:31]
    sheet.append(headers)
    for row in rows:
        sheet.append([str(value) if isinstance(value, Decimal) else value for value in row])
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"  # Never turn user-controlled text into spreadsheet formulas.
    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="173B35")
        cell.font = Font(name="Calibri", color="FFFFFF", bold=True)
        cell.alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 26
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        width = min(50, max(16, max(len(str(c.value or "")) for c in column) + 3))
        sheet.column_dimensions[column[0].column_letter].width = width
    output = io.BytesIO()
    book.save(output)
    book.close()
    return output.getvalue()
