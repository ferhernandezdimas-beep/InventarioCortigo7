# Manual de la entrega actual

## Acceso y equipo

El responsable instala el sistema y crea el primer administrador con `create-admin`. Inicia sesión con tu cuenta individual. Desde el nombre al pie del menú puedes cambiar tu contraseña; Cerrar sesión está en la barra superior. El administrador crea cuentas y asigna roles en Usuarios y roles. Una cuenta desactivada pierde acceso en la siguiente solicitud.

## Catálogos

Crear primero categorías y luego ingredientes. Registrar nombre, categoría, unidad base y nivel mínimo. Código, proveedor, máximo y costo de referencia son opcionales. No se edita la existencia. Editar permite desactivar un ingrediente; una vez que tiene lotes, su unidad base no puede cambiar. Usa filtros y Exportar para obtener el CSV del catálogo.

Proveedores permite registrar/editar datos y desactivar, sin exigir información desconocida. Unidades muestra masa, volumen y conteo. Presentaciones configura una equivalencia explícita en la unidad base: una botella de litro para aceite en ml contiene 1,000 unidades base.

## Entradas y lotes

Registrar entrada permite varios ingredientes y lotes. Puedes capturar unidades base o seleccionar una presentación del mismo ingrediente; la cantidad indica cuántas unidades/presentaciones llegaron y el precio es por esa misma unidad/presentación. Deja el costo vacío si no se conoce: no equivale a cero. Confirma solo cuando hayas revisado los renglones. La pantalla de folio muestra las asignaciones guardadas. Caducidad y código de lote pueden quedar vacíos.

## Salidas

Selecciona el ingrediente, cantidad en su unidad base y motivo del consumo manual. Revisa la vista previa informativa de PEPS. Al confirmar se revalida la existencia bajo bloqueo. Si no alcanza, no se guarda una salida parcial. Si una operación tarda o falla, conserva la referencia del formulario al reintentar para evitar duplicados.

Gerente/Administrador puede abrir una salida y revertirla completa indicando motivo. La reversión vuelve a sus lotes originales y conserva la evidencia. No se pueden editar movimientos ni borrar historia. No uses consumos manuales para simular ajustes, mermas o ventas: utiliza sus módulos específicos.

## Consultas

Resumen de operaciones muestra datos reales y alertas. Inventario separa existencia física, disponible sin caducados y valor de los costos conocidos. Lotes ordena por entrada/id. El detalle de ingrediente reúne historial y lotes. Auditoría muestra actividad sensible a usuarios autorizados.

## Conexión y funciones pendientes

La importación XLSX y los reportes prioritarios CSV/Excel están disponibles desde el menú. Si el navegador pierde conexión, no registra operaciones offline. Contacta al responsable si una operación no puede verificarse en Movimientos.

## Ampliación operativa: recetas y punto de venta

El flujo de recetas y ventas ya está disponible con persistencia y control PEPS.

1. Crear categoría e ingredientes; registrar sus entradas y costos cuando se conozcan.
2. Abrir Platillos y recetas → Nuevo platillo. Definir nombre, categoría del menú, precio final y rendimiento. Agregar cantidades y unidades de la preparación completa. Un producto directo utiliza un ingrediente y rendimiento de una unidad.
3. Consultar la receta para ver cantidades por porción y estimación PEPS. Si falta inventario o costo, se indica que la estimación está incompleta. Editar genera otra versión; no altera las ventas anteriores.
4. Abrir Punto de venta. Buscar por nombre o categoría; los productos sin stock para una porción aparecen deshabilitados. Agregar productos, modificar cantidades y revisar el total validado por el servidor. Seleccionar efectivo, tarjeta o transferencia. En efectivo, capturar el monto recibido; se calcula el cambio al confirmar. No hay cobro bancario integrado.
5. Confirmar la venta. Si falta cualquier ingrediente, la venta completa se rechaza. Al confirmar, consultar/imprimir el comprobante interno y revisar los movimientos PEPS si el rol lo permite.
6. Consultar Ventas. Caja ve únicamente sus ventas. Gerente/Administrador puede cancelar indicando motivo. Por defecto no se devuelve inventario; marcar reincorporación solo si los insumos realmente se recuperaron y siguen siendo utilizables. No se admite reincorporación a lotes caducados. No es un reembolso bancario.
7. Abrir Reportes y costos para filtrar fechas y exportar ventas CSV. Los costos desconocidos se señalan y las canceladas se excluyen de ingresos vigentes.

## Mermas y conteos

Gerente/Administrador puede registrar merma, daño o baja por caducidad. Caducidad retira exclusivamente lotes ya caducados. Las otras bajas pueden afectar inventario físico en PEPS.

En Conteos y ajustes, comparar el saldo físico del sistema (tabla inferior) con el conteo realizado y documentar el motivo. Si el saldo cambió durante el conteo, se rechaza la operación para volver a contar. Diferencias negativas descuentan inventario físico; positivas crean un lote de existencia recuperada con procedencia no verificada, costo pendiente y fecha actual de descubrimiento. No se fabrica una compra ni una fecha histórica.

Categorías y presentaciones ahora permiten editar registros. Cambiar una presentación afecta entradas futuras; los saldos históricos y las ventas confirmadas permanecen conservados. El proveedor ofrece acceso al historial de recepciones asociadas.

## Borradores y correcciones de entradas

Guardar borrador conserva campos incompletos sin alterar existencias. Continúa desde Borradores de recepción; al confirmar se valida todo y se registra una sola recepción. Un borrador modificado por otra persona exige recargar. Descartar conserva evidencia. Si una recepción confirmada mantiene todos sus lotes completos, Gerente/Administrador puede revertirla con motivo y capturar la entrada correcta. Si hubo consumo pendiente, se exige un ajuste documentado.

## Excel, configuración y ayuda

Importar Excel permite cargar el libro, elegir hoja, mapear columnas, revisar errores y confirmar. Descargar plantilla ofrece los encabezados de catálogo/apertura. Una apertura necesita aceptación de procedencia y saldo; no se admite si ya hay lotes. Nunca se inventan fechas de compra o costos.

Reportes ofrece pestañas para ventas, inventario, entradas, salidas, lotes, mermas y recetas. Filtra antes de exportar CSV/XLSX. Configuración permite cambiar la anticipación de caducidades; Ayuda resume los pasos de operación. Cambiar una contraseña requiere iniciar sesión nuevamente y cierra las sesiones previas.
