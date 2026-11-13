import os
import uuid
from decimal import Decimal

import pytest
from flask_migrate import upgrade
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db
from app.models import Category, Ingredient, Unit, User


@pytest.fixture(scope="session")
def postgres_url():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Define TEST_DATABASE_URL para ejecutar integración en PostgreSQL 17 real.")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+psycopg" or not parsed.database.endswith("_test"):
        pytest.fail(
            "Por seguridad, TEST_DATABASE_URL debe usar psycopg y una base cuyo nombre termine en _test."
        )
    engine = create_engine(url)
    with engine.connect() as connection:
        assert int(connection.scalar(text("SHOW server_version_num"))) // 10000 == 17
    engine.dispose()
    return url


@pytest.fixture
def app(postgres_url):
    # Every test owns a new schema. Never clear an existing schema or database.
    schema = "test_" + uuid.uuid4().hex
    engine = create_engine(postgres_url)
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-only-secret-key-never-for-production",
            "SQLALCHEMY_DATABASE_URI": postgres_url,
            "SQLALCHEMY_ENGINE_OPTIONS": {
                "pool_pre_ping": True,
                "isolation_level": "READ COMMITTED",
                "connect_args": {
                    "options": f"-c search_path={schema} -c timezone=UTC -c lock_timeout=5000 -c statement_timeout=30000"
                },
            },
        }
    )
    try:
        with app.app_context():
            upgrade()
        yield app
    finally:
        with app.app_context():
            db.session.remove()
            db.engine.dispose()
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


@pytest.fixture
def seeded(app):
    with app.app_context():
        user = User(
            name="Responsable de prueba", email="admin@example.com", role="admin", active=True
        )
        user.set_password("test-password-strong-123")
        category = Category(name="Verduras de prueba")
        db.session.add_all([user, category])
        db.session.flush()
        unit = db.session.scalar(select(Unit).where(Unit.symbol == "kg"))
        ingredient = Ingredient(
            name="Cebolla de prueba",
            category_id=category.id,
            unit_id=unit.id,
            minimum=Decimal("1"),
            active=True,
            updated_by=user.id,
        )
        ingredient2 = Ingredient(
            name="Jitomate de prueba",
            category_id=category.id,
            unit_id=unit.id,
            minimum=Decimal("0"),
            active=True,
            updated_by=user.id,
        )
        db.session.add_all([ingredient, ingredient2])
        db.session.commit()
        return dict(
            user=user.id,
            ingredient=ingredient.id,
            ingredient2=ingredient2.id,
            unit=unit.id,
            category=category.id,
        )


@pytest.fixture
def client(app):
    return app.test_client()
