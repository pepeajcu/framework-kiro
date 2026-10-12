# 0013 — Identidad visual: `DESIGN.md`, tokens y taste-skill

**Estado:** Aceptada · 2026-10-12

## Contexto

Basecoat entrega un aspecto neutro (shadcn gris). Es un buen punto de partida y
un mal acabado: dos proyectos Kiro, pedidos a una IA sin más contexto, salían
con la misma cabecera, las mismas tarjetas y la misma paleta. `PROJECT.md` ya
resuelve que la IA no invente el dominio; faltaba lo equivalente para la marca.

## Decisión

1. **`DESIGN.md`** en la raíz es el brief de diseño, hermano de `PROJECT.md`:
   estilo, tres diales (variance / motion / density), color, forma, tipografía,
   logo. Lo rellena `/kiro-init` en una entrevista y la IA lo lee antes de tocar
   una plantilla.
2. **El método es [taste-skill](https://github.com/Leonxlnx/taste-skill)** (MIT),
   adaptado en `.claude/skills/kiro-design/`. Se vendorizan tres de sus skills
   (`minimalist`, `soft`, `brutalist`) con su licencia; el resto se resume
   adaptado a nuestro stack, porque el original asume React, GSAP y fuentes de
   CDN.
3. **La identidad vive en tokens, no en plantillas.** `make brand-colors` deriva
   `--primary`, `--primary-foreground` y `--ring` (claro y oscuro) de un hex y
   los escribe en un bloque delimitado de `input.css`. El color del texto del
   botón se elige por contraste WCAG, no a ojo.
4. **El logo** va en `app/static/brand/logo.svg` o `logo.png` (cuadrado 1:1) y
   las plantillas lo piden con `brand_logo()`. `make logo` lo valida antes de
   copiarlo.

## Por qué así

- **No copiar taste-skill entero (89 KB).** Cargarlo en cada sesión cuesta
  contexto y la mitad no aplica (React, GSAP). Se carga el resumen y se abre la
  referencia del estilo elegido.
- **Validar el logo.** Un SVG se puede abrir directamente y ejecutar scripts. Se
  rechazan `<script>`, `on*=`, referencias externas y entidades, y el formato se
  detecta por los bytes, no por la extensión.
- **Bloque delimitado con marcadores** en vez de editar `:root` a mano: el
  comando es idempotente y no pisa lo que el usuario escriba fuera.
- **Fuentes locales.** La CSP es `font-src 'self'` (ADR-0010) y no hay CDN
  (ADR-0005).

## Consecuencias

- Hay un archivo más que mantener al día, y `/kiro-init` pregunta más.
- Los estilos `institucional`, `expresivo` y `panel-de-datos` no tienen
  referencia vendorizada: se definen por dials y reglas.
- Actualizar las referencias de taste-skill es manual (ver
  `.claude/skills/kiro-design/references/NOTICE.md`).
