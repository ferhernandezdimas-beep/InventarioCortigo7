# Instalación local

1. Instalar Docker con Compose v2 y Python 3. Verificar `docker version` y `docker compose version`.
2. Desde la raíz, ejecutar `python3 scripts/init_env.py`. Se crea `.env` con contraseña de base y SECRET_KEY aleatorias; no imprime secretos ni sustituye un archivo existente.
3. Ejecutar `docker compose up -d --build`. PostgreSQL 17 tiene healthcheck. El servicio `migrate` aplica Alembic; después inicia Gunicorn y finalmente Nginx.
4. Ejecutar `docker compose exec web flask --app wsgi create-admin`. Contraseña privada de 12–200 caracteres, sin credenciales predeterminadas. Una instalación que ya tiene administrador se administra desde Usuarios.
5. Abrir http://127.0.0.1:8077 e iniciar sesión.
6. Comprobar `docker compose exec web flask --app wsgi verify-database` y `docker compose exec web flask --app wsgi reconcile-inventory`.

`HTTP_PORT` permite cambiar el puerto si está ocupado. `.env.example` documenta todas las variables. El constructor `URL.create` maneja caracteres especiales en POSTGRES_PASSWORD sin concatenar contraseñas manualmente. Si se usa DATABASE_URL, el esquema obligatorio es `postgresql+psycopg://usuario:contraseña@postgres:5432/cortijo7_db`, con credenciales escapadas para URL. No guardes valores reales en código o documentación.

## Desarrollo fuera del contenedor

Crear `.venv` con Python 3.12 e instalar `requirements-dev.lock`. Proveer POSTGRES_HOST/PORT/USER/PASSWORD/DB o DATABASE_URL mediante el entorno para una instancia PostgreSQL 17 disponible. Ejecutar `.venv/bin/flask --app wsgi db upgrade`, luego `.venv/bin/flask --app wsgi run --port 8077`. No activar debug con datos reales.

Para pruebas, `bash scripts/test.sh -q` inicia una base efímera separada en 55437. Esa excepción local no publica el puerto de la base operativa.

## Si ya existen datos

Esta carpeta estaba vacía al inspeccionarla. Si posteriormente se conecta una base existente, detener el proceso de cambio, obtener un respaldo comprobado, inventariar esquema/volúmenes y preparar un ensayo de transformación con conteos, Decimal, unidades y saldos conciliados. No reinicializar volúmenes ni aplicar transformaciones destructivas sin autorización. Nunca modificar una migración ya aplicada; agregar una revisión nueva.

Para la entrega local puede utilizarse `bash scripts/start_local.sh` o el archivo .command en macOS. `status_local.sh` verifica servicios, revisión, conciliación y HTTP; `stop_local.sh` conserva los datos. Consulte ENTREGA_LOCAL.md para operación y recuperación de contraseñas. Render no se configura ni despliega en esta entrega.
