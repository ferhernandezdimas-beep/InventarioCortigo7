# Flujos implementados

## Preparar el catálogo

Administrador inicial por CLI → categorías → proveedores opcionales → ingredientes con unidad base y niveles → presentaciones opcionales. Una presentación expresa su contenido en la unidad base del ingrediente y no autoriza conversiones implícitas entre masa, volumen y piezas. Las conversiones kg/g y L/ml existen como servicio Decimal probado.

## Recibir

Seleccionar proveedor opcional → agregar uno o varios renglones → indicar ingrediente, cantidad, presentación opcional, costo conocido o vacío, lote y caducidad opcionales → confirmar. Si se selecciona una presentación, el servidor convierte la cantidad y el precio a unidades base. Se crea un lote por renglón y se conserva su costo. Un error revierte la recepción completa.

## Consumir

Seleccionar ingrediente → capturar cantidad base y motivo → consultar vista previa de lotes → confirmar. El servicio vuelve a validar y aplica PEPS bajo bloqueos. Una referencia repetida no duplica la salida. No hay edición directa de cantidades confirmadas.

## Corregir una salida

Gerente o Administrador abre el folio → captura el motivo → confirma reversión completa. Se crean movimientos compensatorios. La reversión no borra el historial y no puede repetirse con una nueva clave. Las correcciones de recepciones completas se realizan mediante reversión; los ajustes físicos se registran en Conteos y ajustes y no deben hacerse editando la base manualmente.

## Consultar y exportar

Dashboard → alertas reales → inventario físico/disponible/valor conocido → detalle del ingrediente y lotes → movimientos → folio con asignaciones. Exportar el catálogo produce CSV con filtros y protección frente a fórmulas de hoja de cálculo.

Ventas, recetas, pagos declarados y mermas autorizadas se describen en la ampliación siguiente. La importación XLSX ofrece vista previa y confirmación separada; no sobrescribe catálogo existente. No hay rutas simuladas.

## Ampliación: receta → venta → inventario

La última revisión implementa platillos, recetas y ventas. Cada receta guarda su versión y cantidades normalizadas a unidad base. El POS cotiza en el servidor y al confirmar bloquea platillos/ingredientes/lotes, valida precios y disponibilidad, registra la venta y guarda consumos PEPS/snapshots en la misma transacción. Una solicitud repetida devuelve el folio sin generar otra venta.

La cancelación deja evidencia y no reincorpora insumos por defecto. Solo un responsable autorizado puede confirmar recuperación física para devolver asignaciones a lotes originales no caducados. Las mermas y conteos están separados del consumo manual y requieren sus propios permisos.
