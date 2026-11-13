> Especificación funcional original conservada y actualizada a PostgreSQL 17. La actualización obligatoria de base prevalece sobre cualquier detalle técnico anterior: dialecto postgresql+psycopg, psycopg 3, NUMERIC, Alembic, transacciones atómicas, bloqueo de filas sin omitir lotes antiguos, idempotencia, fechas UTC y pruebas de concurrencia sobre PostgreSQL 17 real. Respaldos con pg_dump y restauración con pg_restore.
> Este documento describe el alcance completo solicitado, no funciones ya terminadas. Consultar AVANCES.md para el estado real.

# PROMPT MAESTRO — DESARROLLO DEL SISTEMA CORTIJO 7

## 1. Tu rol y objetivo

Actúa como un equipo senior de ingeniería de software integrado por un arquitecto de software, un desarrollador backend especializado en Python y Flask, un ingeniero de bases de datos, un diseñador UI/UX especializado en aplicaciones empresariales y un ingeniero de calidad.

Necesito que desarrolles una **aplicación web profesional, funcional, moderna y visualmente excepcional** para el restaurante **Cortijo 7**, ubicado en San Juan del Río, Querétaro, México.

El sistema se llamará provisionalmente:

**CORTIJO 7 — Sistema de Gestión Integral**

Su propósito principal será reemplazar los controles manuales de Excel utilizados actualmente para administrar los insumos del restaurante, incorporando inventario, compras, proveedores, entradas, salidas, control PEPS, recetas, costos, punto de venta y reportes administrativos.

No quiero únicamente un prototipo visual, un dashboard estático o una demostración con información ficticia.

Quiero desarrollar un sistema real, con arquitectura organizada, base de datos persistente, operaciones funcionales, integridad de datos, seguridad y diseño visual de calidad comercial.

Debes actuar como un desarrollador responsable del producto completo y tomar decisiones técnicas fundamentadas, sin añadir complejidad innecesaria.

**Prioridad general:**

1. Funcionalidad real y confiable.
2. Integridad de inventario y operaciones.
3. Arquitectura clara y mantenible.
4. Experiencia de usuario intuitiva.
5. Diseño elegante y coherente.
6. Seguridad y pruebas.
7. Facilidad de instalación y mantenimiento.

No sacrifiques funcionalidad por estética, ni estética por implementar rápidamente formularios genéricos.

---

## 2. Información del proyecto y fuentes de referencia

El restaurante combina gastronomía mexicana e internacional y tiene una ambientación de hacienda.

Actualmente utiliza Microsoft Excel para controlar inventario, entradas y salidas de ingredientes.

El anteproyecto proporcionado, denominado *Implementación de un software POS*, establece los siguientes objetivos:

- Analizar cómo se administran los insumos actualmente.
- Crear un catálogo de materias primas y productos.
- Configurar existencias mínimas y máximas.
- Registrar entradas y salidas de almacén.
- Implementar PEPS (Primeras Entradas, Primeras Salidas).
- Gestionar lotes de productos y fechas de caducidad.
- Configurar recetas y cantidades de ingredientes.
- Descontar automáticamente los ingredientes cuando se venda un platillo.
- Conocer el costo de los ingredientes utilizados en cada platillo.
- Facilitar la operación del personal.
- Obtener información que permita evaluar costos y desperdicios.

Estos requerimientos constituyen el núcleo confirmado del sistema.

### 2.1. Información identificada en las fotografías del Excel

Las fotografías muestran un archivo de Excel denominado aproximadamente **Catálogo Insumos 2026**, organizado en hojas de inventario, entradas y salidas.

**Hoja: Inventario**

Se identifican estas columnas:

| Campo | Descripción |
|---|---|
| Ingrediente | Nombre del insumo |
| Catálogo | Clasificación o referencia utilizada actualmente |
| Proveedor | Proveedor relacionado |
| Precio Prom | Precio promedio |
| Inv Inicial | Inventario inicial |
| Unidad | Unidad de medida |
| Entradas | Cantidad ingresada |
| Salidas | Cantidad retirada |
| Inv. Final | Existencia final |
| Valor Inv. | Valor monetario del inventario |

**Hoja: Entradas**

Se observan campos relacionados con:

- Fecha.
- Ingrediente.
- Proveedor.
- Presentación en kilogramos o litros.
- Cantidad de presentaciones o piezas recibidas.
- Cantidad total ingresada.
- Precio por presentación.
- Precio por unidad.
- Importe total del ingreso.

**Hoja: Salidas**

Se observan campos relacionados con:

- Fecha.
- Ingrediente.
- Proveedor.
- Presentación en kilogramos o litros.
- Cantidad de presentaciones o piezas retiradas.

Algunos encabezados adicionales no son completamente legibles. No inventes su significado.

En el inventario se identifican materias primas como cebolla, jitomate, aguacate, chile poblano, cilantro, lechuga, arroz, sal, especias, tortillas, carnes y diferentes productos utilizados en cocina.

El sistema debe manejar correctamente ingredientes vendidos o comprados por kilogramos, gramos, litros, mililitros y piezas.

**Importante:** las fotografías son referencias visuales de la operación actual, no equivalen al archivo original ni permiten validar fórmulas, registros completos o estructuras internas. Diseña un importador flexible para recibir el Excel original posteriormente.

### 2.2. Información todavía no confirmada

El anteproyecto no establece con precisión:

- Si existirá una o varias cajas.
- Si habrá varios almacenes.
- Si trabajará sin Internet.
- Si se imprimirán tickets.
- Si se utilizarán mesas y comandas.
- Si habrá facturación electrónica.
- Si los productos se manejarán con lector de códigos.
- Si habrá varias sucursales.
- Cómo se autorizan las mermas o cancelaciones.
- Si todos los ingredientes tienen lotes y fechas de caducidad.
- Si se registrarán compras y pagos a proveedores.
- Si ya existe otro sistema de ventas.

No conviertas estas incógnitas en hechos.

Trabajaremos con una propuesta inicial de una sucursal, un almacén y un punto de venta básico integrado, dejando la arquitectura preparada para futuras ampliaciones razonables.

Crea un documento `docs/DECISIONES_PENDIENTES.md` donde registres las cuestiones que requieran confirmación.

---

## 3. Tecnologías obligatorias

La aplicación será **web responsive**, no una aplicación móvil nativa.

### Backend

- Python.
- Flask.
- Flask-SQLAlchemy o integración SQLAlchemy moderna.
- SQLAlchemy 2.x compatible.
- Flask-Migrate y Alembic.
- Flask-Login.
- Flask-WTF o protección CSRF equivalente.
- Werkzeug para hashing seguro de contraseñas.
- Bibliotecas mantenidas y compatibles entre sí.

