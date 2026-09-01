---
description: Start a formal spec for a large feature — writes requirements.md
---

# Nueva especificación: $ARGUMENTS

Estás abriendo una especificación formal. Esto es para features grandes; para un
cambio normal usa la skill `kiro-feature` directamente y no gastes esta ceremonia.

## Pasos

1. Lee `PROJECT.md`. Si el dominio relevante no está descrito ahí, **pregunta al
   usuario antes de continuar** — no inventes entidades ni reglas.

2. Elige el número: mira `docs/specs/` y usa el siguiente correlativo de tres
   dígitos. Crea `docs/specs/NNN-<slug>/`.

3. Escribe `requirements.md` con esta estructura:

```markdown
# NNN — <Título>

## Problema
Qué no se puede hacer hoy y a quién le duele. Sin solución todavía.

## Requisitos

### R1 — <nombre>
CUANDO <situación>, EL SISTEMA DEBE <comportamiento observable>.
- Criterio de aceptación verificable
- Otro criterio

### R2 — <nombre>
...

## Fuera de alcance
Lo que esta spec explícitamente NO resuelve.

## Preguntas abiertas
Lo que hace falta decidir antes de diseñar. Si esta lista no está vacía,
para aquí y pregúntaselas al usuario.
```

Escribe cada requisito de forma **verificable**: si no se puede escribir un test
que lo compruebe, está mal redactado. "Debe ser rápido" no es un requisito;
"debe responder en menos de 300 ms con 10.000 registros" sí.

4. Muestra al usuario un resumen de los requisitos y las preguntas abiertas.
   **No pases a diseño ni escribas código todavía.** Cuando el usuario apruebe,
   continúa con `/spec-design`.
