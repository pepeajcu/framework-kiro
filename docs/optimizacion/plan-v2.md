# Plan v2 — Kiro: diseño multi-fuente sin contradicciones + blindaje del framework

> Sustituye a `docs/optimizacion/plan-final.md`, que queda como antecedente.
> El stack no cambia: FastAPI, SQLAlchemy síncrono, Jinja2, HTMX, Tailwind v4,
> Basecoat y cero Node en el repo.
> Decisiones del usuario (14-10-2026):
> - bloqueo por niveles;
> - kit iOS completo;
> - `surface = "auto"`;
> - cimientos primero.

## Contexto

La sesión anterior acordó cinco fases solo de diseño:

1. preset iOS;
2. lint de patrones genéricos;
3. `/kiro-style` para briefs de Refero;
4. skillui para webs de referencia;
5. uupm (nextlevelbuilder) como juez.

Revisé el código (HEAD `22b2664`) y verifiqué las fuentes externas. La
intención es buena, pero el plan tiene huecos que producirían errores:

1. **No dice cómo se resuelve un choque.** "Si uupm y taste chocan, decide el
   humano" significa preguntar cada vez. Hace falta una regla escrita que
   resuelva de antemano los choques conocidos.
2. **Son cinco tuberías distintas** hacia `design.toml`, y cada tubería es una
   fuente de bugs.
3. **"uupm bloqueante" y "máximo dos pasadas" se contradicen.** Ya está
   resuelto: bloqueo por niveles.
4. **Hechos nuevos que lo cambian todo:**
   - **taste-skill v2.0.0 salió el 13-10-2026.** Es una reescritura sin diales,
     que exige Node 22 y Chrome, y prohíbe el vidrio, las reglas finas, la
     numeración 01/02, la monoespaciada fuera del código y las píldoras
     flotantes. Choca con iOS y con 5 de los 11 presets de Kiro.
   - **uupm v2.15 adoptó los mismos diales** (`--variance --motion
     --density`): los diales sobreviven, pero ahora vía uupm.
   - **skillui escribe por defecto en `./`**: en la raíz de un proyecto machaca
     `DESIGN.md` y `CLAUDE.md`.
   - **El repo de skillui no tiene archivo LICENSE**, aunque su README dice MIT.
   - **Refero exporta un DESIGN.md estructurado.**
   - **Apple HIG:** el Liquid Glass va solo en la capa de navegación y
     controles, nunca en el contenido. Coincide con la regla actual de Kiro.
5. **El plan dejó fuera la arquitectura y HTMX** de la auditoría, y la
   exploración encontró bugs reales.

**Objetivo**:
- cualquier diseño (taste, uupm, iOS, Refero, skillui, presets) entra al
  proyecto **respetando la guía de uupm**;
- las fuentes se complementan y no se contradicen;
- el framework comete el menor número posible de errores, porque las reglas
  las verifica una máquina en vez de recordarlas la IA.

---

## La idea central (diseño)

**Una constitución, un contrato, una tubería.**

1. **Constitución:** cada fuente es *dueña de un dominio*, no de todo el
   diseño. Los dominios son las **10 categorías de prioridad de la propia guía
   de uupm**. Así "respetar nextlevelbuilder" deja de ser una intención y pasa a
   ser la estructura.
2. **Contrato:** `design.toml` + `DESIGN.md`, como hoy. Todo desemboca ahí.
3. **Tubería única:** toda fuente produce el mismo objeto intermedio
   (`DesignBrief`). Una sola función lo filtra y lo traduce a una propuesta,
   que se aplica con un solo comando.
4. **Toda propuesta = línea base de uupm para el producto + inspiración
   encima.**
   - La inspiración (iOS, Refero, skillui, un preset) solo puede sustituir lo
     que la guía de uupm considera estilo: categorías 4, 6, 7 y la composición
     de la 5.
   - Nunca sustituye lo que es UX: categorías 1, 2, 3, 8 y 9, y la función de
     la 5.

### A0. Tabla de dominios (va en `kiro-design/SKILL.md`, siempre cargada)

| # | Categoría uupm | Prioridad | Dueño en Kiro | Cómo se hace cumplir | ¿DESIGN.md la puede relajar? |
|---|---|---|---|---|---|
| 1 | Accesibilidad | CRÍTICA | uupm + WCAG | Compilador (contraste AA), tests de suelo UX, revisión | **Nunca** |
| 2 | Táctil e interacción | CRÍTICA | uupm (+ HIG con el kit iOS) | Bloque `kiro:a11y` (44 px con puntero grueso), revisión a 375 px | **Nunca** |
| 3 | Rendimiento | ALTA | Plataforma Kiro (CSP, fuentes locales, niveles de motion) + uupm | archcheck, design-check | **Nunca** |
| 4 | Selección de estilo | ALTA | DESIGN.md (el usuario), filtrado por taste; uupm propone candidatos | Revisión | Sí |
| 5 | Layout y responsive | ALTA | Función: uupm (fallback móvil, sin scroll horizontal). Composición: taste (arquetipos, varianza) | Lint y revisión | Solo la composición |
| 6 | Tipografía y color | MEDIA | Validez: contrato (AA, Fontsource). Elección: taste, con las parejas de uupm como reserva | Compilador y revisión | La elección, sí |
| 7 | Animación | MEDIA | Motor de motion de Kiro (niveles, reduced-motion); duraciones y curvas de `motion.csv` de uupm | design-check | El nivel, sí |
| 8 | Formularios y feedback | MEDIA | uupm (estados, errores en línea) + helpers de Kiro (B3) | Tests de suelo y revisión | No: los estados son obligatorios |
| 9 | Navegación | ALTA | uupm (patrones) + arquetipos de cabecera de Kiro | Revisión | La forma sí; la lógica de sesión no |
| 10 | Gráficos y datos | BAJA | `charts.csv` de uupm | Revisión | Sí |

