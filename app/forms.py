from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    FieldList,
    Form,
    FormField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
    i18n,
)
from wtforms.fields.choices import SelectChoice
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)

from app.services.numbers import DomainError, decimal_value


class SpanishForm(FlaskForm):
    class Meta(FlaskForm.Meta):
        def get_translations(self, form):
            return i18n.get_translations(["es"])


class ExactDecimalField(DecimalField):
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data is not None:
            try:
                self.data = decimal_value(self.data)
            except DomainError as exc:
                self.data = None
                raise ValueError(str(exc)) from None


def clean_text(form, field):
    if not field.data or not field.data.strip():
        raise ValidationError("Este campo es obligatorio.")


class LoginForm(SpanishForm):
    email = StringField(
        "Correo electrónico",
        validators=[DataRequired(), Email(), Length(max=254)],
        render_kw={"autocomplete": "username", "inputmode": "email", "autofocus": True},
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(), Length(max=200)],
        render_kw={"autocomplete": "current-password"},
    )


class IngredientForm(SpanishForm):
    name = StringField(
        "Nombre del ingrediente", validators=[DataRequired(), clean_text, Length(max=150)]
    )
    code = StringField("Código interno · opcional", validators=[Optional(), Length(max=50)])
    description = TextAreaField("Descripción · opcional", validators=[Optional(), Length(max=2000)])
    category_id = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    unit_id = SelectField("Unidad base", coerce=int, validators=[DataRequired()])
    supplier_id = SelectField("Proveedor principal · opcional", coerce=int)
    minimum = ExactDecimalField(
        "Existencia mínima",
        places=6,
        validators=[InputRequired(), NumberRange(min=0, max=999999999999)],
    )
    maximum = ExactDecimalField(
        "Existencia máxima · opcional",
        places=6,
        validators=[Optional(), NumberRange(min=0, max=999999999999)],
    )
    reference_cost = ExactDecimalField(
        "Costo de referencia por unidad · opcional",
        places=6,
        validators=[Optional(), NumberRange(min=0, max=999999999999)],
    )
    active = BooleanField("Ingrediente activo", default=True)

    def validate_maximum(self, field):
        if (
            field.data is not None
            and self.minimum.data is not None
            and field.data < self.minimum.data
        ):
            raise ValidationError("El máximo debe ser mayor o igual al mínimo.")


class CategoryForm(SpanishForm):
    name = StringField(
        "Nombre de la categoría", validators=[DataRequired(), clean_text, Length(max=100)]
    )


class SupplierForm(SpanishForm):
    name = StringField("Nombre comercial", validators=[DataRequired(), clean_text, Length(max=150)])
    legal_name = StringField("Razón social · opcional", validators=[Optional(), Length(max=200)])
    contact = StringField("Contacto · opcional", validators=[Optional(), Length(max=100)])
    phone = StringField("Teléfono · opcional", validators=[Optional(), Length(max=30)])
    email = StringField(
        "Correo electrónico · opcional", validators=[Optional(), Email(), Length(max=254)]
    )
    address = TextAreaField("Dirección · opcional", validators=[Optional(), Length(max=1000)])
    notes = TextAreaField("Notas · opcional", validators=[Optional(), Length(max=2000)])
    active = BooleanField("Proveedor activo", default=True)


class PresentationForm(SpanishForm):
    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    name = StringField(
        "Nombre de la presentación", validators=[DataRequired(), clean_text, Length(max=100)]
    )
    base_quantity = ExactDecimalField(
        "Contenido en unidades base",
        places=6,
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )


class ReceiptLine(Form):
    class Meta:
        locales = ["es"]

    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    presentation_id = SelectField("Presentación · opcional", coerce=int, default=0)
    quantity = ExactDecimalField(
        "Cantidad de unidades o presentaciones",
        places=6,
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )
    unit_cost = ExactDecimalField(
        "Precio por unidad o presentación · MXN",
        places=6,
        validators=[Optional(), NumberRange(min=0, max=999999999999)],
    )
    code = StringField("Lote · opcional", validators=[Optional(), Length(max=100)])
    expires_on = DateField("Caducidad · opcional", validators=[Optional()])


class ReceiptForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    revision = HiddenField(default="0")
    supplier_id = SelectField("Proveedor · opcional", coerce=int)
    reference = StringField(
        "Referencia de compra · opcional", validators=[Optional(), Length(max=100)]
    )
    reason = StringField(
        "Observaciones",
        default="Recepción de mercancía",
        validators=[DataRequired(), clean_text, Length(max=300)],
    )
    lines = FieldList(FormField(ReceiptLine), min_entries=1, max_entries=30)


class IssueForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    ingredient_id = SelectField("Ingrediente", coerce=int, validators=[DataRequired()])
    quantity = ExactDecimalField(
        "Cantidad en unidad base",
        places=6,
        validators=[InputRequired(), NumberRange(min=Decimal("0.000001"), max=999999999999)],
    )
    reason = StringField(
        "Motivo de consumo manual", validators=[DataRequired(), clean_text, Length(max=300)]
    )


class ReverseForm(SpanishForm):
    key = HiddenField(validators=[DataRequired()])
    reason = StringField(
        "Motivo de la reversión", validators=[DataRequired(), clean_text, Length(max=300)]
    )


class UserForm(SpanishForm):
    name = StringField("Nombre", validators=[DataRequired(), clean_text, Length(max=100)])
    email = StringField("Correo electrónico", validators=[DataRequired(), Email(), Length(max=254)])
    role = SelectField(
        "Rol",
        choices=[
            SelectChoice("admin", "Administrador"),
            SelectChoice("manager", "Gerente"),
            SelectChoice("warehouse", "Almacén"),
            SelectChoice("cashier", "Caja"),
        ],
    )
    password = PasswordField(
        "Contraseña nueva · mínimo 12 caracteres", validators=[Optional(), Length(min=12, max=200)]
    )
    active = BooleanField("Cuenta activa", default=True)


class PasswordForm(SpanishForm):
    current = PasswordField("Contraseña actual", validators=[DataRequired(), Length(max=200)])
    password = PasswordField(
        "Contraseña nueva", validators=[DataRequired(), Length(min=12, max=200)]
    )
    confirmation = PasswordField(
        "Confirmar contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )
