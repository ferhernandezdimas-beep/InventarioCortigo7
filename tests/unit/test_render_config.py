import pytest
from sqlalchemy.engine import make_url

from app.config import configuration


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_render_connection_string_always_uses_psycopg3(monkeypatch, scheme):
    monkeypatch.setenv("SECRET_KEY", "configuration-test-key-with-at-least-32-characters")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "DATABASE_URL", f"{scheme}://owner:fake-value@internal-host/c7?sslmode=require"
    )
    settings = configuration()
    url = make_url(settings["SQLALCHEMY_DATABASE_URI"])
    assert url.drivername == "postgresql+psycopg"
    assert url.query["sslmode"] == "require"
    assert settings["SESSION_COOKIE_SECURE"] and settings["REMEMBER_COOKIE_SECURE"]


def test_other_database_dialects_are_refused(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "configuration-test-key-with-at-least-32-characters")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        configuration()
