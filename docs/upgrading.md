# Traer mejoras del framework a un proyecto existente

Kiro se distribuye con `git clone`, así que un proyecto creado hoy **no recibe
automáticamente** los arreglos que se hagan al framework mañana. Es el coste
aceptado de este modelo de distribución
([ADR-0003](decisions/0003-git-clone-sobre-plantillas.md)). Esto es lo que sí se
puede hacer.

## Requisito: el remote `upstream`

Si creaste el proyecto con `./setup.sh --git-mode upstream`, ya está listo. Si
no:

```bash
git remote add upstream https://github.com/pepeajcu/framework-kiro.git
```

## Ver qué hay disponible

```bash
make upgrade
```

Hace `git fetch upstream` y muestra qué cambió en las rutas que pertenecen al
framework. Antes de traer nada, lee el changelog:

```bash
git show upstream/main:CHANGELOG.md | head -60
```

Cada entrada lleva una etiqueta:

- **`[SEGURO]`** — se puede traer tal cual.
- **`[MIGRACIÓN]`** — necesita pasos manuales, descritos en la propia entrada.
- **`[RUPTURA]`** — cambia contratos existentes. Léelo entero antes de tocar nada.

## Traer un cambio concreto

Rutas específicas, nunca un merge completo:

```bash
git checkout -b traer-mejoras-kiro
git checkout upstream/main -- app/middleware/csrf.py
make check
git commit -m "chore: traer CSRF de Kiro v0.2.0"
```

## Qué se puede traer y qué no

**Seguro de traer** — archivos que el framework posee y que los proyectos rara
vez editan:

```
app/repositories/base.py    app/middleware/    app/emails/providers/
app/models/base.py          app/templating.py  app/db.py
.claude/skills/             .claude/commands/  Dockerfile
```

**Revisar con cuidado** — casi seguro que los personalizaste:

```
app/templates/base.html     app/static/css/input.css
app/templates/emails/       Makefile            compose.yml
AGENTS.md
```

**Nunca traer:**

```
PROJECT.md    tu dominio de negocio
.env          tus secretos
app/models/   tus modelos, salvo base.py
migrations/   tu historial de esquema
```

## Actualizar Basecoat o HTMX

Van por su propia vía, independiente del framework. Ver [`vendor.md`](vendor.md).

## Si el proyecto se separó mucho

Cuando llevas muchos cambios propios, traer archivo por archivo deja de
compensar. Lo pragmático entonces es leer el diff del framework, entender qué
resuelve, y aplicar la idea a mano sobre tu código. El `CHANGELOG.md` está
escrito para que eso sea posible sin leer el código entero.
