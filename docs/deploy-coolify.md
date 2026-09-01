# Desplegar en Coolify / Dokploy

Kiro trae un `Dockerfile` multi-etapa con etapa `production`: imagen mínima,
usuario sin privilegios y `HEALTHCHECK` propio. Coolify y Dokploy lo consumen
directamente.

## 1. Base de datos

Crea un PostgreSQL desde el panel (Coolify: *New Resource → Database →
PostgreSQL*). Apunta la cadena de conexión **interna**: la app y la base viven
en la misma red, así que el tráfico no sale a internet.

## 2. Aplicación

*New Resource → Application → Dockerfile*, apuntando a tu repositorio.

- **Dockerfile Target:** `production` — importante. Sin esto construye la última
  etapa, que no siempre es la que quieres.
- **Port:** `8000`
- **Health Check Path:** `/health`

## 3. Variables de entorno

Configúralas en el panel, nunca en el repositorio. Las mínimas:

```
APP_NAME=Nombre del proyecto
ENVIRONMENT=production
SECRET_KEY=<openssl rand -hex 32 — uno NUEVO, no el de desarrollo>
DATABASE_URL=postgresql+psycopg://usuario:clave@nombre-servicio-db:5432/basedatos
BASE_URL=https://tu-dominio.com
LOG_LEVEL=INFO
```

Y las de correo y analítica que use el proyecto (`EMAIL_PROVIDER`,
`RESEND_API_KEY`, `GTM_ID`…).

Tres cosas que importan de verdad:

- **`SECRET_KEY` distinta a la de desarrollo.** Reutilizarla significa que
  cualquiera con acceso a tu `.env` local puede falsificar sesiones en producción.
- **`ENVIRONMENT=production`** oculta `/docs` y `/openapi.json`, y activa las
  cookies seguras.
- **`BASE_URL` con el dominio real.** Se usa para construir los enlaces de los
  correos y el `sitemap.xml`, donde no hay petición de la que deducir el host.

## 4. Migraciones

`alembic upgrade head` **no** corre solo al arrancar el contenedor. Es
deliberado: con más de una réplica, varios contenedores arrancando a la vez
intentarían migrar en paralelo.

Configúralo como comando previo al despliegue en el panel:

```
uv run alembic upgrade head
```

En Coolify: *Application → Advanced → Pre-deployment Command*.

## 5. Dominio y TLS

Añade el dominio en el panel. Coolify gestiona Let's Encrypt automáticamente vía
Traefik. Apunta primero el registro DNS A a la IP del servidor, o la emisión del
certificado falla.

## Comprobación posterior

```bash
curl -f https://tu-dominio.com/health
curl -s https://tu-dominio.com/ | grep -c '<h1'      # el HTML llega del servidor
curl -s -o /dev/null -w '%{http_code}' https://tu-dominio.com/docs   # debe ser 404
```

Ese último es la comprobación que se olvida: si `/docs` responde 200, el
`ENVIRONMENT` no está en `production` y estás publicando el esquema entero de tu
API.

## Notas

- **Un proceso por contenedor.** El `CMD` arranca un solo uvicorn a propósito:
  escalar es trabajo del orquestador, que sabe cuánta CPU hay. Varios workers
  dentro de un contenedor esconden el consumo real al panel.
- **Los assets se sirven desde la propia app.** Para tráfico alto, pon un CDN o
  un proxy con caché delante de `/static`.
