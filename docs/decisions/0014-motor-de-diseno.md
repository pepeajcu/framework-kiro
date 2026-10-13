# 0014 — Motor de diseño: `design.toml`, compilador, layouts y percepción

**Estado:** Aceptada · 2026-10-13

## Contexto

El ADR-0013 dio a cada proyecto una identidad (`DESIGN.md`, `make brand-colors`,
`make logo`), pero el pipeline era **con pérdida y no generativo**:

1. De unos treinta tokens de Basecoat solo cambiaban tres (`--primary`,
   `--primary-foreground`, `--ring`). Fondo, texto, `card`, `muted`, `border`,
   `secondary` y `accent` seguían en el gris neutro, que es el 80 % de los
   píxeles de una página: cualquier cambio de estructura se leía igual de gris.
2. `base.html` encerraba todo en `max-w-5xl`, con una cabecera y un pie únicos, y
   `home.html` ("badge + titular + rejilla de tarjetas") era el ejemplo vivo que
   la IA imitaba en cada página nueva.
3. La IA nunca veía lo que producía: el primer borrador, el más genérico, era el
   que quedaba.

Dos proyectos pedidos a una IA, con la misma intención, salían iguales. La
diversidad no se arregla con "más temas", sino con tres propiedades que faltaban:
una superficie paramétrica amplia, selección generativa por proyecto y
verificación perceptual.

## Decisión

1. **`design.toml` es el contrato de máquina; `DESIGN.md` el brief humano.** El
   primero tiene lo que se puede compilar (color, neutros, superficie, radio,
   fuentes, tema de Basecoat, cabecera, nivel de motion); el segundo, lo que hay
   que decidir (tono, referencias, dials, arquetipos y la **firma visual**).
   `make design-check` valida que no se contradigan.
2. **Un compilador puro** en `app/design_engine/` (tipado con `mypy --strict`,
   testeado), con el I/O en `scripts/`. Deriva la paleta completa en OKLCH, claro
   y oscuro, y la escribe en **bloques delimitados e idempotentes** de `input.css`
   (`kiro:theme`, `kiro:brand`, `kiro:fonts`), el patrón que ya usaba
   `make brand-colors`. `make design build` lo aplica todo; `make brand-colors` y
   `make font` pasan a ser atajos que escriben `design.toml` y recompilan.
3. **El contraste se resuelve, no se comprueba a posteriori.** Los grises de texto
   parten del valor de Basecoat y se mueven solo lo necesario hasta cumplir WCAG AA
   contra cada fondo donde se usan. El texto del botón se elige midiendo el color
   que de verdad se emite (`oklch(0.985)` no es blanco puro). Si un color de marca
   no puede llevar la etiqueta del botón, el compilador se niega y propone el hex
   más cercano que sí.
4. **Estructura sin prior fijo.** `base.html` se queda con el esqueleto y expone
   `header`, `main` y `footer`. `layouts/app.html` (contenedor, pantallas
   privadas) y `layouts/landing.html` (a sangre) deciden el ancho. La cabecera es
   un arquetipo elegido en `design.toml` (`partials/headers/`), y la lógica de
   sesión vive aparte en `partials/nav_auth.html`, así que reescribir lo visual no
   puede romper el cierre de sesión. `home.html` y el ejemplo de `kiro-feature`
   son andamio explícito.
5. **Varianza.** Los presets de estilo cambian todos los ejes a la vez (tema,
   radio, neutros, superficie, fuentes, cabecera, motion) para que un relleno
   perezoso ya caiga lejos del default. Los catálogos (`archetypes.md`,
   `type-pairings.md`, referencias de estilo) son recetas en Markdown que la
   skill lee bajo demanda: crecen con texto, sin código. La **firma visual** de
   `DESIGN.md` es obligatoria y no sale de ningún catálogo.
6. **Percepción.** `/_design` (solo desarrollo; no existe en producción) enseña
   tokens con su contraste, escala tipográfica, componentes, un hero de prueba,
   claro y oscuro, y el vocabulario de motion del nivel. `/kiro-design-review`
   captura a 375 y 1280 px y contrasta con `DESIGN.md` y la pregunta "¿se parece
   al default?"; `/kiro-redesign` hace lo mismo con una app ya construida.
