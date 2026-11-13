#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { printf 'Instala Docker Desktop con Compose v2.\n' >&2; exit 1; }
docker info >/dev/null 2>&1 || { printf 'Abre Docker Desktop y vuelve a ejecutar este comando.\n' >&2; exit 1; }
if [[ ! -f .env ]]; then python3 scripts/init_env.py; fi
docker compose up -d --build
bash scripts/status_local.sh --wait
printf '\nSi es la primera instalación, crea tu administrador con:\n  docker compose exec web flask --app wsgi create-admin\n'
