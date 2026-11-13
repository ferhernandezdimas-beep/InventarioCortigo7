# CORTIJO 7 — Sistema de Gestión Integral

Entrega para **uso local** con Python 3.12, Flask, PostgreSQL 17, SQLAlchemy 2, psycopg 3, Jinja2, Bootstrap 5 y JavaScript. Incluye despliegue en Render mediante Docker, Gunicorn, Nginx y PostgreSQL 17. Consulta [despliegue y mantenimiento](docs/DESPLIEGUE.md).

## Abrir el sistema

Con Docker Desktop abierto:

```bash
bash scripts/start_local.sh
```

En macOS también puedes ejecutar `Iniciar Cortijo 7.command`. Abre **http://127.0.0.1:8077**. La instalación crea secretos aleatorios solo si falta `.env`; las migraciones conservan los datos existentes. En una instalación nueva, crea tu administrador privado con:

```bash
docker compose exec web flask --app wsgi create-admin
```

No existen credenciales predeterminadas. Si ya tienes una cuenta, conserva tu correo y contraseña; la actualización puede solicitar un nuevo inicio de sesión. El arranque no carga datos de ejemplo automáticamente. El catálogo inicial y sus operaciones tienen origen sintético documentado en [DATOS_PRUEBA.md](docs/DATOS_PRUEBA.md). Su presentación pública usa nombres comerciales, sin avisos adicionales en las pantallas.

## Incluido

- Login ampliado, contraseñas protegidas, CSRF, permisos por rol, control de intentos, usuarios, revocación de sesiones y auditoría.
- Catálogos de ingredientes, categorías, proveedores, unidades y presentaciones.
- Recepciones multirrenglón, borradores, correcciones trazables, lotes, caducidades, PEPS con bloqueos, salidas, mermas y conteos.
- Platillos y recetas versionadas, costos estimados y ventas con consumo atómico, snapshots e idempotencia.
- Punto de venta, pago declarado, cambio, comprobante interno imprimible y cancelaciones auditadas.
- Importación XLSX con mapeo, validación, vista previa, errores descargables, protección de duplicados y apertura documentada.
- Reportes de ventas, inventario, entradas, salidas, caducidades, mermas y recetas; exportación CSV y XLSX.
- Configuración de alertas, guía de uso y procedimientos locales de respaldo/restauración.

## Mantenimiento local

```bash
bash scripts/status_local.sh
bash scripts/backup.sh
bash scripts/restore_check.sh ruta/al/cortijo7.dump --migrate
bash scripts/stop_local.sh
```

La restauración de verificación utiliza una **base nueva**, comprueba migraciones y concilia cantidades/costos. No reemplaza la original. Los datos viven en un volumen PostgreSQL persistente; no elimines ese volumen para actualizar. No hay respaldos automáticos programados.

Recuperación administrativa de una contraseña, con solicitud privada de valores:

```bash
docker compose exec web flask --app wsgi reset-password
```

**Verificación de entrega:** 150 pruebas de regresión sobre PostgreSQL 17 real, incluida la carga repetible y la presentación del catálogo. Véase [registro de verificación](docs/VERIFICACION_ENTREGA.md).

## Desarrollo y pruebas

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
bash scripts/test.sh -q -W error
```

La integración/concurrencia se ejecuta en **PostgreSQL 17 real**, en esquemas temporales de una base separada terminada en `_test`. Sin TEST_DATABASE_URL, pytest marca esas pruebas como omitidas. No se sustituyen por SQLite. El servicio de pruebas usa memoria efímera y un puerto de loopback separado; la base operativa no publica su puerto.

## Paquete y documentación

`python3 scripts/package_local.py` genera `entrega/cortijo7-local.zip` y su SHA-256. Incluye código, dependencias bloqueadas, recursos locales y documentación. Excluye `.env`, base de datos, respaldos, entorno virtual y datos operativos.

- [Guía de entrega local](docs/ENTREGA_LOCAL.md), [instalación](docs/INSTALACION.md) y [manual de usuario](docs/MANUAL_USUARIO.md).
- [Importación Excel](docs/IMPORTACION_EXCEL.md), [PEPS](docs/CONTROL_PEPS.md) y [respaldos](docs/RESPALDOS.md).
- [Arquitectura](docs/ARQUITECTURA.md), [modelo de datos](docs/MODELO_DATOS.md), [pruebas](docs/PRUEBAS.md) y [requisitos completos](docs/REQUERIMIENTOS.md).
- [Decisiones pendientes](docs/DECISIONES_PENDIENTES.md), [historial inicial](docs/AVANCES.md) y [ampliación anterior](docs/AVANCE_OPERATIVO.md).

La aceptación visual en navegador y la validación del Excel original requieren revisión en el equipo y con los archivos reales. El alcance local no incluye integración bancaria, CFDI, múltiples cajas/sucursales, mesas, impresoras térmicas específicas ni sincronización desconectada.
