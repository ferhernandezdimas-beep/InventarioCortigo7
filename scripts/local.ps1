param([ValidateSet('iniciar','estado','detener','administrador','datos-ejemplo')][string]$Accion='iniciar')
$ErrorActionPreference='Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
function Docker-C7 {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw 'Docker no pudo completar la operación. Revisa el mensaje anterior.' }
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Instala Docker Desktop con Docker Compose y vuelve a abrir esta ventana.' }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { throw 'Abre Docker Desktop y espera a que termine de iniciar.' }
if ($Accion -eq 'iniciar') {
    if (-not (Test-Path '.env')) {
        $ProjectRoot=(Get-Location).Path
        Docker-C7 run --rm --mount "type=bind,source=$ProjectRoot,target=/workspace" --workdir /workspace python:3.12-slim python scripts/init_env.py
    }
    Docker-C7 compose up -d --build --wait --wait-timeout 180
}
switch ($Accion) {
    'administrador' { Docker-C7 compose exec web flask --app wsgi create-admin; exit }
    'datos-ejemplo' { Docker-C7 compose exec web flask --app wsgi seed-demo; exit }
    'detener' { Docker-C7 compose stop; Write-Host 'Servicios detenidos; los datos se conservan.'; exit }
}
Docker-C7 compose ps
Docker-C7 compose exec -T web flask --app wsgi verify-database
Docker-C7 compose exec -T web flask --app wsgi reconcile-inventory
$PortValue='8077'
foreach ($line in (Get-Content '.env')) {
    if ($line -match '^HTTP_PORT=(\d+)$') { $PortValue=$Matches[1] }
}
$LocalUrl="http://127.0.0.1:$PortValue"
$response=Invoke-RestMethod "$LocalUrl/health/ready" -TimeoutSec 10
if ($response.status -ne 'ok') { throw 'El sistema todavía no está listo.' }
Write-Host "Sistema disponible en $LocalUrl"
if ($Accion -eq 'iniciar') {
    Write-Host 'Primera instalación: ejecuta Crear administrador Windows.cmd para crear tu cuenta privada.'
    Start-Process $LocalUrl
}
