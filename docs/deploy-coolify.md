# Desplegar en Coolify / Dokploy

Kiro trae un `Dockerfile` multi-etapa con etapa `production`: imagen mínima,
usuario sin privilegios y `HEALTHCHECK` propio. Coolify y Dokploy lo consumen
directamente.

El despliegue son **dos servicios**: la aplicación (esta imagen) y una **base PostgreSQL del
panel, aparte**. No metas la base dentro de la pila de la app: así tiene respaldos
programados y vive aparte de ella. Al arrancar, la imagen aplica sola las migraciones y el
seed (ADR-0024): no hay pasos manuales.

## 1. Base de datos

Crea un PostgreSQL desde el panel (Coolify: *New Resource → Database →
PostgreSQL*; Dokploy: *Create Service → Database → PostgreSQL*). Usa una contraseña solo
con letras y números. Apunta la cadena de conexión **interna** (en Dokploy, *Internal
Credentials → Internal Host*): la app y la base viven en la misma red, así que el tráfico
no sale a internet. **Activa los respaldos programados** de ese servicio (S3/R2): sin ellos,
perder el volumen es perder los datos.

## 2. Aplicación

*New Resource → Application → Dockerfile*, apuntando a tu repositorio.

- **Dockerfile Target:** `production` — importante. Sin esto construye la última
  etapa, que no siempre es la que quieres.
- **Port:** `8000` — también en **cada dominio**. Un puerto distinto (3000, 8011…) da
  502 aunque la app esté sana.
- **Health Check Path:** `/health`

## 3. Variables de entorno

Configúralas en el panel, nunca en el repositorio. **Una por línea, sin comillas ni
comentarios**, y **pulsa Deploy después de guardarlas**: cambiarlas no hace nada hasta el
siguiente despliegue. Las mínimas:

```
APP_NAME=Nombre del proyecto
ENVIRONMENT=production
SECRET_KEY=<openssl rand -hex 32 — uno NUEVO, no el de desarrollo>
DATABASE_URL=postgresql+psycopg://usuario:clave@nombre-servicio-db:5432/basedatos
ADMIN_EMAIL=admin@tu-dominio.com
ADMIN_PASSWORD=<12 o más caracteres>
ALLOW_REGISTRATION=false
BASE_URL=https://tu-dominio.com
LOG_LEVEL=INFO
```

Y las de correo y analítica que use el proyecto (`EMAIL_PROVIDER`,
`RESEND_API_KEY`, `GTM_ID`…).

Cuatro cosas que importan de verdad:

- **`DATABASE_URL` con `postgresql+psycopg://`.** Con `postgresql://` SQLAlchemy busca otro
  driver y la app no conecta. El host es el del servicio de la base, nunca `127.0.0.1`.

- **`SECRET_KEY` distinta a la de desarrollo.** Reutilizarla significa que
  cualquiera con acceso a tu `.env` local puede falsificar sesiones en producción.
- **`ENVIRONMENT=production`** oculta `/docs` y `/openapi.json`, y activa las
  cookies seguras.
- **`BASE_URL` con el dominio real.** Se usa para construir los enlaces de los
  correos y el `sitemap.xml`, donde no hay petición de la que deducir el host.

## 4. Migraciones y seed

El `CMD` de la imagen ejecuta `alembic upgrade head` y `python -m scripts.seed` antes de
arrancar uvicorn (ADR-0024). Las dos son idempotentes: cada despliegue deja la base al día
y crea el administrador de `ADMIN_EMAIL`/`ADMIN_PASSWORD` sin tocar la contraseña de una
cuenta que ya existe. Si la migración falla, el contenedor no arranca y el error sale en
los **Logs**.

**Con más de una réplica**, varios contenedores arrancando a la vez migrarían en paralelo.
Entonces cambia el `CMD` de la imagen a solo uvicorn y ejecuta
`alembic upgrade head` como comando previo al despliegue (Coolify: *Application → Advanced →
Pre-deployment Command*).

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

## Si sale 502 (Bad Gateway)

1. **Logs del servicio.** El error nombra lo que falta (`secret_key Field required`,
   `password authentication failed`, `connection refused`…).
2. **¿Llegaron las variables?** En Dokploy, en el servidor, solo los nombres:
   `docker service inspect <app-name> --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}' | cut -d= -f1`
   Una lista vacía significa que el servicio no recibió ninguna: guarda y pulsa **Deploy**.
3. **Dominios:** todos al puerto `8000`.
4. **`DATABASE_URL`:** con `+psycopg` y el host interno de la base.

## Si la app guarda archivos

Un directorio de subidas (logos, imágenes) es de root en la imagen y el usuario `app` no
puede escribir: la subida falla con `permission denied`. En el `Dockerfile`, antes de
`USER app`, crea la carpeta con su dueño y monta un volumen del panel en esa ruta; sin
volumen, los archivos se pierden en cada despliegue:

```dockerfile
RUN mkdir -p /srv/var/uploads && chown -R app:app /srv/var
```

Mejor aún, guárdalos en un almacenamiento de objetos (R2/S3) detrás de una interfaz.

## Notas

- **Un proceso por contenedor.** El `CMD` arranca un solo uvicorn a propósito:
  escalar es trabajo del orquestador, que sabe cuánta CPU hay. Varios workers
  dentro de un contenedor esconden el consumo real al panel.
- **Los assets se sirven desde la propia app.** Para tráfico alto, pon un CDN o
  un proxy con caché delante de `/static`.
