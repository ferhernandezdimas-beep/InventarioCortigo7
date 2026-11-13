#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose stop
printf 'Servicios detenidos. Los datos y contenedores se conservan.\n'
