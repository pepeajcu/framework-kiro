# 0011 — Consentimiento por cookie y analítica server-side sin bloquear al usuario

**Estado:** Aceptada · 2026-09-07

## Contexto

v0.3.0 añade GTM, GA4 (Measurement Protocol) y Meta (Conversions API). Tres
decisiones estaban abiertas antes de escribir una línea de código: cómo se
gestiona el consentimiento, si GA4 y Meta comparten la forma de
`app/emails/` (un proveedor activo a la vez), y qué pasa cuando Google o Meta
no responden.

**Consentimiento.** Un CMS de consentimiento (Cookiebot, OneTrust...) trae su
propio script de terceros — justo lo que ADR-0005 y ADR-0007 evitan en el
frontend por sistema. Con dos decisiones posibles nada más (aceptar o
rechazar cookies de marketing) y sin necesidad de granularidad por categoría
todavía, una cookie propia con un endpoint HTMX cubre el caso sin añadir una
dependencia.

**Un proveedor o varios a la vez.** `EMAIL_PROVIDER` elige uno porque solo se
manda un correo por evento. Aquí no aplica: un proyecto puede querer GA4 y
Meta simultáneamente, así que forzar una elección con `match` habría sido
calcar un patrón que no encaja.

**Fallos de red.** `EmailDeliveryError` se relanza porque perder un correo de
recuperación dejas a alguien fuera de su cuenta — importa. Perder un evento de
analítica no tiene ese peso, y bloquear un login mientras Google responde
lo tiene al revés: le suma latencia real a algo que sí importa, por algo que
no.

## Decisión

**Cookie propia (`cookie_consent`), sin CMP.** `app/services/consent.py`
expone `has_marketing_consent(request)`; el banner (`partials/cookie_consent.html`)
es HTMX puro, sin fallback sin JavaScript — si GTM no puede cargar sin JS,
tampoco hace falta que el banner funcione sin él. El valor por defecto sin
decisión es "no": `has_marketing_consent` exige `"accepted"` explícito.

Ese flag gatilla dos cosas, no solo una:

- El snippet de GTM en `base.html` (`settings.gtm_id and consent ==
  "accepted"`).
- Las llamadas a GA4/Meta desde el servidor. `app/routers/auth.py` comprueba
  `has_marketing_consent(request)` antes de programar el evento — sin
  consentimiento, ni siquiera se construye el `AnalyticsEvent`.

**`app/analytics/` calca la forma de `app/emails/`** (`Protocol` +
adaptador por proveedor + doble en memoria para tests), pero
`get_analytics_sender()` devuelve un `CompositeAnalyticsSender` en vez de
elegir uno: arma la lista con cualquier proveedor que tenga su configuración
completa (ver el validador en `app/config.py`), y con ninguno configurado
queda vacío — ese es el "apagado", sin necesitar un adaptador nulo.

**Ningún adaptador relanza sus errores HTTP.** `Ga4AnalyticsSender.track()` y
`MetaAnalyticsSender.track()` atrapan `httpx2.HTTPError`, loguean y siguen —
justo lo contrario de `ResendEmailSender`. Y se disparan con
`background_tasks.add_task(...)` desde `login()`/`register()`, después de
`start_session()`: la cookie de sesión ya está puesta antes de que la
petición HTTP a Google o Meta siquiera empiece.

**Hashing de PII** (`app/analytics/hashing.sha256_lower`) es su propia
función, testeada aparte: strip + lowercase antes de hashear, porque Meta no
normaliza por su cuenta y un hash de `" Ana@X.com"` nunca hace match con uno
de `"ana@x.com"`.

## Consecuencias

- Un evento de analítica jamás puede tumbar ni ralentizar un login o un
  registro — como mucho, se pierde y queda un `logger.warning` en el log.
- Añadir un tercer proveedor (TikTok, LinkedIn...) es un adaptador nuevo más
  una línea en `_build_senders`, no un cambio de forma.
- El CSP de ADR-0010 se actualizó para abrir `script-src`/`img-src`/
  `connect-src` a los dominios de GTM y GA4 — ver `security_headers.py`. Solo
  importa cuando `GTM_ID` está configurado; sin él, esas directivas no
  habilitan nada que la CSP no permitiera ya bloquear en la práctica.
- Sin `client_id` propio (no hay gtag.js, solo el contenedor GTM), cada
  evento de GA4 sin `params["client_id"]` explícito recibe un `uuid4()` de un
  solo uso: llega al informe de GA4 pero no se puede hilar con otros hits del
  mismo visitante. Un proyecto con un tag GA4 dentro de GTM que lea la cookie
  `_ga` puede pasar ese valor y arreglarlo sin tocar el adaptador.
- La cookie de consentimiento no es un registro legal de consentimiento
  (marca de tiempo, versión del texto, IP). Para eso hace falta más que este
  ADR cubre; esto resuelve el gateo técnico, no el cumplimiento normativo
  completo.
