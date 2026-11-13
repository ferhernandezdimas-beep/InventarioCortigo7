# Escenario local de prueba — 10/11/2026

Se incorporó una carga explícita y reproducible a solicitud del usuario. El arranque normal del sistema y las migraciones no la ejecutan. Los registros previos y las credenciales se conservan; no se crean cuentas adicionales.

## Contenido

- 7 proveedores ficticios de San Juan del Río/Bajío y 9 categorías de insumos.
- 46 ingredientes con unidades kg/L/pieza, costos de ejemplo en MXN, mínimos, máximos y presentaciones de compra.
- Dos recepciones por proveedor con lotes/costos diferentes, más ejemplos de caducidad y una recepción corregida mediante reversión.
- 20 productos con receta por porción: chilaquiles, huevos rancheros, enchiladas, tacos, tortas, ensaladas, desayunos, café y bebidas.
- 74 tickets distribuidos en siete fechas locales, con efectivo/cambio, tarjeta y transferencia; dos cancelaciones, una con devolución y otra sin recuperación de insumos.
- Salida de degustación, mermas, ajuste por conteo y un borrador sin confirmar que no afecta existencias.
- Ejemplos de existencia baja, agotado, próximo a caducar, caducado y costo pendiente.

Los nombres llevan «(demo)», los códigos comienzan con `DEMO-` y los motivos indican `[DEMO]`. Los proveedores, contactos, precios, fechas y operaciones son ficticios. Los correos usan el dominio de documentación `example.com`; no se registran teléfonos de terceros. Las auditorías conservan la hora real de carga y las fechas simuladas solo se aplican a los registros de este escenario.

Un aviso visible indica que **las existencias, ventas y costos demo están incluidos en los reportes**. No deben confundirse con la operación real. Las recetas y los precios sirven para practicar; requieren validación del restaurante antes de adoptarse para operar.

## Repetir o reanudar

Después de crear un administrador existente y respaldar la base:

```bash
bash scripts/backup.sh
docker compose exec web flask --app wsgi seed-demo
docker compose exec web flask --app wsgi reconcile-inventory
```

Opcionalmente se puede indicar `--user-id ID` para seleccionar el administrador responsable. Una carga completa repetida no agrega registros. Si se interrumpe, se reanuda con la misma fecha de referencia y claves idempotentes. Cada operación utiliza las mismas transacciones y bloqueos que el sistema normal; no se escribe un saldo artificial para sustituir movimientos. El comando rechaza colisiones con nombres/códigos previos sin manifiesto, un responsable sin rol Administrador, cargas simultáneas y `APP_ENV=production`.

No incluye una opción de borrado masivo. El respaldo anterior a esta carga permite revisar la base previa mediante el procedimiento de restauración a una base nueva; no se debe sobrescribir la instancia activa ni eliminar su volumen para quitar ejemplos. La transición a datos exclusivamente reales requiere un procedimiento específico con respaldo.

## Presentación de la entrega publicada — 12/11/2026

Por solicitud expresa del usuario, la instalación publicada utiliza nombres comerciales sin sufijos, códigos INS/PLT/LT y folios REC/VTA, sin leyendas de prueba en las pantallas. El contenido sigue siendo sintético: no acredita compras, pagos ni proveedores verificados del restaurante. La procedencia se conserva aquí y en los manifiestos de auditoría. La actualización de presentación es transaccional, idempotente y no modifica importes, existencias, fechas, asignaciones ni claves de transacción. Las colisiones con registros ajenos se rechazan sin combinar ni borrar historia.

El comando administrativo `flask --app wsgi prepare-presentation` solo se aplica a una carga inicial completada. La base se transfiere por un respaldo privado a una base nueva, nunca mediante archivos incluidos en Git.
