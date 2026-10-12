---
description: First command to run in a freshly generated Kiro project — fills PROJECT.md and DESIGN.md (brand, style, logo) and explains the two ways to develop from here
---

# Arranque del proyecto

Corre esto la primera vez que se abre un proyecto recién generado por Kiro,
antes de pedir cualquier feature.

## Pasos

1. Lee `PROJECT.md`. Si todavía tiene los `TODO` del molde, entrevista al
   usuario para llenarlo — de forma conversacional, no como un formulario
   rígido. Cubre cada sección del archivo:
   - Qué es el proyecto: quién lo usa, para qué, qué problema resuelve.
   - Entidades principales y sus campos clave.
   - Reglas de negocio que el código debe respetar siempre.
   - Decisiones ya tomadas que no se deben reabrir sin un motivo nuevo.
   - Qué queda explícitamente fuera de alcance.

   Escribe las respuestas directamente en `PROJECT.md`, respetando su
   estructura. No inventes nada que el usuario no haya dicho — si una sección
   no aplica todavía, dilo y sigue a la siguiente.

   Si `PROJECT.md` ya está lleno (sin `TODO` pendientes), no vuelvas a
   preguntar: dilo brevemente y pasa al punto 2.

2. **Identidad visual.** Lee `DESIGN.md`. Si todavía tiene `TODO`, entrevista
   al usuario para llenarlo, también de forma conversacional y en un solo
   bloque de preguntas cortas (no una por mensaje). El método está en
   `.claude/skills/kiro-design/SKILL.md`; léelo antes de preguntar. Cubre:

   - **Colores de negocio / marca.** ¿Tiene un color principal (hex)? ¿Uno
     secundario? Si no tiene ninguno, propón dos o tres paletas coherentes con
     el sector de `PROJECT.md` (un acento sobre neutros, nunca el morado por
     defecto) y deja que elija.
   - **Estilo.** Ofrece las opciones de `kiro-design` con una línea cada una y
     recomienda una según el público: `minimalista` (Notion/Linear),
     `suave-premium` (calmado, caro), `brutalista` (rejilla dura, tipografía
     enorme), `institucional` (sobrio, de confianza), `expresivo` (agencia,
     lanzamiento) o `panel-de-datos` (back-office denso). Puede mezclar
     o describir el suyo. De ahí salen los tres diales (variance / motion /
     density).
   - **Referencias.** Webs o marcas que le gustan, y qué NO quiere que parezca.
   - **Modo oscuro.** Sí, no, o solo oscuro.
   - **Logo.** ¿Tiene? Pídele una ruta de archivo o una URL (SVG preferido; PNG
     solo si es cuadrado 1:1). Si no tiene, sigue: la cabecera mostrará solo el
     nombre y se puede añadir después.

   Después, **aplícalo tú**, no lo dejes como tarea:

   1. Escribe las respuestas en `DESIGN.md` respetando su estructura.
   2. Con logo: `make logo src="<ruta o URL>"`. El script valida el formato
      (rechaza SVG con scripts y PNG no cuadrados); si falla, cuéntale el motivo
      y pídele otro archivo. Se guarda en `app/static/brand/` y la cabecera y el
      favicon lo usan solos.
   3. Con color primario: `make brand-colors primary="#hex"` (añade
      `radius=...` si el estilo lo pide: recto `0`, suave `0.5rem`). Escribe los
      tokens, compila el CSS y avisa si el contraste del botón queda por debajo
      de 4.5:1; en ese caso propón un tono cercano que lo cumpla.
   4. Si eligió fuentes propias, vendorízalas en `app/static/fonts/` (nunca CDN)
      como describe `kiro-design`.
   5. Muéstrale el resultado: arranca `make dev` y dile que abra la portada.
      Pregunta si se siente bien antes de seguir; ajustar ahora es barato.

   No inventes marca: si no sabe, deja la sección como pendiente y dilo. Si
   `DESIGN.md` ya está lleno (sin `TODO`), no vuelvas a preguntar: dilo en una
   línea y pasa al punto 3.

3. Explica al usuario, en su idioma, que hay dos formas de pedir una feature
   a partir de ahora:

   **Golden path directo** — para un CRUD, un campo nuevo, una página, un
   cambio normal. El agente sigue solo las 8 capas en orden: modelo →
   migración → repositorio → schema → servicio → router → template → test.
   No hay pausas para aprobar cada capa — se confía en el patrón.
   - No tiene comando. Se activa pidiendo la feature tal cual, en la
     conversación normal — no hay nada que escribir con `/`.

   **Desarrollo acompañado** — para una feature grande, con requisitos
   todavía no tan claros, ideas por explorar, ambigüedad real, o cuando se
   prefiere ir validando antes de que se escriba código. Es el mismo golden
   path por debajo, pero en tres paradas donde el agente espera aprobación:
   requisitos, diseño, tareas. Lo arranca el propio usuario, cuando lo
   necesite, con estos comandos — cada uno espera la aprobación del anterior,
   no se encadenan solos:
   - `/spec-new` — escribe los requisitos.
   - `/spec-design` — a partir de los requisitos aprobados, escribe el diseño.
   - `/spec-tasks` — a partir del diseño aprobado, escribe la lista de tareas.
   - `/spec-build` — ejecuta la lista de tareas aprobada.

4. Menciona también `/kiro-check`: corre lint + tipos + tests + migraciones
   pendientes, para cuando se quiera una verificación completa.

5. Cierra dejando claro que no hace falta memorizar nada de esto: el agente
   sabe cuándo aplica cada camino, y `PROJECT.md` y `DESIGN.md` son lo único
   que de verdad hay que mantener al día.
