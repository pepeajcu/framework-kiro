# Diseño

> **Este archivo es para la IA**, igual que `PROJECT.md`. `PROJECT.md` dice
> *qué* se construye; este dice *cómo debe verse*. Lo rellena `/kiro-init`.
> El método está en `.claude/skills/kiro-design/SKILL.md` (basado en
> [taste-skill](https://github.com/Leonxlnx/taste-skill)).
>
> Mientras tenga `TODO`, la IA no debe inventar una identidad visual: debe
> pedirte que lo rellenes.

## Identidad

- **Estilo:** TODO <!-- minimalista | suave-premium | brutalista | institucional | expresivo | panel-de-datos | o una descripción propia -->
- **Referencias:** TODO <!-- webs o marcas que te gustan (opcional) -->
- **Público:** TODO <!-- quién lo usa: define el tono más que el gusto -->
- **Tono de los textos:** TODO <!-- ej. cercano y directo / sobrio y técnico -->

## Los tres diales (1–10)

| Dial | Valor | 1 = | 10 = |
|---|---|---|---|
| `DESIGN_VARIANCE` | TODO | simetría perfecta | caos artístico |
| `MOTION_INTENSITY` | TODO | estático | cinematográfico |
| `VISUAL_DENSITY` | TODO | galería, aireado | cabina, denso |

## Color

<!-- Una sola paleta, un solo acento. Se aplica con
     `make brand-colors primary="#hex"`, que escribe los tokens en
     app/static/css/input.css. Aquí se anota la decisión. -->

- **Primario (acento de marca):** TODO <!-- hex, ej. #0F766E -->
- **Secundario / apoyo:** TODO <!-- opcional; si no, neutros -->
- **Neutros:** TODO <!-- cálidos | fríos | puros. Uno solo -->
- **Modo oscuro:** TODO <!-- sí | no | solo oscuro -->

## Forma y tipografía

- **Radio de esquinas:** TODO <!-- recto (0) | suave (0.5–0.75rem) | píldora -->
- **Fuente de títulos:** TODO <!-- local en app/static/fonts, nunca CDN -->
- **Fuente de texto:** TODO
- **Fuente mono:** TODO <!-- opcional -->

## Logo

- **Archivo:** TODO <!-- app/static/brand/logo.svg o logo.png (PNG cuadrado 1:1).
                          Se importa con `make logo src="ruta-o-url"` -->
- **Dónde se muestra:** cabecera, favicon y correos.

## Lo que NO debe parecer

TODO <!-- ej. "no genérico de SaaS", "nada infantil". Frena a la IA tanto como
          lo que sí quieres. -->
