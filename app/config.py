import os
from datetime import timedelta

from sqlalchemy.engine import URL, make_url


def configuration(overrides=None):
    env = os.getenv("APP_ENV", "development")
    url = os.getenv("DATABASE_URL")
    if url:
        url = make_url(url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
    else:
        url = URL.create(
            "postgresql+psycopg",
            username=os.getenv("POSTGRES_USER", "cortijo7"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "cortijo7_db"),
        )
    settings = dict(
        SECRET_KEY=os.getenv("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_size": 3,
            "max_overflow": 2,
            "isolation_level": "READ COMMITTED",
            "connect_args": {
                "options": "-c timezone=UTC -c lock_timeout=5000 -c statement_timeout=30000"
            },
        },
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=env == "production",
        REMEMBER_COOKIE_SECURE=env == "production",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        WTF_CSRF_TIME_LIMIT=8 * 60 * 60,
        TRUST_PROXY=os.getenv("TRUST_PROXY", "false").lower() == "true",
        EXPIRY_ALERT_DAYS=int(os.getenv("EXPIRY_ALERT_DAYS", "7")),
        APP_ENV=env,
    )
    settings.update(overrides or {})
    if not settings["SECRET_KEY"] or len(settings["SECRET_KEY"]) < 32:
        raise RuntimeError("Configura SECRET_KEY con al menos 32 caracteres aleatorios.")
    if make_url(settings["SQLALCHEMY_DATABASE_URI"]).drivername != "postgresql+psycopg":
        raise RuntimeError("La única base admitida es PostgreSQL con psycopg 3.")
    return settings
