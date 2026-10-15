---
description: First command to run in a freshly generated Kiro project — fills PROJECT.md and DESIGN.md (brand, three contrasted design directions, signature) and design.toml, and explains the two ways to develop from here
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

2. **Identidad visual.** Sin esto, todos los proyectos de Kiro salen iguales:
   mismo gris, misma cabecera, mismas tarjetas. Lee
   `.claude/skills/kiro-design/SKILL.md`, `DESIGN.md` y `design.toml`. Si
   `DESIGN.md` todavía tiene `TODO` (o `make design-check` dice que `design.toml`
   sigue en los valores por defecto), hazlo en estas cuatro fases.

   ### 2.1 Pregunta lo que solo el usuario sabe

   Un único bloque de preguntas cortas (no una por mensaje):

   - **Marca.** ¿Tiene un color principal (hex)? ¿Uno secundario? Si no tiene
     ninguno no inventes: lo propondrás en las direcciones.
   - **Referencias.** Webs o marcas que le gustan, y qué NO quiere que parezca.
   - **Público y tono** (sale de `PROJECT.md`; confírmalo, no lo preguntes de
     nuevo si ya está).
   - **Modo oscuro.** Claro, solo oscuro (`surface = "dark"`), o crema/papel.
     Las apps finales no ofrecen selector de tema: es una decisión del proyecto.
   - **Logo.** Una ruta de archivo o una URL (SVG preferido; PNG solo si es
     cuadrado 1:1). Si no tiene, sigue: la cabecera mostrará solo el nombre.

   ### 2.2 Propón TRES direcciones contrastadas

   No una lista sesgada a lo sobrio: tres caminos que se noten distintos al
   primer vistazo. Para cada una, en un bloque corto:

   | | Segura | Atrevida | Experimental |
   |---|---|---|---|
   | Idea | La que no se equivoca para este público | La que se arriesga con criterio | La que el sector no espera |

   Cada dirección lleva **todo** esto, con valores reales (no adjetivos):

   - **Nombre y estilo base**, de la tabla de la skill (`minimalista`,
     `suave-premium`, `brutalista`, `institucional`, `expresivo`,
     `panel-de-datos`, `editorial`, `organico`, `neo-brutalista`, `retro-y2k`,
     `oscuro-tecnologico`, `ios`; y `estandar-shadcn`, que no es una dirección sino el
     aspecto Basecoat elegido a propósito: ofrécelo solo si el usuario pide
     explícitamente "el shadcn estándar", nunca como la opción cómoda).
   - **Paleta:** primario (hex), neutros (`warm`/`cool`/`pure`/`tinted`),
     superficie (`light`/`cream`/`dark`), secundario si lo pide.
   - **Tipografía:** una pareja de `references/type-pairings.md` (las únicas
     instalables con `make font`).
   - **Tema de Basecoat y cabecera** (los de la tabla, o cambia uno con motivo).
   - **Arquetipos** de `references/archetypes.md`: un hero y dos secciones.
   - **Firma visual:** 2-3 gestos *inventados para este proyecto*, concretos y
     repetibles ("titulares serif a 12vw que se salen del borde"). No salen de
     ningún catálogo.
   - **Nivel de movimiento** (1-10) y por qué.

   **De dónde sale cada una** (todas pasan por la misma tubería, ver
   `references/constitution.md`):

   | Dirección | Origen |
   |---|---|
   | Segura | La base de uupm para el producto: `make design-advise q="<producto de PROJECT.md>" name=segura`. Lo que propone es lo que necesita ese tipo de producto |
   | Atrevida | Un estilo que contraste con la segura, filtrado por taste (dials, firma, anti-slop) |
   | Experimental | La referencia que traiga el usuario (un brief de Refero, una web, el DESIGN.md de una marca): `/kiro-style`, con `base=.design/briefs/segura.json` para vestirla sobre la base de uupm. Si no trae ninguna, el estilo que el sector no esperaría |

   Cada propuesta se revisa (`.design/proposals/<nombre>.md`) antes de aplicarse con
   `make design-apply proposal=<nombre>`. Si lo que el usuario pide es el aspecto Basecoat de
   serie a propósito, ofrece `estandar-shadcn`.

   Reglas para que de verdad contrasten: que difieran en **al menos tres ejes**
   (estilo, superficie, tipografía, estructura de cabecera) y que ninguna sea la
   Basecoat gris con otro color de botón. Si el usuario dio un color de marca,
   las tres lo respetan y cambian todo lo demás; si no, cada una propone el suyo
   (nunca el morado por defecto).

   Enséñaselas **vistas**, no solo descritas: arranca `make dev` y da el enlace
   de `/_design?style=<estilo>&primary=<hex>&surface=<superficie>` de cada una
   (el `#` del hex va como `%23`; solo previsualiza paleta y radio; fuentes y tema se ven al aplicar). Deja que
   elija una, mezcle dos o describa la suya. Recomienda una y di por qué.

   ### 2.3 Aplícalo tú, no lo dejes como tarea

   Con la dirección elegida:

   1. `make design-init preset=<estilo> primary="<hex>"` (parte de los valores del
      estilo; añade `force=1` si `design.toml` ya tenía algo propio).
   2. Ajusta lo que difiera del preset, con los atajos:
      `make brand-colors primary=… neutral=… surface=… secondary=… radius=…`,
      `make font name="…" weights="…" role=display|body|mono`,
      `make design-set v="basecoat.theme=… structure.header=… motion.level=…"`.
      Si el compilador rechaza un color por contraste (WCAG AA), te dará el hex
      más cercano que sí se lee: úsalo y cuéntaselo al usuario.
   3. Con logo: `make logo src="<ruta o URL>"`. El script rechaza SVG con
      scripts y PNG no cuadrados; si falla, cuéntale el motivo y pide otro.
   4. Escribe `DESIGN.md` entero, respetando su estructura: estilo, referencias,
      los tres diales (el de movimiento = `motion.level`), la **firma visual**,
      los arquetipos, color, forma y tipografía, y "lo que NO debe parecer".
      No dejes ningún `TODO` salvo lo que el usuario dijo que no sabe.
   5. Si la cabecera elegida es `custom`, reescribe
      `app/templates/partials/headers/custom.html` según la firma (conservando
      sus dos `include`: `brand_mark.html` y `nav_auth.html`).
   6. Ejecuta `make design-check`: debe quedar sin errores. Un aviso de firma
      visual o de dial distinto significa que `DESIGN.md` y `design.toml` se
      contradicen: arréglalo.

   ### 2.4 Enséñaselo y pregunta

   Abre `/_design` y la portada (`/`) con `make dev`, y pregunta si se siente
   bien **antes de seguir**: ajustar ahora es barato. La portada actual es
   andamio a propósito; no la presentes como el diseño final.

   No inventes marca: si no sabe, deja la sección como pendiente y dilo. Si
   `DESIGN.md` ya está lleno (sin `TODO`) y `make design-check` pasa, no vuelvas
   a preguntar: dilo en una línea y pasa al punto 3.

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

4. Menciona también, en una línea cada uno:
   - `/kiro-check` — lint + tipos + tests + migraciones pendientes.
   - `/kiro-design-review` — después de construir una página: captura a 375 y
     1280 px, la compara con `DESIGN.md` y corrige hasta en dos pasadas.
   - `/kiro-redesign` — para una app ya construida que se parece a todas.

5. Cierra dejando claro que no hace falta memorizar nada de esto: el agente
   sabe cuándo aplica cada camino, y `PROJECT.md`, `DESIGN.md` y `design.toml`
   son lo único que de verdad hay que mantener al día.
