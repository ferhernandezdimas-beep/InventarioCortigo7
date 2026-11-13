# Respaldos y restauración PostgreSQL 17

`bash scripts/backup.sh` utiliza el `pg_dump` 17 incluido en el contenedor de PostgreSQL. Genera `backups/*.dump` en formato custom, con permisos privados y sin propietarios/ACL. Comprueba que `pg_restore --list` lee el catálogo. Un archivo legible aún necesita un ensayo de restauración.

```bash
bash scripts/backup.sh
bash scripts/restore_check.sh backups/archivo.dump
```

El segundo comando crea una base NUEVA con nombre aleatorio `c7_restore_check_*`, usando `template0`. No contiene `--clean`, `dropdb` ni reemplazo de la base activa. `pg_restore --exit-on-error --single-transaction` restaura esquema y datos; cualquier fallo revierte esa restauración, dejando la nueva base disponible para diagnóstico. Se utilizan las herramientas 17 del contenedor, no versiones incompatibles del host.

Después verifica:

1. Conexión PostgreSQL 17 y revisión Alembic igual al head del código.
2. Conciliación lote/asignaciones, movimiento/asignaciones y ingrediente/movimientos.
3. Conteos de usuarios, ingredientes, lotes, movimientos y asignaciones, impresos para revisión.
4. En una prueba operativa independiente, iniciar la aplicación contra esa copia y comprobar acceso, catálogo y folios representativos.

Para comparar conteos con la fuente, coordinar una ventana sin escrituras y registrar los conteos al generar el respaldo. `pg_dump` proporciona su snapshot consistente; un conteo de la fuente tomada más tarde con escrituras activas no representa ese mismo snapshot. No basta que el archivo exista.

La base de verificación se conserva y se informa por nombre. Su eliminación y cualquier restauración sobre producción son tareas administrativas posteriores con autorización. El respaldo contiene información sensible: almacenar fuera del repositorio, proteger y cifrar la copia externa. No hay respaldos programados, retención ni transferencia remota configurados en esta entrega.

Referencia: [pg_dump 17](https://www.postgresql.org/docs/17/app-pgdump.html) y [pg_restore 17](https://www.postgresql.org/docs/17/app-pgrestore.html).

Para ensayar un respaldo anterior contra una versión nueva, agrega `--migrate`: `bash scripts/restore_check.sh ruta/archivo.dump --migrate`. Solo la base nueva de verificación recibe Alembic; la fuente no se altera. Después se ejecutan verificación y conciliación. Ejecuta este ensayo antes de actualizar la base operativa.
