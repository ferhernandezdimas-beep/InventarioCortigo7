# Control PEPS en PostgreSQL 17

PEPS consume primero la entrada más antigua elegible; `received_at, id` ofrece un desempate estable. Caducidad no establece el orden: esta política no es FEFO. Se excluyen agotados y fechas anteriores al día local; los lotes sin caducidad conservan NULL.

Cada comando ejecuta estos pasos dentro de `Session.begin()`:

1. Verificar usuario activo y permiso.
2. Insertar la operación con su clave de idempotencia. Si ya existe y el hash coincide, devolver su folio sin repetir movimientos.
3. Bloquear ingredientes por id ascendente con `SELECT ... FOR UPDATE OF ingredients`. Las recepciones siguen el mismo orden.
4. Bloquear lotes por entrada/id con `SELECT ... FOR UPDATE OF inventory_lots`, esperando los lotes ocupados.
5. Revalidar disponibilidad elegible después de adquirir los bloqueos.
6. Descontar lotes, registrar movimiento y asignaciones con costo histórico.
7. Guardar auditoría y confirmar una única transacción.

No se utiliza `SKIP LOCKED`. Si falla cualquier ingrediente, no se confirma ninguno. Las restricciones de saldo proporcionan una protección adicional. Un deadlock, fallo de serialización o timeout revierte la operación completa; el usuario puede reintentar con la misma referencia. No se reintenta parcialmente desde una transacción fallida.

La vista previa mediante Fetch API es informativa y no reserva stock. La confirmación repite la validación bajo bloqueo. La reversión devuelve cantidades a sus lotes de origen, conserva costos y crea movimientos compensatorios; `reverses_id` impide revertir dos veces la misma salida.

Ejemplo de prueba sintético: 10 kg a $20 y 15 kg a $24; retirar 12 kg consume 10 y 2, cuesta $248 y deja 13 kg. Este caso y los consumidores concurrentes se ejecutan en PostgreSQL 17 real.

Conciliación de solo lectura: `flask --app wsgi reconcile-inventory`, comparando lotes/asignaciones, movimiento/asignaciones e ingredientes/movimientos. No repara diferencias automáticamente. Los ajustes positivos se marcan recuperados y las aperturas se marcan opening, ambos sin inventar procedencia de compra. La apertura se ordena desde su registro local y exige aceptación explícita; el archivo histórico auténtico debe revisarse antes de confirmar.
