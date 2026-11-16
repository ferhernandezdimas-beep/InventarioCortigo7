#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/movil"
# Prefer the installed Node 24 LTS when Herd provides it.
node_lts_dir="$HOME/Library/Application Support/Herd/config/nvm/versions/node/v24.15.0/bin"
if [[ -x "$node_lts_dir/node" ]]; then export PATH="$node_lts_dir:$PATH"; fi
if ! command -v node >/dev/null 2>&1; then
  echo 'Instala Node 24 LTS y vuelve a abrir este archivo.'
  read -r -p 'Pulsa Enter para salir.'
  exit 1
fi
if [[ ! -d node_modules ]]; then npm ci; fi
npm start
