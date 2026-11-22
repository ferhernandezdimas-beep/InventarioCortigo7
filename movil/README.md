# Cortijo 7 · Aplicación móvil

**Actualización 1.1.0 preparada localmente; publicación del backend pendiente de acceso de escritura a GitHub.** El APK 1.0.0 enlazado abajo no contiene las funciones nuevas. Estado: [MOVIL_PARIDAD_1_1.md](../docs/MOVIL_PARIDAD_1_1.md).

Aplicación nativa Android/iOS con **Expo SDK 57, React Native, Expo Router, TypeScript y SQLite local**. La fuente oficial de usuarios, permisos y operaciones sigue siendo **Flask + PostgreSQL 17 en Render**. SQLite solo almacena la copia del teléfono y su cola; no sustituye PostgreSQL ni sus pruebas de concurrencia.

## Ubicación y estado

- `movil/`: proyecto móvil, independiente de la web y dentro del mismo repositorio.
- `app/mobile.py`: API `/api/mobile/v1`; `app/mobile_models.py`: sesiones por dispositivo.
- `migrations/versions/e81501c7a001_mobile_device_sessions.py`: migración aditiva; conserva cuentas y movimientos anteriores.
- Servidor configurado: `https://cortijo7.onrender.com`.
- La API móvil ya está publicada en Render. El APK final y la evidencia de comprobaciones se registran en `../docs/APLICACION_MOVIL.md`. La creación de proyectos y compilación en Expo fue autorizada para la cuenta `fernando-hd`.

## Instalar en Android

