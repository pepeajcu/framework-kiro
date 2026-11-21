---
description: Review a page you just built against DESIGN.md, uupm's UX guidance and the anti-slop rules by looking at it (screenshots at 375, 768, 1024 and 1440 px), one report ordered by priority, fixing in at most two passes unless the floor fails
---

# Revisión de diseño

Corre esto después de construir o cambiar una página. No se puede juzgar un
diseño que no se ha visto: aquí lo ves, lo comparas con lo que el proyecto dijo
que quería y con lo que la guía de UX exige, y lo corriges.

**Cómo se cierra.** Hay dos clases de hallazgo y no se tratan igual:

- **El suelo** (accesibilidad, uso táctil, rendimiento y las leyes del stack: categorías
  1 a 3 de `references/constitution.md`). Un ✗ aquí **bloquea** y no tiene límite de
  pasadas: no se da por terminada la tarea con el suelo roto. Casi todo está ya en
  `make check`.
- **El gusto** (estilo, composición, tipografía, movimiento, navegación). **Máximo dos
  pasadas**; lo que siga ✗ después se te escala al usuario con opciones. Lo que decida
  se anota en `DESIGN.md`, en *Decisiones de diseño*, para no volver a preguntarlo.

Argumento opcional: las rutas a revisar (`/`, `/notes`…). Sin argumento, las
páginas cuyas plantillas cambiaron (`git diff --name-only -- app/templates`) más
`/_design`.

## 1. Prepara

1. Lee `DESIGN.md`, `design.toml` y `.claude/skills/kiro-design/SKILL.md`. Si
   `DESIGN.md` tiene `TODO`, para y pide `/kiro-init`: no hay contra qué revisar.
2. Corre `make check`. Un fallo (arquitectura, suelo de UX, contrato sin compilar,
   fuente que falta) se arregla **antes** de mirar nada: lo que verás no sería el
   diseño real.
3. Si cambiaste `design.toml`, `make design build`. Si cambiaste plantillas,
   `make css` (Tailwind descarta las clases que no ve).
4. Asegura que la app corre: `curl -s http://localhost:<APP_PORT>/health` (el
   puerto está en `.env`). Si no, `make dev` en segundo plano y espera a que
   responda. No levantes una segunda instancia si ya hay una.

## 2. Mira

Captura cada ruta a **375×812** (móvil), **768×1024**, **1024×768** y **1440×900**: son
los cuatro anchos de la guía de uupm. Si la superficie es `auto`, captura también en
oscuro. En este orden de preferencia:

1. **Claude in Chrome**, si está disponible *y llega al servidor*: abre la URL,
   redimensiona la ventana y haz capturas. Si el navegador está en otra máquina
   o red, dará "conexión rechazada": no insistas, pasa a la siguiente.
2. **Chrome/Chromium sin interfaz**, desde la terminal:

   ```bash
   for size in 375,812 768,1024 1024,768 1440,900; do
     google-chrome --headless=new --no-sandbox --hide-scrollbars --virtual-time-budget=3000 \
       --window-size=$size --screenshot=/tmp/review-${size%,*}.png http://localhost:8000/
   done
   ```

   Para el resto de la página, `--window-size=1280,3000` (ojo: las alturas `100dvh`
   crecen con la ventana, así que un hero a pantalla completa saldrá enorme).
   Con `design.toml` en `surface = "dark"` ya sale oscuro. Para el modo táctil
   (`pointer: coarse`) hace falta el protocolo DevTools con emulación táctil.
3. **Pídele al usuario** que te pase capturas a esos anchos.

Mira las capturas de verdad (ábrelas), no te fíes de haber escrito el HTML.

## 3. Juzga: una sola lista, ordenada por categoría

Haces **tres pasadas sobre las mismas capturas** y las vuelcas en **un único informe**
ordenado por la prioridad de uupm (1 accesibilidad, 2 táctil, 3 rendimiento, 4 estilo,
5 layout, 6 tipografía y color, 7 animación, 8 formularios, 9 navegación, 10 datos).
Cada línea lleva: **id de regla** (`D1`, `P3`...; o el nombre del criterio si no tiene),
**dueño** (uupm, taste o contrato), **✗** (hay que arreglarlo), **!** (conviene) o **✓**,
la **evidencia** (qué ves, en qué ruta y ancho) y **dónde se arregla**.

