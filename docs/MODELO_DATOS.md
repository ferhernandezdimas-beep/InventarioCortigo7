# Modelo de datos implementado

| Entidades | Función e integridad |
|---|---|
| users | Correo único, hash scrypt, rol restringido y estado activo |
| login_throttles | Contadores atómicos por hash de IP/cuenta y ventana temporal |
| audit_logs | Actor opcional, evento, detalle y fecha UTC |
| ingredient_categories | Clasificación con nombre único |
| measurement_units | g/kg/ml/L/pza, dimensión y factor positivo |
| suppliers | Contacto opcional y desactivación lógica |
| ingredients | Unidad, categoría, proveedor principal, min/max, costo de referencia y responsable |
| purchase_presentations | Equivalencia explícita positiva por ingrediente/nombre |
| inventory_operations | Folio UUID, idempotencia única, hash, responsable, proveedor, motivo y reversión única |
| inventory_lots | Entrada, caducidad opcional, costo opcional, cantidad original y saldo restringido a [0, original] |
| inventory_movements | Cantidad firmada no nula y costo histórico nullable |
| inventory_movement_allocations | Lote, movimiento, cantidad firmada y costo unitario histórico; par único |

La migración inicial incluye las cinco unidades fundamentales; no inserta ingredientes, usuarios o ventas demo. Las FK históricas utilizan RESTRICT. Nombres de ingredientes únicos sin distinguir mayúsculas mediante índice `lower(name)`. Hay índices para PEPS, caducidad, fechas de operación y relaciones consultadas.

Fuente de verdad operativa: saldos de lotes actualizados transaccionalmente y reconciliables con movimientos y asignaciones. No existe stock editable en ingredientes. El costo de referencia nunca reemplaza costos desconocidos ni modifica costos históricos.

Las recepciones y salidas de varios ingredientes se consolidan en `inventory_operations`, `inventory_movements` y sus asignaciones. No se duplican encabezados/partidas en tablas sin comportamiento propio. La segunda revisión `dafd29ee82d6` agrega ocho tablas: menu_items, recipe_versions, recipe_ingredients, sales, sale_items, sale_item_ingredient_snapshots, sale_cancellations e inventory_counts. Amplía los tipos de operación y agrega el origen receipt/recovered a lotes, conservando los registros existentes. Los pagos declarados (un método por venta) se consolidan en sales: método, monto recibido y cambio, sin integración bancaria. Los snapshots se relacionan con el movimiento histórico de ingrediente y sus asignaciones por lote. El índice de reversión y la unicidad de cancelación impiden devoluciones repetidas.

El downgrade de la segunda revisión se rechaza cuando hay recetas, ventas o nuevas operaciones históricas. No se borra esa historia para volver a una versión anterior. La tercera revisión d457194c1424 agrega import_jobs, inventory_receipt_drafts y system_settings; amplía orígenes/tipos de operación y añade users.auth_version para revocar sesiones anteriores a un cambio de contraseña. Los archivos, mapeos, vistas previas y errores de importación se conservan en PostgreSQL. Los borradores no alteran inventario hasta confirmarse.