[Descargar APK anterior 1.0.0](https://expo.dev/artifacts/eas/XTj_yCb-L8w91z6MZL4eok0GidkLzm2i9Ex5cgZUO_k.apk) o utiliza `../entrega/Cortijo7.apk`. La primera sesión utiliza tu usuario actual de Render y necesita internet. El instalador incluye el bundle y puede arrancar sin Metro.

## Ejecutar en Expo Go

Requisitos: Node 24 LTS, npm, Expo Go compatible con SDK 57 y teléfono/computadora en la misma red.

```sh
cd movil
npm ci
npm start
```

Escanea el QR de Metro con Expo Go en Android o la cámara en iPhone. En macOS también puedes abrir **Iniciar Cortijo 7 móvil.command** desde la carpeta principal. Si tu Expo Go indica incompatibilidad, instala la versión correspondiente desde https://expo.dev/go o usa una compilación propia. Este proyecto usa SDK 57; no comparte dependencias con las aplicaciones anteriores de este equipo que usan SDK 54.

`npm run start:tunnel` es una alternativa si la red bloquea la conexión directa; requiere el túnel de desarrollo de Expo. No es necesario para la aplicación instalada.

### Servidor de desarrollo opcional

Copia `.env.example` a `.env` y cambia **solo** `EXPO_PUBLIC_API_URL`. La URL es pública y no debe contener contraseñas, API keys ni credenciales de PostgreSQL. El valor predeterminado apunta a Render. En desarrollo se aceptan direcciones HTTP de la red local; en producción se exige HTTPS. Un teléfono no puede acceder al `localhost` de la computadora: utiliza su IP de la red.

## Funciones

- Acceso con los mismos usuarios y contraseñas de la web; sin registro público.
- Inicio con indicadores, alertas y accesos rápidos según rol.
- Inventario con búsqueda, filtros y lotes en orden PEPS.
- Recepciones con varios ingredientes, proveedor, presentaciones, costos opcionales, lotes y caducidades.
- Salidas con varios ingredientes y validación final PEPS en PostgreSQL.
- POS con carrito, importes decimales exactos, efectivo/tarjeta/transferencia registrados internamente.
- Cola durable con referencia UUID, estado, errores y folio definitivo.
- **Asistente C7**: consultas por ingrediente, reposición, caducidades, porciones posibles, ventas recientes y pendientes. Usa reglas y cálculos locales; funciona sin internet, sin proveedor de IA externo ni claves adicionales. Prepara altas de ingredientes, categorías, proveedores y presentaciones con formulario, revisión y confirmación. Las acciones se encolan sin conexión y el servidor valida permisos e integridad antes de confirmarlas.
- **Sistema**: web completa integrada dentro de la app con la misma cuenta y rol: usuarios, catálogos, recetas, importaciones, ventas, cancelaciones, ajustes, reportes y auditoría según permisos. Exportaciones CSV/Excel con menú nativo para compartir e impresión de tickets. Requiere internet.
- Cuenta, vencimiento del acceso y revocación por dispositivo.
- En la web: **Mis dispositivos móviles**, con revocación de accesos. Un administrador puede revisar los dispositivos de otros usuarios.

La app no reproduce todos los formularios administrativos de la web. El trabajo móvil se concentra en consulta, recepción, salidas, venta y sincronización.

## Qué significa trabajar sin conexión

1. El **primer inicio de sesión y la primera descarga** necesitan internet.
2. Después puedes consultar los datos descargados, usar C7 y guardar entradas, salidas y ventas pendientes, aunque cierres y vuelvas a abrir la aplicación instalada.
3. El acceso local dura hasta siete días desde el inicio de sesión. Al vencer, debes autenticarte online con la misma cuenta. No se guardan contraseñas.
4. Con internet, la app verifica la sesión, envía la cola en orden y descarga una copia consistente de Render. Intenta sincronizar al abrir, recuperar conectividad, volver al primer plano y cada minuto mientras está activa; también dispone de botón manual.
5. **Pendiente no significa confirmado.** Otros teléfonos y la web pueden consumir inventario mientras tú estás offline. Render vuelve a verificar permisos, precios, versión de receta, disponibilidad y caducidad en una transacción completa.
6. Las cantidades locales son la última descarga, no una reserva. La app recalcula la elegibilidad por caducidad al consultar. No modifica el saldo oficial del teléfono fingiendo una confirmación remota.
7. Si cambian la receta o el precio, o falta stock, el registro se marca para revisión. Se conserva la captura y se detienen las siguientes. Revisa la información actualizada, descarta la captura rechazada y crea una corregida. No se fusionan operaciones comerciales automáticamente.
8. Si se pierde la respuesta después del commit, se conserva el UUID y el cuerpo original. El reintento consulta el folio o reproduce la operación idempotente; no genera otro movimiento. Una respuesta incierta no se puede descartar desde la interfaz.
9. Un permiso revocado mantiene la captura pendiente para revisión del responsable; la app puede recuperar el folio propio aunque el permiso haya cambiado después de confirmar.
10. Las recepciones se incorporan al PEPS con la fecha/hora del servidor al sincronizar, sin inventar una entrada histórica. La hora de captura se conserva en el registro local.

**Expo Go es un entorno de desarrollo.** Necesita Metro para cargar el proyecto por primera vez y su caché no garantiza iniciar siempre sin internet. Para uso cotidiano independiente de la computadora y arranque offline, utiliza el APK firmado con el bundle incluido. El APK todavía necesita conexión para el primer acceso y la primera descarga.

## Seguridad y datos locales

Tokens aleatorios guardados mediante SecureStore; el servidor almacena únicamente SHA-256 de cada token. Sesiones revocables, vencimiento de siete días y verificación de `auth_version`, usuario activo y rol. Cambiar la contraseña desde la web invalida el acceso remoto de todos sus dispositivos. No se habilita CORS comodín ni se aceptan cookies para autenticar la API móvil. Los formularios web mantienen CSRF.

Los datos de cada usuario/servidor se guardan en un archivo SQLite separado. SQLite local **no está cifrado mediante SQLCipher en Expo Go**; el teléfono debe usar bloqueo del sistema. No contiene tokens ni hashes de contraseñas. La revocación remota no puede borrar ni bloquear de inmediato un dispositivo que está físicamente sin conexión; el límite local es su vencimiento. No desinstales ni borres datos mientras haya capturas pendientes. Cerrar sesión exige conexión, revoca el token y limpia la copia local, y no permite abandonar pendientes sin resolver.

C7 presenta resultados sobre la copia descargada y muestra su fecha. Las capacidades de cada platillo son independientes porque comparten ingredientes. La consulta de ventas está limitada a los 100 registros más recientes y, en caja, a las ventas propias; para informes completos utiliza la web.

## Compilar un instalador Android

`eas.json` contiene `preview` (APK de distribución interna) y `production` (AAB). El perfil no activa suscripciones de pago. El uso de EAS y su cuota dependen de la cuenta de Expo y requieren autorización para subir el código.

```sh
npx eas-cli@latest login
npx eas-cli@latest init --account <tu-cuenta>
npx eas-cli@latest build --platform android --profile preview
```

Para evitar subir fuentes del backend o archivos del equipo, se entrega `scripts/package_mobile.py`: produce un ZIP con **solo código móvil** mediante una lista explícita de archivos. Extrae ese paquete en una carpeta independiente, instala dependencias y ejecuta allí EAS con `EAS_NO_VCS=1`. No copies `.env`, bases, respaldos ni claves al paquete. Conserva en el original el `extra.eas.projectId` y el `owner` asignados por Expo.

El enlace de EAS permite descargar e instalar el APK en Android. iPhone necesita firma y distribución Apple (por ejemplo, TestFlight o dispositivos registrados); Expo Go sirve para desarrollo. No hay un archivo APK equivalente instalable en iPhone.

## Validación

```sh
npm run typecheck
npm test
npx expo-doctor
npm run export:android
```

En la raíz, ejecutar `bash scripts/test.sh -q -W error` sobre PostgreSQL 17 real. Las pruebas móviles de servidor cubren sesiones existentes, revocación, CSRF web, permisos, aislamiento de datos, UUID repetidos y concurrentes, rollback y recetas cambiadas. Las pruebas TypeScript cubren importes exactos, caducidad offline, asistente, cortes después del commit, reinicio lógico, bloqueo de conflictos y reintentos seguros.

La compilación del bundle y las pruebas no sustituyen la aceptación en un teléfono. Antes de usarlo en operación: hacer el primer acceso, activar modo avión, capturar y cerrar/reabrir, recuperar conexión, verificar folio en la web, provocar falta de stock con dos dispositivos y comprobar la revocación. Usar un entorno de validación para estas operaciones.

Referencias: [SQLite de Expo](https://docs.expo.dev/versions/latest/sdk/sqlite/), [SecureStore](https://docs.expo.dev/versions/latest/sdk/securestore/), [compilar APK](https://docs.expo.dev/build-reference/apk/), [Expo Go](https://expo.dev/go).

## Versión 1.1.0: integración completa y C7 con acciones

El acceso completo es híbrido: las pantallas web reales se muestran en un WebView dentro de la aplicación; los módulos nativos conservan SQLite y la cola offline. No todos los formularios administrativos funcionan sin internet. El alta guiada del catálogo tampoco se considera confirmada hasta que Render responde.

Requiere desplegar el backend y ejecutar `flask db upgrade`, incluida la migración aditiva `f72101c7a002`. No requiere borrar, importar ni exportar datos existentes. Las cuentas actuales continúan vigentes. Estado de publicación y aceptación: `../docs/MOVIL_PARIDAD_1_1.md`.
