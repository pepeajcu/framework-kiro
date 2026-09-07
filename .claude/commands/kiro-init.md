---
description: First command to run in a freshly generated Kiro project — fills PROJECT.md and explains the two ways to develop from here
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

2. Explica al usuario, en su idioma, que hay dos formas de pedir una feature
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

3. Menciona también `/kiro-check`: corre lint + tipos + tests + migraciones
   pendientes, para cuando se quiera una verificación completa.

4. Cierra dejando claro que no hace falta memorizar nada de esto: el agente
   sabe cuándo aplica cada camino, y `PROJECT.md` es lo único que de verdad
   hay que mantener al día.