**Reglas de resolución, en orden:**

1. **Gana la categoría de mayor prioridad**, en el orden de uupm. Las
   categorías 1, 2 y 3 y las leyes del stack no se relajan nunca.
2. **Dentro de una categoría decide su dueño.** Las demás fuentes solo
   aconsejan.
3. **Lo que el usuario dejó escrito en DESIGN.md gana** en las categorías
   relajables. Se anota en la nueva sección `## Decisiones de diseño` con su
   motivo, para no volver a preguntarlo.
4. **Traducción a la plataforma.** Si una propuesta es imposible en Kiro, se
   sustituye por lo más cercano que sí sea posible y se anota por qué. Nada se
   descarta en silencio.
5. **Si de verdad no se resuelve,** se pregunta al humano **una sola vez** y se
   aplica la regla 3.

### Matriz de conflictos conocidos, resueltos de antemano

Va en `references/constitution.md`. Un test verifica que sus IDs existen en el
registro de reglas.

| Choque | Resolución |
|---|---|
| uupm da URL o `@import` de Google Fonts (`typography.csv`) | Equivalente de Fontsource, precalculado al vendorizar; nunca CDN |
| uupm o iOS piden vidrio / Liquid Glass; taste v2 lo prohíbe | **HIG y la regla v1 de Kiro coinciden:** vidrio solo en la capa de navegación y controles (barras fijas, hojas, popovers, tab bar). Nunca en contenido que hace scroll. Superficie sólida si no hay soporte o se pide menos transparencia. No se adopta la prohibición de v2 |
| Orden de secciones de la landing de uupm frente a "nada de tres tarjetas iguales" de taste | **uupm decide QUÉ** secciones y en qué orden. **taste decide CÓMO** se compone cada una: bento, numbered o spec-sheet, nunca tres tarjetas iguales |
| Fintech y salud necesitan señales de confianza (uupm); taste prohíbe el muro de logos en el hero | Las señales van debajo del hero, con datos reales (arquetipo §2.6 `logo-row` o `spec-sheet`) |
| Paleta de uupm con morado o degradado frente a "nada de morado IA" de taste | Se conserva el tono si es el de la marca; saturación por debajo del 80 % y sin glow. Queda marcado en el overlay |
| uupm propone Inter o Roboto; taste dice "Inter no por defecto" | Inter se permite solo con el kit iOS (detrás de la fuente del sistema), con el estilo institucional o si DESIGN.md lo pide. Si no, la pareja más cercana del catálogo de Kiro |
| Prohibiciones de taste v2 (eyebrows, reglas finas, 01/02, mono, píldoras, más de 2 familias) frente a presets de Kiro (`industrial-rule`, `numbered`, `oscuro-tecnologico`, `floating-pill`, `retro-y2k`) | **Kiro se fija a taste v1** (`taste-skill-v1`, mismo repo, MIT). Las "tells" de v2 son avisos que un estilo explícito anula |
| taste v2 exige 4 o más fotos externas y 8 o más elementos en movimiento | No se adopta: lo impiden la CSP y el dial de motion |
| skillui o Refero extraen varios acentos | Se queda **uno**, el de mayor uso en CTAs. El resto va a notas |
| La web de referencia usa fuentes propietarias | Nunca se copian; se usa el equivalente de Fontsource por categoría y métricas |
| El azul de sistema de iOS (`#0088FF`, `#007AFF`) no admite texto blanco con contraste AA | Primario `#0066CC` (blanco a 5.33:1, el azul de enlaces de apple.com). El azul de sistema solo como acento no textual |
| uupm `--persist` escribe `design-system/<slug>/MASTER.md` en el directorio actual | Se ejecuta siempre con `-o .design/uupm`. En Kiro, MASTER = DESIGN.md + design.toml; los *page overrides* van a `## Páginas` de DESIGN.md (notas de UX, nunca tokens, según ADR-0014) |
| uupm tiene un objetivo `kiro.json`; `.kiro/` es la carpeta del IDE Kiro de AWS | No tiene nada que ver con este framework. La carpeta de trabajo de Kiro será `.design/`, nunca `.kiro/` |

**Una sola puerta de entrada:**
- **kiro-design es la única skill de diseño.**
- uupm y taste se vendorizan como *referencias*, sin un `SKILL.md` que compita
  (el de uupm se guarda como `GUIDE.md`).
- design-check avisa si alguien instala una skill de diseño competidora en
  `.claude/skills/` (por ejemplo, `ui-ux-pro-max`, `design-taste-frontend` o
  la salida de skillui).

---

## Fases (orden elegido: cimientos primero). Cada fase = un PR con `make check` en verde

**Paso previo:**
- copiar este plan a `docs/optimizacion/plan-v2.md`;
- marcar `docs/optimizacion/plan-final.md` como "sustituido por plan-v2".

Ningún paso hace commit sin que el usuario lo pida.

### Fase 1 — Cimientos: bugs, `make check` = CI, guardrails

**1a. Bugs reales encontrados**

