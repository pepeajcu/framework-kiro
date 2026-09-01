---
description: Break an approved design into an ordered task list — writes tasks.md
---

# Tareas de la especificación: $ARGUMENTS

## Pasos

1. Lee `requirements.md` y `design.md` de la spec.

2. Escribe `tasks.md` como una lista ordenada de tareas ejecutables:

```markdown
# NNN — Tareas

- [ ] 1. <Tarea concreta>
      Archivos: app/models/x.py, app/models/__init__.py
      Cubre: R1
      Hecho cuando: `make migrations-check` pasa

- [ ] 2. <...>
      Depende de: 1
```

Reglas al trocear:

- Cada tarea toca **una capa**. Sigue el orden del golden path: modelo →
  migración → repositorio → schema → servicio → router → plantilla → test.
- Cada tarea nombra los **archivos concretos** que toca.
- Cada tarea cita **qué requisito cubre**. Un requisito sin tarea es un hueco;
  una tarea sin requisito es alcance inventado — quítala.
- Cada tarea dice **cómo se comprueba que está hecha**, con un comando cuando
  sea posible.
- Los tests no son una tarea final aparte: van junto a la capa que prueban.
- La última tarea siempre es `make check`.

3. Muestra la lista al usuario. Cuando la apruebe, ejecútala con `/spec-build`.
