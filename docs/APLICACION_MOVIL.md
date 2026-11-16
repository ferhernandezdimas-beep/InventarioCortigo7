# Aplicación móvil Cortijo 7 — avance del 15/11/2026

## Entregables locales

- Proyecto separado `movil/` dentro del proyecto existente: Expo SDK 57, React Native y React compatibles con SDK 57, TypeScript, Expo SQLite, SecureStore, Network, Crypto, Haptics y Decimal.js.
- API Flask `/api/mobile/v1` sobre la misma base PostgreSQL 17. No se copian ni recrean usuarios para móvil.
- Nueva tabla `mobile_sessions` mediante Alembic `e81501c7a001`, posterior a `d457194c1424`; cambio aditivo sin modificar tablas históricas.
- La web conserva sus rutas y formularios. Se añade `/mi-cuenta/dispositivos` para consultar/revocar accesos; mantiene CSRF. Los administradores pueden gestionar los dispositivos de todos.
- Inicio, inventario filtrable, lotes PEPS, recepciones de varios renglones y presentaciones, salidas, carrito POS, estados y folios de sincronización, cuenta y C7.
- C7 usa cálculos/reglas locales: no es un modelo generativo ni depende de un proveedor de IA. No modifica datos desde el chat. Ofrece reposición según mínimos/máximos, lotes a revisar, capacidades de recetas independientes, consultas por ingrediente y ventas recientes según permisos.
- `Iniciar Cortijo 7 móvil.command`, `movil/eas.json`, documentación y `scripts/package_mobile.py` para entregar únicamente código móvil, con SHA-256.

## Arquitectura de sincronización

El teléfono no se conecta directamente a PostgreSQL ni contiene credenciales de Render. Se comunica por HTTPS con Flask. El inicio de sesión comprueba el mismo hash de contraseña de la web y comparte el control de intentos persistente. Emite un token aleatorio por dispositivo, del que PostgreSQL conserva únicamente SHA-256, con vencimiento de siete días. SecureStore guarda el token y SQLite guarda el snapshot y la cola en archivos separados por usuario/servidor.

El snapshot se obtiene en una transacción PostgreSQL REPEATABLE READ READ ONLY. Incluye catálogos y lotes para roles autorizados, productos/versiones de receta para POS, últimos 100 movimientos y últimas 100 ventas; caja recibe solo sus ventas y no recibe inventario, proveedores ni formulaciones. No se publican hashes de contraseñas ni datos privados de contacto de proveedores.

Los registros locales tienen UUID estable, contenido congelado y estados pendiente, conflicto y confirmado. Se conserva el intento antes del envío y el folio después del acuse. Un corte en cualquiera de esas etapas vuelve a utilizar la misma clave. Para recuperar un acuse perdido, la API permite consultar una referencia confirmada propia, incluso después de un cambio de rol. Una cuenta no puede consultar referencias de otra.

Cada registro se confirma usando los servicios existentes de inventario/ventas: transacción completa, NUMERIC/Decimal, bloqueo de ingredientes y lotes en orden, PEPS sin SKIP LOCKED y restricciones de integridad. No se cambia el comportamiento de las ventas web. Las ventas móviles añaden un mapa de versiones de recetas al hash de idempotencia y validan esas versiones bajo el bloqueo del producto. Las solicitudes web anteriores conservan su formato de hash cuando no incluyen ese mapa.

Una captura offline no reserva existencias ni garantiza una venta. El servidor puede rechazarla íntegramente por falta de stock, precios o receta distintos. El primer conflicto detiene las capturas siguientes hasta resolverlo; no se aplica una política de sobrescribir o «último cambio gana» a inventario. El dispositivo descarga datos nuevos aunque un envío encuentre un conflicto, para ayudar a revisarlo.

Los errores de autenticación, permisos, concurrencia o red mantienen una captura pendiente. Los rechazos de validación de negocio se muestran para revisión y permiten descartar la captura local, sin borrar movimientos de la web. Los resultados inciertos no permiten descarte desde la app. Las respuestas definitivas de éxito conservan el folio y no se vuelven a enviar.

## Alcance offline

Hace falta internet para el primer acceso, primera descarga, renovación de sesión y confirmación final. Con una sesión local vigente se pueden consultar la copia descargada, usar C7 y guardar capturas aunque se cierre la aplicación. El servidor sigue siendo la autoridad; no existe consistencia instantánea entre teléfonos desconectados.

La disponibilidad se recalcula con las caducidades de los lotes descargados incluso si cambia el día mientras se está offline. La hora de captura permanece en el registro local; las recepciones se incorporan al orden PEPS con la fecha del servidor al sincronizar, sin simular compra histórica.

La sesión local caduca como máximo en siete días. Un dispositivo físicamente desconectado no puede conocer una revocación inmediata. Al reconectar se comprueban cuenta activa, auth_version y rol actuales. Cambiar la contraseña invalida todas las sesiones anteriores. Se puede revocar solo un dispositivo desde la web. Los archivos SQLite locales no están cifrados con SQLCipher en Expo Go; debe utilizarse el bloqueo del sistema del teléfono. No contienen tokens ni contraseñas.

