from decimal import ROUND_HALF_UP, Decimal, InvalidOperation


class DomainError(ValueError):
    pass


def decimal_value(value, *, positive=False):
    if isinstance(value, (float, bool)):
        raise DomainError("Captura cantidades decimales válidas, sin números binarios.")
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise DomainError("La cantidad no es válida.") from None
    if not number.is_finite() or abs(number) >= Decimal("1000000000000"):
        raise DomainError("La cantidad está fuera del rango permitido.")
    if number.as_tuple().exponent < -6:
        raise DomainError("Se permiten hasta seis decimales.")
    if positive and number <= 0:
        raise DomainError("La cantidad debe ser mayor que cero.")
    return number


def convert(quantity, source, target):
    quantity = decimal_value(quantity, positive=True)
    if source.dimension != target.dimension:
        raise DomainError("No se pueden mezclar unidades de masa, volumen y piezas.")
    result = quantity * source.factor / target.factor
    return decimal_value(result, positive=True)


def cost_value(value):
    if not value.is_finite() or abs(value) >= Decimal("1000000000000000000"):
        raise DomainError("El importe total está fuera del rango permitido.")
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
