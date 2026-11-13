"""Generate local secrets without printing them or overwriting existing settings."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit("Ya existe .env; se conserva sin cambios.")
data = (root / ".env.example").read_text()
data = data.replace("SECRET_KEY=\n", "SECRET_KEY=" + secrets.token_hex(32) + "\n")
data = data.replace("POSTGRES_PASSWORD=\n", "POSTGRES_PASSWORD=" + secrets.token_urlsafe(32) + "\n")
# Exclusive creation avoids a concurrent invocation replacing an existing file.
with target.open("x") as handle:
    target.chmod(0o600)
    handle.write(data)
print("Se creó .env con secretos locales aleatorios. No lo agregues al repositorio.")
