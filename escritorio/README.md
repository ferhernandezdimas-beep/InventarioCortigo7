# Cortijo 7 · Escritorio

Aplicación Windows y macOS conectada a **https://cortijo7.onrender.com**, con Electron y la interfaz web completa. Comparte los usuarios, roles, permisos y datos de Render con la web y el móvil. No crea otra base ni copia cuentas.

## Funciones

Inventario, entradas/salidas, lotes PEPS, proveedores, ingredientes, unidades, categorías, presentaciones, recetas, ventas, cancelaciones, ajustes, importaciones Excel, reportes, auditoría y administración: las mismas pantallas y validaciones del servidor, según el rol. Incluye navegación, zoom, impresión, guardar PDF y descargas CSV/Excel con selector nativo. El selector de archivos permite importar XLSX.

Esta versión requiere internet. Si falla la conexión, muestra una pantalla de recuperación; no confirma capturas offline ni reenvía formularios automáticamente. Si se perdió la respuesta al guardar, consultar el folio o historial antes de repetir la operación. El módulo nativo offline del móvil sigue siendo independiente.

El asistente guiado C7 de la app móvil no se incorpora como una segunda interfaz en esta entrega de escritorio. Se incluye lo disponible en la web, sin quitar sus módulos.

## Instalar

Los artefactos se entregan en `../entrega/escritorio/` y se compilan también mediante `.github/workflows/escritorio.yml`.

- **Mac Apple Silicon (M1/M2/M3/M4 y posteriores)**: DMG `mac-arm64`. Abrir y arrastrar Cortijo 7 a Aplicaciones.
- **Mac Intel**: DMG `mac-x64`.
- **Windows x64**: instalador `.exe` generado por GitHub Actions en Windows; crea accesos en Inicio y Escritorio. Alternativa portable: descomprimir **todo** el ZIP `win-x64` en una carpeta y ejecutar `Cortijo 7.exe`; no mover solo el ejecutable.

No requiere Python, Docker, Node ni PostgreSQL en la computadora donde se instala. Usar el correo y contraseña de Render. La sesión de escritorio es independiente de las sesiones del navegador y móvil, y conserva sus cookies en el perfil del sistema operativo. El servidor aplica la caducidad y los permisos vigentes.

La distribución inicial no cuenta con certificado comercial Windows ni notarización Apple. Mac se firma ad hoc para integridad local; esto no equivale a identificación de desarrollador Apple. El sistema puede advertir que el editor no está identificado. Para distribución masiva se requiere firmar/notarizar con certificados del titular. No se contratan certificados ni se alteran las protecciones del equipo durante la compilación.

## Desarrollo y compilación

Node 24 LTS y npm:

```sh
cd escritorio
npm ci
npm run check
npm start
npm run build:mac
npm run build:win
npm run build:win:portable
```

Los instaladores se construyen preferentemente en su propio sistema operativo. `build:win` utiliza NSIS; el flujo GitHub Actions usa Windows para evitar dependencias Wine en Mac. La versión portable Windows se puede empaquetar desde Mac. La compilación no modifica el servidor ni migra la base.

Para desarrollo local, exclusivamente con el código sin empaquetar:

```sh
CORTIJO7_DESKTOP_URL=http://127.0.0.1:8077 npm start
```

Los binarios empaquetados solo aceptan la dirección HTTPS oficial. Las instalaciones locales Flask mantienen datos independientes y no se sincronizan automáticamente con Render.

## Seguridad y mantenimiento

El contenido remoto usa WebContentsView, sandbox, aislamiento de contexto, Node desactivado y sin preload. La barra local tiene un preload separado con un conjunto cerrado de comandos IPC y validación de origen/marco emisor. El protocolo local solo entrega tres archivos públicos; no permite leer fuentes, credenciales ni rutas arbitrarias. No se ignoran errores TLS y se bloquean navegación externa, ventanas emergentes y permisos sensibles. Los reportes descargables se limitan a CSV/XLSX del servidor oficial.

Los cambios web publicados en Render aparecen al actualizar la pantalla. Los cambios del contenedor Electron requieren un instalador nuevo; no hay actualizador automático. Las actualizaciones del backend siguen el procedimiento del proyecto existente. Para respaldos PostgreSQL se usan sus herramientas y procedimientos del servidor; esta app no descarga respaldos ni contiene secretos de Render/PostgreSQL.

Pruebas: `npm run check` valida sintaxis y política de confianza. `env -u ELECTRON_RUN_AS_NODE npx electron tests/smoke.cjs` en macOS abre la aplicación real y comprueba login público, aislamiento, IPC, bloqueo de archivos locales, generación PDF, error offline y reconexión, sin usar usuarios reales ni crear movimientos. Es una prueba de arranque; impresión física, importación, exportación autenticada y flujos de cada rol necesitan aceptación con una cuenta autorizada.
