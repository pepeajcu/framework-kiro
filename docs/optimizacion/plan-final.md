# Plan Final — Kiro: Identidad + Calidad UX con Triple Juez

> Fecha: 14 de octubre de 2026
> Estado: **sustituido por [`plan-v2.md`](plan-v2.md)** (14-10-2026). Se conserva
> como antecedente: el plan v2 conserva sus cinco ideas, pero añade una
> constitución de dominios, una tubería única y los cimientos del framework.
> Nada de este plan modifica el stack (FastAPI, SQLAlchemy sync, Jinja2, HTMX,
> Tailwind v4, Basecoat, cero Node.js). Solo añade capacidades al motor de
> diseño y a las skills del proyecto.

---

## Los tres jueces (arquitectura definitiva)

Toda entrada de diseño (presets, briefs pegados, skillui, uupm, navegador)
desemboca en un contrato único (`design.toml` + `DESIGN.md`). Los asesores
**proponen**; el contrato **decide**; los jueces **arbitran**.

| Juez | Rol | Cuándo | Bloqueante |
|---|---|---|---|
| **Contrato + `make check`** | La ley: validez, coherencia, accesibilidad (contraste AA) | Siempre | Sí (CI) |
| **uupm (NextLevelBuilder)** | El inspector de UX: calidad de oficio por industria, paletas, fuentes, estados, checklist | Al terminar cada página/feature + auditoría completa opcional | Sí |
| **taste-skill** | El director de arte: originalidad, firma visual, anti-slop | En la misma revisión | Sí |

**Ciclo de calidad:** construir → revisión (uupm UX + taste) → corregir →
segunda revisión → cierre solo con todo en verde.

**Separación de roles (evita contradicciones):**

| Juez | Pregunta que responde | Ejemplo |
|---|---|---|
| Contrato + check | ¿Se *puede* hacer? | Un color sin contraste AA → rechazado |
| uupm | ¿Está *bien hecha* la UX? | "Un dashboard fintech necesita X patrón, estados de carga, foco visible…" |
| taste-skill | ¿Tiene *personalidad*? | "Esto huele a plantilla genérica de IA" |

Si uupm y taste chocan, la palabra final la tiene el humano.

---

## Las 5 fases

### Fase 1 — Preset iOS/Apple *(rápido)*

- Preset `ios` en `app/design_engine/presets.py`:
  `neutral="pure"`, `surface="light"`, `radius="1rem"`, tema `luma`,
  cabecera `sticky-blur`, motion 6, tipografía Inter / Plus Jakarta Sans
  (SF Pro no está en Fontsource; ADR-0005 obliga a fuentes locales).
- Referencia nueva: `.claude/skills/kiro-design/references/ios.md`
  (barras translúcidas = `sticky-blur` + `backdrop-blur` solo en barras fijas,
  botones pill del tema `luma`, "liquid glass" aproximado con `color-mix` en
  OKLCH, diales V/M/D sugeridos).
- Registro en la tabla de presets de `kiro-design/SKILL.md` y en `/kiro-init`.
- Tests: extender `tests/test_design_engine.py` (compila, contraste AA, no
  cuenta como "default").

### Fase 2 — Lint de patrones genéricos (R13) *(rápido)*

- Registro de patrones prohibidos por defecto en
  `app/design_engine/checks.py`: héroe centrado + 3 tarjetas, muro de logos
  ("confían en nosotros"), carrusel de testimonios, pricing de 3 columnas
  idénticas, "badge + título + cards"…
- **Opt-in explícito**: si `DESIGN.md` declara *"minimalista estándar de
  shadcn"*, el lint se silencia con aviso (no en silencio). Lo genérico solo
  si se pide a propósito.
- Entra en `make check`.

### Fase 3 — `/kiro-style` (pegar briefs tipo Refero o texto libre) *(medio)*

- Comando `.claude/commands/kiro-style.md`: pegar brief → traducir a
  `DESIGN.md` (identidad, diales, firma visual, arquetipos, color, tipografía)
  → aplicar con `make design-init` / `brand-colors` / `font` / `design-set`
  → `make design build` → revisar en `/_design`.
