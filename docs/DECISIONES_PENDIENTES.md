# Decisiones pendientes

Supuesto inicial: una sucursal, un almacén, moneda MXN y zona America/Mexico_City. Los roles son Administrador, Gerente, Almacén y Caja. Los permisos se centralizan; no se deben inferir políticas definitivas de merma/cancelación a partir de estos roles.

Por confirmar antes de operación real:

1. Responsables, autorizaciones y documentos requeridos para merma, daño, caducidad, ajustes y cancelaciones.
2. Política del inventario de apertura: procedencia no verificada, orden PEPS y costos desconocidos. La carga de apertura está habilitada con aceptación explícita y sin inventar fechas o compras históricas.
3. Días de alerta de caducidad; propuesta configurable: 7. Se permite consumir hasta la fecha de caducidad inclusive; confirmar si los productos requieren otra regla.
4. Número de cajas, almacenes, mesas/comandas y sucursales futuras; no se implementan múltiples cajas ni sucursales en esta fase.
5. Tickets, impresoras, lector de códigos, conexión con ventas existentes y facturación electrónica.
6. Validar precios finales y tratamiento fiscal, descuentos y cierre de caja. El POS actual registra un método declarado (efectivo, tarjeta o transferencia), sin desglosar impuestos ni conectar bancos.
7. Archivo XLSX original, encabezados reales, equivalencias comerciales y política de reimportación. Las fotografías no acreditan fórmulas ni cantidades completas.
8. Dominio, HTTPS, infraestructura, retención/cifrado de respaldos, responsable de recuperación y objetivos de recuperación.
9. Revisión del diseño en navegador de escritorio, tablet y móvil; no hay navegador conectado en esta sesión.
10. Trabajo sin conexión: no implementado. La interfaz avisa de fallas; no promete sincronización posterior.

Recetas, costos históricos de venta, pagos declarados y reportes básicos están implementados. La importación y los reportes prioritarios ya están implementados; la verificación del libro original y los formatos operativos particulares requieren datos auténticos. Las políticas conservadoras de merma/conteo/cancelación se detallan en AVANCE_OPERATIVO.md y deben validarse con el restaurante antes de uso comercial. No se registran ventas o importaciones ficticias para aparentar su implementación.
