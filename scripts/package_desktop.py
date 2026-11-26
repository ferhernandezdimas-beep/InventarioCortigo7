"""Package only desktop source; never include backend, accounts, caches or secrets."""

import hashlib
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / "escritorio"
output = root / "entrega" / "escritorio"
output.mkdir(parents=True, exist_ok=True)
archive = output / "Cortijo7-escritorio-fuentes.zip"
files = [source / name for name in ["package.json", "package-lock.json", "README.md"]]
for directory in ["src", "assets", "tests"]:
    files.extend(
        p
        for p in (source / directory).rglob("*")
        if p.is_file() and p.suffix in {".cjs", ".js", ".html", ".css", ".png", ".plist"}
    )
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
    for file in sorted(files):
        bundle.write(file, "escritorio/" + file.relative_to(source).as_posix())
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
(output / "FUENTES-SHA256SUMS").write_text(
    hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n"
)
print(archive)
