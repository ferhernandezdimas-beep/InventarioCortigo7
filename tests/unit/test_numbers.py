from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import create_app
from app.services.numbers import DomainError, convert, cost_value, decimal_value


@pytest.mark.parametrize(
    "source,target,quantity,expected",
    [
        ("kg", "g", "3", "3000"),
        ("g", "kg", "1500", "1.5"),
        ("L", "ml", "4", "4000"),
        ("ml", "L", "250", "0.25"),
        ("pza", "pza", "3", "3"),
    ],
)
def test_exact_conversion(source, target, quantity, expected):
    units = {
        s: SimpleNamespace(dimension=d, factor=Decimal(f))
        for s, d, f in [
            ("kg", "mass", "1000"),
            ("g", "mass", "1"),
            ("L", "volume", "1000"),
            ("ml", "volume", "1"),
            ("pza", "count", "1"),
        ]
    }
    assert convert(quantity, units[source], units[target]) == Decimal(expected)


def test_reject_incompatible_units():
    with pytest.raises(DomainError):
        convert("1", SimpleNamespace(dimension="count"), SimpleNamespace(dimension="mass"))


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "-Infinity", "abc", "0", "-1", "1.0000001", "1000000000000", 0.1, True],
)
def test_reject_invalid_quantities(value):
    with pytest.raises(DomainError):
        decimal_value(value, positive=True)


def test_monetary_precision():
    assert Decimal("0.1") * Decimal("3") == Decimal("0.3")
    assert cost_value(Decimal("1.1234565")) == Decimal("1.123457")


def test_require_official_driver(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        create_app({"SECRET_KEY": "test-only-secret-that-has-enough-characters"})
