#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps
docker compose exec -T web flask --app wsgi verify-database
docker compose exec -T web flask --app wsgi reconcile-inventory
python3 scripts/local_status.py "$@"