### Frontend

- HTML5 semántico.
- CSS3.
- JavaScript moderno.
- Jinja2.
- Bootstrap 5 como base de componentes cuando resulte conveniente.
- CSS personalizado para lograr identidad visual propia.
- Chart.js para gráficas.
- Fetch API para solicitudes asincrónicas.
- HTMX o Alpine.js solamente donde simplifiquen interacciones reales.

Evita incorporar React, Vue o frameworks adicionales sin una necesidad técnica clara.

Quiero que Flask sea el núcleo del proyecto y que el frontend se mantenga fácil de entender y modificar.

### Base de datos

**PostgreSQL 17**, con tablas transaccionales, claves foráneas, índices e integridad referencial.

Usar SQLAlchemy para definir modelos y consultas.

No crear la estructura permanentemente mediante `db.create_all()` como sustituto de migraciones.

### Desarrollo y despliegue

- Docker y Docker Compose.
- Variables de entorno.
- Archivo `.env.example`.
- Git.
- Dependencias con versiones compatibles controladas.
- Gunicorn para producción.
- Nginx o reverse proxy equivalente.
- HTTPS en producción.
- Documentación de instalación.
- Copias de seguridad y procedimiento de restauración.

El proyecto debe ser ejecutable localmente mediante instrucciones claras y reproducibles.

No incluir credenciales reales dentro del repositorio.

### Configuración regional

- Idioma: español de México.
- Moneda: MXN.
- Zona horaria: `America/Mexico_City`.
- Fechas mostradas: `dd/mm/aaaa`.
- Importes con formato monetario mexicano.
- Cantidades con precisión decimal.
- Almacenamiento temporal consistente, preferentemente UTC en la base de datos, convirtiendo a hora local para presentación.

Usa `Decimal` y columnas `DECIMAL` para cantidades y dinero. No utilices `float` para cálculos monetarios o de inventario.

---

# 4. Identidad visual y dirección de diseño

Esta sección es fundamental.

Quiero una aplicación que parezca diseñada cuidadosamente para un restaurante real, no una plantilla administrativa descargada ni una interfaz genérica creada automáticamente.

La identidad debe combinar:

**Elegancia contemporánea + hacienda mexicana + gastronomía + tecnología empresarial.**

No quiero una interfaz recargada de colores, sombras excesivas, degradados innecesarios, emojis o componentes decorativos que no aporten funcionalidad.

## 4.1. Sistema de diseño

Utiliza esta propuesta inicial de colores:

| Elemento | Color |
|---|---|
| Verde institucional | `#173B35` |
| Verde profundo | `#102C28` |
| Fondo cálido | `#F7F6F2` |
| Superficie blanca | `#FFFFFF` |
| Arena suave | `#E8E2D8` |
| Terracota/acento | `#B36B4F` |
| Texto principal | `#242825` |
| Texto secundario | `#747A76` |
| Bordes | `#E7E8E3` |

Los colores deben ser variables CSS reutilizables.

No utilices el color de acento indiscriminadamente.

### Tipografía

Propuesta:

- Inter o Manrope para interfaz, tablas, formularios y números.
- Cormorant Garamond o una serif elegante únicamente en elementos de identidad y títulos destacados, cuando aporte valor.

No abuses de combinaciones tipográficas.

### Diseño de componentes

- Sidebar lateral elegante y compactable.
- Barra superior discreta.
- Tarjetas con bordes finos y sombras muy sutiles.
- Radio de esquinas moderado.
- Espaciado consistente.
- Tablas legibles y bien alineadas.
- Indicadores visuales de estado sobrios.
- Iconografía coherente, preferentemente Lucide.
- Formularios organizados por secciones.
- Modales únicamente cuando tengan sentido.
- Confirmaciones claras para operaciones críticas.
- Estados vacíos diseñados cuidadosamente.
- Estados de carga visibles.
- Mensajes de error y éxito comprensibles.

Evita el estilo de dashboard genérico con grandes tarjetas multicolores.

### 4.2. Diseño adaptable

El sistema deberá ofrecer una experiencia consistente en:

**Escritorio:** navegación completa, tablas y formularios optimizados para administración.

**Tablet:** punto de venta táctil, navegación adaptada y controles suficientemente grandes.

**Móvil:** consultas, movimientos sencillos, alertas y operaciones administrativas compatibles con pantallas pequeñas.

No fuerces una tabla con muchas columnas dentro de la pantalla móvil. Utiliza vistas compactas, tarjetas o desplazamiento horizontal controlado según corresponda.

No es obligatorio que la pantalla de cobro móvil tenga exactamente la misma distribución que en escritorio.

### 4.3. Microinteracciones

Incorpora de manera moderada:

- Transiciones de 150–250 ms.
- Estados hover.
- Indicadores de enfoque para teclado.
- Skeletons o estados de carga cuando sean útiles.
- Confirmaciones después de guardar.
- Respuesta inmediata de botones.
- Validación contextual.
- Notificaciones no intrusivas.

Todas las animaciones deben ser discretas, rápidas y accesibles.

### 4.4. Calidad visual

Cada pantalla debe pasar estos criterios:

1. Jerarquía visual clara.
2. Consistencia entre módulos.
3. Alineaciones precisas.
4. Espaciados uniformes.
5. Tipografía legible.
6. Contraste suficiente.
7. Ausencia de texto cortado.
8. Formularios simples y ordenados.
9. Componentes coherentes.
10. Diseño específico para Cortijo 7.

No muestres imágenes de comida genéricas en todos los módulos. Si existen imágenes oficiales del restaurante, permitir configurarlas posteriormente.

No inventes un logotipo oficial. Utiliza un tratamiento tipográfico elegante del nombre hasta disponer de los recursos auténticos.

---

# 5. Estructura de navegación

Propongo la siguiente organización:

```text
CORTIJO 7
Sistema de Gestión Integral

PRINCIPAL
├── Inicio
└── Punto de Venta

INVENTARIO
├── Inventario General
├── Entradas
├── Salidas
├── Lotes y Caducidades
├── Movimientos
└── Ajustes de Inventario

CATÁLOGOS
├── Ingredientes
├── Categorías
├── Unidades de Medida
└── Proveedores

OPERACIÓN
├── Platillos
├── Recetas
└── Costos de Producción

ANÁLISIS
├── Reportes
├── Ventas
└── Indicadores

ADMINISTRACIÓN
├── Usuarios
├── Roles y Permisos
├── Importación de Datos
├── Auditoría
└── Configuración
```

