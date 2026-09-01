---
description: Design phase of a spec — writes design.md from approved requirements
---

# Diseño de la especificación: $ARGUMENTS

## Pasos

1. Localiza la spec en `docs/specs/`. Lee su `requirements.md` completo.
   Si quedan preguntas abiertas sin responder, **para y pregúntalas**.

2. Lee el código que se va a tocar. No diseñes a ciegas: mira los modelos,
   repositorios y plantillas que ya existen y que esta feature debe reutilizar.
   Lee también `docs/decisions/` para no proponer algo ya descartado.

3. Escribe `design.md`:

```markdown
# NNN — Diseño

## Enfoque
Cómo se resuelve, en un párrafo. Si hubo alternativas reales, di cuál se
descartó y por qué.

## Modelo de datos
Tablas nuevas y campos añadidos, con tipos y restricciones.
Relaciones. Índices necesarios y por qué.

## Capas
- Modelos: qué archivos
- Repositorios: qué métodos de consulta hacen falta
- Servicios: qué reglas de negocio se aplican y dónde
- Routers: qué rutas, qué devuelven
- Plantillas: qué páginas y qué fragmentos HTMX

## Reutilización
Qué código EXISTENTE se usa. Nombra archivos y funciones concretas.

## Riesgos
Qué puede salir mal. Migraciones destructivas, rendimiento, seguridad.
```

4. Verifica contra las reglas de `AGENTS.md`: SSR siempre, toda consulta en un
   repositorio, migración por cada modelo nuevo, nada de async.

5. Muestra el diseño al usuario. **Espera aprobación** antes de `/spec-tasks`.
