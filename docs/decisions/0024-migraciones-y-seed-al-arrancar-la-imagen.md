# 0024 — Las migraciones y el seed se aplican al arrancar la imagen

**Estado:** Aceptada · 2026-11-26 · Sustituye lo que decía `docs/deploy-coolify.md` §4

## Contexto

Hasta ahora la imagen de producción solo arrancaba uvicorn y la guía de despliegue pedía
ejecutar `alembic upgrade head` como comando previo en el panel. En el primer despliegue
real de un proyecto (Dokploy) ese paso se olvidó y la base quedó vacía, además de que el
servicio no recibió sus variables y un dominio apuntaba al puerto equivocado: tres causas
a la vez, un mismo 502. Un paso manual que se olvida es un fallo esperable, no una
excepción.

## Decisión

- **El `CMD` de producción ejecuta `alembic upgrade head` y `python -m scripts.seed`
  antes de `uvicorn`**, encadenados con `&&`: si la base no está lista, el contenedor no
  arranca y el error sale en los Logs.
- Ambas operaciones son idempotentes (el seed no cambia la contraseña de una cuenta que ya
  existe), así que repetirlas en cada arranque es inocuo.
- **El despliegue son dos servicios:** la aplicación con Dockerfile y una base PostgreSQL
  del panel, aparte y con respaldos programados. No se empaqueta la base con la app.
- La guía documenta el diagnóstico del 502 (logs, variables recibidas, puerto del dominio)
  y el permiso de escritura en carpetas de subidas.

## Consecuencias

- Un despliegue deja la base al día sin pasos manuales.
- **Con más de una réplica**, varias migraciones podrían correr a la vez: la guía indica
  volver a solo uvicorn y migrar como paso previo al despliegue.
- Una migración lenta retrasa el arranque (el `HEALTHCHECK` espera 10 s y 3 intentos de
  30 s); si un día tarda más, subir `--start-period`.
- Los proyectos ya generados toman el cambio copiando el `CMD` del `Dockerfile`
  (`[SEGURO]`, ver `CHANGELOG.md`).