| Bug | Dónde | Arreglo |
|---|---|---|
| Handler de página sin `OptionalUser` (viola la regla 10) | `app/routers/auth.py:343` | Declarar `user: OptionalUser` |
| Ejemplo de la skill que usa `NotFoundError` sin importarlo | `.claude/skills/kiro-feature/SKILL.md:151-173` | Añadir el import y señalar `app/routers/notes.py` como ejemplo vivo |
| Un parámetro inválido devuelve **JSON 422** en una app HTML | `app/main.py` no tiene handler de `RequestValidationError` | Página 400, o toast si la petición viene de HTMX |
| Los errores en peticiones HTMX fallan sin que el usuario vea nada: htmx 2.0.10 no hace swap de 4xx/5xx | `app/main.py:79-121` | Contrato de errores HTMX (abajo) |
| "Re-render con 400" no funciona en formularios `hx-post` | `base.html` no tiene `htmx-config` | Meta `htmx-config`: swap de 400 y 422 |
| Un servicio importa `fastapi.Request` | `app/services/consent.py:11` | `has_marketing_consent(cookie_value)`; el router le pasa la cookie |
| "router → service → repository, sin excepciones", pero las lecturas ya se saltan el servicio | `AGENTS.md:64`, `notes.py:55`, `kiro-feature:140` | Regla explícita: **las lecturas** pueden ir de router a repositorio; **las escrituras** pasan siempre por un servicio |
| `make check` dice ser lo que corre CI y no lo es | `Makefile:138`, `ci.yml` | `make check` = `lint types css design-check archcheck test migrations-check`. CI llama a `make check`, más `pip-audit` y Docker |
| El hook de mypy del pre-commit tiene una lista de dependencias desfasada | `.pre-commit-config.yaml:30-43` | `language: system` → `uv run mypy app`, sin lista que mantener |
| `is_htmx()` no se usa, y `main.py:101` repite la comprobación | `app/templating.py:79` | Usarla |
| Refrescar las referencias de taste tira de `main`, que ahora es v2 | `references/NOTICE.md` | Fijar el SHA del commit en la receta y en NOTICE |

**1b. Contrato de errores HTMX** (`app/hypermedia.py`)

- En una petición HTMX, los errores 403, 404, CSRF, validación y 500 responden
  con `HX-Reswap: none` más un toast OOB en `#toaster`, y conservan el código
  de estado.
- Las peticiones normales siguen recibiendo la página de error completa.
- Basecoat 1.0.2 inicializa cualquier `.toast` que aparezca en `#toaster`
  (está verificado en el JS vendorizado), así que no hace falta JS nuevo.

**1c. `scripts/archcheck.py`**

Solo usa librería estándar (`ast` + regex sobre Jinja). Corre en `make check` y
en el pre-commit, y `mypy` lo cubre.

| ID | Regla |
|---|---|
| K1 | Sin construcción de SQL (`select`, `insert`, `text`, `.execute`, `.scalars`) en routers ni servicios. `Session` como tipo sí |
| K2 | `.commit()` y `.rollback()` solo en `app/db.py` |
| K3 | Sin `fastapi` ni `starlette` en services, repositories, models, schemas, design_engine, emails ni analytics |
| K4 | Un router no escribe a través de un repositorio |
| K5 | `os.getenv` y `os.environ` solo en `config.py` |
| K6 | Un `async def` de handler contiene algún `await` |
| K7 | Un handler que renderiza `pages/` declara `OptionalUser`, `CurrentUser` o `require_role` |
| K8 | Cada módulo de `app/models/` está importado en `__init__` |
| J1 | Un `partials/` no hace `extends`; un `pages/` extiende un layout, nunca `base.html` |
| J2 | Todo `<form method="post">` incluye `csrf_field.html` |
| J3 | Sin hex, `rgb(` ni `bg-[#` en plantillas (salvo `emails/`, `basecoat/` y `pages/design.html`) |
| J4 | Sin clases de Basecoat que ya no existen (`btn-primary`, `btn-sm`…) |
| J5 | Sin `<script>` en línea ni URLs externas en `src` o `href` |

- **Formato del mensaje,** pensado para la IA: dice qué hacer y cita la regla
  de AGENTS.md.
  `app/routers/x.py:12 K1 SQL en un router → muévelo a app/repositories/x.py (AGENTS.md regla 1)`
- **Excepciones** con motivo obligatorio: `# kiro: allow K6 — motivo` o
  `{# kiro: allow J5 — motivo #}`. Todas aparecen en el resumen.
- Los grep manuales de `/kiro-redesign` pasan a ser estas reglas.
- **Tests:**
  - un fixture bueno y otro malo por regla (`tests/archcheck/`);
  - el `app/` real sale limpio;
  - K8 se verifica también por metadatos: importar `app.models` y después cada
    módulo con `pkgutil`, y comprobar que `Base.metadata.tables` no cambia.

### Fase 2 — Constitución y tubería única

**Documentos**
- La tabla de dominios va a `kiro-design/SKILL.md`.
- La matriz va a `references/constitution.md`.
- `DESIGN.md` gana dos secciones: `## Decisiones de diseño` (choques resueltos
  y relajaciones, con motivo) y `## Procedencia` (fuentes con URL y fecha).

**Registro de reglas** `app/design_engine/rules.py`
- Cada regla tiene: ID, categoría uupm (1-10), dueño, severidad, si es
  relajable, mensaje y arreglo.
- design-check, los tests de suelo UX y el informe de la revisión usan **los
  mismos IDs**.
- Un test comprueba que los IDs de `constitution.md` coinciden con los del
  registro.

**Cambios en el contrato** (`app/design_engine/contract.py`)
- Todos los campos nuevos tienen valor por defecto, así que `is_default` sigue
  significando lo mismo.
- `[rules] allow = [...]` acepta solo IDs relajables. Uno de las categorías 1-3
  es un error de contrato.
- Preset **`estandar-shadcn`:** el look Basecoat por defecto *elegido a
  propósito*. Lleva `allow` sobre los patrones genéricos y design-check deja de
  dar error por "sigue por defecto".
  - Responde a la pregunta original: lo genérico, solo si se pide
    explícitamente.
  - Los tests de presets lo excluyen de la regla "difiere en varios ejes".
- Cada campo nuevo implica regenerar con un script el bloque toml de las
  referencias de estilo (`test_design_docs.py:38-47` lo exige).

