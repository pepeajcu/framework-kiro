# __KIRO_PROJECT_NAME__

__KIRO_PROJECT_DESCRIPTION__

Construido con [Kiro](https://github.com/pepeajcu/framework-kiro): Python · FastAPI · HTMX · PostgreSQL,
renderizado en servidor de principio a fin.

---

## Arrancar

```bash
make up        # levanta PostgreSQL
make migrate   # aplica el esquema
make dev       # http://localhost:8000
```

`./setup.sh` ya dejó todo esto configurado. Si es la primera vez que clonas el
proyecto en una máquina nueva, copia `.env.example` a `.env` y rellena los
valores que te pase quien lo configuró.

## Comandos

```bash
make help      # lista todo lo disponible
make check     # lint + tipos + tests + migraciones — es lo que corre CI
make revision m="añade tabla de proveedores"   # nueva migración
make css       # recompila Tailwind
```

## Cómo está organizado

```
app/
├── routers/       ← entrada HTTP. Devuelven HTML, no JSON.
├── services/      ← lógica de negocio
├── repositories/  ← ÚNICA capa que habla con la base de datos
├── models/        ← tablas (SQLAlchemy)
├── schemas/       ← validación de entrada/salida (Pydantic)
└── templates/     ← Jinja2 + HTMX. Componentes en templates/basecoat/
```

El flujo de una petición es siempre el mismo:
`router → service → repository → modelo → plantilla Jinja → HTML`.

## Trabajar con IA en este proyecto

Este proyecto está preparado para que un agente (Claude Code, OpenCode, Codex)
produzca código correcto sin que tengas que explicarle la arquitectura cada vez.

1. **`AGENTS.md`** — las reglas del stack y las convenciones. Ya está escrito.
2. **`PROJECT.md`** — tu dominio de negocio. **Rellénalo antes de pedir la
   primera feature.** Es lo único que impide que la IA se invente tus entidades.
3. **`.claude/skills/`** — recetas paso a paso para las tareas habituales
   (añadir una feature, un componente, una migración).

Para una feature normal basta con pedirla. Para algo grande, usa el flujo de
especificación: `/spec-new`, `/spec-design`, `/spec-tasks`, `/spec-build`.

## Despliegue

Ver [`docs/deploy-coolify.md`](docs/deploy-coolify.md).

## Licencia

Ver [`LICENSE`](LICENSE).
