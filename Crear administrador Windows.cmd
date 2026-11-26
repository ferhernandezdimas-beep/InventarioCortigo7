@echo off
cd /d "%~dp0"
docker compose exec web flask --app wsgi create-admin
pause
