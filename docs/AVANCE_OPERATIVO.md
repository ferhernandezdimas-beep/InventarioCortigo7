# Ampliación operativa — 02/11/2026

## Cambios de interfaz solicitados

Las capturas evidenciaron un límite de 1,100 px en formularios dentro de un área de trabajo más ancha. Se eliminó ese límite y se reorganizaron las pantallas:

- Entradas y salidas utilizan una columna principal y una lateral con orientación pertinente a la operación; se apilan en pantallas pequeñas.
- El encabezado de recepción utiliza todo el ancho; el detalle presenta hasta tres campos por fila en escritorio. Se pueden agregar y quitar renglones, conservando índices únicos.
- Categorías y presentaciones muestran un formulario compacto junto a su listado, con edición de registros.
- Si faltan ingredientes/categorías, se explica qué crear y se ofrece un acceso directo. No se muestran selectores vacíos sin orientación ni se habilita una confirmación imposible.
- La navegación lateral tiene desplazamiento propio para mantener accesibles los nuevos módulos. Los cambios de CSS/JS llevan una versión en la URL para renovar la caché.

El navegador de automatización no está conectado. Los cambios se basaron en las capturas aportadas y se verificaron mediante renderizado HTTP de Flask, incluyendo estados vacíos; todavía requiere revisión visual manual en escritorio, tablet y móvil.

## Funcionalidad agregada

**Platillos y recetas:** categorías del menú, precio final en MXN, preparado/producto directo, disponibilidad, rendimiento, cantidades, conversiones por dimensión, versiones inmutables y control de edición desactualizada. La unidad base del ingrediente queda protegida también cuando se usa en recetas. El costo por porción se estima aplicando PEPS sin reservar inventario; faltantes o costos desconocidos impiden presentar un total definitivo.

**Punto de venta:** búsqueda y categorías, disponibilidad para una porción, carrito con edición/eliminación, total cotizado por el servidor, efectivo/tarjeta/transferencia declarados, monto recibido/cambio y comprobante interno imprimible. Al confirmar se vuelven a validar precios, recetas y stock. Venta, método de pago, snapshots y movimientos comparten una transacción. No hay cobro bancario ni emisión fiscal.

**Cancelaciones:** evidencia de responsable, fecha y motivo; no se borra la venta. Por defecto no reincorpora inventario. Gerente/Administrador puede confirmar recuperación física para devolver cantidades a lotes originales no caducados. La cancelación y la devolución son idempotentes; no existe reembolso bancario automático. Caja consulta solamente sus ventas y no tiene permiso de cancelar.

**Inventario:** mermas/daños/caducidades con permiso específico y costos por lote; caducidad solo retira lotes caducados. Conteos registran saldo anterior, conteo y diferencia; un saldo que cambió durante el proceso obliga a contar de nuevo. Los ajustes positivos son existencia recuperada de procedencia no verificada, costo pendiente y fecha actual de descubrimiento, sin simular una compra. Esta política conservadora debe validarse con el responsable antes del uso comercial.

**Consultas:** reportes básicos de ventas/costos/mermas por periodo, cancelaciones separadas, exportación CSV, dashboard con ventas reales y acceso al historial de recepciones por proveedor.

## Migración y conservación de datos

La revisión nueva `dafd29ee82d6` se agrega después de `afbfed7dbf1a`. Agrega ocho tablas, amplía tipos de operación y añade origen de lote; no recrea ni vacía la base. El downgrade rechaza eliminar historia operativa nueva.

Antes de actualizar se generó `backups/cortijo7_20261103T035541Z_8R8IPd/cortijo7.dump` con pg_dump custom. Se restauró en `c7_restore_check_20261103045555_15052` y se aplicó la nueva revisión exclusivamente en esa copia. PostgreSQL 17, head Alembic y conciliación correctos. La copia conservó 1 usuario; el catálogo operativo todavía no contenía ingredientes/lotes/movimientos. La suite añade un ensayo con inventario previo sintético para comprobar conservación de cantidades y costos.

`restore_check.sh --migrate` permite repetir ese ensayo en una base nueva; conserva tanto la fuente como la copia para revisión. No se cargaron platillos, ventas o inventario sintéticos en la instalación del usuario.

## Verificación

**100 pruebas aprobadas** mediante `pytest -q -W error` sobre PostgreSQL 17 real. Incluyen PEPS, venta de varios platillos, insuficiencia/rollback, conservación histórica, unidades, pagos declarados, precios cambiados, consumidores simultáneos, solicitudes duplicadas concurrentes, cancelaciones, conteos, mermas, permisos y flujos HTTP completos con CSRF.

Ruff, compilación Python, validación de sintaxis JavaScript y Bash sin errores. Las pruebas utilizan esquemas temporales propios dentro de la base de pruebas; no alteran la base operativa.

## Pendiente

Importador XLSX y apertura histórica autorizada; borradores/correcciones de recepción; reportes y filtros avanzados; cierre de caja/descuentos/impuestos según definición comercial; fotos oficiales y hardware de impresión; revisión visual en navegador; HTTPS, privilegios de base separados y programación/retención de respaldos antes de producción. El proyecto representa un avance operativo amplio y todavía requiere aceptación antes de usar ventas reales.
