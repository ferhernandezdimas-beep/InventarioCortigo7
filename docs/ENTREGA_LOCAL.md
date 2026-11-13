# Entrega local de CORTIJO 7 — 08/11/2026

Esta entrega está preparada para ejecutar el sistema en una computadora local con Docker. Render queda fuera de esta entrega; no se ha creado ni publicado una instalación remota.

## Abrir la instalación actual

Con Docker Desktop abierto, ejecuta desde la raíz del proyecto:

```bash
bash scripts/start_local.sh
```

En macOS también está disponible `Iniciar Cortijo 7.command`. El script construye/arranca PostgreSQL, aplica migraciones, inicia Gunicorn/Nginx y comprueba versión, revisión, inventario y acceso HTTP. La dirección habitual es **http://127.0.0.1:8077**; `HTTP_PORT` en `.env` permite cambiarla.

Para consultar el estado o detener los servicios conservando sus datos:

```bash
bash scripts/status_local.sh
bash scripts/stop_local.sh
```

Si ya tienes una cuenta, sigue utilizando tu correo y contraseña. La actualización de sesiones puede pedirte iniciar sesión otra vez. No se cambia tu contraseña ni se cargan datos de demostración automáticamente. El escenario de entrenamiento solicitado para esta instancia se documenta en [DATOS_PRUEBA.md](DATOS_PRUEBA.md).

## Instalar una copia nueva

1. Descomprime `entrega/cortijo7-local.zip` en una carpeta propia.
2. Instala Docker Desktop con Compose v2 y Python 3. La primera construcción necesita Internet para descargar imágenes y dependencias; los recursos de interfaz se sirven localmente durante el uso.
3. Ejecuta `bash scripts/start_local.sh`. Se crea `.env` con secretos aleatorios solamente cuando no existe.
4. Crea el primer administrador mediante `docker compose exec web flask --app wsgi create-admin`. El comando solicita nombre, correo y contraseña privada de al menos 12 caracteres. No hay credenciales públicas predeterminadas.
5. Abre la dirección local y comprueba el flujo de preparación descrito a continuación.

No sustituyas `.env`, no elimines volúmenes y no ejecutes una inicialización para intentar corregir una instalación con datos. El paquete de código no incluye tu base de datos: para trasladar registros utiliza el procedimiento de respaldo/restauración y conserva la configuración privada por un canal separado.

## Preparación para operar

1. Administrador crea cuentas individuales y asigna Administrador, Gerente, Almacén o Caja.
2. Configurar categorías, ingredientes, unidades base y proveedores. Las presentaciones comerciales requieren una equivalencia explícita.
3. Elegir entre registrar entradas reales o cargar un saldo inicial documentado. Importar catálogo no cambia existencias. La apertura no puede aplicarse a ingredientes que ya tengan lotes.
4. Revisar lotes, fechas y costos. Los costos desconocidos se conservan como pendientes; no se convierten a cero.
5. Crear platillos/productos y recetas. Verificar rendimiento y cantidad por porción. Los productos sin existencias suficientes para una porción aparecen deshabilitados en POS.
6. Registrar la venta, declarar el pago y comprobar folio/consumos. El pago de tarjeta/transferencia es un registro interno: no procesa movimientos bancarios. El comprobante imprimible no es CFDI.
7. Consultar reportes y generar un respaldo al terminar la operación de acuerdo con la responsabilidad acordada.

## Inventario y correcciones

- Recepciones: varios renglones/lotes; borradores parciales con control de revisión. Guardar un borrador no mueve inventario. Confirmar es una transacción atómica e idempotente.
- PEPS: primero la entrada elegible más antigua; espera bloqueos y revalida disponibilidad. No se salta un lote ocupado. Caducados y agotados quedan fuera de ventas/consumo normal.
- Salidas: motivo, actor, cantidades, lotes y costo histórico. Reversión completa mediante movimientos compensatorios.
- Recepciones corregidas: Gerente/Administrador puede revertir una recepción cuando todos sus lotes siguen completos y después registrar la entrada correcta. Si hay consumo pendiente, se conserva la recepción y se documentan diferencias mediante conteo/ajuste.
- Mermas/caducidades: permisos específicos. La baja por caducidad solo afecta lotes caducados.
- Conteos: el saldo anterior debe seguir vigente al confirmar. Diferencias positivas generan existencia recuperada de origen no verificado, costo pendiente y fecha actual de descubrimiento; no simulan compras.
- Cancelaciones: conservan la venta. Por defecto no devuelven insumos. Solo se reincorporan cantidades cuando un responsable confirma recuperación física y los lotes originales no están caducados.

