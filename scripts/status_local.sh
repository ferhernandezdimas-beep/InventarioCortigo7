#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps
docker compose exec -T web flask --app wsgi verify-database
docker compose exec -T web flask --app wsgi reconcile-inventory
port="$(awk -F= '/^HTTP_PORT=/{print $2; exit}' .env | tr -d '\r\"\047')"
port="${port:-8077}"
[[ "$port" =~ ^[0-9]+$ ]] && ((port >= 1 && port <= 65535)) || { printf 'HTTP_PORT no es válido.\n' >&2; exit 1; }
url="http://127.0.0.1:$port"
curl --fail --silent --show-error --max-time 10 "$url/health/ready" >/dev/null
printf 'Aplicación disponible en %s\n' "$url"