La navegación debe cambiar según los permisos del usuario.

Ocultar una opción del menú no sustituye la verificación del permiso en el backend.

---

# 6. Módulo de autenticación y usuarios

Implementar autenticación real.

### Funcionalidades

- Inicio de sesión.
- Cierre de sesión.
- Sesiones seguras.
- Contraseñas almacenadas mediante hashing seguro.
- Validación de formularios.
- Protección CSRF.
- Protección contra intentos repetitivos de inicio de sesión.
- Administración de usuarios.
- Activación y desactivación.
- Cambio de contraseña.
- Registro de actividad sensible.

### Roles iniciales propuestos

**Administrador:** acceso general a configuración y operaciones.

**Gerente:** acceso a inventario, recetas, costos, reportes y supervisión.

**Almacén:** entradas, salidas, lotes y consulta de existencias.

**Caja:** punto de venta y consulta de ventas autorizadas.

Los permisos deben centralizarse y no depender de condiciones duplicadas en múltiples archivos.

La creación del administrador inicial debe realizarse mediante un comando seguro de inicialización, evitando credenciales predeterminadas públicas o permanentes.

---

# 7. Dashboard principal

La pantalla de inicio debe ser una de las más cuidadas visualmente.

## Encabezado

Mostrar el nombre del restaurante y un saludo apropiado.

Ejemplo:

**Resumen de operaciones**

Consulta el estado del inventario y la actividad del restaurante.

Fecha actual y usuario autenticado.

## Indicadores principales

- Valor conocido del inventario.
- Cantidad de ingredientes activos.
- Ingredientes con existencias bajas.
- Lotes próximos a caducar.
- Ventas del día.
- Costo de insumos consumidos.

El dato del valor total debe diferenciar entre información calculable y costos pendientes de registrar.

No mostrar valores ficticios como si fueran reales.

## Secciones

**Actividad reciente:** últimas entradas, salidas, ventas y ajustes.

**Alertas:** productos agotados, existencias bajas y caducidades próximas.

**Resumen de ventas:** gráfica por periodo.

**Movimientos de inventario:** vista resumida.

**Acciones rápidas:**

- Registrar entrada.
- Registrar salida.
- Nuevo ingrediente.
- Abrir punto de venta.
- Consultar reportes.

### Diseño

Dashboard espacioso, equilibrado, profesional y sin saturación de tarjetas.

---

# 8. Módulo de ingredientes y catálogo

Este módulo será uno de los pilares principales.

## Datos por ingrediente

- Identificador interno.
- Código opcional.
- Nombre.
- Descripción.
- Categoría.
- Unidad base.
- Proveedor principal opcional.
- Existencia mínima.
- Existencia máxima.
- Existencia actual calculada.
- Costo de referencia, cuando se conozca.
- Estado activo/inactivo.
- Fecha de creación.
- Fecha de modificación.
- Usuario responsable.

Las existencias actuales no deben depender de un campo que pueda editarse libremente.

Deben calcularse a partir de los registros válidos de movimientos o de saldos mantenidos transaccionalmente y reconciliables con el historial.

## Acciones

- Crear.
- Editar.
- Consultar.
- Desactivar.
- Filtrar.
- Buscar.
- Consultar historial.
- Consultar lotes.
- Consultar movimientos.
- Exportar.

## Tabla principal

Columnas sugeridas:

| Ingrediente | Categoría | Disponible | Unidad | Mínimo | Estado | Acciones |
|---|---|---:|---|---:|---|---|

Permitir búsquedas por nombre, proveedor y categoría.

Los estados deben mostrar:

- Disponible.
- Existencia baja.
- Agotado.
- Inactivo.

No permitir eliminar físicamente ingredientes con movimientos históricos.

---

# 9. Unidades de medida y conversiones

Este módulo debe funcionar correctamente antes de desarrollar la lógica completa de inventario.

### Unidades fundamentales

- Kilogramo.
- Gramo.
- Litro.
- Mililitro.
- Pieza.

Permitir configurar presentaciones comerciales.

Ejemplo:

```text
Ingrediente: Cebolla blanca
Unidad base: gramos

Compra:
Presentación: 1 kilogramo
Cantidad recibida: 3

Cantidad real:
3,000 gramos
```

Otro ejemplo:

```text
Ingrediente: Aceite
Unidad base: mililitros

Compra:
Presentación: botella de 1 litro
Cantidad: 4

Cantidad real:
4,000 mililitros
```

Las conversiones deben usar precisión decimal.

No convertir automáticamente piezas a kilogramos si no existe una equivalencia configurada explícitamente para esa presentación.

Distinguir unidades de masa, volumen y conteo.

No mezclar cantidades incompatibles.

---

# 10. Módulo de proveedores

Crear administración de proveedores.

Campos:

- Nombre comercial.
- Razón social opcional.
- Contacto opcional.
- Teléfono opcional.
- Correo electrónico opcional.
- Dirección opcional.
- Notas.
- Estado.

Funciones:

- Registrar proveedor.
- Editar.
- Consultar.
- Desactivar.
- Asociar productos.
- Consultar entradas relacionadas.
- Consultar historial de compras registradas.

No obligar a capturar información que el restaurante todavía no tenga.

---

# 11. Módulo de entradas de inventario

Debe reemplazar la hoja actual de Excel llamada **Entradas**.

## Formulario

Campos de encabezado:

- Fecha de entrada.
- Proveedor.
- Referencia de compra opcional.
- Observaciones.
- Usuario responsable.

Permitir agregar múltiples ingredientes en una misma entrada.

Campos por renglón:

- Ingrediente.
- Presentación.
- Cantidad de presentaciones.
- Contenido por presentación.
- Unidad.
- Cantidad total calculada.
- Precio de compra.
- Costo unitario calculado.
- Número de lote opcional.
- Fecha de caducidad opcional.

## Reglas

1. Una entrada confirmada aumenta existencias.
2. Debe generar movimientos trazables.
3. Debe registrar costos cuando estén disponibles.
4. Debe permitir varios productos por recepción.
5. Debe permitir varios lotes de un mismo ingrediente.
6. Debe validar cantidades positivas.
7. No debe duplicar movimientos por enviar dos veces el formulario.
8. No debe permitir modificar silenciosamente una entrada confirmada.
9. Toda corrección posterior debe ser trazable.
10. La operación debe ser transaccional.

### Presentación visual

Diseñar el formulario como una operación de almacén real:

- Encabezado de recepción.
- Tabla editable de productos.
- Total de unidades.
- Total monetario conocido.
- Observaciones.
- Botón de confirmar recepción.

