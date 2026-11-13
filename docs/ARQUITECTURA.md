# Arquitectura

PostgreSQL 17 es el único motor. SQLAlchemy 2 utiliza exclusivamente `postgresql+psycopg`, validado al iniciar. Flask-SQLAlchemy administra consultas por solicitud; cada comando crítico de inventario abre una sesión independiente con una transacción completa. Flask-Migrate/Alembic crea todas las tablas; no se ejecuta creación automática de esquema al arrancar.

`app/__init__.py` contiene la factory y extensiones. Los blueprints `auth`, `dashboard`, `catalog`, `inventory`, `admin`, `recipes`, `pos`, `reports`, `imports` y `settings` separan operaciones. `app/services/inventory.py` concentra las escrituras de lotes y movimientos. `numbers.py` valida Decimal y conversiones; `queries.py` calcula saldos e indicadores. Las rutas validan Flask-WTF y permisos centrales en `permissions.py`.

Jinja2 renderiza HTML semántico. Bootstrap y CSS propio aportan el sistema visual verde/arena/terracota. JavaScript mejora navegación móvil, formularios y vista previa, sin decidir consumos. Chart.js representa operaciones reales. Todos los recursos se sirven localmente; la política CSP restringe recursos al propio origen.

## Persistencia y concurrencia

- `NUMERIC(18,6)` en cantidades y costos unitarios, `NUMERIC(24,6)` en costos de movimientos. Decimal de extremo a extremo; seis decimales y redondeo HALF_UP de costos derivados.
- `TIMESTAMP WITH TIME ZONE` en eventos, UTC en conexiones, conversión a America/Mexico_City en presentación. Caducidad es una fecha de calendario local independiente.
- READ COMMITTED; ingredientes bloqueados por id ascendente, lotes por entrada/id. Recepciones y salidas comparten ese protocolo.
- Identificador UUID de idempotencia único y hash del contenido/actor/tipo. `INSERT ON CONFLICT` espera al competidor; una repetición idéntica devuelve el folio original. Un contenido distinto se rechaza.
- Timeout de bloqueo de 5 s y de consulta de 30 s. Deadlock/serialización/timeout provocan rollback y un mensaje para reintentar con la misma referencia.

## Seguridad y operación

Flask-Login, scrypt, CSRF en toda escritura, cookies HttpOnly/SameSite, cookies Secure en producción, verificación de usuarios activos en cada solicitud, permisos backend y auditoría. Límite de login persistido mediante upsert PostgreSQL: 10 intentos por IP/correo y 100 por IP cada 15 minutos, compartido por workers.

La red Docker interna comunica base, migración y web. Nginx es la única entrada y se publica en loopback. `TRUST_PROXY=true` se configura solo en esta topología para confiar en una única cabecera de IP reescrita por Nginx. No publiques Gunicorn directamente con ese valor. `services/sales.py` confirma venta, método de pago declarado, snapshots y consumos dentro de una sola transacción. `consume_fifo` y `restore_movements` participan en la sesión del servicio llamante: no abren otra transacción ni confirman parcialmente. Orden de venta: idempotencia → platillos por id → ingredientes por id → lotes por entrada/id. Las recetas se editan bajo el mismo bloqueo de platillo; una edición desactualizada se rechaza por versión. Los precios y totales esperados se revalidan en el servidor.

Referencias oficiales: [dialecto psycopg de SQLAlchemy](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#module-sqlalchemy.dialects.postgresql.psycopg), [transacciones](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html), [bloqueos PostgreSQL 17](https://www.postgresql.org/docs/17/explicit-locking.html).

Los importes de venta utilizan NUMERIC(14,2). Las cantidades por porción se redondean a seis decimales con HALF_UP antes de multiplicar por el número de unidades; estimación y venta comparten la misma regla. Se bloquean conversiones entre dimensiones incompatibles y cantidades que redondeen a cero.

La importación usa openpyxl/defusedxml con límites de lectura, contenido almacenado en PostgreSQL, validación previa y confirmación atómica. La conciliación compara cantidades, costos y pertenencia de ingrediente por lote/movimiento en REPEATABLE READ de solo lectura. Las sesiones incorporan la versión de autenticación del usuario; cambiar/restablecer contraseña revoca las anteriores. El healthcheck exige PostgreSQL 17 y revisión Alembic igual al head del código.