**Pasada uupm (UX).** Consulta lo que toca al producto de `PROJECT.md`:
`make design-ux q="<la página que revisas>" domain=ux`, y los `Anti-patrones` de la
propuesta de uupm si la hay (`.design/proposals/*.md`). Comprueba: estados de carga, vacío
y error; errores de formulario junto al campo; foco visible en todo lo que se pulsa;
objetivos táctiles de 44 px a 375 px; nada que desborde en horizontal; jerarquía de
encabezados; que lo clicable lo parezca; transiciones de 150 a 300 ms; contraste.

**Pasada taste (personalidad).**

- **a) `DESIGN.md`.** ¿Aparece la **firma visual** en esta página (los 2-3 gestos)?
  ¿Se usan los arquetipos elegidos? ¿Coinciden estilo, tono y dials con lo que se
  ve? ¿Se parece a algo de "lo que NO debe parecer"?
- **b) La lista anti-slop de `kiro-design`**: hero que cabe en el primer pliegue con
  visual real; una sola escala de radios; un acento; tipografía local con carácter; sin
  emoji, sin em dashes, sin nombres de relleno; sin color escrito a mano (solo tokens).
- **c) Patrones genéricos `P1` a `P10`.** `make design-check` ya los detecta; aquí se
  confirman mirando. Cada uno es ✗ salvo que `[rules] allow` de `design.toml` lo
  permita (y entonces `DESIGN.md` debe decir por qué).
- **d) La pregunta clave: ¿se parece a la plantilla por defecto?** Responde con
  hechos: ¿la cabecera es la `sticky-blur` gris de partida y el proyecto no la eligió?
  ¿titular centrado + tres tarjetas iguales + botón? ¿el fondo, el texto y los bordes
  son el gris neutro de Basecoat? ¿la fuente es la del sistema? ¿sale igual que `/`
  recién clonado, solo con otro color de botón? Con dos o más "sí" **converge con el
  default** y es un ✗: la causa suele estar en la estructura, no en el color.

**Pasada del kit** (solo si `[structure] kit` de `design.toml` no es `none`): lo que el
kit exige de plataforma (para `ios`, las medidas de Apple HIG: barras con material solo en
la capa de navegación, 44 pt, márgenes de 16 y 20 px, texto base de 17 px).

**Si dos criterios chocan**, no preguntes: la tabla de `references/constitution.md`
dice quién gana. Solo lo que no esté resuelto allí se pregunta al usuario, una vez.

## 4. Corrige

Arregla lo ✗ primero, luego lo !. Dónde:

| El problema es de… | Se arregla en… |
|---|---|
| Color, grises, superficie, radio | `design.toml` (`make brand-colors`, `make design-set`) |
| Fuentes | `make font` |
| Cómo se sienten los componentes | `[basecoat] theme` |
| La forma de la cabecera | `[structure] header`, o `partials/headers/custom.html` |
| La estructura de la página | la plantilla: otro arquetipo de `references/archetypes.md` |
| Falta de personalidad | la firma visual: aplícala de verdad en la página |
| Movimiento | atributos `data-motion`, dentro del nivel del proyecto |
| Un patrón genérico que el proyecto quiere de verdad | `make design-set v="rules.allow=P1"` y una línea en *Decisiones de diseño* |

**No toques**: la lógica de sesión (`partials/nav_auth.html`), las rutas, los
formularios (`csrf_field`), los atributos de HTMX, ni lo vendorizado
(`app/static/css/vendor/`, `app/templates/basecoat/`, `.claude/skills/kiro-design/uupm/`).
No añadas JavaScript por página. No superes el nivel de motion del proyecto sin
pedirlo: si hace falta, se sube en `design.toml` y se dice. **El suelo no se relaja**:
ni con `[rules] allow` ni porque el usuario lo pida sin haber leído esto; si de verdad
quiere un contraste menor, díselo y que decida por escrito.

Tras corregir: `make design build` si tocaste el contrato, `make css`, y
**vuelve a capturar**.

## 5. Repite y cierra

Segunda pasada: vuelve a juzgar solo lo que cambió y lo que quedó ✗. Después corre
`make design-check` y `make check` y presenta el **informe único**:

- Lo que encontraste y lo que cambiaste, ordenado por categoría.
- Las capturas finales (rutas de los archivos).
- Lo que **no** se pudo resolver, para que decida el usuario con las opciones a la vista.
  Esto vale para el **gusto**: no sigas iterando por tu cuenta. Si lo que queda es del
  **suelo**, no cierres: arréglalo, aunque haga falta una tercera pasada.

No hagas commit: eso lo decide quien revisa.
