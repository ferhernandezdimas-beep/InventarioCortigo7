#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
archive=${1:?Indica un archivo .dump generado con pg_dump --format=custom}
if [[ ! -f "$archive" ]]; then
  printf 'No existe el archivo indicado.\n' >&2
  exit 1
fi
# Always create a new database. Never clean, drop or replace an existing one.
target="c7_restore_check_$(date -u +%Y%m%d%H%M%S)_${RANDOM}"
docker compose exec -T postgres pg_restore --list < "$archive" > /dev/null
docker compose exec -T -e RESTORE_DB="$target" postgres sh -c 'exec createdb --username="$POSTGRES_USER" --template=template0 "$RESTORE_DB"'
docker compose exec -T -e RESTORE_DB="$target" postgres sh -c 'exec pg_restore --username="$POSTGRES_USER" --dbname="$RESTORE_DB" --exit-on-error --single-transaction --no-owner --no-acl' < "$archive"
if [[ "${2:-}" == "--migrate" ]]; then
  docker compose run --rm --no-deps -T -e POSTGRES_DB="$target" -e DATABASE_URL= web flask --app wsgi db upgrade
fi
docker compose run --rm --no-deps -T -e POSTGRES_DB="$target" -e DATABASE_URL= web flask --app wsgi verify-database
docker compose run --rm --no-deps -T -e POSTGRES_DB="$target" -e DATABASE_URL= web flask --app wsgi reconcile-inventory
docker compose exec -T -e RESTORE_DB="$target" postgres sh -c 'exec psql --username="$POSTGRES_USER" --dbname="$RESTORE_DB" --set=ON_ERROR_STOP=1 --command="SELECT (SELECT count(*) FROM users) AS usuarios, (SELECT count(*) FROM ingredients) AS ingredientes, (SELECT count(*) FROM inventory_lots) AS lotes, (SELECT count(*) FROM inventory_movements) AS movimientos, (SELECT count(*) FROM inventory_movement_allocations) AS asignaciones;"'
printf 'Restauración y conciliación verificadas en %s. La base original permanece intacta.\n' "$target"
printf 'La base de verificación se conserva para revisión. Su eliminación es una operación administrativa posterior.\n'