Agregar opción de guardar borrador cuando sea útil y diferenciando claramente borrador de movimiento confirmado.

---

# 12. Módulo de lotes y PEPS

Este es el componente técnico más importante.

**PEPS significa Primeras Entradas, Primeras Salidas.**

El sistema deberá consumir primero las cantidades correspondientes a las entradas más antiguas que sean elegibles.

La fecha de caducidad es una propiedad independiente.

No confundas PEPS con FEFO (First Expired, First Out). FEFO prioriza la caducidad más próxima y sería una política diferente.

## Ejemplo funcional

Ingrediente: Cebolla blanca.

```text
Lote A
Fecha de entrada: 01/09/2026
Cantidad: 10 kg
Costo unitario: $20/kg

Lote B
Fecha de entrada: 05/09/2026
Cantidad: 15 kg
Costo unitario: $24/kg
```

Se requiere retirar 12 kg.

Resultado:

```text
Lote A: -10 kg
Lote B: -2 kg

Existencia restante:
Lote A: 0 kg
Lote B: 13 kg
```

Costo del movimiento:

```text
10 × $20 = $200
 2 × $24 = $48

Costo total: $248
```

Los números son únicamente un escenario de prueba, no información real del restaurante.

## Reglas obligatorias

- Ordenar lotes por fecha de entrada y criterio estable de desempate.
- Registrar el lote de origen de cada cantidad consumida.
- Permitir un consumo distribuido entre varios lotes.
- Conservar el costo real de cada asignación.
- No permitir existencia negativa por defecto.
- No consumir lotes agotados.
- Identificar lotes caducados.
- Bloquear por defecto el consumo de lotes caducados.
- Informar cuando no exista stock elegible suficiente.
- Registrar cada movimiento.
- Mantener integridad incluso ante operaciones simultáneas.

La salida y las asignaciones por lote deben guardarse en una transacción atómica.

Para evitar inconsistencias cuando dos usuarios realizan operaciones simultáneamente, utilizar bloqueo transaccional de filas u otro mecanismo sólido compatible con PostgreSQL 17.

No consultar simplemente la existencia disponible y actualizarla después sin proteger la operación concurrente.

## Caducidades

Visualizar:

- Lotes activos.
- Lotes agotados.
- Lotes caducados.
- Próximos a caducar.
- Cantidad disponible por lote.

El número de días de anticipación para las alertas debe ser configurable.

Los ingredientes sin fecha de caducidad no deben recibir una fecha inventada.

## Inventario inicial sin lotes

Es posible que el Excel original no incluya la trazabilidad completa de todos los insumos existentes.

En ese caso:

- Permitir registrar un saldo inicial documentado.
- Identificarlo como inventario de apertura.
- Marcar su procedencia histórica como no verificada.
- No inventar fechas de compra, caducidades ni costos.
- Mantener separada la información histórica incompleta de los nuevos lotes plenamente trazables.

Documentar la política de consumo del inventario inicial y solicitar su validación antes de operar con datos reales.

---

# 13. Módulo de salidas de inventario

Debe reemplazar la hoja de Excel llamada **Salidas**.

## Tipos propuestos

- Consumo manual.
- Merma.
- Producto dañado.
- Producto caducado.
- Ajuste negativo autorizado.
- Consumo asociado a venta, generado automáticamente.

La autorización de cada tipo deberá estar controlada por permisos.

## Formulario

- Fecha.
- Ingrediente.
- Cantidad.
- Unidad.
- Motivo.
- Observaciones.
- Usuario.
- Referencia de operación.

El sistema debe mostrar qué lotes se consumirán antes de confirmar una salida, cuando corresponda.

## Reglas

- Aplicar PEPS.
- Descontar inventario.
- Generar movimiento.
- Registrar lotes afectados.
- Registrar costos consumidos.
- Impedir cantidades inválidas.
- Registrar la persona responsable.
- Evitar borrado de movimientos confirmados.

Las cancelaciones y correcciones deben generar movimientos compensatorios auditables.

---

# 14. Módulo de ajustes de inventario

Implementar conteos y ajustes controlados.

Ejemplo:

```text
Existencia registrada: 15 kg
Existencia física: 14.5 kg

Diferencia: -0.5 kg
```

El ajuste deberá requerir:

- Ingrediente.
- Existencia física.
- Diferencia calculada.
- Motivo.
- Usuario responsable.
- Confirmación.

Los ajustes positivos requieren una política documentada sobre procedencia, fecha y costo del inventario recuperado.

No fabricar un historial de compra para justificar un ajuste.

Registrar el antes y el después.

---

# 15. Módulo de platillos y recetas

Crear catálogo de platillos del restaurante.

## Datos del platillo

- Código opcional.
- Nombre.
- Categoría.
- Descripción.
- Precio de venta.
- Imagen opcional.
- Estado disponible/no disponible.
- Receta asociada.
- Rendimiento o porciones, cuando aplique.

Ejemplo:

**Hamburguesa de la casa**

Precio de venta: configurable.

Receta:

| Ingrediente | Cantidad |
|---|---:|
| Carne | 180 g |
| Pan | 1 pieza |
| Queso | 30 g |
| Lechuga | 20 g |
| Jitomate | 30 g |

## Constructor de recetas

Diseñar una interfaz donde se pueda:

1. Crear una receta.
2. Buscar ingredientes existentes.
3. Agregar ingredientes a la receta.
4. Definir cantidades.
5. Elegir unidades.
6. Visualizar costo conocido.
7. Guardar la receta.
8. Editar una nueva versión.
9. Consultar historial de cambios.

Debe resultar fácil modificar las cantidades sin utilizar formularios largos y poco prácticos.

## Costo de receta

Calcular un costo estimado usando información de inventario disponible y una metodología definida.

Distinguir claramente entre:

**Costo estimado de receta:** estimación antes de vender.

**Costo real de ingredientes consumidos:** costo de los lotes efectivamente asignados durante una venta.

Si algún ingrediente no tiene precio confiable, indicar que el costo está incompleto.

No presentar una cifra parcial como costo total definitivo.

## Historial

Al modificar una receta, no alterar retroactivamente las ventas anteriores.

Mantener una versión o snapshot de ingredientes, cantidades y costos pertinentes al momento de finalizar cada venta.

---

# 16. Descuento automático de ingredientes

Este es uno de los principales objetivos del restaurante.

### Flujo

```text
Se registra una venta
         ↓
Se identifican los platillos
         ↓
Se consultan sus recetas
         ↓
Se calculan ingredientes
         ↓
Se validan existencias
         ↓
Se aplica PEPS
         ↓
Se asignan lotes
         ↓
Se calculan costos
         ↓
Se descuentan existencias
         ↓
Se registra el movimiento
         ↓
Se confirma la venta
```

