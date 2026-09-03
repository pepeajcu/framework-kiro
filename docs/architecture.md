# Arquitectura

## El flujo de una petición

Siempre el mismo, sin excepciones:

```
navegador
   ↓  GET /providers/flores-gt
router          app/routers/providers.py     entrada HTTP, delgada
   ↓
service         app/services/provider.py     reglas de negocio (si las hay)
   ↓
repository      app/repositories/provider.py ÚNICA capa que consulta la BD
   ↓
model           app/models/provider.py       tabla SQLAlchemy
   ↓
template        app/templates/pages/...      Jinja2
   ↓
HTML completo
```

Ninguna capa salta a otra. Un router no consulta la base de datos; un
repositorio no sabe qué es una petición HTTP.

## Por qué esta separación

No es ceremonia. Cada regla resuelve un problema concreto:

**Toda query en `repositories/`.** Las consultas repartidas por los routers no
se pueden reutilizar, ni testear aisladas, ni auditar cuando una resulta lenta.
Una sola capa significa un solo sitio donde mirar. `BaseRepository` ya trae
`get`, `list`, `count`, `create`, `update`, `delete` tipados; solo añades los
métodos de consulta propios de tu dominio.

**La transacción pertenece a la petición.** `app/db.py:get_db` abre la sesión,
hace commit si todo fue bien y rollback ante cualquier excepción. Si un router
hiciera commit a mitad, un fallo posterior dejaría media operación escrita.

**Solo `config.py` lee el entorno.** Un `os.getenv` disperso convierte cualquier
despliegue en una búsqueda a ciegas de qué variable falta.

**SSR siempre.** El SEO es un requisito permanente en los proyectos que usan
Kiro. El contenido debe estar en el HTML que envía el servidor, no inyectado
después por JavaScript.

## Estructura

```
app/
├── main.py            fábrica de la app, middlewares, manejadores de error
├── config.py          Settings — el único punto que lee el entorno
├── db.py              engine, sesión, get_db
├── deps.py            dependencias compartidas (DbSession, AppSettings)
├── exceptions.py      excepciones de dominio, sin acoplar a FastAPI
├── templating.py      Jinja2 configurado, helper render(), asset()
├── security.py        hashing argon2, tokens opacos, cookie de sesión
├── logs.py            logging estructurado (JSON desplegado, legible en local)
├── middleware/        request_id, cabeceras de seguridad, cookie CSRF
├── models/            tablas SQLAlchemy — base.py trae los mixins
├── repositories/      acceso a datos — base.py trae el CRUD genérico
├── services/          lógica de negocio
├── routers/           entrada HTTP
├── schemas/           validación Pydantic
├── emails/            correo transaccional — un adaptador por proveedor
├── templates/
│   ├── base.html      plantilla raíz: meta, OG, assets
│   ├── pages/         páginas completas
│   ├── partials/      fragmentos HTMX (NO extienden base.html)
│   ├── emails/        plantillas de correo (.html + .txt por mensaje)
│   ├── components/    componentes propios del proyecto
│   └── basecoat/      macros vendorizadas — no editar
└── static/
```

## Decisiones que sorprenden

Tres cosas contradicen lo que un desarrollador (o un modelo) asumiría:

1. **SQLAlchemy síncrono con FastAPI.** Los handlers son `def`, no `async def`;
   FastAPI los corre en un threadpool. Ver
   [ADR-0002](decisions/0002-sqlalchemy-sincrono.md).
2. **Cero Node.js**, incluso con Tailwind. Ver
   [ADR-0005](decisions/0005-sin-nodejs.md).
3. **Las variantes de los componentes son atributos `data-*`**, no clases.
   `<button class="btn" data-variant="primary">`, nunca `btn-primary`.

## Convenciones de base de datos

`app/models/base.py` fija dos cosas que rara vez se piensan a tiempo:

- **Convención de nombres de constraints.** Sin ella PostgreSQL inventa nombres,
  Alembic no distingue una constraint existente de una nueva, y las migraciones
  autogeneradas se llenan de drop/create espurios.
- **Claves UUIDv7.** Ordenadas temporalmente, así los inserts caen en el extremo
  derecho del índice B-tree en vez de dispersarse como con UUIDv4.

Ambas se definen una vez y no se cambian: modificarlas después haría
irreproducibles las migraciones ya escritas.
