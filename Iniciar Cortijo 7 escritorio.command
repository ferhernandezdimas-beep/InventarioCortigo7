#!/bin/zsh
cd "${0:A:h}/escritorio" || exit 1
if [[ "$(uname -m)" == "arm64" ]]; then
  desktop_bundle="dist/mac-arm64/Cortijo 7.app"
else
  desktop_bundle="dist/mac/Cortijo 7.app"
fi
if [[ -d "$desktop_bundle" ]]; then
  open "$desktop_bundle"
else
  desktop_node_dir='/Users/luisfernandohernandez/Library/Application Support/Herd/config/nvm/versions/node/v24.15.0/bin'
  if [[ -x "$desktop_node_dir/node" ]]; then export PATH="$desktop_node_dir:$PATH"; fi
  if ! command -v npm >/dev/null; then
    echo 'Instala el DMG de entrega/escritorio. Para ejecutar desde fuentes necesitas Node 24.'
    read -r '?Presiona Enter para cerrar.'
    exit 1
  fi
  if [[ ! -d node_modules/electron ]]; then npm ci || exit 1; fi
  env -u ELECTRON_RUN_AS_NODE npm start
fi
