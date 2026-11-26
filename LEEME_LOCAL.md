# Cortijo 7 · Instalación local para Windows y Mac

Este paquete contiene el código de la web, backend, base PostgreSQL mediante Docker, migraciones, recursos, pruebas y documentación. Incluye también las fuentes móviles y de escritorio en sus propias carpetas. La instalación principal se utiliza desde el navegador en **http://127.0.0.1:8077**.

## Antes de empezar

1. Instala y abre **Docker Desktop**, con Docker Compose v2. En Windows utiliza contenedores Linux y completa la configuración WSL2 que solicite Docker.
2. Descomprime **todo** el ZIP en una carpeta propia, por ejemplo `Documentos/Cortijo7`; no ejecutes archivos dentro del ZIP ni combines esta carpeta con otra instalación existente.
3. Necesitas internet la primera vez para descargar imágenes y dependencias. Después, con las imágenes ya construidas y Docker abierto, el sistema puede operar sin Render ni internet.
4. Verifica que el puerto 8077 esté disponible. Si otra instalación lo utiliza, detén esa instalación antes de continuar o configura `HTTP_PORT` en `.env`.

No necesitas instalar Python o PostgreSQL por separado. El sistema genera una `.env` privada con secretos aleatorios solo si falta. La configuración genera también un nombre Docker propio (`COMPOSE_PROJECT_NAME`) para aislar los contenedores y el volumen de otras instalaciones. Conserva esa configuración para que PostgreSQL siga reconociendo sus credenciales y su volumen.

## Windows

Haz doble clic en **Iniciar Cortijo 7 Windows.cmd**. La primera construcción puede tardar varios minutos. Cuando termine, abre el navegador y muestra el estado de los contenedores.

Luego ejecuta **Crear administrador Windows.cmd** y captura nombre, correo y contraseña. La contraseña no se muestra mientras la escribes. Entra con esa cuenta a http://127.0.0.1:8077.

Para detener los servicios utiliza **Detener Cortijo 7 Windows.cmd**. Conserva la carpeta y el volumen de Docker.

Los lanzadores `.cmd` no requieren PowerShell ni cambiar sus políticas. También se incluye `scripts/local.ps1` como alternativa para usuarios que ya tienen habilitado ejecutar sus propios scripts.

## Mac

Desde Terminal, dentro de la carpeta descomprimida:

```bash
bash scripts/start_local.sh
docker compose exec web flask --app wsgi create-admin
```

También está el lanzador **Iniciar Cortijo 7.command**; si el ZIP no conserva su permiso de ejecución, utiliza el comando anterior. Abre http://127.0.0.1:8077 y entra con el administrador que acabas de crear.

Para detener: `bash scripts/stop_local.sh`. Para comprobar estado: `bash scripts/status_local.sh`.

## Comandos equivalentes con Docker

Desde PowerShell o Terminal, en la carpeta del proyecto:

```text
docker run --rm --mount "type=bind,source=RUTA_COMPLETA_DE_LA_CARPETA,target=/workspace" --workdir /workspace python:3.12-slim python scripts/init_env.py
docker compose up -d --build --wait --wait-timeout 180
docker compose exec web flask --app wsgi create-admin
```

Sustituye `RUTA_COMPLETA_DE_LA_CARPETA` por la ruta real, sin quitar las comillas. Ejecuta el primer comando solo si **no existe `.env`**. El archivo `.env.example` sirve de referencia, pero sus secretos vacíos deben generarse antes de iniciar.

Para comprobar datos:

```text
docker compose exec -T web flask --app wsgi verify-database
docker compose exec -T web flask --app wsgi reconcile-inventory
```

Para detener conservando datos: `docker compose stop`.

## Usuarios, datos y operación sin internet

La instalación nueva comienza vacía. **No incluye cuentas, contraseñas ni datos de Render**. Local y Render son bases independientes: crear o vender localmente no sincroniza con Render, ni viceversa. Los usuarios de Render no sirven automáticamente en esta instalación; crea tus cuentas locales desde Administración.

Puedes usar todos los módulos web y sus roles localmente. Flask, SQLAlchemy, PostgreSQL 17, las migraciones y PEPS funcionan dentro de los contenedores. Los activos web se incluyen en el proyecto para no depender de CDNs. La instalación no incluye procesamiento bancario ni IA generativa externa.

Carga opcional de un escenario realista, únicamente si quieres datos sintéticos para conocer el sistema, **después de crear el administrador**:

```text
docker compose exec web flask --app wsgi seed-demo
```

No se carga automáticamente y no sustituye ni borra operaciones existentes. Consulta `docs/DATOS_PRUEBA.md` antes de ejecutarlo en una instalación de trabajo.

## Fuentes de escritorio y móvil

Los instaladores de escritorio publicados se conectan a Render; no cambian automáticamente al servidor local. Para usar la ventana Electron con este servidor desde fuentes necesitas Node 24 y ejecutar, dentro de `escritorio/`, `npm ci` una vez y:

Mac:
```bash
CORTIJO7_DESKTOP_URL=http://127.0.0.1:8077 npm start
```

Windows PowerShell:
```powershell
$env:CORTIJO7_DESKTOP_URL='http://127.0.0.1:8077'
npm start
```

Las fuentes móviles están en `movil/`; consulta su README para configurar la URL de la computadora. Un teléfono no accede al `localhost` de la computadora. Esta entrega local se limita a la interfaz de loopback y no publica el servicio a la red.

## Conservación y respaldos

Los datos viven en un volumen persistente de Docker. No borres el volumen, no uses `docker compose down -v` y no elimines Docker Desktop si necesitas conservarlos. No regeneres la contraseña de `.env` con una base ya inicializada. No hay respaldos automáticos.

Mac: `bash scripts/backup.sh`. En Windows, desde PowerShell, también puedes generar un respaldo binario seguro sin redirección de salida:

```text
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/cortijo7-local.dump'
docker compose cp postgres:/tmp/cortijo7-local.dump ./cortijo7-local.dump
```

Guarda el `.dump` y una copia privada de `.env` fuera de la carpeta de trabajo. Los procedimientos de verificación/restauración están en `docs/` y `scripts/restore_check.sh`; verifican sobre una base nueva. No restaures sobre tus datos activos sin una copia y autorización del responsable.

## Si no abre

- Confirma que Docker está iniciado y que terminó de descargar/construir las imágenes.
- Ejecuta `docker compose ps` y `docker compose logs --tail=80 web migrate nginx`.
- Abre `http://127.0.0.1:8077/health/ready`; debe responder `{"status":"ok"}`.
- Si ya existía una instalación en esta computadora, conserva su `.env` y volumen. No copies una contraseña nueva encima de ella.
- La primera descarga requiere internet; para uso posterior sin red, conserva las imágenes y contenedores de Docker.
