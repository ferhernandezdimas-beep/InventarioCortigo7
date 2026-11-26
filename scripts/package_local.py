"""Deliver local sources with an explicit allowlist and no runtime/user data."""

import hashlib
import re
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
output = root / "entrega"
output.mkdir(exist_ok=True)
archive = output / "cortijo7-local.zip"
names = [
    "LEEME_LOCAL.md",
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
    "Iniciar Cortijo 7 Windows.cmd",
    "Crear administrador Windows.cmd",
    "Detener Cortijo 7 Windows.cmd",
    "Iniciar Cortijo 7 escritorio.command",
    "Iniciar Cortijo 7 móvil.command",
]
files = [root / name for name in names]
for directory in ["app", "docs", "docker", "migrations", "scripts", "tests"]:
    files.extend(
        p
        for p in (root / directory).rglob("*")
        if p.is_file()
        and p.suffix
        in {
            ".py",
            ".html",
            ".css",
            ".js",
            ".json",
            ".png",
            ".svg",
            ".ico",
            ".woff",
            ".woff2",
            ".ttf",
            ".md",
            ".txt",
            ".sh",
            ".ps1",
            ".conf",
            ".ini",
            ".mako",
        }
        and not any(
            part.startswith(".") or part == "__pycache__" for part in p.relative_to(root).parts
        )
    )
for project in ["movil", "escritorio"]:
    for name in [
        "package.json",
        "package-lock.json",
        "README.md",
        "App.tsx",
        "app.json",
        "eas.json",
        "tsconfig.json",
        ".env.example",
        ".easignore",
        ".npmrc",
        ".nvmrc",
    ]:
        p = root / project / name
        if p.is_file():
            files.append(p)
    for directory in ["src", "assets", "tests", "vendor"]:
        files.extend(
            p
            for p in (root / project / directory).rglob("*")
            if p.is_file()
            and (
                p.suffix
                in {
                    ".ts",
                    ".tsx",
                    ".js",
                    ".cjs",
                    ".mjs",
                    ".css",
                    ".html",
                    ".json",
                    ".png",
                    ".plist",
                    ".md",
                }
                or p.name == "LICENSE"
            )
        )
secret = re.compile(
    rb"rnd_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(set(files)):
        relative = path.relative_to(root)
        if path.is_symlink() or any(
            part in {"node_modules", ".git", ".expo", "__pycache__", "backups", "entrega"}
            for part in relative.parts
        ):
            raise SystemExit("Se detectó una ruta no permitida: " + str(relative))
        if path.name.startswith(".env") and path.name != ".env.example":
            raise SystemExit("Se detectó un entorno privado: entrega cancelada.")
        if secret.search(path.read_bytes()):
            raise SystemExit("Se detectó una posible credencial: " + str(relative))
        bundle.write(path, "cortijo7/" + relative.as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    for name in [
        "LEEME_LOCAL.md",
        "compose.yaml",
        "app/mobile_actions.py",
        "migrations/versions/f72101c7a002_assistant_catalog_actions.py",
        "Iniciar Cortijo 7 Windows.cmd",
    ]:
        assert "cortijo7/" + name in bundle.namelist(), name
    assert not any(
        name.endswith((".dump", ".db", ".sqlite", ".pyc", "/.env")) for name in bundle.namelist()
    )
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
(output / "cortijo7-local.zip.sha256").write_text(digest + "  " + archive.name + "\n")
print(f"Entrega local creada: {archive} ({archive.stat().st_size:,} bytes)")
print(
    "Incluye web, fuentes móvil/escritorio y guía local; excluye credenciales y datos operativos."
)