## Escenario de prueba

Una receta consume:

```text
Carne: 180 g
Pan: 1 pieza
Lechuga: 20 g
```

Se venden 3 unidades.

El consumo resultante debe ser:

```text
Carne: 540 g
Pan: 3 piezas
Lechuga: 60 g
```

El sistema debe descontar las cantidades correspondientes de sus lotes disponibles.

Si no existe stock suficiente, debe aplicar una política segura por defecto: no finalizar la venta con consumo incompleto y mostrar la causa.

La política de permitir ventas con inventario insuficiente, si alguna vez se requiere, debe confirmarse y configurarse explícitamente. No implementarla como comportamiento silencioso.

La confirmación de venta y el descuento de inventario deben ser atómicos.

No descontar ingredientes al agregar un platillo al carrito o crear un borrador.

Solo al confirmar la venta, según el flujo definido.

---

# 17. Módulo de punto de venta (POS)

Implementar un POS básico pero funcional, preparado para computadora y tablet.

Este módulo es parte de la propuesta de alcance y debe poder ajustarse cuando el restaurante confirme cómo registra actualmente sus ventas.

## Pantalla

Distribución de dos áreas principales.

### Área izquierda

- Buscador de productos.
- Categorías.
- Tarjetas de platillos.
- Nombre.
- Precio.
- Imagen cuando exista.
- Estado de disponibilidad.

### Área derecha

**Venta actual**

- Platillos seleccionados.
- Cantidad.
- Precio unitario.
- Subtotal.
- Eliminación de renglones.
- Total.
- Botón para cobrar.

El POS debe ser rápido, táctil, claro y sin distracciones.

## Flujo de venta

1. Seleccionar platillos.
2. Agregar al carrito.
3. Modificar cantidades.
4. Validar importes.
5. Seleccionar método de pago.
6. Confirmar.
7. Registrar la venta.
8. Descontar ingredientes.
9. Generar comprobante interno.

Métodos iniciales sugeridos:

- Efectivo.
- Tarjeta.
- Transferencia.

Registrar el método declarado, pero **no implementar cobros bancarios reales** sin una integración expresamente contratada.

Para efectivo, permitir capturar monto recibido y calcular cambio.

## Ventas canceladas

No eliminar ventas confirmadas físicamente.

Registrar:

- Motivo.
- Usuario.
- Fecha.
- Relación con venta original.
- Efectos de reversión en inventario y costos.

El procedimiento de reversión deberá devolver cantidades de forma trazable a los lotes originales cuando sea válido. Si los lotes están bloqueados, caducados o modificados, requerirá una política de ajuste segura.

No duplicar devoluciones por cancelaciones repetidas.

## Comprobantes

Generar un comprobante interno imprimible desde el navegador.

No describirlo como factura fiscal ni CFDI.

La integración con impresoras térmicas específicas quedará pendiente de confirmar el hardware.

## Productos directos

Contemplar la posibilidad de vender productos que no utilizan una receta de preparación, como bebidas envasadas.

Debe existir una distinción explícita entre:

- Platillo preparado con receta.
- Producto vendido directamente con control de existencias.
- Producto o servicio sin control de inventario, si está autorizado.

No aplicar consumos ficticios.

---

# 18. Reportes e indicadores

Crear un módulo de reportes útil para la administración del restaurante.

## Reportes prioritarios

**Inventario actual**

- Ingrediente.
- Existencia.
- Unidad.
- Costo conocido.
- Valor conocido.
- Estado.

**Entradas**

- Fechas.
- Proveedores.
- Productos.
- Cantidades.
- Costos.

**Salidas**

- Fecha.
- Ingrediente.
- Cantidad.
- Motivo.
- Usuario.
- Valor consumido conocido.

**Caducidades**

- Ingrediente.
- Lote.
- Fecha de caducidad.
- Cantidad disponible.

**Ventas**

- Fecha.
- Productos.
- Cantidades.
- Total.
- Método de pago.
- Estado.

**Costos de platillos**

- Platillo.
- Costo estimado.
- Precio de venta.
- Margen bruto estimado.

**Mermas**

- Ingrediente.
- Cantidad.
- Motivo.
- Costo asociado.

## Gráficas

Agregar con Chart.js:

- Ventas por día.
- Consumo de ingredientes.
- Productos más vendidos.
- Costos de insumos por periodo.
- Mermas por categoría.

Utilizar datos reales.

No mostrar gráficas con datos simulados en un entorno de producción.

## Filtros

- Hoy.
- Últimos 7 días.
- Últimos 30 días.
- Rango personalizado.

## Exportación

Implementar exportación CSV y XLSX de reportes prioritarios.

Una exportación PDF puede incorporarse donde realmente aporte valor, sin comprometer la prioridad de los módulos principales.

### Indicador financiero

Si se muestra utilidad, utilizar la denominación correcta:

**Margen bruto estimado por ingredientes**, no utilidad neta del restaurante.

No asumir que ingredientes representan la totalidad de los costos operativos.

---

# 19. Importación del Excel existente

Este módulo será especialmente valioso porque permitirá aprovechar la información actual del restaurante.

Implementar un importador de archivos `.xlsx` usando `openpyxl` o una biblioteca apropiada.

## Flujo esperado

```text
Seleccionar archivo Excel
          ↓
Leer hojas disponibles
          ↓
Seleccionar hoja
          ↓
Mapear columnas
          ↓
Validar información
          ↓
Mostrar vista previa
          ↓
Detectar errores/duplicados
          ↓
Confirmar importación
          ↓
Registrar resultados
```

## Requisitos

- Permitir mapear encabezados.
- Detectar filas vacías.
- Validar ingredientes.
- Identificar nombres repetidos.
- Normalizar espacios y diferencias triviales.
- Validar unidades.
- Reconocer formatos numéricos habituales.
- Identificar precios faltantes.
- Diferenciar cero de dato desconocido.
- Mostrar errores por fila.
- Permitir descargar un resumen de errores.
- Evitar duplicaciones en importaciones repetidas.
- Registrar quién importó el archivo.
- Conservar un registro de la operación.

No modificar ni eliminar automáticamente datos existentes sin confirmación.

### Importación inicial

Permitir importar:

- Catálogo de ingredientes.
- Categorías, si sus valores están identificados.
- Proveedores.
- Unidades.
- Existencias iniciales.

No asumir que todas las columnas y cálculos del Excel están correctos.

**El libro original todavía debe solicitarse y verificarse.**

