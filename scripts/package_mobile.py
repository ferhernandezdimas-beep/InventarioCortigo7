"""Deliver only mobile sources; never collect backend, credentials or runtime data."""

import hashlib
import json
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "movil"
output = root / "entrega"
output.mkdir(exist_ok=True)
archive = output / "cortijo7-movil-fuentes.zip"
names = [
    "App.tsx",
    "index.ts",
    "package.json",
    "package-lock.json",
    "app.json",
    "tsconfig.json",
    "eas.json",
    ".env.example",
    ".easignore",
    ".nvmrc",
    "README.md",
]
files = [source / n for n in names]
for directory in ["src", "tests", "assets"]:
    files.extend(
        p
        for p in (source / directory).rglob("*")
        if p.is_file() and p.suffix in {".ts", ".tsx", ".png", ".json"}
    )
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(files):
        relative = path.relative_to(source)
        assert not any(
            part in {"node_modules", ".expo"} or part.startswith(".env") and part != ".env.example"
            for part in relative.parts
        )
        bundle.write(path, "cortijo7-movil/" + relative.as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert json.loads(bundle.read("cortijo7-movil/package.json"))["name"] == "cortijo7-movil"
(output / "cortijo7-movil-SHA256SUMS").write_text(
    hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
)
print(archive)
