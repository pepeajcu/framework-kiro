# Kiro Design Engine — propuesta de ingeniería y plan final

> **Estado:** implementado el 2026-10-13 (v0.1 a v1.0 del plan, en un solo
> paso). Ver [«Informe de implementación»](#informe-de-implementación) al final:
> qué se hizo tal cual, en qué se apartó la implementación del plan y por qué.
> Sustituye a `docs/plan-diseno.md` como plan de referencia (aquella
> consolidación de los tres análisis es el insumo; este documento es el
> diseño del sistema que la ejecuta).
>
> **Punto de retorno:** commit `61b882f`, el estado anterior a la implementación.
> Para volver: `git reset --hard 61b882f` (descarta TODO lo implementado).
>
> **Convención confirmada:** "personalizable por el cliente" = el
> desarrollador que usa Kiro para construir su proyecto, vía `/kiro-init`,
> `make` y `design.toml`. Las apps finales NO ofrecen selectores de tema a
> sus usuarios.

---

## 1. El problema, formalizado

El pipeline actual de identidad es **con pérdida y no generativo**:

```
intención del cliente ──► DESIGN.md (prosa) ──► 3 variables CSS + logo
                                                ↑
                       cuello de botella: app/branding.py:227 (brand_tokens)
                       solo deriva --primary, --primary-foreground y --ring
```

Tres defectos estructurales, verificados en el código:

1. **Cuello de botella de tokens.** De ~20 tokens de Basecoat, solo cambian
   3. Fondo, texto, `card`, `muted`, `border`, `secondary`, `accent` quedan
   congelados en el gris neutro. Cualquier cambio de estructura se sigue
   leyendo gris: el fondo y el texto son el 80 % de los píxeles de una página.
2. **Prior estructural fijo.** `app/templates/base.html:85` encierra todo en
   `max-w-5xl`; el header sticky-blur y el footer de una línea se heredan
   siempre; `home.html` ("badge + h1 + grid de cards") es el ejemplo vivo que
   la IA imita en cada página nueva. El espacio de diseño de la IA colapsa
   por imitación del ejemplo, no por incapacidad.
3. **Sin señal de feedback.** La IA nunca ve lo que produce. El primer
   borrador — el más genérico — es el que queda.

**Conclusión de ingeniería.** La diversidad no se consigue con "más temas",
sino dando al sistema tres propiedades que hoy no tiene:

| Propiedad | Significado |
|---|---|
| **Superficie paramétrica amplia** | Muchos ejes independientes de personalización, no 3 variables |
| **Selección generativa** | Arquetipos y firma visual elegidos por proyecto, no un default fijo |
| **Verificación perceptual** | Medir que la salida no se parece al default, y corregir si sí |

---

## 2. Principios del motor

1. **Generativo, no enlatado.** Se descartan starters precocinados por preset:
   una tienda de plantillas es el problema original con otro disfraz, y cinco
   homes fijos son cinco cosas que mantener y volver a imitar. Los catálogos
   del motor son *recetas*; la composición la hace la IA por proyecto; la
   firma visual es capa libre.
2. **Compilado, no runtime.** Cero JS para tokens: toda la identidad se
   resuelve a CSS estático en build. Cumple ADR-0005 (sin Node, sin CDN) y la
   CSP actual (`script-src 'self'`).
3. **Intención declarativa separada de la aplicación.** `design.toml` es el
   contrato máquina (lo que se puede compilar); `DESIGN.md` es el brief humano
   (tono, referencias, público, firma visual). El compilador valida la
   consistencia entre ambos; ninguno sustituye al otro.
4. **Degradación elegante.** Sin JS, todo el contenido visible (regla 3 de
   AGENTS.md intacta): el estado oculto de una animación solo existe bajo la
   clase `.js-motion` que pone el propio script. `prefers-reduced-motion`
   apaga todo el motion. Navegadores sin scroll-driven CSS reciben estático.
5. **Extensible por convención.** Añadir un estilo, un arquetipo o una pareja
   tipográfica = soltar un `.md` en `references/`. Cero código, cero registro.
6. **Cada fase entrega valor sola** y el default sigue siendo Basecoat neutro
   hasta que `/kiro-init` diga lo contrario.

---

## 3. Arquitectura — cuatro subsistemas, un flujo de datos

```
 /kiro-init (entrevista: propone 3 direcciones contrastadas)
        │ escribe
        ▼
 design.toml ───► COMPILADOR ───► input.css (bloques delimitados idempotentes)
 (intención)   scripts/design.py   + app/static/fonts/ + import del tema Basecoat
                                       │
                                       │ make css
                                       ▼
 DESIGN.md (firma visual) ───► LAYOUTS + TEMPLATES (slots Jinja)
 kiro-design (reglas + catálogos:       │ {% block main %}, {% block header %}
 archetypes, type-pairings, styles)    │
                                       ▼
                               PERCEPCIÓN: /_design (iterar identidad)
                               + /kiro-design-review (capturas 375/1280 px,
                                 anti-convergencia, hasta 2 pasadas)
```

### Subsistema A — Compilador de tokens

El corazón del motor. Transforma intención en CSS, de forma determinista y
testable.

- **Entrada:** `design.toml` (lo escribe `/kiro-init`; editable a mano):
  ```toml
  # Contrato de diseño del proyecto. Lo compila `make design build`.
  [brand]
  primary  = "#C2410C"
  neutral  = "warm"        # warm | cool | pure | tinted
  surface  = "cream"       # light | dark | cream | ...
  secondary = ""           # opcional
  radius   = "0.5rem"

  [type]
  display = { name = "Fraunces", weights = ["400", "700"] }
  body    = { name = "Inter", weights = ["400", "600"] }

  [basecoat]
  theme = "rhea"          # vega | nova | maia | lyra | mira | luma | sera | rhea

  [motion]
  level = 6               # 1-10, ver tabla de niveles

  [structure]
  header = "floating-pill" # sticky-blur | floating-pill | industrial-rule |
                           # terminal-bar | custom
  ```
- **Salida:** paleta OKLCH completa (~20 tokens, claro y oscuro), `@font-face`
  + `--font-display`/`--font-sans`, import del tema, `--radius`, nivel de
  motion. Todo en bloques delimitados e idempotentes de `input.css` — el
  mismo patrón que `apply_brand_block` ya usa.
- **Validaciones en compilación:** WCAG AA de cada par texto/fondo (claro y
  oscuro), firma de bytes woff2, pesos declarados = pesos descargados, tema
  existente en la lista, nivel de motion con archivos vendorizados presentes.
- **Dónde vive:** funciones puras en `app/design_engine/` (o extendiendo
  `app/branding.py`), I/O en `scripts/design.py`. Comandos:
  `make design build` (aplica todo) y `make design watch` (rebuild al cambio).
  `make brand-colors` y `make font` siguen existiendo como atajos de un solo
  eje: escriben `design.toml` y recompilan.

### Subsistema B — Estructura

Quita el prior fijo para que exista dónde desplegar una identidad:

- `base.html` se queda solo con el esqueleto común (`head`, body attributes,
  CSRF por `hx-headers`) y expone `{% block main %}` y `{% block header %}`.
- `layouts/app.html`: el `max-w-5xl` actual, para pantallas privadas.
- `layouts/landing.html`: a sangre, secciones propias, bloque `scripts` (donde
  se carga motion), para portadas y landings.
- `partials/nav_auth.html`: la lógica de sesión (usuario, logout POST, CSRF)
  aislada, para que reescribir la parte visual de header/footer no la rompa.
- `pages/home.html` y el ejemplo de `kiro-feature` neutralizados: comentario
  explícito de "andamio, no diseño", listado con `divide-y` en vez de grid de
  cards, señalando a `DESIGN.md` para la forma real.
- Arquetipos de header documentados (sticky-blur, floating-pill,
  industrial-rule, terminal-bar) con su elección en `design.toml`.

### Subsistema C — Varianza

Lo que hace que dos proyectos gemelos no se parezcan:

- **Catálogos generativos** (`.claude/skills/kiro-design/references/`):
  - `archetypes.md`: hero (split, tipografía gigante, bento asimétrico,
    editorial, marquee, sticky-stack, horizontal-pan), sección, textura
    (grano, rejilla, duotono, malla) y navegación, cada uno con su caída a
    móvil.
  - `type-pairings.md`: ~25 parejas tipográficas por estilo (serif
    editoriales, condensadas, mono, display).
  - Referencias de estilo que faltan: `expresivo.md`, `institucional.md`,
    `panel-de-datos.md` — hoy 3 de 6 presets no tienen receta y la IA cae al
    Basecoat sobrio.
- **Firma visual obligatoria** en `DESIGN.md`: 2–3 gestos que el proyecto se
  compromete a repetir ("titulares serif a 12vw que se salen del borde",
  "todo mono en mayúsculas con un acento ácido"). **Es la capa que no puede
  converger, porque no sale de ningún catálogo.**
- **`/kiro-init` propone 3 direcciones** contrastadas (segura, atrevida,
  experimental) con paleta, fuentes, arquetipos y firma — no una lista sesgada
  a lo sobrio.
- **Defaults por preset:** elegir un estilo aplica tema de Basecoat, radio,
  fuentes sugeridas y diales por defecto; incluso un relleno perezoso da
  variedad.
- **Motion por niveles de dial**, con API declarativa — la IA jamás escribe
  JS por página, solo atributos:

  ```html
  <h1 data-motion="split-reveal">…</h1>
  <ul data-motion="stagger" data-motion-delay="0.08">…</ul>
  ```

  | Dial | Motor | Peso aprox. | Instalación |
  |---|---|---|---|
  | 1–3 | Transiciones CSS | 0 | — |
  | 4–6 | `motion.js` propio (IntersectionObserver) | 1–2 KB | de serie |
  | 7–8 | Motion (motion.dev) vendorizado | 5–20 KB | `make motion level=motion` |
  | 9–10 | GSAP + ScrollTrigger (+ Lenis opc.) | ~45 KB | `make motion level=gsap` |

  Reglas: carga solo en `layouts/landing.html`; gate `.js-motion`; init vía
  `htmx.onLoad` y limpieza de triggers del fragmento saliente;
  `matchMedia` para `prefers-reduced-motion`. Pesos medidos al vendorizar.

### Subsistema D — Percepción

Cierra el bucle: la IA ve lo que diseña y corrige.

- **`/_design`** (solo en desarrollo, flag en `settings`): tokens, escala
  tipográfica, botones, formularios, una card, un hero de prueba, claro y
  oscuro. Donde se itera la identidad antes de construir features. En v1.0
  acepta `?style=…` como preview de estilo antes de elegirlo.
- **`/kiro-design-review`**: arranca `make dev`, captura a 375 px y 1280 px
  (Claude in Chrome si está disponible; si no, pide captura al usuario),
  contrasta con `DESIGN.md` + checklist anti-slop + "¿se parece a la plantilla
  por defecto?", y corrige en hasta 2 pasadas.
- **`/kiro-redesign`**: audita una app ya construida contra su `DESIGN.md` y
  empuja varianza — rescata los proyectos existentes.
- **`make design-check`**: validación estática del contrato (WCAG, fuentes,
  tema, motion presente para el dial, y alerta si `design.toml` sigue en
  valores por defecto = convergencia potencial).

---

## 4. Personalización por el cliente

El cliente es el desarrollador que usa Kiro. Cada proyecto es un clon del
framework (ADR-0003), así que todo esto vive en su copia y le pertenece.

| Capa | Cómo la personaliza |
|---|---|
| **Tokens** | Cualquier hex, temperatura de neutro, superficie, cualquier fuente de Fontsource, logo. Vía entrevista (`/kiro-init`), directo (`make brand-colors`, `make font`) o editando `design.toml` + `make design build` |
| **Estructura** | Elige arquetipo de header/hero en la entrevista, o reescribe el partial visual — la lógica de sesión queda intacta en `nav_auth.html` |
| **Varianza** | La firma visual es capa libre: la inventa el cliente; los catálogos son extensibles soltando `.md` en `references/` |
| **Motion** | Dial 1–10; subir de nivel instala lo necesario con un comando |
| **Re-aplicar todo** | `make design build` — idempotente, un solo comando reconstruye la identidad completa |
| **Actualizar el motor** | `make upgrade` + `make design build`: el estado vive en `design.toml` + bloques delimitados, no en ediciones manuales dispersas |

---

## 5. Versiones y plan de implementación

Cada versión entrega valor sola y pasa `make check`. Las duraciones son
orientativas (un desarrollador con la IA del framework).

### v0.1 — Estructura + superficie (semanas 1–2)

El MVP que mata el "gris con otro botón".

**Tareas:**
1. `base.html`: extraer `{% block main %}` y `{% block header %}`.
2. Crear `layouts/app.html` y `layouts/landing.html`; migrar páginas
   existentes a `app.html` (sin cambios visibles).
3. Extraer la lógica de sesión del header a `partials/nav_auth.html`.
4. Neutralizar `home.html` y el ejemplo de `kiro-feature`.
5. `app/branding.py`: extender la derivación a la paleta completa (parámetros
   `neutral`, `surface`, `secondary`); reutilizar `rgb_to_oklch`,
   `oklch_to_rgb`, `contrast_ratio`, `render_brand_block`, `apply_brand_block`.
6. `make font name=… weights=… role=…`: descarga woff2 de Fontsource
   (validación por firma de bytes), `@font-face` + tokens en bloque
   idempotente.
7. Tabla estilo → tema Basecoat en la skill; `/kiro-init` la aplica.
8. `/_design` básico (router + plantilla + flag en `settings`).
9. Tests: contraste WCAG de cada par texto/fondo, idempotencia de bloques,
   validación woff2. ADR-0014.

**Archivos:** `app/templates/base.html`, `app/templates/layouts/*`,
`app/templates/partials/nav_auth.html`, `app/templates/pages/home.html`,
`app/branding.py`, `scripts/brand.py` (+ nuevo `scripts/font.py`),
`Makefile`, `app/config.py`, `app/routers/design.py`,
`app/templates/pages/design.html`, `.claude/skills/kiro-design/SKILL.md`,
`.claude/skills/kiro-feature/SKILL.md`, `tests/test_branding.py`,
`docs/decisions/0014-…`.

**Aceptación:**
- Prueba de convergencia v1: 3 configuraciones de diseño distintas sobre el
  mismo código producen capturas (1280 px) que difieren en layout,
  superficie y tipografía — no solo el color del botón.
- Login, registro y notas siguen en verde (layouts/app.html no rompe nada).
- `make check` verde (mypy strict sobre branding).

### v0.2 — Compilador + varianza (semanas 3–4)

**Tareas:**
1. Esquema de `design.toml` + `scripts/design.py` (`build` / `watch`),
   unificando brand, fuentes, tema, radius y nivel de motion en un solo build.
   `make brand-colors` y `make font` se convierten en atajos que escriben el
   toml y recompilan.
2. `references/archetypes.md` y `references/type-pairings.md`.
3. Referencias que faltan: `expresivo.md`, `institucional.md`,
   `panel-de-datos.md`.
4. Molde de `DESIGN.md`: nuevas secciones Firma visual y Arquetipos.
5. `/kiro-init`: flujo de 3 direcciones contrastadas.
6. Defaults por preset en la skill.

**Aceptación:** `make design build` re-aplica la identidad completa desde un
solo archivo; elegir "expresivo" produce algo expresivo; el compilador falla
con mensaje claro ante toml inválido (WCAG incumplido, fuente inexistente).

### v0.3 — Motion (semanas 5–6)

**Tareas:**
1. `app/static/js/motion.js` (dials 4–6): reveals, stagger, contadores,
   marquee — IntersectionObserver + `data-motion`.
2. `make motion level=motion|gsap`: vendoriza con validación y `NOTICE.md`.
3. Integración: gate `.js-motion`, `htmx.onLoad` + limpieza de triggers,
   `prefers-reduced-motion`, carga solo en `layouts/landing.html`.
4. Documentar niveles y API declarativa en la skill.

**Aceptación:** dial 9 produce pin/scrub real en una landing; con JS
deshabilitado todo el contenido es visible; `make check` verde; CSP sin
cambios (`script-src 'self'`).

### v0.4 — Percepción (semanas 7–8)

**Tareas:**
1. `/kiro-design-review` completo (capturas 375/1280, hasta 2 pasadas).
2. `/kiro-redesign` para apps existentes.
3. `make design-check` (validación estática del contrato + alerta de
   convergencia potencial).

**Aceptación:** el review detecta "se parece al default" y corrige en ≤2
pasadas; `design-check` en rojo cuando `design.toml` está en defaults.

### v1.0 — Expansión

1. Referencias nuevas: `editorial`, `neo-brutalista`, `retro/y2k`,
   `orgánico`, `oscuro-tecnológico`.
2. Vendorizar `redesign-skill` y `brandkit` del upstream (licencia en
   `NOTICE.md`).
3. `/_design?style=…` como preview antes de elegir.
4. Sección del motor en `docs/upgrading.md` + CHANGELOG.

**Aceptación:** dos proyectos con el mismo preset difieren por su firma
visual; `make upgrade` + `make design build` re-sintetizan la identidad de un
proyecto vivo sin romperlo.

---

## 6. Optimización — por qué esta solución y no otra

- **Costo runtime = 0 para tokens.** Todo es CSS estático compilado en build;
  Tailwind ya elimina clases no usadas; fuentes woff2 subset latin solo con
  los pesos declarados; cache-busting vía `asset()` (mtime) ya resuelto.
- **Motion escalonado.** Solo lo que el dial pide, solo en landing, medido al
  vendorizar. El 90 % de las apps (dials 1–6) paga 0–2 KB.
- **Compilador puro.** Funciones sin estado: testeable con pytest, tipado con
  `mypy --strict`, sin dependencias más allá de `httpx2` para descargas.
- **Eficiencia de contexto de la IA.** Los catálogos son `.md` que la skill
  lee bajo demanda; no inflan cada conversación. La API declarativa de motion
  evita que la IA escriba JS distinto (e inmantenible) por página.
- **El espacio de salida es multiplicativo:**

  ~10 estilos × ~7 arquetipos de hero × ~25 parejas tipográficas
  × paleta continua (hex × temperatura × superficie) × 11 niveles de motion
  × firma libre por proyecto

  La convergencia deja de ser el resultado probable y pasa a ser algo que el
  subsistema D detecta y corrige.

- **Descartado por diseño:** starters precocinados por preset (jaula),
  overrides de tokens por página vía `render()` (toca el core, valor marginal:
  un proyecto = una identidad), cambiar el default `vega` → `nova`
  (cosmético; el default debe empujar a correr `/kiro-init`).

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Scope creep en los catálogos | v0.2 solo las 3 referencias que faltan; el resto en v1.0 |
| Mantenimiento del JS de motion | API declarativa por `data-*`, un solo archivo, la IA nunca escribe JS por página |
| Deriva `design.toml` ↔ `DESIGN.md` | Contrato explícito: toml = aplicable por máquina; DESIGN.md = prosa + firma; `design-check` valida consistencia |
| La IA converge dentro de un catálogo | 3 direcciones en `/kiro-init` + firma libre + check "¿se parece al default?" en el review |
| Actualizar el framework en proyectos vivos | Estado del motor solo en `design.toml` + bloques delimitados → `make upgrade` + `make design build` |
| Licencias | Fontsource = OFL/Apache; GSAP gratuito comercial desde 2025; `NOTICE.md` al vendorizar |
| SEO / contenido sin JS | Gate `.js-motion`: el estado oculto solo existe si el script corrió |

---

## 8. Verificación y KPI

**KPI de éxito (`make design-check` + prueba manual):** sobre el mismo código,
N `DESIGN.md`/`design.toml` distintos deben producir capturas (1280 px y
375 px) que difieran en **layout, tipografía y superficie**. Hoy ese test
falla con N=2; con v0.1 pasa con N=3.

Procedimiento:
1. `make check` en verde.
2. `make design build` con 3 contratos distintos (minimalista,
   neo-brutalista, editorial) + `make css` → comparar capturas: deben diferir
   en las tres dimensiones, no solo el color del botón.
3. Auth y notes en verde tras migrar a layouts.
4. Con v0.3: página visible con JS deshabilitado; reduced-motion apaga todo.

---

## 9. Cómo sigue creciendo la diversidad (modelo de crecimiento)

El motor no es un conjunto finito de opciones: es un generador con catálogos
aditivos, un espacio continuo de color y una capa libre.

1. **Los catálogos crecen con texto.** Viste un diseño que te gusta →
   documentas un `.md` (referencia de estilo, arquetipo de hero, pareja
   tipográfica) → ya es una opción para los próximos proyectos. Cero código.
2. **La paleta es continua.** Cualquier hex × temperatura × superficie se
   deriva en OKLCH; no hay "paleta 3 de 8".
3. **La firma visual no sale de ningún catálogo.** Dos proyectos con el mismo
   preset divergen por sus gestos.
4. **El subsistema D detecta la convergencia cuando aparece.** "¿Se parece al
   default?" es un check explícito del review, no una esperanza.

---

## 10. Archivos críticos (mapa de la implementación)

| Qué | Dónde |
|---|---|
| Layouts y slots | `app/templates/base.html`, `app/templates/layouts/{app,landing}.html` |
| Lógica de sesión del header | `app/templates/partials/nav_auth.html` |
| Compilador | `app/branding.py` → `app/design_engine/`, `scripts/design.py` |
| Contrato | `design.toml` (raíz del proyecto) |
| Catálogos | `.claude/skills/kiro-design/references/` |
| Percepción | `app/routers/design.py`, `app/templates/pages/design.html`, `.claude/commands/kiro-design-review.md` |
| Comandos | `.claude/commands/kiro-init.md` (3 direcciones), `.claude/commands/kiro-redesign.md` |
| Motion | `app/static/js/motion.js`, `app/static/js/vendor/` |
| Makefile | `design build/watch`, `font`, `brand` (ext), `motion`, `design-check` |
| Tests | `tests/test_branding.py`, `tests/test_design_engine.py` |
| ADRs | `docs/decisions/0014-motor-de-diseno.md` (+ motion vendorizado, + compilador) |

---

## Informe de implementación

**Resultado.** Los cuatro subsistemas y las cinco versiones del plan están
implementados. `make check` en verde con **569 tests** (había 134), `mypy
--strict` sobre `app/` y migraciones sin deriva. La prueba de convergencia del
plan se cumple con N = 6: seis contratos distintos sobre el mismo código producen
páginas que difieren en superficie, tipografía, forma de los componentes y
cabecera (capturas a 1280 px y 375 px, sin errores de consola). Ver ADR-0014 y
ADR-0015, que son el registro de las decisiones.

### Qué se hizo, subsistema a subsistema

| Plan | Implementación |
|---|---|
| **A. Compilador** | `app/design_engine/` (contrato Pydantic, paleta OKLCH, bloques, fuentes, motion, presets, checks, runtime) y `scripts/{design,font,motion,fetch,brand}.py`. Bloques `kiro:theme`, `kiro:brand`, `kiro:fonts` idempotentes en `input.css` |
| **B. Estructura** | `layouts/{app,landing}.html`, `partials/nav_auth.html`, `partials/brand_mark.html`, cuatro cabeceras más `custom` en `partials/headers/`, `home.html` y el ejemplo de `kiro-feature` neutralizados |
| **C. Varianza** | Once presets (los seis de 1.1 más cinco nuevos), `archetypes.md`, `type-pairings.md` (25 parejas), ocho referencias de estilo nuevas, `redesign.md` y `brandkit.md` vendorizados, firma visual y arquetipos en `DESIGN.md`, `/kiro-init` con tres direcciones, motion por niveles |
| **D. Percepción** | `/_design` (con `?style=` y claves de `[brand]`), `/kiro-design-review`, `/kiro-redesign`, `make design-check` |

### Dónde se apartó del plan (y por qué)

1. **Motion One 10.18, no «Motion latest».** Medido al vendorizar: el bundle
   actual de `motion` (14.2) pesa 154 KB (51 KB gzip), más que GSAP y ScrollTrigger
   juntos. La 10.18 pesa 24.6 KB (9.8 KB gzip), que es lo que el plan estimaba
   (5-20 KB).
2. **Las librerías no se commitean en el framework.** La licencia de GSAP no
   aborda la redistribución de sus `.min.js`; para no heredar esa duda en cada
   clon, `make design build` las descarga al proyecto, fijadas por versión y
   SHA-256, con su `NOTICE.md`. El plan decía «vendorizado con NOTICE.md»: se
   mantiene, pero bajo demanda y por proyecto.
3. **`motion.js` pesa 3.4 KB gzip, no 1-2 KB.** La estimación del plan era previa
   al código: son cinco comportamientos más la integración con HTMX.
4. **`spring` no es un valor propio de `data-motion`.** Es un modificador
   (`data-motion-ease="spring"`) de `reveal`: así el estado oculto sigue
   perteneciendo solo a valores que el núcleo sabe animar (si no, un `spring` sin
   adaptador cargado quedaría invisible). Se añadió `progress` al vocabulario.
5. **Lenis no se incluye** (era opcional en el plan).
6. **`make design watch` solo recompila `design.toml`**; el CSS lo recompila
   `make css-watch` en otra terminal.
7. **Objetivos de Makefile añadidos:** `design-init` y `design-set`. `make design
   set a=b` no es posible (make trata `a=b` como una variable), así que las
   ediciones puntuales son `make design-set v="a=b"`.
8. **`/_design?style=` acepta también las claves de `[brand]`** (`?primary=`,
   `?surface=`…), y avisa cuando una paleta previsualizada no cumple AA.
9. **Seis cambios que el plan no preveía y la verificación hizo necesarios:**
   - Un `.dark` anidado no oscurecía nada (Tailwind resuelve `--color-*` en
     `:root`); el compilador re-mapea el tema bajo `.dark`. Sin esto no hay
     bandas oscuras en una web clara. Lo encontró una captura.
   - El texto del botón se medía contra blanco puro pero se emitía
     `oklch(0.985)`: el contraste informado era optimista.
   - La cabecera `terminal-bar` salía como una franja blanca en superficies
     oscuras; ahora es una barra de tarjeta con regla.
   - `htmx:beforeCleanupElement` llega con nodos que no son `Element`; el
     `unobserve` lanzaba una excepción dentro del intercambio de HTMX.
   - `make design-set motion.level=99` dejaba escapar una traza de Pydantic; todo
     el contrato pasa ahora por un único punto de validación.
   - `design-check` avisaba por atributos que solo aparecían en comentarios Jinja
     y en la propia página `/_design`.
10. **`design.toml` en la imagen de producción** (`Dockerfile`) y **un paso de CI**
    (`design check --allow-defaults`), que el plan no listaba.
11. **Los tests no afirman el estado de fábrica.** `tests/` viaja a cada proyecto:
    uno que exigiera `design.toml` por defecto o `DESIGN.md` con `TODO` pondría
    `make check` en rojo justo después de `/kiro-init`.

### Cómo se verificó

- Navegador real (Chrome sin interfaz, por el protocolo DevTools): scroll, `pin`,
  `horizontal` (la banda pasa de -10 a -900 px), `scrub`, `parallax`, `spring`,
  HTMX (armado y limpieza), contenido visible **sin JS** y con
  **`prefers-reduced-motion`**, y los seis presets a 1280 y 375 px.
- Imagen de producción construida con Docker: contiene `design.toml` y los
  assets, y `/_design` no existe en ella.
- Los fragmentos de `archetypes.md` se renderizaron en una página de laboratorio.
- Publicado como **v1.2.0** (2026-10-13), junto con la corrección de `urllib3`
  (2.7.0 a 2.8.0) que dejaba rojo el paso `pip-audit` de CI. Queda como mejora de
  herramientas ajena a este plan: el hook de `mypy` de `.pre-commit-config.yaml`
  trae una lista de `additional_dependencies` desactualizada (le faltan `httpx2`,
  `argon2`, `itsdangerous`, `jinja2` y `uuid-utils`) y falla en su entorno aislado;
  `make types` es la comprobación fiable.
