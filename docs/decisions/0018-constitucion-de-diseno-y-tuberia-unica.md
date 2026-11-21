# 0018 — Constitución de diseño y una sola tubería hacia el contrato

**Estado:** Aceptada · 2026-10-14

## Contexto

La dirección visual de un proyecto puede llegar por cinco caminos: un preset,
taste-skill, el asesor uupm (nextlevelbuilder), un brief pegado (Refero o texto
libre) y una web de referencia (skillui). Saben cosas distintas y se contradicen:
uupm da URLs de Google Fonts (la CSP las bloquea), pide vidrio donde taste-skill v2
lo prohíbe, ordena las secciones de una landing de una forma y taste prohíbe tres
tarjetas iguales, extrae varios acentos donde Kiro admite uno.

El plan anterior resolvía eso con "si chocan, decide el humano", que significa
preguntar cada vez. Y proponía cinco tuberías hacia `design.toml`, una por fuente:
cinco sitios donde escribir el contrato y cinco conjuntos de bugs.

## Decisión

1. **Una constitución**: cada fuente es dueña de un dominio, no del diseño entero.
   Los dominios son las diez categorías de la guía de uupm, en su orden de
   prioridad (accesibilidad, táctil, rendimiento, estilo, layout, tipografía y
   color, animación, formularios, navegación, gráficos). Las tres primeras son el
   **suelo**: nunca se relajan. El resto es gusto y un proyecto puede permitir una
   regla a propósito. Está en `references/constitution.md` y, como código, en
   `app/design_engine/rules.py`; un test impide que el documento cite una regla
   que no existe.
2. **Los choques conocidos están resueltos de antemano** en una tabla, una sola vez.
   Lo que no esté en la tabla se pregunta al humano una vez y se anota en
   `DESIGN.md` («Decisiones de diseño»), para no volver a preguntarlo.
3. **Una tubería**: toda fuente produce un `DesignBrief`; `propose` (pura) lo filtra y
   lo traduce a un contrato: un solo acento que pasa AA (o el hex más cercano que
   sí, registrado como `D1`), cada fuente tipográfica a su familia de Fontsource o a
   la del catálogo por categoría, el tema de Basecoat derivado del radio y la
   densidad. Nada se descarta en silencio: es una `Decision`, una `nota` o un
   punto «sin resolver».
4. **Proponer y aplicar son dos pasos.** `make design-propose` escribe
   `.design/proposals/<nombre>.{json,toml,md}` sin tocar el proyecto;
   `make design-apply` lo aplica, guarda una copia en `.design/backup/`, añade lo
   decidido a `DESIGN.md` y compila. No sustituye una identidad propia sin `force=1`.
5. **`[rules] allow` en `design.toml`** permite reglas de gusto a propósito, y
   `design-check` lo recuerda en cada ejecución. El preset **`estandar-shadcn`** es
   el aspecto Basecoat elegido a propósito: es la única forma de tener lo genérico
   sin aviso.
6. **Los patrones genéricos** (hero centrado con tres tarjetas, muro de logos,
   carrusel de testimonios, precios en tres columnas, `h-screen`, desenfoque fuera
   de una barra, emoji, vocabulario de plantilla, raya larga, nombres de relleno)
   son avisos `P1`-`P10`, no errores.

## Consecuencias

- **Son heurísticas sobre el marcado**, no un análisis de la página renderizada. Por
  eso son avisos y se pueden permitir. El desenfoque (`P6`) mira los ancestros de
  la etiqueta; un falso positivo se resuelve permitiendo la regla con un motivo.
- **El suelo no se negocia ni a petición del usuario**: `allow = ["D1"]` es un error
  de contrato. Si algún día hay que relajar el contraste, será otro ADR.
- **`estandar-shadcn` no cuenta como identidad distinta**: queda fuera de la prueba
  de que los presets difieren en varios ejes, a propósito.
- **El contrato crece solo si se usa**: `[rules]` no aparece en `design.toml` hasta
  que algo se permite, así que las referencias de los demás estilos no cambian.
- **`.design/` es un área de trabajo** (propuestas, copias, referencias extraídas) y
  está en `.gitignore`; la carpeta de Kiro es `.design/`, nunca `.kiro/`, que es la
  del IDE Kiro de AWS.
- Las fases siguientes cuelgan de esto: uupm, el kit iOS y las fuentes externas
  producen `DesignBrief` y no escriben el contrato por su cuenta.