Sin ese archivo, implementar una importación genérica probada con plantillas sintéticas y documentar la validación pendiente con datos reales.

---

# 20. Diseño de la base de datos

Crear un modelo relacional normalizado.

Esta es una propuesta lógica inicial; puedes mejorar los nombres, relaciones y estructuras cuando exista una justificación técnica clara.

### Seguridad

```text
users
roles
permissions
role_permissions
user_roles
audit_logs
```

### Catálogos

```text
ingredient_categories
ingredients
measurement_units
suppliers
ingredient_suppliers
purchase_presentations
```

### Inventario

```text
inventory_receipts
inventory_receipt_items
inventory_lots
inventory_movements
inventory_movement_allocations
inventory_adjustments
inventory_adjustment_items
```

### Recetas

```text
menu_categories
menu_items
recipe_versions
recipe_ingredients
```

### Ventas

```text
sales
sale_items
sale_item_ingredient_snapshots
payments
sale_cancellations
```

### Operación

```text
import_jobs
import_job_errors
system_settings
```

Puedes consolidar entidades cuando sea lógico y evitar tablas duplicadas sin beneficio real.

## Reglas de datos

- Claves primarias estables.
- Claves foráneas explícitas.
- Restricciones de unicidad.
- Índices relevantes.
- Cantidades con precisión decimal.
- Costos históricos preservados.
- Fechas y usuarios responsables.
- Relaciones coherentes.
- Estado activo/inactivo donde corresponda.

La tabla de movimientos debe permitir conocer:

- Qué cambió.
- Cuánto cambió.
- Cuándo ocurrió.
- Quién lo realizó.
- Por qué ocurrió.
- De qué operación proviene.
- Qué lotes resultaron afectados.

## Integridad del inventario

No confiar exclusivamente en un campo `stock` editable.

Definir una fuente de verdad transaccional y un mecanismo de reconciliación.

Si se mantiene una existencia agregada para rendimiento, debe actualizarse atómicamente y poder validarse contra los movimientos.

Evitar modificaciones directas desde controladores que omitan las reglas del dominio.

Toda operación crítica debe pasar por servicios de negocio.

---

# 21. Arquitectura del backend

Utilizar el patrón **Application Factory** y Flask Blueprints.

Estructura sugerida:

```text
cortijo7/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   │
│   ├── auth/
│   ├── dashboard/
│   ├── users/
│   ├── ingredients/
│   ├── suppliers/
│   ├── inventory/
│   ├── recipes/
│   ├── pos/
│   ├── reports/
│   ├── imports/
│   │
│   ├── models/
│   │
│   ├── services/
│   │   ├── inventory_service.py
│   │   ├── fifo_service.py
│   │   ├── recipe_service.py
│   │   ├── sales_service.py
│   │   ├── costing_service.py
│   │   └── import_service.py
│   │
│   ├── templates/
│   │   ├── layouts/
│   │   ├── components/
│   │   ├── auth/
│   │   ├── dashboard/
│   │   ├── inventory/
│   │   ├── ingredients/
│   │   ├── recipes/
│   │   ├── pos/
│   │   └── reports/
│   │
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── icons/
│   │   └── images/
│   │
│   ├── forms/
│   └── utils/
│
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── docs/
├── scripts/
├── docker/
│
├── Dockerfile
├── compose.yaml
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── wsgi.py
```

Es una estructura de referencia, no una obligación de crear archivos vacíos.

Adapta las carpetas a la arquitectura real.

### Reglas de arquitectura

- Rutas delgadas.
- Validaciones claras.
- Servicios para la lógica de negocio.
- Modelos sin responsabilidades excesivas.
- Consultas optimizadas.
- Manejo explícito de transacciones.
- Errores consistentes.
- Permisos centralizados.
- Reutilización de componentes.
- Sin código duplicado.
- Sin constantes mágicas.
- Sin lógica PEPS implementada en JavaScript.
- Sin cálculos críticos exclusivamente del lado del cliente.

El frontend puede mostrar cálculos preliminares, pero el backend debe validar y calcular definitivamente.

---

# 22. Seguridad y confiabilidad

Aplicar buenas prácticas de seguridad web.

### Obligatorio

- Autenticación segura.
- Control de permisos backend.
- CSRF.
- Validación de entrada.
- Escape apropiado en plantillas.
- Consultas parametrizadas mediante ORM.
- Cookies de sesión seguras.
- Secretos mediante variables de entorno.
- Configuración diferenciada para desarrollo y producción.
- Manejo de errores sin revelar información interna.
- Registro de eventos relevantes.
- Protección de archivos subidos.
- Límites de tamaño de importación.
- Prevención de acciones repetidas.
- Desactivación de modo debug en producción.

No utilizar contraseñas en texto plano.

No exponer información sensible en logs.

No implementar una función peligrosa de borrar toda la base de datos desde la interfaz.

### Respaldo

Documentar e implementar un procedimiento operable de respaldo de PostgreSQL 17.

Incluir instrucciones verificables de restauración.

No afirmar que existen respaldos automáticos si no hay un mecanismo configurado y comprobado.

---

# 23. Pruebas obligatorias

Utilizar `pytest`.

Las pruebas no son opcionales.

## Pruebas de unidades

- Conversiones kg/g.
- Conversiones L/ml.
- Validación de cantidades.
- Cálculos monetarios.
- Costos por lote.
- Cálculos de receta.
- Determinación de existencias.

## Pruebas PEPS

Caso 1: consumo de un solo lote.

Caso 2: consumo repartido entre dos lotes.

Caso 3: consumo exacto.

Caso 4: insuficiencia de existencias.

Caso 5: lote agotado.

Caso 6: lote caducado.

Caso 7: lotes con la misma fecha de entrada.

Caso 8: costos unitarios diferentes.

Caso 9: reversión de una salida.

Caso 10: dos usuarios intentando consumir el mismo stock simultáneamente.

La prueba real de concurrencia debe utilizar PostgreSQL 17 o un entorno con semántica equivalente; no considerar SQLite una demostración suficiente de bloqueo de filas.

## Pruebas de ventas

- Venta válida.
- Venta con varias unidades.
- Venta con varios platillos.
- Descuento correcto de ingredientes.
- Error durante la operación.
- Rollback completo.
- Cancelación.
- Protección frente a duplicados.
- Persistencia de costos históricos.

## Pruebas de permisos

- Acceso permitido.
- Acceso denegado.
- Usuario inactivo.
- Operaciones restringidas.
- Acceso directo a URL protegida.

## Pruebas de importación

- Archivo válido.
- Archivo sin columnas necesarias.
- Números inválidos.
- Ingredientes repetidos.
- Unidades desconocidas.
- Archivo vacío.
- Reimportación.

