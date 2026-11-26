@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
where docker >nul 2>&1
if errorlevel 1 (
  echo Instala Docker Desktop con Docker Compose antes de continuar.
  goto :error
)
docker info >nul 2>&1
if errorlevel 1 (
  echo Abre Docker Desktop y espera a que termine de iniciar.
  goto :error
)
if not exist .env (
  docker run --rm --mount "type=bind,source=%CD%,target=/workspace" --workdir /workspace python:3.12-slim python scripts/init_env.py
  if errorlevel 1 goto :error
)
docker compose up -d --build --wait --wait-timeout 180
if errorlevel 1 goto :error
docker compose exec -T web flask --app wsgi verify-database
if errorlevel 1 goto :error
docker compose exec -T web flask --app wsgi reconcile-inventory
if errorlevel 1 goto :error
set "C7_PORT=8077"
for /f "tokens=2 delims==" %%P in ('findstr /r /x "HTTP_PORT=[0-9][0-9]*" .env') do set "C7_PORT=%%P"
echo Sistema disponible en http://127.0.0.1:%C7_PORT%
echo Primera instalacion: ejecuta Crear administrador Windows.cmd para crear tu cuenta.
start "" "http://127.0.0.1:%C7_PORT%"
pause
exit /b 0
:error
echo No se pudo iniciar. Revisa el mensaje anterior. Los datos existentes se conservan.
pause
exit /b 1
