# 0002 — SQLAlchemy síncrono, no async

**Estado:** Aceptada · 2026-09-01
**Revierte:** la intención original de `docs/framework/vision.md` §8, que decía "async".

## Contexto

FastAPI se asocia por defecto con `async def`, y el documento de visión asumía
SQLAlchemy asíncrono. Al contrastarlo con el objetivo del framework —minimizar
alucinaciones— la asunción no se sostiene.

El SQLAlchemy asíncrono concentra los errores más frecuentes de la IA en este
stack:

- `await` olvidados, que fallan lejos del punto donde se escribieron.
- `MissingGreenlet` al tocar una relación con carga perezosa: en async hay que
  declarar `selectinload`/`joinedload` explícitamente en cada consulta.
- Mezclar sesión síncrona y asíncrona en el mismo flujo.
- El `env.py` de Alembic requiere andamiaje asíncrono adicional.
- Los tests necesitan fixtures asíncronas y un event loop compartido.

Y el beneficio no aplica: en una app SSR el coste dominante son los viajes a la
base de datos, no la concurrencia de conexiones.

## Decisión

**SQLAlchemy 2.0 síncrono**, con modelos tipados (`Mapped[...]`) y handlers
declarados con `def`. FastAPI ejecuta los handlers síncronos en un threadpool
automáticamente, así que no bloquean el event loop.

`async` se reserva para **HTTP saliente** (`httpx`): envío de correo y eventos
de analítica server-side, donde sí es una espera de red pura.

## Consecuencias

- La carga perezosa de relaciones funciona sin ceremonia. Menos superficie de
  error para la IA y para el humano.
- El `env.py` de Alembic y las fixtures de test son los estándar, que es
  exactamente lo que más aparece en el material de entrenamiento de los modelos.
- Bajo mucha concurrencia el límite lo marca el tamaño del threadpool. Es un
  techo real pero lejano: si un proyecto lo alcanza, la respuesta es escalar
  horizontalmente antes que migrar a async.
- **Regla para agentes:** no conviertas handlers a `async def` "para que sea más
  rápido". Sin esperas de red reales dentro, es más lento, no más rápido.