## Pruebas visuales y funcionales

Cuando exista un navegador o herramienta compatible:

- Revisar escritorio.
- Revisar tablet.
- Revisar móvil.
- Verificar navegación.
- Confirmar formularios.
- Revisar tablas.
- Detectar desbordamientos.
- Confirmar diseño consistente.

Si no dispones de navegación automatizada, documenta claramente las pruebas manuales pendientes.

Nunca afirmes que una prueba pasó si no fue ejecutada.

---

# 24. Experiencia de usuario por módulo

No quiero pantallas que solo contengan un título, una tabla genérica y botones predeterminados.

Cada módulo debe estar diseñado para su operación específica.

### Inventario

Vista de tabla profesional con filtros, alertas y acceso rápido al historial.

### Entradas

Formulario de recepción con múltiples productos, totales y confirmación.

### Salidas

Formulario rápido con motivo, cantidades y vista previa de lotes consumidos.

### Lotes

Tabla con fechas, existencias y estados claros.

### Recetas

Constructor visual de ingredientes con cantidades y resumen de costos.

### POS

Interfaz táctil enfocada en rapidez, categorías y carrito.

### Reportes

Panel claro con filtros, tablas y gráficas informativas.

### Usuarios

Administración sencilla de cuentas, roles y estados.

### Configuración

Opciones organizadas por secciones, con instrucciones claras y sin saturación.

---

# 25. Estados de interfaz

Implementa en todas las pantallas pertinentes:

**Vacío:** no existen registros y se ofrece una acción pertinente.

**Cargando:** se informa que la operación sigue en curso.

**Error:** se explica el problema y cómo corregirlo.

**Éxito:** confirmación de operación realizada.

**Sin permiso:** mensaje claro sin exposición de datos.

**Sin conexión:** el navegador informa una falla de conectividad y evita confirmar erróneamente una transacción.

No asumir que la aplicación funciona offline. La compatibilidad con trabajo desconectado y sincronización posterior será una decisión futura.

---

# 26. Operaciones críticas y consistencia

El sistema administrará inventario real y registros monetarios, por lo tanto:

- No se debe finalizar una operación parcialmente.
- Las ventas y consumos deben compartir una transacción.
- Las operaciones concurrentes no deben producir stock negativo accidental.
- Las solicitudes duplicadas deben controlarse.
- Los movimientos confirmados deben conservar historial.
- Los importes históricos no deben recalcularse a partir de precios actuales.
- Las cantidades utilizadas deben conservar unidades consistentes.
- Las cancelaciones deben dejar evidencia.
- Las fallas deben poder diagnosticarse.
- Las validaciones del servidor son obligatorias.

Utiliza identificadores de idempotencia cuando resulte necesario para confirmar ventas y movimientos.

En operaciones que afecten varias entidades, define claramente cuándo empieza y cuándo termina la transacción.

---

# 27. Fases de implementación

No intentes crear todo el código en un único bloque desorganizado.

Trabaja de forma incremental, entregando funcionalidades completas y comprobables.

## Fase 1 — Fundación

1. Inspeccionar el repositorio.
2. Crear estructura Flask si no existe.
3. Configurar base de datos.
4. Configurar Docker.
5. Implementar migraciones.
6. Crear sistema de configuración.
7. Implementar autenticación.
8. Establecer sistema visual.
9. Crear layout principal.
10. Documentar instalación.

**Resultado:** aplicación ejecutable, login funcional y navegación consistente.

## Fase 2 — Catálogos

1. Ingredientes.
2. Categorías.
3. Unidades de medida.
4. Presentaciones.
5. Proveedores.
6. Validaciones.
7. Pruebas.

**Resultado:** catálogo completamente funcional.

## Fase 3 — Inventario

1. Recepciones.
2. Lotes.
3. Movimientos.
4. PEPS.
5. Salidas.
6. Ajustes.
7. Existencias.
8. Alertas.
9. Historial.
10. Pruebas transaccionales.

**Resultado:** inventario operativo con trazabilidad.

## Fase 4 — Recetas

1. Platillos.
2. Ingredientes por receta.
3. Unidades y cantidades.
4. Versionado.
5. Costeo.
6. Validaciones.

**Resultado:** recetas configurables y costos calculables.

## Fase 5 — Punto de venta

1. Catálogo para venta.
2. Carrito.
3. Totales.
4. Métodos de pago.
5. Registro de venta.
6. Descuento de ingredientes.
7. PEPS.
8. Comprobante interno.
9. Cancelaciones controladas.
10. Pruebas integrales.

**Resultado:** flujo real de venta a descuento de inventario.

## Fase 6 — Reportes

1. Dashboard con datos reales.
2. Inventario.
3. Entradas.
4. Salidas.
5. Ventas.
6. Costos.
7. Caducidades.
8. Mermas.
9. Exportaciones.

## Fase 7 — Migración

1. Importador XLSX.
2. Mapeo de columnas.
3. Validaciones.
4. Vista previa.
5. Registro de importaciones.
6. Plantilla de Excel.
7. Pruebas.

## Fase 8 — Calidad y entrega

1. Revisar UI/UX.
2. Revisar responsive.
3. Ejecutar pruebas.
4. Corregir errores.
5. Revisar seguridad.
6. Validar operaciones PEPS.
7. Documentar despliegue.
8. Documentar respaldos.
9. Elaborar guía de usuario.
10. Preparar checklist de puesta en producción.

---

# 28. Información de ejemplo y datos de prueba

Durante el desarrollo puedes crear datos sintéticos.

Ejemplos:

- Cebolla blanca.
- Jitomate.
- Aguacate.
- Lechuga.
- Carne de res.
- Tortillas.
- Aceite.
- Arroz.

También puedes crear platillos ilustrativos.

Pero:

**Nunca presentes datos sintéticos como datos reales de Cortijo 7.**

Los datos de demostración deben estar claramente identificados.

La carga demo deberá ser opcional y separada de la inicialización de producción.

No sobrescribir registros reales al ejecutar scripts de prueba.

---

# 29. Documentación requerida

Crear documentación útil y concisa.

```text
README.md

docs/
├── ARQUITECTURA.md
├── REQUERIMIENTOS.md
├── DECISIONES_PENDIENTES.md
├── MODELO_DATOS.md
├── FLUJOS_NEGOCIO.md
├── CONTROL_PEPS.md
├── IMPORTACION_EXCEL.md
├── INSTALACION.md
├── DESPLIEGUE.md
├── RESPALDOS.md
├── PRUEBAS.md
└── MANUAL_USUARIO.md
```

