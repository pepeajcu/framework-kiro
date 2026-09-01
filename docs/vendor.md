# Dependencias vendorizadas

Kiro copia estas librerías al repositorio en vez de consumirlas desde npm o un
CDN. El porqué está en [ADR-0004](decisions/0004-basecoat-en-vez-de-portar-shadcn.md)
y [ADR-0005](decisions/0005-sin-nodejs.md); en resumen: cero Node.js, cero
peticiones a terceros que bloqueen el render, y componentes que son tuyos y
puedes editar.

| Librería | Versión | Licencia | Origen |
|---|---|---|---|
| [Basecoat](https://basecoatui.com) | 1.0.2 | MIT | `basecoat-css` en npm |
| [HTMX](https://htmx.org) | 2.0.10 | 0BSD | `htmx.org` en npm |

## Dónde vive cada cosa

```
app/static/css/vendor/basecoat/   CSS fuente que compila Tailwind
├── base/                         reset y variables
├── components/                   un archivo por componente
├── styles/                       los 8 temas (vega, nova, maia, lyra…)
└── basecoat-<tema>.css           punto de entrada de cada tema

app/static/js/vendor/
├── basecoat.min.js               los 11 componentes que necesitan JS
└── htmx.min.js

app/templates/basecoat/*.jinja    macros de los componentes complejos
```

Solo 9 componentes tienen macro Jinja (select, dialog, combobox, command,
popover, dropdown-menu, sidebar, tabs, toast). El resto —botones, tarjetas,
badges, inputs, tablas, alertas— son **solo clases CSS**: se escriben
directamente en el HTML, sin macro.

## Cambiar de tema

Edita la línea del tema en `app/static/css/input.css` y recompila con `make css`:

```css
@import "./vendor/basecoat/basecoat-nova.css";   /* vega | nova | maia | lyra | mira | luma | sera | rhea */
```

## Actualizar Basecoat

**Antes de actualizar:** si editaste algún archivo dentro de `vendor/`, tus
cambios se pierden. La forma correcta de personalizar es sobreescribir en
`app/static/css/input.css` o en `app/templates/components/`, nunca tocando
`vendor/`.

```bash
VERSION=1.1.0
curl -sL "https://registry.npmjs.org/basecoat-css/-/basecoat-css-$VERSION.tgz" | tar xz
cp -r package/dist/{base,components,styles} app/static/css/vendor/basecoat/
find package/dist -maxdepth 1 -name '*.css' ! -name '*.cdn*' \
  -exec cp {} app/static/css/vendor/basecoat/ \;
cp package/dist/js/all.min.js app/static/js/vendor/basecoat.min.js
cp package/templates/jinja/*.jinja app/templates/basecoat/
rm -rf package
make css && make dev   # revisa visualmente antes de commitear
```

Actualiza después la tabla de versiones de arriba.

## Actualizar HTMX

```bash
curl -sL https://cdn.jsdelivr.net/npm/htmx.org@2.0.11/dist/htmx.min.js \
  -o app/static/js/vendor/htmx.min.js
```

HTMX 2.x es estable en su API. Antes de saltar a una major, lee sus notas de
migración: los atributos `hx-*` son la superficie de toda la interactividad del
proyecto.
