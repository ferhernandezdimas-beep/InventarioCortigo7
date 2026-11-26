# Paquete local de Cortijo 7

La entrega `cortijo7-local.zip` contiene las fuentes web/backend, migraciones, dependencias fijadas, recursos estáticos, documentación y las fuentes de móvil/escritorio. El primer documento a leer es `LEEME_LOCAL.md` en la raíz. Incluye lanzadores Windows `.cmd`, alternativa PowerShell y arranque Bash para Mac.

La instalación Docker no requiere Python/PostgreSQL instalados en el host. Descarga imágenes y dependencias la primera vez y conserva contenedores, imágenes y un volumen PostgreSQL 17 para operar después sin Render. La nueva configuración genera secretos aleatorios y un nombre de proyecto Docker propio; no sobrescribe `.env` existente. El usuario crea su administrador privado. La instalación nueva no copia cuentas ni datos de Render.

Se comprobó una extracción nueva del ZIP con una configuración y volumen independientes: construcción Docker, migraciones hasta `f72101c7a002`, salud HTTP, conciliación de inventario, creación de administrador sintético, login con CSRF, inventario y catálogos. Las redirecciones Nginx conservan el puerto local. Se verificó además la generación de configuración mediante Docker en dos carpetas distintas y que una `.env` existente no se sobrescribe. La prueba no sustituye la aceptación de los lanzadores en una computadora Windows; este equipo de verificación es Mac.

Durante la primera comprobación se detectó una colisión con el nombre Docker anterior. La instalación original se restauró con su configuración privada, pasó la salud y la conciliación y conservó su volumen. El nombre propio por instalación se añadió para evitar esta colisión en las instalaciones nuevas. No se exportó ni se modificó la base de Render.

El paquete se genera con `scripts/package_local.py`, con listas de rutas y extensiones permitidas, comprobación del ZIP y detección básica de secretos. Se excluyen `.env` privadas, claves, respaldos, datos persistidos, `.git`, dependencias instaladas, cachés, binarios de entrega y archivos generados. El SHA-256 se publica junto al ZIP.
