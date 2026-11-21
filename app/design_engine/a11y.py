"""The accessibility floor, compiled into every project.

Accessibility, touch and performance are the first three categories of the uupm
guide and the part of the design that no brief, preset or `DESIGN.md` can relax
(`references/constitution.md`). The colour half of it is solved by the palette
compiler (WCAG AA). This is the rest that CSS can guarantee on its own:

- **Touch targets of 44 px** when the pointer is a finger. A button keeps its
  visual size; its pressable area grows around it. Fields and the label of a
  checkbox or radio do get taller: there is nothing to hide there.
- **A visible focus** for anything focusable, as a fallback with zero
  specificity: a component that draws its own ring keeps it.
- **More contrast on request** (`prefers-contrast: more`): borders and field
  outlines follow the text colour.
- **Reduced motion**: nothing keeps animating or transitioning for someone who
  asked for none. The 0.01 ms (not 0) keeps `transitionend` firing, which Basecoat's
  toasts and dialogs wait for to remove themselves.

It is emitted on every build, whatever `design.toml` says, between the markers
`kiro:a11y`. `tests/test_ux_floor.py` renders the pages and checks the markup half.
"""

from __future__ import annotations

from app.design_engine.blocks import render_block

TOUCH_TARGET_PX = 44

A11Y_CSS = f"""\
/* Suelo de accesibilidad: no depende del contrato (ver app/design_engine/a11y.py). */
@media (pointer: coarse) {{
  .btn {{
    position: relative;
  }}
  /* Un dedo necesita {TOUCH_TARGET_PX} px. El botón no cambia: se amplía su zona de pulsación. */
  .btn::after {{
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: max(100%, {TOUCH_TARGET_PX}px);
    height: max(100%, {TOUCH_TARGET_PX}px);
    transform: translate(-50%, -50%);
  }}
  :where(
      input:not([type="checkbox"], [type="radio"], [type="range"], [type="hidden"]),
      select,
      textarea
    ) {{
    min-height: {TOUCH_TARGET_PX}px;
  }}
  :where(label:has(> input[type="checkbox"], > input[type="radio"])) {{
    min-height: {TOUCH_TARGET_PX}px;
    display: inline-flex;
    align-items: center;
  }}
}}

/* Foco visible de respaldo: especificidad cero, así que el anillo de un componente prevalece. */
:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible {{
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}}

@media (prefers-contrast: more) {{
  :root:root,
  .dark.dark {{
    --border: color-mix(in oklab, var(--foreground) 55%, var(--background));
    --input: color-mix(in oklab, var(--foreground) 55%, var(--background));
  }}
}}

@media (prefers-reduced-motion: reduce) {{
  *,
  *::before,
  *::after {{
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }}
}}
"""


def render_a11y_block() -> str:
    return render_block("a11y", A11Y_CSS)
