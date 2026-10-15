# Diseño

> **Este archivo es para la IA**, igual que `PROJECT.md`. `PROJECT.md` dice
> *qué* se construye; este dice *cómo debe verse*. Lo rellena `/kiro-init`.
> El método está en `.claude/skills/kiro-design/SKILL.md` (basado en
> [taste-skill](https://github.com/Leonxlnx/taste-skill)).
>
> Tiene dos mitades que deben coincidir. **`design.toml`** es lo que una máquina
> puede aplicar (colores, fuentes, tema, cabecera, nivel de movimiento) y se
> compila con `make design build`. **Este archivo** es lo que hay que decidir:
> tono, referencias, los diales, los arquetipos y, sobre todo, la **firma
> visual**. `make design-check` avisa si se contradicen.
>
> Mientras tenga `TODO`, la IA no debe inventar una identidad visual: debe
> pedirte que lo rellenes.

## Identidad

- **Estilo:** TODO <!-- minimalista | suave-premium | brutalista | institucional | expresivo | panel-de-datos | editorial | organico | neo-brutalista | retro-y2k | oscuro-tecnologico | estandar-shadcn | ios | o una descripción propia -->
- **Referencias:** TODO <!-- webs o marcas que te gustan (opcional) -->
- **Público:** TODO <!-- quién lo usa: define el tono más que el gusto -->
- **Tono de los textos:** TODO <!-- ej. cercano y directo / sobrio y técnico -->

## Los tres diales (1–10)

| Dial | Valor | 1 = | 10 = |
|---|---|---|---|
| `DESIGN_VARIANCE` | TODO | simetría perfecta | caos artístico |
| `MOTION_INTENSITY` | TODO | estático | cinematográfico |
| `VISUAL_DENSITY` | TODO | galería, aireado | cabina, denso |

<!-- MOTION_INTENSITY es el `motion.level` de design.toml: deben coincidir. -->

## Firma visual

<!-- LO MÁS IMPORTANTE de este archivo. Dos o tres gestos que el proyecto se
     compromete a repetir en cada página. No salen de ningún catálogo: se
     inventan para este proyecto. Es lo que hace que dos proyectos del mismo
     estilo no se parezcan.

     Buenos: "titulares serif a 12vw que se salen del borde", "todo en
     monoespaciada y mayúsculas con un único acento ácido", "una rejilla fina
     siempre visible", "cada sección con su número en el margen".
     Malos: "moderno", "limpio", "profesional" (no se pueden repetir ni comprobar). -->

1. TODO
2. TODO
3. <!-- opcional -->

## Arquetipos

<!-- Elegidos de .claude/skills/kiro-design/references/archetypes.md. No
     repetir el mismo en dos secciones seguidas. -->

- **Hero:** TODO <!-- split | type-giant | bento | editorial | marquee | sticky-stack | horizontal-pan -->
- **Secciones:** TODO <!-- statement | numbered | spec-sheet | dark-band | faq … -->
- **Texturas:** TODO <!-- grain | grid | duotone | mesh | ninguna -->
- **Cabecera:** TODO <!-- sticky-blur | floating-pill | industrial-rule | terminal-bar | custom (= [structure] header) -->

## Color

<!-- Una sola paleta, un solo acento. Se aplica con
     `make brand-colors primary="#hex" [neutral=…] [surface=…] [secondary="#hex"]`,
     que escribe design.toml y compila los ~30 tokens (claro y oscuro) con
     contraste WCAG AA resuelto. Aquí se anota la decisión. -->

- **Primario (acento de marca):** TODO <!-- hex, ej. #0F766E -->
- **Secundario / apoyo:** TODO <!-- opcional; si no, ninguno -->
- **Neutros:** TODO <!-- warm | cool | pure | tinted. Uno solo -->
- **Superficie:** TODO <!-- light | cream | dark (dark = solo oscuro, sin selector de tema) -->

## Forma y tipografía

<!-- Las fuentes se instalan con `make font` (locales, de Fontsource, nunca CDN).
     Parejas probadas en .claude/skills/kiro-design/references/type-pairings.md -->

- **Radio de esquinas:** TODO <!-- recto (0) | suave (0.5–0.75rem) | píldora -->
- **Tema de Basecoat:** TODO <!-- vega nova maia lyra mira luma sera rhea (= [basecoat] theme) -->
- **Fuente de títulos:** TODO
- **Fuente de texto:** TODO
- **Fuente mono:** TODO <!-- opcional -->

## Logo

- **Archivo:** TODO <!-- app/static/brand/logo.svg o logo.png (PNG cuadrado 1:1).
                          Se importa con `make logo src="ruta-o-url"` -->
- **Dónde se muestra:** cabecera, favicon y correos.

## Lo que NO debe parecer

TODO <!-- ej. "no genérico de SaaS", "nada infantil". Frena a la IA tanto como
          lo que sí quieres. -->

## Decisiones de diseño

<!-- Lo que se decidió a propósito y no debe volver a preguntarse: una regla de
     gusto permitida (`[rules] allow` en design.toml) con su motivo, un color
     que tuvo que moverse para llegar a contraste, un choque entre fuentes de
     diseño resuelto. `make design-apply` añade aquí lo que decidió; a mano, una
     línea por decisión, con fecha y motivo. Accesibilidad, uso táctil y
     rendimiento no se relajan nunca: no se anotan aquí. -->

## Procedencia

<!-- De dónde salió cada dirección de diseño: un estilo, un brief, una web de
     referencia (URL y fecha). Se toma el lenguaje visual, nunca logos,
     imágenes, código ni fuentes. `make design-apply` añade aquí su línea. -->
