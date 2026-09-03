# 0009 — CSRF de doble envío, validado como dependencia

**Estado:** Aceptada · 2026-09-03

## Contexto

Un formulario en el sitio de otra persona puede enviar un POST al tuyo, y el
navegador adjunta las cookies de tu usuario. Sin comprobación, esa petición es
indistinguible de una legítima.

`SameSite=Lax` en la cookie de sesión ya evita que el navegador la mande en un
POST desde otro sitio, y cubre el ataque en todos los navegadores actuales. Pero
es una defensa que depende enteramente de que el navegador la implemente bien y
de que nadie cambie ese atributo por otro motivo. Una segunda capa que no
dependa de eso cuesta poco.

Dos formas de montarla:

- **Token por sesión guardado en servidor.** Más estricto; obliga a un
  almacenamiento adicional y a invalidarlo con cada rotación.
- **Doble envío.** Un token aleatorio va en una cookie *y* también en el
  formulario. Quien ataca desde otro dominio puede lograr que el navegador mande
  la cookie, pero la política de mismo origen le impide leerla para copiarla en
  el formulario. Sin estado en el servidor.

Y una decisión de implementación con más consecuencias de las que parece: dónde
se valida. Lo natural es un middleware. **No funciona**: leer el formulario
dentro de un middleware consume el cuerpo de la petición, y el handler lo recibe
vacío. El síntoma —"el campo llega vacío"— aparece lejísimos de su causa.

## Decisión

**Doble envío, con la validación en una dependencia global de FastAPI.**

La cookie la pone un middleware (que solo escribe cabeceras, sin tocar el
cuerpo); la comprobación es una dependencia, que corre sobre el mismo objeto
`Request` que el handler y aprovecha el formulario ya parseado y cacheado por
Starlette. Al ser global, una ruta nueva nace protegida en vez de tener que
acordarse.

El token llega a la página desde el servidor: en un campo oculto para los
formularios y en `hx-headers` sobre el `<body>` para todo lo que haga HTMX. Como
ningún JavaScript necesita leerlo, la cookie es `HttpOnly`.

`create_app(enforce_csrf=False)` existe para los tests, igual que el cliente de
test de Django desactiva la comprobación por defecto. **No hay variable de
entorno equivalente**, a propósito: un despliegue no debe estar a una errata de
quedarse sin protección.

## Consecuencias

- Toda ruta nueva queda protegida sin hacer nada.
- Todo formulario necesita una línea: `{% include "components/csrf_field.html" %}`.
  Olvidarla da un 403 con un mensaje que explica qué pasó.
- **Es un `include` y no un macro por una razón concreta:** los macros de Jinja
  no ven el contexto de la plantilla salvo que se importen `with context`, y
  olvidarlo no da error — renderiza un token vacío y el formulario falla al
  enviarse. Un include recibe el contexto siempre. No lo conviertas en macro.
- **Coste real:** el doble envío no protege frente a quien pueda escribir
  cookies en tu dominio, por ejemplo desde un subdominio comprometido. Si algún
  día hay subdominios de terceros, esto hay que revisarlo.
- Los tests de un proyecto no ejercitan el CSRF salvo que lo pidan
  explícitamente. Es el mismo trato que hace Django, y la alternativa —que cada
  POST de cada test tenga que pedir antes un formulario— no compensa.
