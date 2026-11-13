"""HTTP readiness on loopback; never evaluates or prints environment secrets."""

import json
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
port = "8077"
if (root / ".env").exists():
    for line in (root / ".env").read_text().splitlines():
        if line.startswith("HTTP_PORT="):
            port = line.split("=", 1)[1].strip().strip("\"'")
if not port.isdigit() or not 1 <= int(port) <= 65535:
    raise SystemExit("HTTP_PORT no es un puerto local válido.")
url = f"http://127.0.0.1:{port}"
if "--url" in sys.argv:
    print(url)
    raise SystemExit(0)
deadline = time.monotonic() + (30 if "--wait" in sys.argv else 0)
while True:
    try:
        with urlopen(url + "/health/ready", timeout=5) as response:
            if json.load(response).get("status") != "ok":
                raise ValueError()
        break
    except (URLError, ValueError, TimeoutError):
        if time.monotonic() >= deadline:
            raise SystemExit(
                "La aplicación aún no está lista. Revisa Docker y ejecuta bash scripts/status_local.sh."
            )
        time.sleep(1)
print(f"Aplicación disponible en {url}")