7. **`surface = "dark"` significa "solo oscuro".** El compilador pone la paleta
   oscura en `:root` y la plantilla añade `class="dark"` a `<html>`. Las apps
   finales no ofrecen selector de tema (convención del plan).

## Por qué así

- **Bloques delimitados en vez de editar `input.css` a mano.** El comando es
  idempotente, no pisa lo que el proyecto escriba fuera de los marcadores y deja
  un único lugar donde la máquina escribe. El estado del motor está en
  `design.toml`; actualizar es `make upgrade` + `make design build`.
- **Un `.dark` que re-mapea `--color-*`.** Basecoat declara
  `--color-background: var(--background)` en `:root`, y una propiedad con `var()`
  se resuelve donde se declara: un `<section class="dark">` dentro de una página
  clara heredaba el color claro ya resuelto. Re-declarar el mapeo bajo `.dark`
  hace que cualquier banda oscura funcione, que es justo lo que una web clara
  necesita para tener un hero o un pie oscuros. Lo encontró una captura de
  `/_design`, no la lectura del CSS.
- **El runtime lee `design.toml`** (cabecera, superficie oscura, scripts de motion,
  precarga). Los tokens siguen siendo CSS estático, sin coste en ejecución; pero
  qué cabecera se incluye es una decisión de *marcado* que solo una plantilla
  puede tomar. En desarrollo se relee al cambiar el archivo; en producción se
  resuelve una vez; un archivo roto cae a los valores por defecto con un aviso en
  el log, nunca tumba la página.
- **Sin starters por preset.** Cinco homes precocinados son una tienda de
  plantillas: el problema original con otro disfraz. Los presets son contratos,
  no páginas.
- **Fontsource y woff2 locales.** La CSP es `font-src 'self'` (ADR-0010) y no hay
  CDN (ADR-0005). Cada fuente se valida por la firma `wOF2` y por la longitud que
  declara su propia cabecera, y `make font` comprueba contra la API de Fontsource
  que la familia y los pesos existen. Satoshi, Cabinet Grotesk y General Sans (que
  recomendaban las skills de taste-skill) no están en Fontsource.

## Descartado

- **Overrides de tokens por página** vía `render()`: toca el núcleo para un valor
  marginal; un proyecto es una identidad.
- **Cambiar el default de `vega` a `nova`**: es cosmético; el default debe empujar
  a correr `/kiro-init`, no a verse "más agencia" sin configurar nada.
- **Un compilador en Node** (PostCSS, Style Dictionary): ADR-0005.

## Consecuencias

- Archivos nuevos: `design.toml`, `app/design_engine/`, `app/routers/design.py`,
  `scripts/{design,font,motion,fetch}.py`, `layouts/`, `partials/headers/`. El
  `Dockerfile` copia `design.toml` a la imagen de producción.
- El `design.toml` que se distribuye está en los valores por defecto, a propósito:
  `make design-check` lo marca en rojo ("converge con cualquier otro Kiro"). No
  forma parte de `make check`, para que el framework en sí no falle.
- Los atajos reescriben `design.toml` en formato canónico: un comentario propio
  dentro de ese archivo no sobrevive. La prosa va en `DESIGN.md`.
- Un color de marca que no pase AA con el texto del botón ya no solo avisa: el
  build falla con una sugerencia. Es más estricto que `make brand-colors` en 1.1.
- Las 11 identidades (6 existentes más `editorial`, `organico`, `neo-brutalista`,
  `retro-y2k`, `oscuro-tecnologico`) tienen preset y referencia; añadir otra es un
  preset en `presets.py`, una referencia `.md` y una fila en la skill (un test
  vigila que las tres coincidan).
- Uso del tema de Basecoat: ocho temas, con diferencias reales de forma (medidas
  del CSS vendorizado), que son la palanca individual más fuerte sobre cómo se
  sienten los componentes.
