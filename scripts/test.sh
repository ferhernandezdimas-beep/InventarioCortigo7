#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose -f compose.test.yaml up -d --wait
export TEST_DATABASE_URL=postgresql+psycopg://cortijo7_test:local-test-only@127.0.0.1:55437/cortijo7_test
.venv/bin/python -m pytest "$@"
