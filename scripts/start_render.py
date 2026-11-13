"""Start migrations, Gunicorn and unprivileged Nginx on Render's assigned port."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def migrate():
    # Free services have no pre-deploy command. Serialize schema upgrades at startup.
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from flask_migrate import upgrade
    from sqlalchemy import text

    sys.path.insert(0, str(ROOT))
    from app import create_app
    from app.extensions import db

    with create_app().app_context():
        with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("SELECT pg_advisory_lock(7004001)"))
            try:
                version = int(connection.scalar(text("SHOW server_version_num")))
                if version // 10000 != 17:
                    raise RuntimeError("Se requiere PostgreSQL 17.")
                upgrade(directory=str(ROOT / "migrations"))
                config = Config()
                config.set_main_option("script_location", str(ROOT / "migrations"))
                revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != ScriptDirectory.from_config(config).get_current_head():
                    raise RuntimeError("La revisión de la base no coincide con el código.")
            finally:
                connection.execute(text("SELECT pg_advisory_unlock(7004001)"))


def main():
    os.chdir(ROOT)
    port = os.environ.get("PORT", "10000")
    if not port.isdigit() or not 1024 <= int(port) <= 65535 or int(port) == 8000:
        raise RuntimeError("PORT no es válido para el proxy web.")
    migrate()
    config = Path("/tmp/cortijo7-nginx.conf")
    config.write_text((ROOT / "docker/nginx.render.conf").read_text().replace("__PORT__", port))
    children = []
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(
            subprocess.Popen(
                [
                    "gunicorn",
                    "--bind",
                    "127.0.0.1:8000",
                    "--workers",
                    "2",
                    "--timeout",
                    "45",
                    "--access-logfile",
                    "-",
                    "wsgi:app",
                ]
            )
        )
        children.append(subprocess.Popen(["nginx", "-c", str(config), "-g", "daemon off;"]))
        while not stopping:
            for child in children:
                result = child.poll()
                if result is not None:
                    return result or 1
            time.sleep(0.25)
        return 0
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    raise SystemExit(main())