No se deben desinstalar ni borrar datos con pendientes. Cerrar sesión exige internet, revoca el token y limpia la copia local; no permite abandonar operaciones sin resolver. El modo offline se diseñó para una app instalada con el bundle incluido; la caché de Expo Go no garantiza el arranque offline independiente de Metro.

La administración completa de catálogos, recetas y usuarios, importaciones, cancelaciones, ajustes y reportes continúa en la web. Hay un acceso directo desde la app. No se trasladaron todos esos formularios a React Native ni se añadieron integraciones bancarias.

## Instalación y distribución

Usar Node 24 LTS y `npm ci` dentro de `movil`. `npm start` muestra el QR de Expo Go. El teléfono debe tener Expo Go compatible con SDK 57; las otras apps anteriores del equipo utilizan SDK 54 y no comparten `node_modules` con este proyecto.

`preview` de EAS está configurado para APK Android, `production` para AAB. Para iPhone se necesita firma/distribución Apple; no hay un APK para iOS. No se contrató ningún plan de pago.

## Publicación y distribución

El usuario autorizó preparar la actualización **sin exportar datos de Render**, confirmó Android e iPhone y autorizó crear el proyecto Expo en `fernando-hd` y subir únicamente fuentes móviles para compilar el APK gratuito. No se generó un respaldo remoto ni se abrió acceso externo de PostgreSQL durante este avance. La migración es aditiva: crea únicamente la tabla de sesiones y sus índices; preserva usuarios y operaciones.

Proyecto Expo creado: https://expo.dev/accounts/fernando-hd/projects/cortijo7-movil · ID `d1d58bfa-8a74-4dfb-b9cb-c004d13ba89a`. El código que se envía a EAS se extrae de un paquete con lista explícita de fuentes móviles a una carpeta temporal independiente, fuera del repositorio web. El paquete excluye `.env`, bases, respaldos y código del backend. Expo administra la firma Android del APK.

Se registrarán a continuación el commit publicado, estado del despliegue, enlace de compilación y resultado de comprobaciones HTTPS. Hasta disponer de esa evidencia, la publicación se considera en proceso. No se contrató ningún plan de pago. La firma y distribución de una app iOS independiente siguen requiriendo la cuenta/configuración Apple; el proyecto nativo iOS se puede abrir para desarrollo con Expo Go compatible.

La base gratuita de Render existente conserva su vencimiento documentado del 12/12/2026; la app móvil no cambia ese plan ni proporciona respaldo automático de producción.

## Verificación realizada y aceptación pendiente

Se registran los resultados finales de pruebas al completar este avance. Los comandos son `npm run typecheck`, `npm test`, `npx expo-doctor` y `npm run export:android`; la regresión Python se ejecuta sobre PostgreSQL 17 real. No se utiliza SQLite para simular concurrencia de servidor.

No hay emulador Android/iOS disponible en este equipo para certificar la interacción nativa. La compilación del bundle, TypeScript y las pruebas del protocolo no equivalen a probar un APK instalado. Antes de operación se debe revisar en un teléfono: primer acceso real, modo avión, captura, cierre/reapertura, reconexión, recuperación de folio en la web, conflicto de dos dispositivos, cambio de receta y revocación del acceso. La publicación de la API y un APK firmado siguen los pasos pendientes indicados arriba.

### Evidencia de publicación del backend

- Commit de aplicación: `0a1c130c4fa1a16d5b5e388ecb209f03fe74e2a7`.
- Despliegue: `dep-dbt8b7u1egvs73fnecig`, estado **live** confirmado por Render.
- HTTPS: `/health/ready` y `/login` respondieron 200. La salud verifica PostgreSQL 17 y la revisión actual de Alembic, incluida la nueva tabla de sesiones móviles.
- `/api/mobile/v1/auth/me` y `/snapshot` respondieron 401 sin token; `/auth/login` rechazó el objeto vacío con 400 JSON.
- 174 pruebas Python aprobadas en PostgreSQL 17 local aislado. No se inició sesión con credenciales reales del usuario durante la comprobación pública ni se crearon movimientos operativos para probar.
- No se exportaron datos ni se modificó la allowlist de PostgreSQL. El autodespliegue sigue deshabilitado.
- La versión móvil final usa SDK 57, recomendado por Expo para Expo Go físico durante la transición a SDK 58, y rutas en `movil/src/app/` con Expo Router. La primera compilación SDK 58 fue preliminar; no es la distribución final.

La dependencia de navegación utiliza la versión corregida oficial `decode-uri-component@0.5.1`, convertida a CommonJS conservando licencia y fuente en `movil/vendor/` para la interfaz de query-string 7 que utiliza Expo Router 57. Se probaron UTF-8, cantidades decimales y entradas malformadas. También se fija minimatch corregido para las herramientas de fingerprint. No se cambió la versión nativa de Expo para resolver esos avisos.
