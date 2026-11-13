from decimal import Decimal

from wtforms import (
    BooleanField,
    FieldList,
    Form,
    FormField,
    HiddenField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, Regexp

from app.forms import ExactDecimalField, SpanishForm, clean_text


class RecipeLineForm(Form):
    class Meta:
        locales = ["es"]

    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    quantity = ExactDecimalField(
        "Cantidad por preparación",
        places=6,
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )
    unit_id = SelectField("Unidad de captura", coerce=int, validators=[DataRequired()])


class RecipeForm(SpanishForm):
    expected_version = HiddenField(
        default="0",
        validators=[
            DataRequired(),
            Regexp(r"^\d{1,9}$", message="La versión de la receta no es válida."),
        ],
    )
    name = StringField(
        "Nombre del platillo o producto", validators=[DataRequired(), clean_text, Length(max=150)]
    )
    code = StringField("Código · opcional", validators=[Optional(), Length(max=50)])
    category = StringField(
        "Categoría del menú", validators=[DataRequired(), clean_text, Length(max=80)]
    )
    price = ExactDecimalField(
        "Precio de venta · MXN",
        places=2,
        validators=[InputRequired(), NumberRange(min=0, max=999999999999)],
    )
    kind = SelectField(
        "Tipo de producto",
        choices=lambda: {
            "prepared": "Platillo preparado",
            "direct": "Producto directo con inventario",
        },
    )
    yield_quantity = ExactDecimalField(
        "Porciones que rinde esta preparación",
        places=6,
        default=Decimal("1"),
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )
    description = TextAreaField("Descripción · opcional", validators=[Optional(), Length(max=2000)])
    notes = TextAreaField(
        "Notas de esta versión · opcional", validators=[Optional(), Length(max=500)]
    )
    active = BooleanField("Disponible para venta", default=True)
    lines = FieldList(FormField(RecipeLineForm), min_entries=1, max_entries=60)


class SaleForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    cart = HiddenField(default="[]", validators=[DataRequired(), Length(max=20000)])
    expected_total = HiddenField(validators=[DataRequired()])
    method = SelectField(
        "Método de pago declarado",
        choices=lambda: {"cash": "Efectivo", "card": "Tarjeta", "transfer": "Transferencia"},
    )
    received = ExactDecimalField(
        "Efectivo recibido · MXN",
        places=2,
        validators=[Optional(), NumberRange(min=0, max=999999999999)],
    )


class CancellationForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    reason = StringField(
        "Motivo de cancelación", validators=[DataRequired(), clean_text, Length(max=300)]
    )
    restock = BooleanField(
        "Confirmo que los insumos se recuperaron físicamente y pueden volver a sus lotes originales"
    )


class WasteForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    quantity = ExactDecimalField(
        "Cantidad retirada en unidad base",
        places=6,
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )
    category = SelectField(
        "Tipo de baja",
        choices=lambda: {
            "waste": "Merma de operación",
            "damaged": "Producto dañado",
            "expired": "Producto caducado",
        },
    )
    reason = TextAreaField(
        "Motivo y evidencia de la baja", validators=[DataRequired(), clean_text, Length(max=250)]
    )


class CountForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    expected_quantity = ExactDecimalField(
        "Existencia del sistema antes del conteo",
        places=6,
        validators=[InputRequired(), NumberRange(min=0, max=999999999999)],
    )
    counted_quantity = ExactDecimalField(
        "Existencia física contada · unidad base",
        places=6,
        validators=[InputRequired(), NumberRange(min=0, max=999999999999)],
    )
    reason = TextAreaField(
        "Motivo y procedencia de la diferencia",
        validators=[DataRequired(), clean_text, Length(max=300)],
    )