- El brief original se guarda en una sección nueva de `DESIGN.md`
  ("Brief pegado") para trazabilidad y validación de coherencia.
- El flujo es agnóstico al formato: funciona con Refero u otro generador de
  prompts de estilo (refero.design no respondía al verificar; no es
  dependencia).

### Fase 4 — `kiro-reference` (web de referencia vía skillui) *(grande)*

- **skillui queda externo** (npm global, opcional; el usuario lo instala si
  quiere). Cero Node en el repo (ADR-0005 intacta). MIT, 2.4k estrellas,
  `github.com/amaancoderx/npxskillui`. Soporte indistinto de modo `default`
  (análisis estático) y `ultra` (Playwright).
- **Importador Python** `scripts/reference.py import --from <carpeta>`:
  - `tokens/colors.json` → `brand.primary` validado por contraste AA
    (+ `suggest_primary` si falla), neutros, superficie.
  - `tokens/typography.json` → equivalentes Fontsource (skillui baja Google
    Fonts; aquí se mapea y valida con `make font`).
  - `tokens/spacing.json` / radio → dial de densidad y `radius`.
  - `references/ANIMATIONS.md` (GSAP/keyframes) → propuesta de `motion.level`.
  - `references/LAYOUT.md` / `COMPONENTS.md` → arquetipos del catálogo.
  - **Propuesta primero**: reporte + diff; solo escribe con `--apply`
    explícito. Nunca pisa una identidad existente sin `--force`.
- **Plan B sin skillui**: extracción asistida con el navegador del entorno
  (misma skill, misma salida al contrato).
- **Candados**: extraer lenguaje visual, no copiar logos/imágenes/código
  verbatim; URL de referencia registrada en `DESIGN.md` (procedencia); la
  firma visual sigue siendo obligatoria (evita clones de Linear/Notion).
- Tests: salidas de ejemplo → el importador siempre produce un contrato
  válido.

### Fase 5 — uupm como Juez Principal *(grande, prioridad del usuario)*

Repo: `github.com/nextlevelbuilder/ui-ux-pro-max-skill` (136k estrellas, MIT).
Contenido útil: 79 estilos de UI, 192 reglas por industria, 192 paletas,
74 pares tipográficos, 34 patrones de landing, 119 guías de UX, checklist
de entrega. Su `search.py` es Python stdlib puro (sin dependencias ni red).

1. **Vendorizar** `search.py` + datos curados (estilos, paletas por industria,
   pares tipográficos, patrones) en `app/design_engine/advisor/`.
   Python stdlib, sin npm, sin red. MIT + NOTICE.
2. **Rol proponer**: `make design-advise q="landing de spa de lujo"` →
   propone un sistema de diseño completo (patrón + estilo + paleta +
   tipografía + efectos + anti-patrones + checklist). Se traduce al contrato:
   fuentes a Fontsource, colores por contraste AA; lo inexpresable se degrada
   al preset más cercano con nota en `DESIGN.md`.
3. **Rol revisor**: `/kiro-design-review` extendido con la pasada uupm
   (reporte unificado con la pasada taste): consulta por producto/industria
   del `PROJECT.md`, checklist de UX, observaciones concretas → la IA corrige
   → segunda vuelta. **Bloqueante** para cerrar la tarea.
4. **Alcance doble**: por feature en el día a día (dentro de
   `/kiro-design-review`) + auditoría UX completa opcional (`/kiro-ux-audit`).
5. Tests: 20 consultas de ejemplo → el advisor siempre produce un contrato
   válido (fuzz contra `parse_contract`).

---

## Orden de ejecución

**1+2 → 5 → 3 → 4**

Los quick wins primero (iOS + lint genérico); después uupm (prioridad del
usuario); luego briefs pegados; al final la extracción de webs de referencia.

---

## Decisiones registradas

- skillui se integra como herramienta externa opcional + importador Python
  propio. No entra Node al framework.
- El importador de skillui propone primero y aplica solo con `--apply`.
- La revisión uupm vive dentro de `/kiro-design-review` (un comando, dos
  pasadas, reporte unificado).
- La revisión uupm es bloqueante para cerrar una tarea.
- Alcance: por feature (diario) + auditoría completa (opcional).
