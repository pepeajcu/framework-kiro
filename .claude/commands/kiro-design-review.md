---
description: Review a page you just built against DESIGN.md and the anti-slop rules by looking at it (screenshots at 375 and 1280 px), asking "does it look like the default template?", and fixing it in at most two passes
---

# Revisión de diseño

Corre esto después de construir o cambiar una página. No se puede juzgar un
diseño que no se ha visto: aquí lo ves, lo comparas con lo que el proyecto dijo
que quería, y lo corriges. **Máximo dos pasadas**: si tras la segunda quedan
cosas, las reportas en vez de dar vueltas.

Argumento opcional: las rutas a revisar (`/`, `/notes`…). Sin argumento, las
páginas cuyas plantillas cambiaron (`git diff --name-only -- app/templates`) más
`/_design`.

## 1. Prepara

1. Lee `DESIGN.md`, `design.toml` y `.claude/skills/kiro-design/SKILL.md`. Si
   `DESIGN.md` tiene `TODO`, para y pide `/kiro-init`: no hay contra qué revisar.
2. Corre `make design-check`. Un error ahí (contrato sin compilar, fuente que
   falta, atributo de motion por encima del nivel) se arregla **antes** de mirar
   nada: lo que verás no sería el diseño real.
3. Si cambiaste `design.toml`, `make design build`. Si cambiaste plantillas,
   `make css` (Tailwind descarta las clases que no ve).
4. Asegura que la app corre: `curl -s http://localhost:<APP_PORT>/health` (el
   puerto está en `.env`). Si no, `make dev` en segundo plano y espera a que
   responda. No levantes una segunda instancia si ya hay una.

## 2. Mira

Captura cada ruta a **1280×900** (escritorio) y **375×812** (móvil), y a la vez
el contenido bajo el primer pliegue. En este orden de preferencia:

1. **Claude in Chrome**, si está disponible *y llega al servidor*: abre la URL,
   redimensiona la ventana y haz capturas. Si el navegador está en otra máquina
   o red, dará "conexión rechazada": no insistas, pasa a la siguiente.
2. **Chrome/Chromium sin interfaz**, desde la terminal:

   ```bash
   google-chrome --headless=new --no-sandbox --hide-scrollbars --virtual-time-budget=3000 \
     --window-size=1280,900 --screenshot=/tmp/review-1280.png http://localhost:8000/
   google-chrome --headless=new --no-sandbox --hide-scrollbars --virtual-time-budget=3000 \
     --window-size=375,812  --screenshot=/tmp/review-375.png  http://localhost:8000/
   ```

   Esas dos son lo que ve una persona al llegar, que es donde se decide. Para el
   resto de la página, `--window-size=1280,3000` (ojo: las alturas `100dvh`
   crecen con la ventana, así que un hero a pantalla completa saldrá enorme).
   Con `design.toml` en `surface = "dark"` ya sale oscuro; si el proyecto tiene
   un selector de tema propio, captura también el otro modo.
3. **Pídele al usuario** que te pase capturas a esos dos anchos.

Mira las capturas de verdad (ábrelas), no te fíes de haber escrito el HTML.

## 3. Juzga

Contrasta con tres cosas, y anota cada hallazgo como ✗ (hay que arreglarlo),
! (conviene) o ✓.

**a) `DESIGN.md`.** ¿Aparece la **firma visual** en esta página (los 2-3 gestos)?
¿Se usan los arquetipos elegidos? ¿Coinciden estilo, tono y dials con lo que se
ve? ¿Se parece a algo de "lo que NO debe parecer"?

**b) La lista anti-slop de la skill** (`kiro-design`), en concreto: hero que cabe
en el primer pliegue con visual real; sin "tres tarjetas iguales"; una sola
escala de radios; un acento; tipografía local con carácter; estados de carga,
vacío y error; contraste; foco visible; sin emoji, sin em dashes, sin nombres de
relleno; sin color escrito a mano (solo tokens).

**c) La pregunta clave: ¿se parece a la plantilla por defecto?** Responde con
hechos, no con impresiones:

- ¿La cabecera es la `sticky-blur` gris de partida y el proyecto no la eligió?
- ¿Titular centrado + tres tarjetas iguales + botón? ¿El badge sobre el titular?
- ¿El fondo, el texto y los bordes son el gris neutro de Basecoat?
- ¿La fuente es la del sistema (no hay `[type]` en `design.toml`)?
- ¿Sale igual que `/` recién clonado, solo con otro color de botón?

Si dos o más son "sí", **converge con el default** y es un ✗: la causa suele
estar en la estructura (arquetipo, layout, cabecera), no en el color.

Revisa también a 375 px: nada se desborda en horizontal, las columnas caen a una,
los objetivos táctiles miden al menos 44 px, el hero no empuja la acción fuera
del primer pliegue.

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

**No toques**: la lógica de sesión (`partials/nav_auth.html`), las rutas, los
formularios (`csrf_field`), los atributos de HTMX, ni lo vendorizado
(`app/static/css/vendor/`, `app/templates/basecoat/`). No añadas JavaScript por
página. No superes el nivel de motion del proyecto sin pedirlo: si hace falta,
se sube en `design.toml` y se dice.

Tras corregir: `make design build` si tocaste el contrato, `make css`, y
**vuelve a capturar**.

## 5. Repite una vez, y cierra

Segunda pasada: vuelve a juzgar solo lo que cambió y lo que quedó ✗. Después
corre `make design-check` y `make check` y presenta:

- Lo que encontraste y lo que cambiaste, en pocas líneas.
- Las capturas finales (rutas de los archivos).
- Lo que **no** se pudo resolver en dos pasadas y por qué, para que decida el
  usuario. No sigas iterando por tu cuenta.

No hagas commit: eso lo decide quien revisa.