No crear documentos vacíos simplemente para cumplir la estructura.

La documentación debe reflejar la implementación real.

El manual deberá explicar:

- Inicio de sesión.
- Creación de ingredientes.
- Registro de entradas.
- Registro de salidas.
- Consulta de lotes.
- Creación de recetas.
- Registro de ventas.
- Consulta de reportes.
- Importación de datos.
- Administración básica.

---

# 30. Criterios de aceptación

No consideres terminado el proyecto hasta que se verifique, como mínimo, lo siguiente:

- [ ] La aplicación inicia correctamente mediante el procedimiento documentado.
- [ ] Existe una conexión funcional con PostgreSQL 17.
- [ ] Las migraciones se ejecutan correctamente.
- [ ] Se puede iniciar y cerrar sesión.
- [ ] Los usuarios tienen permisos adecuados.
- [ ] Se pueden crear y administrar ingredientes.
- [ ] Se pueden crear y consultar proveedores.
- [ ] Se pueden registrar entradas con lotes.
- [ ] Se pueden registrar salidas.
- [ ] PEPS consume las entradas correctas.
- [ ] Las existencias no quedan negativas accidentalmente.
- [ ] Los costos de consumo se calculan correctamente.
- [ ] Se pueden crear platillos y recetas.
- [ ] Las ventas generan registros persistentes.
- [ ] Las ventas descuentan los ingredientes correspondientes.
- [ ] No se generan consumos duplicados.
- [ ] Las operaciones fallidas realizan rollback.
- [ ] Las cancelaciones son auditables.
- [ ] Los reportes consultan información real.
- [ ] Se pueden importar archivos Excel válidos.
- [ ] Existe historial de movimientos.
- [ ] La interfaz funciona correctamente en escritorio y tablet.
- [ ] Las vistas móviles esenciales son utilizables.
- [ ] Los formularios validan sus campos.
- [ ] Los errores se manejan adecuadamente.
- [ ] La aplicación protege sus rutas.
- [ ] Las pruebas principales se ejecutan.
- [ ] El repositorio incluye instrucciones completas.
- [ ] No existen credenciales sensibles hardcodeadas.
- [ ] No existen módulos que aparenten funcionar pero utilicen únicamente información estática.

Si algo no está terminado, indícalo explícitamente.

---

# 31. Reglas para modificar código

Estas reglas son obligatorias.

1. Si el repositorio ya contiene código, inspecciónalo antes de modificarlo.
2. No elimines archivos o funcionalidades existentes sin justificación.
3. No reestructures código funcional innecesariamente.
4. No implementes soluciones temporales presentándolas como definitivas.
5. Evita archivos excesivamente grandes.
6. No dupliques lógica de negocio.
7. No crees controladores con cientos de líneas de lógica transaccional.
8. Mantén nombres claros.
9. Documenta decisiones complejas.
10. No introduzcas dependencias innecesarias.
11. No uses datos falsos para ocultar módulos incompletos.
12. No agregues funcionalidades fuera del alcance sin documentarlas.
13. No inventes resultados de pruebas.
14. No elimines migraciones aplicadas sin una estrategia segura.
15. No realices cambios destructivos en una base de datos real sin autorización.

El código, los nombres de clases, las variables y los comentarios técnicos pueden mantenerse en inglés siguiendo convenciones de Python.

Todos los textos visibles al usuario deberán estar en español claro.

---

# 32. Requisitos de calidad visual final

Quiero que el resultado transmita que fue desarrollado específicamente para Cortijo 7.

No debe parecer un panel administrativo genérico.

El producto debe tener:

- Identidad visual reconocible.
- Componentes diseñados de forma consistente.
- Buena tipografía.
- Espaciado profesional.
- Diseño minimalista.
- Navegación intuitiva.
- Formularios cuidados.
- Tablas refinadas.
- Buen tratamiento de información numérica.
- Indicadores de estado accesibles.
- Una interfaz de ventas especialmente bien resuelta.
- Excelente experiencia en computadora y tablet.

Prioriza la calidad de ejecución por encima de efectos decorativos.

Una interfaz sobria, perfectamente alineada y funcional es preferible a un diseño llamativo con problemas de usabilidad.

---

# 33. Forma en que debes trabajar

A partir de este momento quiero que actúes como responsable técnico del desarrollo.

**Paso 1.** Inspecciona el entorno y los archivos disponibles.

**Paso 2.** Identifica si el repositorio contiene un proyecto existente o si debe inicializarse.

**Paso 3.** Elabora un plan técnico breve y concreto con los módulos, dependencias y orden de implementación.

**Paso 4.** Registra los supuestos no confirmados sin bloquear el desarrollo de los módulos claramente definidos.

**Paso 5.** Comienza inmediatamente con la implementación.

**Paso 6.** Trabaja por fases completas, incluyendo backend, frontend, persistencia, validaciones y pruebas.

**Paso 7.** Verifica cada fase antes de continuar con las funcionalidades dependientes.

**Paso 8.** Mantén un registro claro de avances y decisiones.

**Paso 9.** Cuando encuentres un problema, analízalo y corrígelo sin recurrir a parches que comprometan la integridad del sistema.

**Paso 10.** Presenta el resultado real de cada fase.

### Reporte al terminar cada fase

Informa:

- Funcionalidades implementadas.
- Archivos importantes creados o modificados.
- Migraciones agregadas.
- Pruebas ejecutadas.
- Resultados verificados.
- Errores o limitaciones pendientes.
- Próximo módulo a desarrollar.

No afirmes que el sistema funciona completamente si faltan pruebas o dependencias.

---

# 34. Primera instrucción de ejecución

Comienza ahora.

Primero inspecciona el repositorio y el entorno disponible.

Si está vacío, inicializa el proyecto Flask con una arquitectura limpia, conexión PostgreSQL 17 mediante Docker Compose, migraciones, autenticación segura y el sistema de diseño de Cortijo 7.

Después implementa un dashboard funcional y continúa con el módulo de ingredientes, que será la base para inventario y PEPS.

No entregues solamente propuestas, capturas, pseudocódigo o explicaciones.

**Debes crear el código y los archivos necesarios en el repositorio de trabajo.**

Mantén las operaciones reales de inventario protegidas contra inconsistencias desde el principio.

Conserva la arquitectura preparada para los siguientes módulos.

Toma decisiones técnicas fundamentadas y documenta lo que no esté confirmado.

La meta es construir **CORTIJO 7 — Sistema de Gestión Integral**, una aplicación web robusta, elegante, profesional y preparada para operar con información auténtica de un restaurante.

**Empieza por la inspección técnica y la Fase 1.**
