# Registro de avance — 02/11/2026

## Inspección y alcance

La carpeta de trabajo estaba vacía, incluidos archivos ocultos. No había código, migraciones ni datos del proyecto que transformar. Se leyó el prompt maestro adjunto y se conservó su especificación funcional en `REQUERIMIENTOS.md`, actualizando el motor definitivo a PostgreSQL 17. Se inició Git; `.env`, entorno virtual y respaldos están excluidos.

## Fase 1 — Fundación implementada

Application Factory, blueprints, configuración por entorno, Flask-SQLAlchemy 2.x, psycopg 3, Flask-Migrate/Alembic, login/logout, CSRF, scrypt, controles de intentos en PostgreSQL, permisos por rol, cuentas activas, administración de usuarios, cambio de contraseña y auditoría. Layout responsive Cortijo 7, recursos locales, estados vacíos, indicadores reales y Chart.js. Compose incluye PostgreSQL 17 persistente, healthchecks, migración previa, Gunicorn sin privilegios y Nginx en loopback 8077.

Archivos centrales: `app/__init__.py`, `config.py`, `extensions.py`, `auth.py`, `permissions.py`, `admin.py`, `dashboard.py`, `templates/`, `static/`, `Dockerfile`, `compose.yaml` y `docker/nginx.conf`.

## Fase 2 — Catálogos implementados

Ingredientes con búsqueda, filtros, paginación, detalle, edición y desactivación; categorías; cinco unidades fundamentales; servicio de conversiones Decimal; presentaciones explícitas; proveedores y exportación CSV. La unidad de un ingrediente queda protegida cuando tiene historial. Campos opcionales no se completan con datos inventados.

Archivos centrales: `app/catalog.py`, `forms.py`, `models.py`, `services/numbers.py` y vistas de catálogo. El historial consolidado de compras por proveedor y edición avanzada de categorías/presentaciones siguen pendientes.

## Fase 3 — Inventario avanzado, todavía parcial

Recepciones multirrenglón y presentaciones; lotes y caducidades; existencias física/elegible y costos conocidos; salidas manuales; PEPS con bloqueo ordenado de ingredientes y lotes; vista previa informativa mediante Fetch; idempotencia concurrente; costos por asignación; rollback integral; reversión de salida auditada y conciliación de solo lectura.

Pendientes de esta fase: ajustes físicos/mermas con permisos específicos, política y carga de apertura, correcciones de recepciones, borradores y filtros/paginación adicionales en lotes e inventario. No está autorizada ni habilitada una operación de borrado total.

Archivos centrales: `app/services/inventory.py`, `services/queries.py`, `inventory.py`, vistas de inventario y comandos de verificación.

## Migración

`afbfed7dbf1a` crea las 12 tablas iniciales de seguridad, catálogos e inventario con claves, FK, CHECK, unicidad e índices. Incluye únicamente unidades fundamentales; no carga usuarios o datos demo. Se aplicó en PostgreSQL 17 real. Los esquemas de prueba se generan por Alembic.

## Verificaciones ejecutadas

- Suite ampliada: **66 pruebas aprobadas**, con `pytest -q -W error`, sobre PostgreSQL 17 real. Incluye conexiones concurrentes, no sobreconsumo, solicitudes duplicadas de entrada/salida, orden de bloqueo con varios ingredientes, espera al lote antiguo bloqueado, PEPS, costos, rollback, reversiones, permisos y CSRF.
- Compilación Python, Ruff, sintaxis Bash y `pip check` sin errores.
- Construcción Docker y arranque de PostgreSQL → migración → Gunicorn → Nginx verificados. Conectividad y revisión comprobadas con `verify-database`; conciliación correcta.
- HTTP `/health/ready` responde `{"status":"ok"}` y `/login` responde 200 a través de Nginx en 8077. Cabeceras de seguridad presentes.
- `pg_dump` custom generado y restaurado con `pg_restore` a `c7_restore_check_20261103032825_26259`. Revisión Alembic, conectividad y conciliación correctas. La base restaurada corresponde a una instalación vacía de usuarios/ingredientes/lotes; no demuestra recuperación de una operación comercial real. Se conserva para revisión y no se modificó la base original.
- `.env`, `.venv` y `backups` comprobados como ignorados por Git. No se creó cuenta operativa ni contraseña pública.

## Límites y siguiente fase

No hubo navegador conectado; la revisión visual de escritorio/tablet/móvil sigue pendiente. El renderizado de vistas y los formularios se verificaron con el cliente HTTP de Flask y CSRF activo. No hay HTTPS/certificado, programación de respaldos o infraestructura de producción configurados.

Siguiente trabajo: cerrar políticas y funciones pendientes del inventario, después recetas/versionado/costos, POS transaccional, reportes e importación XLSX según las fases originales. El sistema completo aún no está terminado y no se presenta como listo para operar ventas reales.
