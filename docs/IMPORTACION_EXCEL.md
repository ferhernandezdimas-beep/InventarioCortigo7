# Importación de Excel

El módulo Importar Excel está disponible a Administrador y Gerente. Utiliza openpyxl y defusedxml; almacena el libro y su historial en PostgreSQL y no escribe rutas de archivos suministradas por el usuario.

## Flujo

1. Descargar la plantilla o cargar un .xlsx propio (máximo 2 MB).
2. Elegir la hoja. La primera fila debe contener encabezados y cada hoja admite hasta 2,000 registros / 60 columnas.
3. Elegir catálogo o catálogo con apertura. Mapear Ingrediente y Unidad base; mapear Categoría o elegir una predeterminada. Los demás campos son opcionales.
4. Generar vista previa. Revisar nombres normalizados, categorías/proveedores nuevos, unidades, cantidades y costos. Descargar el CSV de errores si corresponde.
5. Corregir todos los errores y confirmar. Ningún registro de catálogo o inventario cambia durante la vista previa.

## Campos

Ingrediente, unidad base, categoría, proveedor, código, mínimo, máximo, costo de referencia, existencia de apertura y costo por unidad base de apertura. Se reconocen kg/g, L/ml y piezas con nombres comunes; no se mezclan dimensiones ni se convierte una pieza a masa o volumen.

Se admiten números decimales, moneda MXN y separadores habituales: 1,234.56 / 1.234,56 / 1,25. Un grupo regular como 1,000 se interpreta como miles; utiliza punto decimal para eliminar ambigüedad. La vista previa es obligatoria. Los vacíos de costo permanecen desconocidos y cero se conserva como valor explícito.

## Integridad

No se sobrescriben campos del ingrediente existente. Se rechazan ingredientes inactivos o con otra unidad, filas duplicadas dentro de la hoja y valores inválidos. El mismo archivo/hoja/modo/mapeo confirmado no se importa de nuevo. Confirmaciones concurrentes están serializadas y una falla revierte el catálogo y la apertura completos.

La apertura solo se admite para ingredientes sin historia de lotes; al confirmar se verifica otra vez esa condición bajo bloqueos. Requiere un motivo y aceptación explícita de saldo/procedencia/orden PEPS. Los lotes se marcan `opening`, con fecha actual de registro y caducidad desconocida; la procedencia histórica no se presenta como una compra verificada.

Se rechazan macros, archivos dañados, fórmulas en campos seleccionados y libros cuyo tamaño descomprimido exceda 20 MB. Las exportaciones neutralizan texto que pueda convertirse en fórmula. Cada carga, vista previa, error y confirmación conserva evidencia en import_jobs y auditoría.

El libro original del restaurante aún no se recibió. El importador y la plantilla genérica se prueban con libros sintéticos; el mapeo real debe verificarse con el archivo auténtico antes de confirmar una apertura.
