# Cortijo 7 · Entrega de escritorio 1.0.0

Aplicación desarrollada para **Windows x64 y macOS Apple Silicon/Intel**, en la carpeta `escritorio/`, junto con la web y el móvil. Utiliza Electron 45.5.0 y electron-builder 26.18.0. El sistema Flask/PostgreSQL de Render es la misma fuente de datos, usuarios, roles y validaciones; no se añadió otra base ni se efectuaron migraciones para escritorio.

## Distribución

[Descargas de escritorio 1.0.0](https://github.com/ferhernandezdimas-beep/InventarioCortigo7/releases/tag/escritorio-v1.0.0).

| Equipo | Archivo | Instalación |
| --- | --- | --- |
| Windows x64 | `Cortijo7-1.0.0-win-x64.exe` | Ejecutar el asistente; crea accesos en Inicio y Escritorio |
| Windows x64 portable | `Cortijo7-1.0.0-win-x64.zip` | Extraer todo y ejecutar `Cortijo 7.exe` |
| Mac Apple Silicon | `Cortijo7-1.0.0-mac-arm64.dmg` | Abrir y arrastrar Cortijo 7 a Aplicaciones |
| Mac Intel | `Cortijo7-1.0.0-mac-x64.dmg` | Abrir y arrastrar Cortijo 7 a Aplicaciones |

Copias locales en `entrega/escritorio/`, junto con `SHA256SUMS`, fuentes y capturas. No requiere instalar Python, Node, Docker o PostgreSQL en la computadora del usuario. La distribución inicial carece de certificado comercial Windows y notarización Apple; los paquetes Mac tienen firma ad hoc verificada, por lo que puede aparecer un aviso de editor no identificado.

## Comportamiento

Se abre el sistema web completo dentro de una ventana de escritorio. El servidor conserva sus controles por rol: inventario, entradas/salidas, lotes, ventas, cancelaciones, recetas, ajustes, catálogos, importación XLSX, reportes, usuarios y auditoría. Incluye barra de navegación, zoom, impresión, guardar PDF y diálogos nativos para importar/guardar documentos. La sesión local de escritorio es independiente del navegador y de la app móvil, pero el usuario y la base son los mismos.

**Requiere internet.** Ante un fallo de red muestra una vista de recuperación y no reenvía automáticamente formularios. Las operaciones no se guardan offline en esta versión. El módulo offline y el asistente nativo C7 del móvil continúan en su propia aplicación. Los cambios del servidor se muestran al recargar; las actualizaciones de Electron requieren un instalador nuevo.

## Validación realizada

- Cinco pruebas de política aprobadas: servidor permitido, navegación, protocolo local, comandos IPC y descargas.
- Instalación limpia de dependencias aprobada; auditoría npm sin vulnerabilidades tras fijar versiones corregidas de minimatch 9/10, conservando las interfaces de las ramas 3/5.
- Prueba gráfica real en Mac: login público de Render, Node/require deshabilitados en el contenido remoto, sin puente IPC remoto, comandos IPC acotados, bloqueo de navegación a archivos locales, generación de PDF, fallo de red simulado mediante bloqueo de solicitudes y reconexión.
- Capturas de login y estado sin conexión revisadas visualmente.
- Ambos DMG verificados con `hdiutil verify`; firma ad hoc del paquete Apple Silicon verificada con `codesign --verify --deep --strict`.
- El binario Mac Apple Silicon empaquetado arrancó y permaneció abierto sin errores de firma.
- ZIP Windows verificado con ejecutable y `resources/app.asar` incluidos. Instalador EXE compilado en Windows mediante GitHub Actions, descargado y comprobado como ejecutable PE.
- [Compilaciones Windows/macOS aprobadas](https://github.com/ferhernandezdimas-beep/InventarioCortigo7/actions/runs/45752585110), commit `4ef1996`.

No se utilizaron usuarios reales para las pruebas ni se crearon movimientos operativos. No hay un equipo Windows ni Mac Intel conectado para certificar su interacción; la compilación no sustituye la aceptación de instalación en esos equipos. Queda la aceptación con cuenta autorizada de los flujos por rol, impresoras físicas, importación/exportación autenticada y cierre/reapertura de sesión.

## Mantenimiento

Fuentes empaquetadas mediante `scripts/package_desktop.py`, con una lista explícita de archivos. No se incluyen backend, secretos, usuarios, bases, respaldos ni dependencias instaladas. Los binarios locales se generaron desde una extracción limpia en una carpeta temporal para evitar metadatos Finder/iCloud que impiden firmar aplicaciones. El flujo `.github/workflows/escritorio.yml` permite regenerar instaladores en Windows y macOS.