**`DesignBrief`** (`app/design_engine/brief.py`, Pydantic, puro)
- `source` (preset | advisor | brief | reference);
- procedencia;
- colores candidatos con rol y peso de uso;
- fuentes con rol y categoría;
- radio;
- pistas de densidad, motion, tema y cabecera;
- palabras clave de estilo;
- notas UX y anti-patrones de uupm.

**`propose(base, overlay, current, rules) -> Proposal`** (puro)
1. Fusiona la línea base de uupm con la inspiración, por categorías, según la
   tabla A0.
2. Elige un único acento.
3. Fontsource: tabla precalculada, con la categoría como respaldo.
4. Contraste AA con `derive_palette` y `suggest_primary`
   (`app/design_engine/palette.py`).
5. Escala de radio, y tema por radio y densidad.
6. Aplica las reglas.

Devuelve el contrato, los fragmentos de DESIGN.md, las decisiones tomadas
(regla, de, a, por qué) y lo que quedó sin resolver.

**CLI**
- `scripts/design.py propose --from <brief.json>` escribe
  `.design/proposals/<slug>.{toml,md}`.
- `make design-apply proposal=<slug>`:
  - guarda una copia de seguridad;
  - escribe con `write_atomically`;
  - fusiona las secciones de DESIGN.md;
  - corre `build` y `check`;
  - **no pisa una identidad propia sin `force=1`**.
- `.design/` va al `.gitignore`.
- **Reutiliza** `init`, `set_values` y `write_atomically`
  (`scripts/design.py`), `set_colors` (`scripts/brand.py`), `add_font` y
  `lookup` (`scripts/font.py`), y `load_contract`, `contract_to_data`,
  `contract_from_data` y `dump_contract`.

**Lint de patrones genéricos** (R13): `_check_patterns` en
`app/design_engine/checks.py`
- Reutiliza el recorrido de plantillas de `_check_templates`, que ya quita los
  comentarios Jinja.
- Detecta:
  - hero centrado con badge y tres tarjetas iguales;
  - muro de logos;
  - pricing de tres columnas idénticas;
  - `h-screen`;
  - `backdrop-blur` o `.material` fuera de un elemento fijo o sticky;
  - emoji en el markup;
  - vocabulario prohibido;
  - em dash en el texto visible;
  - nombres de relleno.
- Son **avisos** (taste opina, no bloquea en CI) y se silencian con
  `[rules] allow`. La revisión los trata como ✗ salvo que estén permitidos.

### Fase 3 — uupm integrado (dueño de la UX) y juez determinista

**Vendorizado** (`scripts/vendor_uupm.py`, herramienta del mantenedor del
framework)
- Descarga el tarball de un **commit fijado** (v2.15.0) y verifica su SHA-256,
  como hace `scripts/motion.py`.
- Copia una lista permitida a `.claude/skills/kiro-design/uupm/`:
  - `scripts/` (`search.py`, `core.py`, `design_system.py` y dependencias);
  - `data/` sin `phosphor-icons-upstream.json`, `google-fonts.csv` ni
    `google-font-licenses.json`, unos 1.1 MB;
  - `LICENSE` y `NOTICE`;
  - el `SKILL.md` original renombrado a **`GUIDE.md`**, para que no compita
    como skill.
- La suite de tests de uupm debe pasar con ese subconjunto. Si falla, se
  incluye el archivo que falte.
- `ruff` excluye esa carpeta (`extend-exclude`).

**Overlay de Kiro, precalculado al vendorizar** (`uupm-kiro/compat.csv`). Los
tests lo verifican sin red.
- **Fuentes de `typography.csv`:** si existen en Fontsource y cuál es la más
  cercana.
- **Paletas de `colors.csv`:** si pasan AA con el compilador de Kiro, el
  primario sugerido y las marcas de taste (saturación, morado).
- **Estilos de `styles.csv`:** preset o kit de Kiro más cercano.
- **Filas de `stacks/html-tailwind.csv` que no aplican en Kiro** (CDN,
  configuración JS), con su motivo.

Los choques se resuelven **una vez, en CI**, y no en cada conversación.

**Adaptador**
- Lo puro va en `app/design_engine/advisor.py`, tipado y bajo mypy: convierte
  el JSON de `search.py --json` en un `DesignBrief`.
- La E/S va en `scripts/design.py advise`, que ejecuta
  `python -I …/search.py --json` con los diales leídos de DESIGN.md.
- `make design-advise q="spa de lujo"` produce la línea base y su propuesta.

**La guía de uupm, paso a paso dentro de Kiro** (sección de `kiro-design/SKILL.md`)
1. **Analizar:** tipo de producto y público salen de PROJECT.md.
2. **Sistema de diseño:** `make design-advise` (su `--design-system`), con el
   resultado persistido en `.design/uupm/`.
3. **Búsquedas por dominio:** su `search.py --domain ux|chart|landing…`.
4. **Stack:** `--stack html-tailwind` con el overlay, donde ganan
   `kiro-component` y `kiro-design`.
5. **Checklist de entrega:** el de uupm se integra en el "Before you say done"
   de Kiro, sin duplicados y ordenado por prioridad.
6. **La IA nunca lee los CSV a mano:** pregunta con el CLI, así que el coste de
   contexto es cero.

**Juez determinista** (lo que bloquea en CI, categorías 1-3)
- **Bloque compilado `kiro:a11y`:**
  - con `pointer: coarse`, objetivos táctiles de 44 px (con el área ampliada
    en `::after`, sin cambiar el tamaño visual);
  - foco visible garantizado;
  - `prefers-contrast: more` → bordes más marcados.
  - Los botones de Basecoat miden 28-40 px: hoy se incumple la categoría 2 de
    uupm en todos los temas.
