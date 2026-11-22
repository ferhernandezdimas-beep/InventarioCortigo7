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

Se ejecutan pruebas del servidor sobre PostgreSQL 17 real, con esquemas aislados; pruebas TypeScript de instrucciones guiadas y persistencia/reintentos offline; formato, tipado y exportación de bundles Android/iOS. **195 pruebas Python aprobadas**, **15 pruebas móviles aprobadas**, formato y tipado correctos, bundles Android/iOS exportados, **21/21 comprobaciones Expo** y auditoría npm sin vulnerabilidades. La instalación limpia de dependencias del paquete de entrega también pasó.

APK 1.1.0 en compilación: https://expo.dev/accounts/fernando-hd/projects/cortijo7-movil/builds/cb88f90a-ee85-4c85-8cc0-d3cea27c70e8.

Publicación pendiente: GitHub devuelve 403 para la cuenta local Fernando-HD. Se necesita habilitar y aceptar acceso de escritura al repositorio autorizado. El código local nuevo no debe confundirse con el backend actualmente publicado. La versión anterior del APK permanece disponible hasta terminar la nueva compilación.

No hay emuladores ni teléfonos conectados para certificar interacción nativa. Antes del uso operativo: comprobar acceso de cada rol, alta C7, resultado visible en web, descarga CSV/Excel, importación, impresión, modo avión, cierre/reapertura, reconexión, resultados inciertos y revocación de dispositivo.
