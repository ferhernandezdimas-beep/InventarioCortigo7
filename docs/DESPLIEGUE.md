# Despliegue en Render

Repositorio: https://github.com/ferhernandezdimas-beep/InventarioCortigo7. El código, Dockerfile.render y render.yaml son públicos. Los secretos, respaldos y bases nunca se incorporan a Git ni a la imagen.

## Servicios y arranque

- Servicio web Docker gratuito en Oregon. Dockerfile.render instala Nginx y dependencias bloqueadas; ejecuta scripts/start_render.py sin privilegios.
- PostgreSQL administrado gratuito, versión 17 explícita, misma región. La aplicación utiliza la conexión interna. Las URLs postgresql:// de Render se normalizan al dialecto postgresql+psycopg conservando sus opciones.
- Render termina HTTPS. Nginx escucha PORT y comunica con Gunicorn en 127.0.0.1:8000. APP_ENV=production habilita cookies Secure y HSTS. TRUST_PROXY=true se utiliza únicamente detrás de esta cadena de proxies.
- Healthcheck /health/ready: exige PostgreSQL 17 y revisión Alembic actual. El autodespliegue queda deshabilitado para revisar actualizaciones.

El plan gratuito no tiene pre-deploy command. Al arrancar, un bloqueo asesor PostgreSQL serializa Alembic; se verifica versión y revisión antes de servir tráfico. No se usa create_all ni se inicializan catálogos/usuarios automáticamente.

## Entorno y transferencia

Configurar DATABASE_URL con la conexión interna, SECRET_KEY aleatoria de al menos 32 caracteres, APP_ENV=production y TRUST_PROXY=true. Render asigna PORT. No incluir secretos en Dockerfile/render.yaml ni en argumentos públicos de comandos.

La instalación local se transfiere mediante un respaldo privado a una base remota nueva. Se exige que el destino no tenga tablas de aplicación antes de restaurar. El acceso externo de transferencia se limita temporalmente a una IP /32 y se elimina al terminar. No hay sincronización automática entre la instalación local y Render después de esta copia.

El catálogo inicial tiene origen sintético documentado en DATOS_PRUEBA.md. Por solicitud del usuario, su presentación usa nombres normales sin leyendas adicionales. La procedencia técnica y los manifiestos de auditoría se conservan.

## Plan gratuito y respaldos

El servicio puede suspenderse por inactividad y tardar en responder al primer acceso. PostgreSQL gratuito vence a los 30 días y no tiene respaldos administrados; debe actualizarse o trasladarse antes de vencer. Verificar la fecha concreta que muestra Render. No se contratan planes de pago automáticamente.

Respaldar antes de cada actualización y acordar retención privada fuera de Render. Los trabajos de importación se guardan en PostgreSQL, no en el disco efímero del contenedor.

## Actualizaciones

1. Respaldar y verificar la restauración en una base nueva.
2. Ejecutar Ruff, pruebas sobre PostgreSQL 17 y construcción Docker. GitHub Actions incluye la regresión.
3. Subir un commit revisado a main y activar Manual Deploy para ese commit.
4. Revisar logs sin copiar secretos; comprobar healthcheck, acceso, roles, ventas, inventario, reportes y conciliación.
5. Conservar código anterior y respaldos. Una reversión de imagen no revierte datos/migraciones.

No eliminar tablas ni volúmenes para corregir un despliegue. La instalación local sigue usando compose.yaml y ENTREGA_LOCAL.md.

Referencias: [Flask](https://render.com/docs/deploy-flask), [Blueprint](https://render.com/docs/blueprint-spec), [plan gratuito](https://render.com/docs/free), [respaldos](https://render.com/docs/postgresql-backups).
