"""Build a reproducible source delivery using an explicit allowlist; exclude runtime data."""

import hashlib
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "entrega"
output.mkdir(exist_ok=True)
archive = output / "cortijo7-local.zip"
directories = ["app", "docs", "docker", "migrations", "scripts", "tests"]
names = [
    "README.md",
    "Dockerfile",
    "Dockerfile.render",
    "render.yaml",
    "compose.yaml",
    "compose.test.yaml",
    ".env.example",
    ".gitignore",
    ".dockerignore",
    "pyproject.toml",
    "requirements.txt",
    "requirements.lock",
    "requirements-dev.txt",
    "requirements-dev.lock",
    "wsgi.py",
    "Iniciar Cortijo 7.command",
]
files = [root / name for name in names if (root / name).is_file()]
for directory in directories:
    files.extend(
        path
        for path in (root / directory).rglob("*")
        if path.is_file()
        and not any(
            part in {"__pycache__", ".DS_Store", ".pytest_cache"}
            for part in path.relative_to(root).parts
        )
        and path.suffix not in {".pyc", ".log", ".dump"}
    )
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(set(files)):
        relative = path.relative_to(root)
        if path.name.startswith(".env") and path.name != ".env.example":
            raise SystemExit("Archivo de entorno privado detectado: entrega cancelada.")
        bundle.write(path, "cortijo7/" + relative.as_posix())
with zipfile.ZipFile(archive) as bundle:
    if bundle.testzip():
        raise SystemExit("El archivo de entrega no superó la validación ZIP.")
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / "SHA256SUMS").write_text(f"{digest}  {archive.name}\n")
print(f"Entrega local creada: {archive}")
print(
    "El paquete contiene código, dependencias, recursos y documentación; excluye credenciales y datos operativos."
)
