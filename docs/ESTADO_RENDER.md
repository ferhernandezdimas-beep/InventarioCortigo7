# Estado de preparación de Render — 12/11/2026

## Completado

- 150 pruebas aprobadas sobre PostgreSQL 17 real; Ruff y compilación correctos.
- Imagen Docker de producción construida; Nginx → Gunicorn → PostgreSQL respondió HTTP 200 en prueba local separada. Cookies Secure y cabeceras comprobadas.
- PostgreSQL 17 gratuito creado en el espacio Cortijo7; región Oregon.
- Respaldo local transferido solo después de verificar que el destino estaba vacío. La cuenta y contraseña existentes se conservan. La base local no se sustituyó.
- Copia remota: 46 ingredientes, 20 productos, 95 lotes, 733 movimientos, 101 operaciones y 75 ventas. Incluye registros agregados por el usuario después de la carga inicial.
- Presentación sin rótulos en nombres, comprobantes ni pantallas; conciliación de cantidades/costos correcta. La procedencia sintética de la carga inicial queda documentada en DATOS_PRUEBA.md.
- 18 vistas autenticadas verificadas mediante Flask/HTTP contra la copia remota. No se atribuye inspección visual de navegador ni publicación web a esta prueba.
- Acceso externo temporal a PostgreSQL cerrado; conexión privada preparada.

## Pendiente por autorización externa

El push a ferhernandezdimas-beep/InventarioCortigo7 fue rechazado con HTTP 403 para la cuenta local Fernando-HD. El código está en commits locales y origin apunta al repositorio solicitado. GitHub debe autorizar escritura mediante la cuenta propietaria, la integración o un colaborador autorizado.

La validación del Blueprint informa que main aún no existe en el repositorio remoto. No se ha creado ni publicado el servicio web: hacerlo sin código disponible produciría un despliegue fallido.

Después de resolver el acceso: push main → validar render.yaml → crear Web Service gratuito con Dockerfile.render y la conexión interna existente → revisar despliegue → comprobar HTTPS y flujos autenticados. No crear otra base ni restaurar encima de la copia ya preparada.

## Fecha límite del plan gratuito

La base creada vence el **12/12/2026 21:47**, hora de Ciudad de México, según Render. Respaldar y actualizar de plan o trasladar los datos antes de esa fecha. No se ha contratado ningún plan de pago.

Las credenciales y archivos privados de transferencia están fuera del repositorio. Los ZIP de entrega contienen únicamente código/documentación y no incluyen la base ni sus respaldos.
