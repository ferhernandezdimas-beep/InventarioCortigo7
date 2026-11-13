# Pruebas de entrega local — 10/11/2026

Resultado ejecutado: **146 pruebas aprobadas**, sin advertencias, con `pytest -q -W error` sobre PostgreSQL 17 real.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.lock
bash scripts/test.sh -q -W error
```

El script inicia una base PostgreSQL 17 efímera y separada de la operativa. TEST_DATABASE_URL debe utilizar postgresql+psycopg y un nombre terminado en `_test`. Cada prueba crea su propio esquema, aplica Alembic y elimina únicamente ese esquema al finalizar. Sin URL de pruebas, la integración se marca como omitida; eso no acredita concurrencia.

## Cobertura verificada

- Decimal, conversiones kg/g y L/ml, dimensiones incompatibles, cantidades inválidas y costos.
- PEPS: lotes simples/repartidos, consumo exacto, agotados/caducados, desempate, costos distintos/desconocidos, reversión y rollback integral.
- Conexiones concurrentes: no sobreconsumo, orden consistente entre varios ingredientes, espera al lote antiguo ocupado, ventas/entradas duplicadas e importaciones/aperturas y borradores confirmados simultáneamente.
- Recetas y ventas: cantidades, rendimiento, snapshots, conservación de precios/costos históricos, cambio, pago inválido, precios modificados, varias unidades/platillos y cancelaciones.
- Seguridad: login/logout POST, CSRF activo, roles, acceso directo denegado, usuarios inactivos, límites de intentos y revocación de sesiones por cambio/restablecimiento de contraseña.
- Excel: libros dañados/vacíos, mapeo, números regionales, filas repetidas, unidades inválidas, fórmulas, confirmación sin escrituras parciales, apertura documentada y prevención de reimportación. Las exportaciones XLSX se vuelven a abrir con openpyxl y se comprueba que el texto no se convierte en fórmula.
- Borradores incompletos, versiones desactualizadas, confirmación idempotente y correcciones de recepción con protección del inventario consumido.
- Migraciones: revisión inicial con usuario e inventario previos y actualización hasta head conservando historial/cantidades.
- Conciliación de solo lectura: lotes, movimientos, asignaciones, costos y pertenencia del ingrediente, incluyendo detección de inconsistencias.
- Renderizado y formularios HTTP de los módulos nuevos, con usuarios autenticados y permisos reales.

- Escenario demo: conservación de cuenta/datos previos, 74 ventas con consumo real por receta, conciliación, fechas, borrador válido, reanudación tras interrupción, rechazo de colisiones y carga repetida sin duplicados. Vistas pobladas de lotes caducados, inventario, POS, recetas y reportes.

## Comprobaciones adicionales ejecutadas

Ruff, compilación Python, sintaxis JavaScript/Bash y pip check sin errores. El paquete ZIP se extrajo en una carpeta temporal: se comprobaron código, recursos locales y que init_env conserva un archivo de entorno ya existente. Se verificó la exclusión de secretos/datos operativos.

Se restauró el respaldo de la instalación en una base nueva y se aplicó d457194c1424 antes de actualizar la original; conexión, head y conciliación correctos. La copia conservó el usuario existente; el catálogo operativo estaba vacío. El caso con inventario poblado se comprueba con datos sintéticos exclusivamente en la base de pruebas.

## Límites de verificación

No hay navegador automatizado conectado. El tamaño del login se ajustó usando la captura recibida; las vistas se verificaron mediante Flask/HTTP, sin afirmar que se haya realizado inspección visual en escritorio/tablet/móvil. La aceptación visual, impresión en el equipo de destino y el mapeo del Excel original deben revisarse con esos recursos reales. No se probaron integraciones bancarias, fiscales, de impresoras térmicas ni despliegue remoto porque no forman parte de esta entrega local.
