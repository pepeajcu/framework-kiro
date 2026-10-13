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
app/design_engine/          app/templates/layouts/
scripts/design.py  scripts/font.py  scripts/motion.py  scripts/fetch.py
app/static/js/motion*.js    app/static/css/motion.css
```

**Revisar con cuidado** — casi seguro que los personalizaste:

```
app/templates/base.html     app/static/css/input.css
app/templates/emails/       Makefile            compose.yml
AGENTS.md                   app/templates/partials/headers/  (sobre todo custom.html)
```

**Nunca traer:**

```
PROJECT.md    tu dominio de negocio
DESIGN.md     tu identidad: estilo, firma visual, arquetipos
design.toml   tu contrato de diseño (colores, fuentes, tema, cabecera, motion)
.env          tus secretos
app/models/   tus modelos, salvo base.py
migrations/   tu historial de esquema
app/static/fonts/   tus fuentes (las instala make design build)
app/static/brand/   tu logo
```

## Actualizar el motor de diseño

La identidad de un proyecto vive en **`design.toml` y en los bloques `kiro:*` de
`input.css`**, no en ediciones sueltas. Eso hace que traer mejoras del motor sea
mecánico:

```bash
make upgrade                                   # qué hay de nuevo
git checkout upstream/main -- app/design_engine/ scripts/ app/templates/layouts/ \
    app/templates/partials/ app/static/js/motion.js app/static/js/motion-lib.js \
    app/static/js/motion-gsap.js app/static/css/motion.css
make design build                              # re-sintetiza la identidad desde design.toml
make design-check                              # y comprueba que coincide
make check
```

`make design build` es idempotente: reescribe los bloques generados a partir de
tu `design.toml`, descarga lo que falte (fuentes, librerías de motion) y deja
intacto lo que escribiste fuera de los bloques. Si el motor añadió una clave
nueva al contrato, tu `design.toml` sigue siendo válido (las claves nuevas
tienen valor por defecto); `make design-check` te avisa de lo que convenga
decidir.

Cuidado con dos cosas al traer `partials/`: si tu cabecera es `custom`, no
sobrescribas `partials/headers/custom.html`; y si reescribiste `header.html` o
`footer.html` a mano, compara antes (la lógica de sesión vive en
`nav_auth.html`, que sí conviene traer).

Un proyecto creado **antes** de que existiera el motor (v1.1 o anterior) no
tiene `design.toml`. Trae los archivos de arriba, `design.toml` y `DESIGN.md`
(si no tienes uno propio), y **fusiona a mano** los pocos archivos que son tuyos
pero cambiaron (compara con `git diff HEAD upstream/main -- <archivo>`):

| Archivo | Qué cambió |
|---|---|
| `app/templates/base.html` | los huecos `header`, `main`, `footer`; la clase `dark`; precarga de fuentes y scripts de motion |
| `app/main.py` | registra `routers/design.py` si `settings.design_preview_enabled` |
| `app/config.py` | el ajuste `design_preview` |
| `Makefile` | los comandos `design`, `font`, `motion`, `brand-colors` ampliado |
| `Dockerfile` | `COPY design.toml` en la etapa de producción |
| `pages/*.html` | extienden `layouts/app.html` en vez de `base.html` |

Después, `make brand-colors primary="#tu-color"` crea `design.toml` y migra tu
bloque `kiro:brand` de tres variables al completo, y `make design-check` dice
qué falta.

## Actualizar Basecoat o HTMX

Van por su propia vía, independiente del framework. Ver [`vendor.md`](vendor.md).

## Si el proyecto se separó mucho

Cuando llevas muchos cambios propios, traer archivo por archivo deja de
compensar. Lo pragmático entonces es leer el diff del framework, entender qué
resuelve, y aplicar la idea a mano sobre tu código. El `CHANGELOG.md` está
escrito para que eso sea posible sin leer el código entero.