## Importación y reportes

Importaciones → cargar .xlsx → seleccionar hoja → mapear columnas → vista previa → corregir errores → confirmar. La plantilla está disponible desde el módulo. Se admiten hasta 2 MB, 2,000 filas y 60 columnas; no macros ni fórmulas en campos importados. Se detectan filas repetidas, unidades desconocidas, números inválidos y reimportaciones; una confirmación fallida revierte todo. Los datos de catálogo existentes no se sobrescriben.

Una apertura exige confirmar saldo/procedencia y motivo. Su fecha es la del registro, con historial previo marcado como no verificado. No se inventan compras ni caducidades. Esta política debe ser conocida por el responsable que autoriza el saldo físico.

Reportes: ventas/costos por periodo, inventario, entradas, salidas/consumos, lotes/caducidades, mermas y costo estimado de recetas. Exportación CSV/XLSX; cantidades y montos XLSX se conservan como texto decimal exacto. Consultas paginadas y exportaciones limitadas a 10,000 filas para exigir filtros y evitar truncamientos silenciosos.

## Respaldo y recuperación

```bash
bash scripts/backup.sh
bash scripts/restore_check.sh ruta/al/cortijo7.dump --migrate
```

El respaldo es PostgreSQL custom. La restauración de verificación crea una base nueva, aplica migraciones cuando se indica `--migrate`, comprueba la revisión y concilia cantidades/costos en una instantánea consistente de solo lectura. La fuente permanece intacta y la copia se conserva para revisión. Una restauración sobre la base activa requiere un procedimiento administrativo específico; el script no la reemplaza.

No hay una tarea automática ni copia externa programada. El responsable debe establecer la frecuencia, ubicación privada, copia fuera del equipo y retención. Véase RESPALDOS.md.

Para recuperar una contraseña con acceso administrativo a la computadora:

```bash
docker compose exec web flask --app wsgi reset-password
```

El comando solicita correo/contraseña sin imprimirla y revoca las sesiones anteriores. Una cuenta desactivada no se reactiva automáticamente.

## Verificación de la entrega

Resultado de la ampliación del 10/11/2026: **146 pruebas aprobadas en PostgreSQL 17 real**, con advertencias tratadas como error, incluida la carga demo y las vistas pobladas. La migración d457194c1424 y la conciliación también se verificaron sobre una copia restaurada antes de actualizar la base original. Véase VERIFICACION_ENTREGA.md.


- PostgreSQL 17 real, dialecto postgresql+psycopg y migraciones versionadas.
- Pruebas automatizadas de autenticación/CSRF, permisos, PEPS, concurrencia, ventas, recetas, importación, borradores, correcciones y conservación de historia.
- Recursos CSS/JS/fuentes incluidos localmente y sin CDN durante la operación.
- Secretos, datos operativos, respaldos y entorno virtual excluidos del archivo de entrega.
- El navegador automatizado de esta sesión no está conectado: las vistas se validaron mediante respuestas/formularios HTTP y la captura de referencia. Queda la aceptación visual manual de escritorio, tablet, móvil y salida de impresión en el equipo de destino.

La verificación del Excel original del restaurante también depende del archivo real: el importador genérico está probado, pero no se atribuyen a fotografías encabezados ilegibles ni fórmulas no recibidas. Mesas, múltiples cajas/sucursales, cierres de caja, CFDI, cobros bancarios, sincronización desconectada e impresoras térmicas específicas no forman parte de la operación local confirmada.
