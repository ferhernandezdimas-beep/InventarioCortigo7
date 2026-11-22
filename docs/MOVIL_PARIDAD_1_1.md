# Cortijo 7 móvil 1.1.0 · funciones completas y asistente con acciones

## Alcance implementado

La pestaña **Sistema** incorpora las vistas Flask/Jinja originales dentro de la app Android/iOS. Se usa el mismo usuario y su rol vigente, sin volver a introducir la contraseña. El backend cambia el token por una cookie HttpOnly mediante POST; el token no se incorpora a direcciones ni al JavaScript de las páginas. Revocar el dispositivo, cambiar la contraseña, inactivar la cuenta o vencer su acceso invalida también esta sesión.

| Área | Acceso móvil | Sin internet |
| --- | --- | --- |
| Inventario, lotes e indicadores descargados | Nativo y Sistema | Consulta de la última descarga |
| Entradas, salidas y ventas | Nativo y Sistema | Captura nativa pendiente de validación |
| Usuarios, roles y dispositivos | Sistema, según rol | Requiere internet |
| Catálogos y presentaciones | Sistema y cuatro altas guiadas C7 | C7 guarda la solicitud pendiente |
| Productos, recetas y versiones | Sistema | Consulta nativa de productos descargados |
| Ajustes, cancelaciones y movimientos | Sistema, según rol | Requiere internet |
| Importaciones Excel y errores de importación | Sistema | Requiere internet |
| Reportes CSV/Excel, auditoría y tickets | Sistema, según rol | Requiere internet para consultar/exportar |

Las exportaciones utilizan los mismos controladores y permisos web, con archivos compartibles mediante el sistema del teléfono. Los tickets abren la impresión nativa. La selección de archivos para importar utiliza el formulario web y el selector del WebView. La compatibilidad final del selector, compartir e impresión debe verificarse en Android e iPhone reales.

## Asistente C7 sin costo

No es un modelo generativo. Reconoce instrucciones guiadas y conserva sus consultas locales de inventario y ventas. Ejemplo: `Crea ingrediente "Aguacate Hass" categoría Verduras unidad kg mínimo 2,5 máximo 15`. Abre un formulario con todos los campos del alta web; el usuario revisa y confirma. Puede crear ingredientes, categorías, proveedores y presentaciones. No ejecuta instrucciones arbitrarias, SQL ni cambios implícitos.

Cada alta utiliza una referencia UUID, permisos `catalog.write`, los mismos formularios/validadores del servidor, transacción atómica, auditoría y registro de idempotencia. Reenviar una referencia tras perder la respuesta devuelve el resultado original. Cambiar sus datos rechaza la solicitud. Crear un ingrediente no aumenta existencias; se requiere una entrada separada.

Sin conexión se conserva la solicitud. El alta no está confirmada ni disponible para otras operaciones hasta sincronizar y recibir su ID de PostgreSQL. Las relaciones nuevas necesitan sincronizar primero el catálogo correspondiente. Roles y disponibilidad se vuelven a validar al reconectar. SQLite no garantiza existencias compartidas ni sustituye PostgreSQL.

## Actualización del servidor

Migración aditiva `f72101c7a002`, sucesora de `e81501c7a001`: crea exclusivamente `mobile_actions` y su índice por usuario. No elimina cuentas, inventario ni movimientos. Desplegar código y ejecutar `flask db upgrade` usando el procedimiento habitual del proyecto. No se autorizó exportar los datos operativos de Render, por lo que esta actualización no genera respaldos remotos.

## Validación y entrega

Se ejecutan pruebas del servidor sobre PostgreSQL 17 real, con esquemas aislados; pruebas TypeScript de instrucciones guiadas y persistencia/reintentos offline; formato, tipado y exportación de bundles Android/iOS. GitHub Actions del commit desplegado: [completado correctamente](https://github.com/ferhernandezdimas-beep/InventarioCortigo7/actions/runs/44994909856).

**195 pruebas Python aprobadas**, **15 pruebas móviles aprobadas**, formato y tipado correctos, bundles Android/iOS exportados, **21/21 comprobaciones Expo** y auditoría npm sin vulnerabilidades. La instalación limpia de dependencias del paquete de entrega también pasó.

APK 1.1.0 terminado: https://expo.dev/accounts/fernando-hd/projects/cortijo7-movil/builds/cb88f90a-ee85-4c85-8cc0-d3cea27c70e8.

Publicación completada el 22/11/2026, 00:43, hora de Ciudad de México. Commit de aplicación `d61ac4184308811f816cc5d8b8b46a42e5852d24`, despliegue Render `dep-dc18tn9ksfps7387g6hg`, estado `live`. Salud `/health/ready`: 200. Los POST a `/api/mobile/v1/web-session`, `/actions` y `/documents` sin credenciales devuelven 401 JSON, ya no 404. La salud valida PostgreSQL 17 y la revisión de Alembic vigente. No se exportaron datos remotos, no se abrió la allowlist y no se crearon movimientos operativos para verificar.

APK 1.1.0 (versionCode 2): [descargar instalador](https://expo.dev/artifacts/eas/Syh_kt_JK7av0wzmeJ6X8USrrW6nG0T5J6yH11N-p_o.apk?download=1). Copias locales `entrega/Cortijo7-1.1.0.apk` y `entrega/Cortijo7.apk`. ZIP íntegro, bundle incluido y bloque de firma APK v2/v3 presente. Tamaño: 100,793,202 bytes. SHA-256: `b43bde3f2d14dc0c30022566d1f0aad7444297534e7ea7bb3679507c78bf6473`. La versión anterior se conserva como `Cortijo7-1.0.0.apk`.

El cambio posterior que explica amigablemente un 404 está en las fuentes actualizadas; el APK 1.1.0 contiene las funciones de Sistema y C7 compiladas antes de ese mensaje. Con el backend actualizado, el 404 de arranque está resuelto sin reinstalar la versión 1.1.0.

Si la app quedó en el error anterior, cerrarla completamente y abrirla otra vez; entrar a Sistema con la sesión vigente. Si solicita acceso, utilizar la misma cuenta de la web. No borrar datos ni desinstalar si hay capturas pendientes.

No hay emuladores ni teléfonos conectados para certificar interacción nativa. Antes del uso operativo: comprobar acceso de cada rol, alta C7, resultado visible en web, descarga CSV/Excel, importación, impresión, modo avión, cierre/reapertura, reconexión, resultados inciertos y revocación de dispositivo.
