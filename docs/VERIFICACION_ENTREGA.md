# Registro de verificación — entrega local del 08/11/2026

| Comprobación | Evidencia |
|---|---|
| Suite completa PostgreSQL 17 | 142 pruebas aprobadas con advertencias tratadas como error |
| Regresión de funciones previas | Autenticación, permisos, recetas, ventas, PEPS, reversiones y migraciones incluidas |
| Importaciones/apertura | Confirmación atómica, errores por fila, reimportación y concurrencia verificadas |
| Borradores/correcciones | Sin movimientos al guardar; una recepción al confirmar; recepción consumida protegida |
| Código y dependencias | Ruff, compileall, node --check, bash -n y pip check correctos |
| Respaldo previo | backups/cortijo7_20261109T002131Z_OIBXXu/cortijo7.dump, formato custom de PostgreSQL |
| Ensayo de actualización | c7_restore_check_20261109004801_17554: restore + Alembic d457194c1424 + conciliación correctos |
| Conservación de datos | Usuario previo conservado; inventario poblado probado en esquemas de prueba separados |
| Paquete de entrega | ZIP extraído, archivos verificados, SHA-256 generado, .env y datos excluidos |
| Inicialización | Entorno nuevo generado y segundo intento rechazado sin reemplazar secretos |
| Instancia local actualizada | PostgreSQL 17, revisión d457194c1424 y conciliación correctos; servicios saludables en 127.0.0.1:8077 |
| Acceso HTTP | Login y recursos locales responden 200; acceso sin sesión redirige al login |
| Navegador visual | No conectado; aceptación manual pendiente, sin atribuirla a las pruebas HTTP |
| Render | Sin configurar ni desplegar; entrega exclusivamente local |

La revisión d457194c1424 agrega tres tablas de entrega, renovación de sesiones y tipos/orígenes adicionales. No borra datos; los downgrades rechazan eliminar historia nueva. Las copias de restauración se conservan para revisión. No se restableció la contraseña operativa ni se insertó catálogo/inventario de ejemplo.

Para repetir la comprobación de la instancia: `bash scripts/status_local.sh`. Para instrucciones de uso y límites de alcance, consultar ENTREGA_LOCAL.md.

## Ampliación solicitada: datos de prueba — 10/11/2026

La carga demo fue autorizada expresamente después de la entrega anterior. La cuenta y el proveedor previamente existentes se conservan. No se cambiaron contraseñas ni se crearon usuarios ficticios.

| Comprobación | Resultado |
|---|---|
| Suite final PostgreSQL 17 | 146 pruebas aprobadas con `-q -W error` |
| Datos incorporados | 46 ingredientes, 9 categorías, 7 proveedores nuevos, 46 presentaciones y 20 productos con receta |
| Operación de ejemplo | 74 ventas, 2 cancelaciones, 93 lotes, 707 movimientos, 97 operaciones y 1 borrador |
| Datos previos | 1 usuario y 1 proveedor conservados; 8 proveedores totales después de la carga |
| Conciliación posterior | Lotes, asignaciones y movimientos coinciden en cantidad y costo |
| Repetición del comando | Carga reconocida; ningún registro duplicado |
| Vistas pobladas | 14 rutas autenticadas verificadas mediante Flask/HTTP interno sobre la instancia; sin atribuir revisión visual de navegador |
| Corrección de vista | Tabla de lotes recibe fecha local explícita; ya muestra lotes caducados sin error de Jinja |
| Instancia | Disponible en http://127.0.0.1:8077; PostgreSQL 17 y d457194c1424 |

Respaldos conservados (nombres fechados en UTC):

- Antes de la carga: `backups/cortijo7_20261111T033456Z_jzjD4l/cortijo7.dump`.
- Después de la carga: `backups/cortijo7_20261111T034715Z_IxRYoS/cortijo7.dump`.

Ambos archivos son respaldos custom de PostgreSQL y sus catálogos se verificaron con `pg_restore --list`. El escenario está identificado mediante nombres/códigos demo y un aviso persistente: sus ventas, costos y existencias se incluyen en los reportes. Véase [DATOS_PRUEBA.md](DATOS_PRUEBA.md).
