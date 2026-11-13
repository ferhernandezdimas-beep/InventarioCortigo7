#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p backups
backup_dir=$(mktemp -d "backups/cortijo7_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")
archive="$backup_dir/cortijo7.dump"
if ! docker compose exec -T postgres sh -c 'exec pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --no-owner --no-acl' > "$archive"; then
  printf 'Falló pg_dump. Archivo incompleto conservado para diagnóstico: %s\n' "$archive" >&2
  exit 1
fi
docker compose exec -T postgres pg_restore --list < "$archive" > /dev/null
printf 'Respaldo generado y catálogo legible: %s\n' "$archive"
printf 'Verifica la restauración con: bash scripts/restore_check.sh %q\n' "$archive"
