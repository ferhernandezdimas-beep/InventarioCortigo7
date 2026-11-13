# Despliegue de Render completado — 12/11/2026

Dirección pública: **https://cortijo7.onrender.com**
Repositorio: https://github.com/ferhernandezdimas-beep/InventarioCortigo7

## Estado verificado

- Servicio web `cortijo7`, ID `srv-dbr8vpetlv9c73fqohs0`, plan gratuito, Oregon. Render confirmó estado `live`.
- Despliegue `dep-dbr8vpmtlv9c73fqoisg`, código de aplicación del commit `48b6171349e62e82c271773c7d5716c3a17820d9`.
- PostgreSQL 17 administrado, plan gratuito, misma región; revisión Alembic d457194c1424.
- Gunicorn con dos procesos detrás de Nginx sin privilegios y HTTPS terminado por Render.
- `/health/ready` y `/login`: HTTP 200 desde la dirección pública. Cookies Secure, HSTS y protección de marcos verificadas.
- 28 vistas autenticadas y 6 recursos comprobados desde HTTPS público: inventario, catálogos, lotes/caducidades, entradas, salidas, borradores, recetas, POS, ventas, reportes y administración. Esta verificación HTTP no equivale a inspección visual automatizada en navegador.
- 150 pruebas aprobadas localmente sobre PostgreSQL 17 real. GitHub Actions completó correctamente la regresión del commit publicado: https://github.com/ferhernandezdimas-beep/InventarioCortigo7/actions/runs/43364728380.
- `render.yaml` aprobado mediante la validación oficial después de publicar main.

## Datos y acceso

La copia remota conserva la cuenta y contraseña existentes. Se transfirió a una base nueva después de comprobar que estaba vacía; la instalación local se conserva y no existe sincronización posterior automática.

Datos verificados al transferir: 46 ingredientes, 20 productos, 95 lotes, 733 movimientos, 101 operaciones y 75 ventas. Incluyen las operaciones posteriores introducidas por el usuario. La conciliación confirmó cantidades, asignaciones y costos. Los nombres de catálogo y comprobantes no muestran rótulos de prueba; su procedencia inicial queda documentada en DATOS_PRUEBA.md y la auditoría.

La restauración y comprobación usaron acceso externo temporal limitado a una IP /32. Ese acceso se cerró; la aplicación usa la conexión privada de Render. Credenciales, base y respaldos quedan fuera de Git y de las imágenes.

## Mantenimiento

El autodespliegue está deshabilitado. Para publicar cambios: probar y respaldar → push revisado a main → Manual Deploy → comprobar salud, sesiones, flujos y conciliación. Los commits posteriores que solo actualizan documentación no modifican el código del despliegue comprobado.

El servicio gratuito puede suspenderse por inactividad. La base creada vence el **12/12/2026 a las 21:47, hora de Ciudad de México**. Debe respaldarse y actualizarse de plan o trasladarse antes del vencimiento. No se ha contratado ningún plan de pago.