- **`tests/test_ux_floor.py`**, que viaja a cada proyecto:
  - renderiza todas las rutas GET sin parámetros, anónimo y logueado;
  - las comprueba con `html.parser`: `lang`, un `h1`, un `title`, toda entrada
    con su label, `img` con `alt`, `width` y `height`, nombres accesibles, sin
    `user-scalable=no`, sin `tabindex` positivo y `<form method="post">` con
    CSRF;
  - las rutas con parámetros se declaran en una lista.

**Comandos**
- **`/kiro-design-review`:**
  1. `make check`;
  2. pasada uupm: el MASTER del producto, los `Anti_Patterns` de
     `ui-reasoning.csv` y las guías UX que tocan;
  3. pasada taste (v1 + "¿se parece al default?");
  4. pasada HIG si `kit = "ios"`;
  5. **un informe único, ordenado por categoría uupm**, en el que cada hallazgo
     lleva ID, dueño, ✗/!/✓, evidencia y dónde se arregla.
  - Capturas a 375, 768, 1024 y 1440 px, las de la guía de uupm. En claro y
    oscuro si la superficie es `auto`.
  - **Cierre por niveles:**
    - un ✗ de las categorías 1-3 o del stack bloquea, sin límite de pasadas;
    - el resto tiene dos pasadas, y después se escala con opciones;
    - lo que se decida se escribe en `## Decisiones de diseño`.
- **Auditoría completa:** un modo `/kiro-redesign` "solo auditoría", sin
  comando nuevo. Menos comandos, menos confusión.
- **`/kiro-init` 2.2,** las tres direcciones, sale de la misma tubería:

  | Dirección | De dónde sale |
  |---|---|
  | Segura | La línea base de uupm para el producto |
  | Atrevida | Un preset que contraste, filtrado por taste |
  | Experimental | La referencia que traiga el usuario (Refero, URL, DESIGN.md de marca); si no trae ninguna, iOS u otro preset que contraste |

### Fase 4 — Kit iOS completo y `surface = "auto"`

**Contrato**
- `[structure] kit = "none" | "ios"`.
- `Header` admite `ios-bar`.
- `Surface` admite `auto`.
- `Fallback` admite `system`.

**`surface = "auto"`**
- `render_palette_block` emite los tokens oscuros también dentro de
  `@media (prefers-color-scheme: dark)`, así que **funciona sin JS**.
- `js/theme-auto.js` (un archivo, síncrono en el head, solo con `auto`)
  sincroniza la clase `.dark` para las variantes `dark:` de Basecoat.
- Antes de cerrar, hay que verificar si basta con redefinir
  `@custom-variant dark` en un bloque `kiro:`; si basta, el JS sobra.
- Sigue sin haber selector manual.

**Fuente del sistema** (`fallback = "system"`)
- Pila: `-apple-system, BlinkMacSystemFont, "Inter", sans-serif`, **sin
  `system-ui` delante de Inter**: así se ve SF Pro real en Apple e Inter local
  en los demás.
- No se precarga la fuente: el navegador solo descarga Inter si la usa.
- SF Pro no se puede autoalojar (licencia de Apple), y tampoco se usan SF
  Symbols.
