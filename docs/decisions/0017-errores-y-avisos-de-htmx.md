# 0017 — Errores y avisos de HTMX: un contrato, no una página por respuesta

**Estado:** Aceptada · 2026-10-14

## Contexto

Cuatro cosas, comprobadas en el código y en un Chrome real, hacían que un error en
una petición HTMX no se viera o saliera mal:

1. **htmx 2 no intercambia ninguna respuesta 4xx/5xx por defecto.** Un `hx-delete`
   sobre una nota ajena daba 403 y no pasaba nada visible. Lo mismo para la regla de
   AGENTS.md "un formulario rechazado se vuelve a pintar con un 400".
2. **Los manejadores de error devolvían la página completa** (`pages/404.html`) a
   una petición que iba a incrustarla en un rincón de la página.
3. **Un parámetro mal formado devolvía el JSON 422 de FastAPI** en una web de
   páginas HTML.
4. **La respuesta 500 salía sin cabeceras de seguridad y sin `X-Request-ID`.**
   Starlette contesta una excepción no capturada desde *fuera* de la pila de
   middleware. Un test nuevo lo destapó: AGENTS.md prometía lo contrario.

Y una quinta, más grave, que apareció al escribir el test de los toasts: **Jinja no
escapaba nada de lo que vive en archivos `.jinja`.** `Jinja2Templates` de Starlette
usa `select_autoescape()`, que solo escapa `.html`, `.htm` y `.xml`; las macros de
Basecoat y `components/form.html.jinja` (que repite en cada formulario lo que el
usuario escribió) se renderizaban en crudo.

Alternativas reales para los avisos:

- **Cabecera `HX-Trigger` y un `toaster.toast({...})` en JavaScript.** Funciona sobre
  cualquier código de estado, pero la API de Basecoat 1.0.2 construye el toast con
  una plantilla de cadena sin escapar `title` ni `description`: XSS en cuanto el
  texto incluya algo del visitante. Y es JavaScript propio que mantener.
- **Intercambiar todo `[45]..`.** Es la receta de la documentación de htmx, pero una
  página de error de un proxy (502, 504) acabaría incrustada en la página.
- **Responder 200 con el toast.** Miente a los logs, a los monitores y a cualquier
  cliente que mire el código.
- **`render_block` para fragmentos de la misma plantilla.** Ya existe el camino
  `partials/`; tener dos maneras de hacer lo mismo es ambigüedad para la IA.

## Decisión

1. **`app/hypermedia.py`**: `error_response` devuelve la página a una navegación y
   un toast a una llamada HTMX, con el mismo código de estado. Un enlace con
   `hx-boost` y una restauración de historial mandan `HX-Request` pero intercambian
   el cuerpo entero: reciben página. `toast_response` es la misma pieza para un
   mensaje propio.
2. **El toast es HTML renderizado por el servidor**: `HX-Reswap: none` más un swap
   fuera de banda (`hx-swap-oob="beforeend"`) a `#toaster`. Basecoat inicializa y
   cierra cualquier `.toast` que aparezca en la página; no hay JavaScript nuestro y
   Jinja escapa el texto. Las respuestas llevan `Vary: HX-Request`.
3. **`base.html` declara qué códigos intercambia htmx** (`htmx-config`): los que esta
   app emite (400, 403, 404, 409, 422, 429, 500). Un 502 de un proxy sigue sin tocar
   la página. Un código nuevo se añade ahí.
4. **Un parámetro mal formado es una página 400** (o un toast), no un JSON.
5. **El manejador del 500 pone a mano `X-Request-ID` y las cabeceras de seguridad**
   (`apply_security_headers`, compartida con el middleware).
6. **El escapado cubre `.jinja`**: el entorno de Jinja se construye con
   `select_autoescape` incluyendo esa extensión. El correo de texto plano ya
   desactivaba el escapado con un `overlay`. Un test recorre `app/templates/` y
   falla si aparece una extensión nueva sin decidir.

## Consecuencias

- **Un formulario `hx-post` que se rechaza con 400 funciona sin más**, porque htmx
  lo intercambia. A cambio, un manejador no debe contestar 4xx/5xx a una llamada
  HTMX con un documento entero: lo hacen los manejadores globales y hay que
  respetarlo en los propios.
- **Un fallo de red, un timeout o un 502 de un proxy no pasan por la app**, así que el
  servidor no puede avisar. Lo cubre `app/static/js/kiro-htmx.js` (un archivo global, no
  un script por página): escucha `htmx:sendError`, `htmx:timeout` y `htmx:responseError` y
  pinta el mismo toast de Basecoat. Solo para lo que el servidor no cubre (un código que
  htmx intercambia ya trae su toast), sin repetir el aviso mientras el anterior siga a la
  vista, y con `textContent`: nunca `innerHTML` con texto variable. Verificado en Chrome:
  sin red, 502, timeout, un 404 (un solo aviso) y cierre automático.
- **El escapado de `.jinja` cambia la salida de las macros** para quien pasara HTML
  en un argumento sin `| safe`. Las de Basecoat ya marcan lo que es marcado
  (`title | safe`, `trigger | safe`...), así que se comportan como su autor pensaba.
- **No usar `toaster.toast({...})` con texto del visitante**: es la API que no
  escapa. Está dicho en `app/hypermedia.py` y en AGENTS.md.
