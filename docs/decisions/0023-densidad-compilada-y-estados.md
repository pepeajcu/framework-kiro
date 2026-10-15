# 0023 — Densidad compilada y los tres estados

**Estado:** Aceptada · 2026-10-14

## Contexto

Los tres diales de `DESIGN.md` eran prosa. `MOTION_INTENSITY` ya mandaba (es
`motion.level`), pero `VISUAL_DENSITY` no la leía nadie: un proyecto a 2 (una galería) y uno a 9 (una
cabina) tenían los mismos márgenes, porque cada plantilla escribía su propio `py-16`. El
análisis de la auditoría lo resumió bien: los diales no transforman la **estructura** de la
página. A la vez, uupm y taste exigen tres estados (cargando, vacío, error) que cualquier
lista, formulario o consulta necesita y que una IA se olvida de forma sistemática.

El ADR-0014 ya rechazó una solución: macros de página por estilo (`starters`), porque
convierten el catálogo en una jaula y dos proyectos del mismo estilo acaban iguales.

## Decisión

1. **Solo se compila el ritmo, no la forma.** `[structure] density` (1 a 10) emite el bloque
   `kiro:rhythm`: `--kiro-section-y`, `--kiro-gap`, `--kiro-row-h` y tres utilidades,
   `section-y`, `gap-rhythm` y `min-h-row`. Una plantilla dice `section-y` y sigue la densidad del
   proyecto sin saberla. La composición (el arquetipo) sigue siendo una receta que una persona
   o una IA elige, no una macro.
2. **El bloque se emite siempre**, también con la densidad por defecto (5), para que las
   utilidades existan desde el primer `make css` y el `input.css` del framework ya lo trae.
3. **Dos garantías del suelo se respetan**: en móvil la sección se estrecha (×0,65) y con
   puntero táctil una fila nunca baja de 44 px (`--kiro-row-h`).
4. **`design-check` compara `VISUAL_DENSITY` de `DESIGN.md` con `structure.density`**, como ya
   hacía con motion. Cada preset lleva su densidad en el contrato y un test exige que coincida con su dial.
5. **Los tres estados son macros estructurales** en `components/states.html.jinja`
   (`loading`, `empty`, `error_state`), sobre componentes de Basecoat y los tokens del
   proyecto: no tienen opinión visual propia, así que no hacen que dos proyectos se parezcan.
   `loading` es un esqueleto con la forma del resultado (no un spinner) y `role="status"`;
   `error_state` es `role="alert"` y admite un reintento HTMX.

## Consecuencias

- **La varianza sigue siendo criterio humano**: ningún valor del contrato cambia la composición.
  Es a propósito (ADR-0014).
- **Cambiar la densidad cambia todas las secciones que usen `section-y`**, y solo esas: una
  plantilla con `py-16` escrito a mano no la sigue. La skill y los arquetipos piden la utilidad;
  no hay regla de `archcheck` que prohíba un `py-16` (sería una opinión de estilo).
- **Una tabla de nueve escalones** (`rhythm.py`) decide los valores. Son monótonos y un test lo
  exige; si un proyecto necesita otros, sobrescribe las variables fuera del bloque.
- **El contrato crece un campo con valor por defecto**: un proyecto existente no cambia hasta
  que lo toca. La línea `density` solo aparece en `design.toml` cuando no es 5.