- Inter entra en `type-pairings.md` (fila 26, marcada "solo kit ios /
  institucional"), lo que obliga a actualizar el test de 25 parejas.

**Preset `ios`**

| Eje | Valor |
|---|---|
| Diales V/M/D | 3/5/4 |
| Primario | `#0066CC` |
| Neutros / superficie | `cool` / `auto` |
| Radio | `0.75rem` |
| Kit / cabecera | `ios` / `ios-bar` |
| Motion | nivel 5, con muelle por CSS `linear()` (sin JS extra) |
| Fuentes | Inter 400/600, `fallback = "system"` |

El tema de Basecoat (`maia` o `luma`) se fija midiendo en `/_design` frente a
capturas de iOS 26. El criterio: botón cápsula de 36 px o más, tarjetas sin
sombra pesada.

**`app/static/css/kits/ios.css`**
- Es del framework, como `vendor/`: no se edita.
- Solo tokens, sin hex.
- Fondo agrupado (`background` ↔ `muted`), separadores con sangría de 16 px,
  radios concéntricos, márgenes de 16 y 20 px, escala de Dynamic Type de HIG
  (17/22 el cuerpo, 34/41 el título grande…) y feedback de pulsación
  (`scale(0.97)`).
- **Materiales `.material-thin`, `.material-regular` y `.material-thick`:**
  - fondo con `color-mix` + `backdrop-filter`, con el prefijo `-webkit-`;
  - superficie sólida con `@supports not`, `prefers-reduced-transparency` o
    `prefers-contrast: more`.
  - Safari no soporta `prefers-reduced-transparency`, así que **el compilador
    calcula la opacidad mínima** que garantiza AA del texto sobre fondo negro y
    sobre fondo blanco (`--kit-material-alpha`). Lo comprueba un test.
  - Sin filtros SVG de desplazamiento: solo se ven en Chromium.

**Componentes** en `app/templates/components/ios/` (del proyecto, como
`components/`), HTML accesible que funciona sin JS:
- `grouped_list` y `list_row` (chevron, detalle, switch);
- `segmented` (radios; `hx-get` opcional);
- `tab_bar` (fija abajo por debajo de 768 px, con `aria-current`);
- `sheet` (dialog o drawer de Basecoat con agarrador);
- `large_title`.

**Cabecera `ios-bar`**
- Barra con material, y título compacto al hacer scroll mediante animación
  ligada al scroll, como mejora progresiva y sin JS.
- Conserva `brand_mark.html` y `nav_auth.html`.

**`references/ios.md`**
- Dos modos:
  - landing al estilo apple.com (layout `landing`);
  - app al estilo iOS (layout `app` + componentes).
- Recoge las cifras de HIG, el vidrio solo en la capa de navegación y la lista
  de "lo que NO".

**Tests**
- La deriva entre presets y documentación (12 estilos, tabla del SKILL y
  bloque toml).
- `kits/ios.css` sin hex, con mínimos de 44 px y con su respaldo sólido.
- Los componentes renderizan HTML válido y con labels.
- `auto` funciona sin JS.

### Fase 5 — Entradas externas: Refero, DESIGN.md de marcas, skillui y webs

Todas producen un `DesignBrief` y pasan por la misma tubería. Un solo comando,
**`/kiro-style <entrada>`**:

| Entrada | Cómo se lee |
|---|---|
| **"Copy .md" de Refero Styles** (y cualquier DESIGN.md de la familia Stitch: skillui, VoltAgent/awesome-design-md) | Parser determinista de sus tablas en `app/design_engine/external_md.py`: colores (`Name \| Value \| Token \| Role`), escala tipográfica, espaciado y radios, Do/Don't. Un solo parser cubre tres fuentes |
| **Texto libre o prompt pegado** | La IA rellena el JSON de `DesignBrief` (esquema que imprime `make design-brief-schema`) y Pydantic lo valida. La IA extrae; el código valida y traduce |
| **URL con skillui** (opcional, el usuario lo instala; Node queda fuera del repo) | Envoltorio que **siempre** pasa `--out .design/reference/<n> --no-skill --format design-md` (sin eso machaca `DESIGN.md` y `CLAUDE.md`). Adaptador tolerante de `tokens/{colors,typography,spacing}.json`, con fixtures de skillui 1.3.4 |
| **URL sin skillui** (respaldo nativo) | `scripts/reference.py capture <url>`: capturas con Chrome sin interfaz y **con sandbox** (es una web de terceros), más HTML y CSS con `httpx2` (límite de tamaño y tiempo). Frecuencia de colores por contexto (botones y enlaces = acento), `font-family`, moda de `border-radius` y presencia de animaciones |
| **MCP de Refero** (opcional, de pago) | Si el usuario lo tiene conectado, `refero_get_style` devuelve datos estructurados que van al mismo `DesignBrief` |

**Candados**
- Se extrae lenguaje visual. Nunca se copian logos, imágenes, código ni fuentes
  (solo equivalentes de Fontsource).
- La procedencia va a DESIGN.md.
- La firma visual sigue siendo obligatoria.
- Primero se propone; se aplica solo con `design-apply`.
- **La licencia de skillui es ambigua:** se usa como herramienta externa y no
  se redistribuye.

**Tests:** fixtures de un DESIGN.md de Refero, de la salida de skillui y de una
web local (`http.server`). Las tres deben dar un contrato válido y un
design-check sin errores.

### Fase 6 — Ergonomía HTMX y formularios

- **`toast(...)`:**
  - en una respuesta HTMX, añade el fragmento OOB;
  - en una 303, escribe una cookie flash firmada (itsdangerous, ya es
    dependencia) que `render()` consume en la página siguiente.
  - Así el post/redirect/get por fin puede decir "Nota creada".
- **`validate_form(Model, **raw) -> FormResult[T]`** en `app/schemas/base.py`:
  - expone `.ok`, `.data`, `.values` y `.errors`, y nunca lanza excepción;
  - las macros `field(form, …)`, más las nuevas `textarea`, `select` y
    `checkbox`, toman de ahí valores y errores;
  - `help` se enlaza con `aria-describedby`.
  - Se quita el eco manual de `auth.py` y `notes.py`, y el cuerpo de la nota
    pasa a ser un textarea.
- Se descarta `render_block`: ya existe el camino `partials/`, y dos maneras de
  hacer lo mismo es ambigüedad para la IA.
- AGENTS.md y la skill `kiro-feature` documentan toast, errores y formularios.

### Fase 7 — Densidad compilada y estados (la fricción 7, sin "jaulas")

- **`[structure] density`** (1-10):
  - el compilador emite un bloque `kiro:rhythm` con `--kiro-section-y`,
    `--kiro-gap` y `--kiro-row-h`, más utilidades `@utility section-y`;
  - layouts y snippets de `archetypes.md` pasan a usarlas;
  - design-check avisa si no coincide con `VISUAL_DENSITY` de DESIGN.md, igual
    que con motion.
- La varianza sigue siendo criterio humano.
- **Macros solo estructurales**, sin opinión visual: el trío
  `components/states.html.jinja` (cargando, vacío, error), que uupm y taste
  exigen y que siempre se olvida.
- Los arquetipos visuales siguen siendo recetas, no macros: ADR-0014 rechaza
  los "starters" porque convierten el catálogo en una jaula.

---

## Lo que cambia frente al plan anterior

| Plan anterior | Este plan | Por qué |
|---|---|---|
| Triple juez; el humano desempata cada choque | Constitución por dominios con las 10 categorías de uupm y una matriz de choques precalculada | Cero preguntas repetidas; la guía de uupm pasa a ser la estructura |
| 5 tuberías hacia el contrato | `DesignBrief` → `propose` → `design-apply` | Un camino que probar |
| uupm en `app/design_engine/advisor/` | Datos y scripts en `.claude/skills/kiro-design/uupm/`; en `app/` solo el adaptador tipado | No mete 1 MB ni código ajeno bajo `mypy --strict` |
| Test con 20 consultas de ejemplo | Test exhaustivo sobre los 192 tipos de producto, más un overlay precalculado | Cobertura total y choques resueltos en CI |
| Preset iOS (solo tokens) con Inter | Kit completo; SF real vía la fuente del sistema; `#0066CC`; `auto` | `#007AFF` falla AA con blanco; el usuario pidió el estilo, no solo los colores |
| R13 entra en `make check` como error | Aviso relajable con `[rules] allow` y el preset `estandar-shadcn` | Las heurísticas dan falsos positivos; un opt-in en texto libre es frágil |
| `/kiro-style` y `kiro-reference` por separado | Un `/kiro-style` y un parser común de DESIGN.md externos | Refero, skillui y awesome-design-md comparten formato |
| `/kiro-ux-audit` nuevo | Un modo de `/kiro-redesign` | Menos comandos |
| Arquitectura y HTMX fuera del plan | Fases 1 y 6 | Bugs reales encontrados |

**No se integran** (una línea cada uno):
- **taste v2:** Node 22, fotos externas y prohibiciones incompatibles. Solo
  sus "tells", como avisos.
- **impeccable:** Node, y se solapa con taste.
- **frontend-design de Anthropic:** se solapa con taste.
- **apple-hig-skills:** snapshot de HIG de febrero de 2025, anterior a Liquid
  Glass. Se escribe `ios.md` propio citando HIG.

## ADRs (con la skill `kiro-adr`)

Numerados por orden de ejecución, no por tema:

- **0016** — `make check` es la puerta de CI y las reglas de AGENTS.md las
  comprueba una máquina. *(Escrito: fase 1.)*
- **0017** — Errores y avisos de HTMX: un contrato, no una página por respuesta,
  más el escapado de `.jinja`. *(Escrito: fase 1.)*
- **0018** — Constitución de diseño y tubería única. *(Fase 2.)*
- **0019** — uupm vendorizado, con overlay y sin skill competidora. *(Fase 3.)*
- **0020** — Kit iOS, `surface="auto"` y `fallback="system"`; actualiza ADR-0014.
  *(Fase 4.)*
- **0021** — Fuentes externas: skillui externo, extractor nativo y candados.
  *(Fase 5.)*
- **Además:** ADR-0013 deja constancia de que Kiro sigue taste v1, fijado por SHA, y
  corrige "tres skills vendorizadas" → cinco. *(Hecho en la fase 1.)*

## Riesgos

| Riesgo | Mitigación |
|---|---|
| uupm cambia sus columnas | SHA fijado y test de cabeceras de CSV: falla en el paso de vendorizado, no en un proyecto |
| taste sigue evolucionando hacia v2 | SHA fijado; v2 solo como avisos |
| skillui sin mantenimiento (último push en mayo) o cambia su formato | Fixtures versionados, adaptador tolerante y extractor nativo como respaldo |
| Falsos positivos de R13 | Avisos relajables, nunca errores en CI |
| Las variantes `dark:` de Basecoat con `auto` | Verificación visual obligatoria en la fase 4; respaldo `theme-auto.js` |
| Los tests de suelo UX rompen proyectos ya generados | Solo reglas de la categoría 1, que son de verdad obligatorias. Se documenta en CHANGELOG `[MIGRACIÓN]` |
| Coste de contexto | La IA consulta uupm por CLI y nunca lee los CSV; los catálogos son `.md` que se leen bajo demanda |

## Verificación

1. **Cada fase:**
   - `make check` en verde: lint, tipos, css, design-check, archcheck, tests y
     migraciones.
   - El workflow `e2e-setup` (los 3 sabores) genera un proyecto y corre su
     `make check`.
2. **archcheck:** los fixtures buenos y malos por regla; el `app/` real
   limpio; una excepción sin motivo no cuenta.
3. **HTMX:** con TestClient, con y sin `HX-Request`, para 403, 404, 422 y 500
   (toast OOB y `HX-Reswap`). Una 303 con flash se ve en la página siguiente.
4. **Tubería:** las cuatro entradas sobre un proyecto temporal deben acabar con
   contrato válido, `design-check` sin errores y `make design build`
   idempotente:
   - `make design-init preset=ios`;
   - `make design-advise q="dashboard fintech"`;
   - el fixture de Refero;
   - la web local.
5. **uupm:** los 192 tipos de producto dan un contrato válido, y el overlay
   cubre todas las filas.
6. **Visual:**
   - `make dev` y Chrome sin interfaz por CDP (la extensión no llega a
     localhost en esta máquina; evitar `pkill -f`);
   - capturas de `/`, `/notes` y `/_design` a 375, 768, 1024 y 1440 px;
   - `ios` en claro y oscuro;
   - la página sin JS y con reduced-motion.
7. **El KPI de convergencia del plan anterior,** ampliado con `ios` y
   `estandar-shadcn`: N contratos dan capturas distintas en layout, tipografía
   y superficie.

## Archivos críticos

- **Fase 1:**
  - `app/main.py`, `app/hypermedia.py` (nuevo) y `app/templating.py`;
  - `app/routers/auth.py` y `app/services/consent.py`;
  - `Makefile`, `.github/workflows/ci.yml` y `.pre-commit-config.yaml`;
  - `scripts/archcheck.py` (nuevo) y `tests/archcheck/`;
  - `AGENTS.md`, `.claude/skills/kiro-feature/SKILL.md` y `base.html`.
- **Fase 2:**
  - `app/design_engine/{contract,checks,presets,rules,brief}.py`;
  - `scripts/design.py`;
  - `.claude/skills/kiro-design/SKILL.md` y `references/constitution.md`;
  - `DESIGN.md`.
- **Fase 3:**
  - `scripts/vendor_uupm.py`;
  - `.claude/skills/kiro-design/uupm/` y `uupm-kiro/compat.csv`;
  - `app/design_engine/{advisor,compiler,palette}.py`;
  - `tests/test_ux_floor.py`;
  - `.claude/commands/{kiro-design-review,kiro-redesign,kiro-init}.md`.
- **Fase 4:**
  - `app/design_engine/{contract,palette,fonts,runtime}.py`;
  - `app/static/css/kits/ios.css` y `app/static/js/theme-auto.js`;
  - `app/templates/components/ios/` y `partials/headers/ios-bar.html`;
  - `references/{ios,type-pairings}.md`.
- **Fase 5:**
  - `app/design_engine/{external_md,reference}.py`;
  - `scripts/reference.py`;
  - `.claude/commands/kiro-style.md`.
- **Fase 6:**
  - `app/schemas/base.py`, `components/form.html.jinja`;
  - `app/routers/{auth,notes}.py`.
- **Fase 7:**
  - `app/design_engine/{contract,compiler}.py`;
  - `references/archetypes.md`, `components/states.html.jinja`.

---

## Informe de ejecución

### Fase 1 — hecha (14-10-2026)

`make check` en verde con **698 tests** (569 al empezar). Verificado además en un
Chrome real por el protocolo DevTools: htmx carga la configuración del `<meta>`, un
404 y un fallo de CSRF producen un toast sin tocar el contenido, Basecoat lo
inicializa y lo cierra solo a los ~5 s, un 400 se intercambia y un 502 no.

**Lo que salió y no estaba en el plan** (los tests nuevos lo destaparon):

1. **Jinja no escapaba nada de lo que vive en archivos `.jinja`**: las macros de
   Basecoat y `components/form.html.jinja`. Starlette usa `select_autoescape()`, que
   solo cubre `.html`, `.htm` y `.xml`. Se detectó al probar que el toast escapa su
   título. Corregido, con un test que recorre `app/templates/`.
2. **Una respuesta 500 salía sin CSP, sin `X-Frame-Options` y sin `X-Request-ID`**:
   Starlette la genera fuera de la pila de middleware. Corregido en el manejador.
3. **Regresión propia, atrapada al arrancar el servidor de verdad:** una edición mía
   borró `app = create_app()` al final de `app/main.py`. Habría roto `make dev`, el
   `Dockerfile` y producción, y ningún test lo veía porque todos llaman a
   `create_app()`. Restaurado y con un test que resuelve `app.main:app` con el
   importador de uvicorn.
4. **Un bug en mi propio `archcheck` (K6)**, atrapado por su test: `await` dentro de
   una función anidada contaba para la exterior.
5. **Los cuatro POST de autenticación** que re-renderizan un formulario tampoco
   declaraban `user` (la exploración solo había visto el GET).

**Desviaciones respecto al plan:**

- Los toasts siguen siendo OOB renderizado por el servidor, como se aprobó, pero se
  descartó explícitamente `HX-Trigger` + `toaster.toast()`: la API de Basecoat no
  escapa el texto. Queda en el ADR-0017.
- `htmx-config` no intercambia `[45]..` entero sino los códigos que la app emite, para
  que la página de error de un proxy (502) no acabe incrustada.
- K7 se aplica a todo handler que renderiza `pages/...`, también a los POST que
  re-renderizan el formulario (el plan solo hablaba de páginas).
- `tests/archcheck/` quedó como un único `tests/test_archcheck.py`: el resto de
  `tests/` es plano.
- Las referencias de taste-skill se comprobaron byte a byte contra upstream: los cinco
  archivos coinciden con `main` y con el último commit previo a la v2 (`9da1763`).

**Hueco cerrado después:** un fallo de red, un timeout o un 502 de un proxy dan ahora un toast
(`kiro-htmx.js`, ADR-0017), verificado en Chrome.

### Fases 2 a 7: hechas (14-10-2026)

`make check` en verde. Todo lo prometido está implementado y probado; lo notable:

- **Fase 2:** constitución de diseño (`rules.py`, `constitution.md`), `DesignBrief`, `propose` y
  `design-apply`, avisos `P1`-`P10`, `[rules] allow` y el preset `estandar-shadcn`.
- **Fase 3:** uupm v2.15.0 vendorizado con lock por hash y solapamiento (fuentes frente a
  Fontsource, paletas frente al compilador, estilos frente a presets), `make design-advise` /
  `design-ux`, bloque `kiro:a11y` (zona de pulsación de 44 px, comprobada con emulación táctil),
  `tests/test_ux_floor.py` y un barrido de los 192 tipos de producto.
- **Fase 4:** kit iOS, `surface = "auto"` (la variante `dark` de Tailwind se redefine: sin JS),
  `fallback = "system"` y materiales con opacidad calculada. Verificado en Chrome real.
- **Fase 5:** `/kiro-style`, `make design-reference` (md, url, skillui, carpeta de skillui),
  lector tolerante de Refero/Stitch.
- **Fase 6:** `validate_form`/`FormResult`, macros `textarea`/`select`/`checkbox`, cookie flash.
- **Fase 7:** `[structure] density` compilada (`section-y`, `gap-rhythm`, `min-h-row`) y
  `components/states.html.jinja`.

**Desviaciones respecto al plan:**

- **El CSS del kit iOS va dentro del bloque compilado** y no en `app/static/css/kits/ios.css`:
  un `@import` solo es válido antes del resto de reglas y el compilador es puro.
- **`surface = "auto"` no necesita `theme-auto.js`**: redefinir `@custom-variant dark` basta
  (comprobado con el CLI de Tailwind y en el navegador).
- **La densidad compilada se limita al ritmo** (tres medidas y tres utilidades), no a la forma.
- `/kiro-ux-audit` no existe: es `/kiro-redesign auditoría`.
- ADR renumerados por orden de ejecución: 0016 a 0023.

**Hueco cerrado después:** un fallo de red, un timeout o un 502 de un proxy dan ahora un toast
(`kiro-htmx.js`, ADR-0017), verificado en Chrome.
