---
description: Execute an approved task list, checking off tasks as they complete
---

# Ejecutar la especificación: $ARGUMENTS

## Pasos

1. Lee `tasks.md` de la spec, y también `design.md` para tener el contexto.
   Lee la skill `kiro-feature`: es el patrón que hay que seguir en cada capa.

2. Ejecuta las tareas **en orden**, una a una:
   - Implementa la tarea.
   - Comprueba su criterio de "hecho cuando".
   - Marca `- [x]` en `tasks.md` antes de pasar a la siguiente.

3. Si una tarea resulta estar mal planteada —falta información, el diseño no
   encaja con el código real, aparece un caso no contemplado— **para y díselo al
   usuario.** No improvises un rediseño a medio camino: actualiza `design.md`
   primero.

4. No te saltes tareas ni las reordenes por conveniencia. El orden existe porque
   cada capa depende de la anterior.

5. Al terminar, corre `make check` y arregla lo que falle.

6. Resume: qué se construyó, qué requisitos quedan cubiertos, y qué quedó
   pendiente si algo se quedó fuera.
