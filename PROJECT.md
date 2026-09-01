# __KIRO_PROJECT_NAME__

> **Este archivo es para la IA.** Es lo primero que lee un agente antes de
> escribir código, y es lo único que le impide inventarse tu dominio de negocio.
> `AGENTS.md` explica *cómo* se construye en Kiro; este archivo explica *qué*
> se está construyendo. Mantenlo al día: vale más que cualquier prompt largo.

__KIRO_PROJECT_DESCRIPTION__

- **Dominio de producción:** __KIRO_PROJECT_DOMAIN__
- **Base de datos:** `__KIRO_DB_NAME__`

---

## Qué es este proyecto

<!-- Descripción de negocio en 3-5 frases. Quién lo usa, para qué, y qué
     problema resuelve. Evita el lenguaje de marketing: la IA necesita hechos.
     Ejemplo: "Catálogo de proveedores de bodas en Guatemala. Las novias buscan
     y comparan proveedores; los proveedores pagan una suscripción mensual para
     aparecer. No hay pagos dentro de la plataforma: el contacto es por
     WhatsApp." -->

TODO: describir el proyecto.

## Entidades principales

<!-- Los modelos del dominio y sus campos clave, con las relaciones entre
     ellos. No hace falta el esquema completo (para eso está el código): sí
     hacen falta los nombres correctos y qué significa cada uno. -->

TODO: listar las entidades.

| Entidad | Qué representa | Campos clave |
|---|---|---|
| | | |

## Reglas de negocio

<!-- Las invariantes que el código debe respetar SIEMPRE. Son las que la IA no
     puede deducir leyendo el esquema.
     Ejemplos:
       - El stock nunca puede quedar negativo.
       - Un proveedor sin suscripción activa no aparece en las búsquedas.
       - Los precios se guardan en centavos, como enteros. Nunca float. -->

TODO: listar las reglas.

## Decisiones ya tomadas (no reabrir sin una razón nueva)

<!-- Sirve para que la IA no proponga una y otra vez algo que ya se descartó.
     Anota la decisión Y el motivo.
     Ejemplo: "No hay carrito persistente: el carrito vive en la sesión. Motivo:
     el ticket medio es de un solo artículo; persistirlo no compensa." -->

TODO: registrar decisiones.

## Fuera de alcance

<!-- Lo que este proyecto explícitamente NO hace. Igual de útil que lo que sí
     hace, porque frena a la IA cuando intenta ser servicial de más. -->

TODO: delimitar el alcance.
