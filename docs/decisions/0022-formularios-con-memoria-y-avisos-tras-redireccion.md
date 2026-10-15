# 0022 — Formularios con memoria y avisos tras una redirección

**Estado:** Aceptada · 2026-10-14

## Contexto

Cada formulario repetía lo mismo a mano: construir el modelo dentro de un `try`, atrapar
`ValidationError`, volver a pintar la plantilla con `form_errors(exc)` y copiar al contexto
cada valor escrito (`email`, `title`, `body`...), y cada plantilla repetía
`{% set errors = errors | default({}) %}`. Una IA que añadía un formulario copiaba el patrón
y se olvidaba de algo (un valor, la contraseña que no debe volver, el `aria-describedby`).
La macro `field` solo sabía pintar un `<input>`: el cuerpo de una nota de hasta 4000
caracteres se escribía en una sola línea. Y un POST/redirect/GET no podía decir "Nota
guardada": un 303 no lleva HTML.

## Decisión

1. **`validate_form(Modelo, **crudo) -> FormResult`** (`app/schemas/base.py`): nunca lanza;
   devuelve `data` si todo pasó, o `values` (lo escrito) y `errors` (el primer mensaje de cada
   campo). **Los campos cuyo nombre contiene `password`, `secret` o `token` nunca van a
   `values`**: lo que no se guarda no se puede devolver al navegador. `with_errors()` añade un
   error que no es de un campo. El handler decide el código de estado y nada más.
2. **Las macros leen el `FormResult`** (`form=form`): `field`, y las nuevas `textarea`,
   `select` y `checkbox`. Enlazan el error y la ayuda con `aria-describedby`, marcan
   `aria-invalid` y escapan todo (los `.jinja` se escapan desde el ADR-0017). Un `<input
   type="password">` se pinta vacío aunque alguien meta el valor a mano. `value=` y `errors=`
   se conservan: ningún proyecto existente se rompe.
3. **`flash(response, settings, "...")`** deja un aviso para la **siguiente** página: una cookie
   firmada con `itsdangerous` y sal propia (`kiro.flash`, sin poder usarse como sesión ni al
   revés), `HttpOnly`, `SameSite=Lax`, dos minutos. `render()` la lee, `base.html` la pinta
   como un toast de Basecoat dentro de `#toaster` y la respuesta la borra. Solo la consume una
   página completa (`pages/...`): un fragmento HTMX no se la come sin mostrarla.
4. **Alternativas descartadas**: guardar el aviso en la sesión de base de datos (una escritura
   por mensaje y una lectura por página para una cosa que dura segundos), un parámetro en la
   URL (un enlace compartido repetiría el aviso, y es texto que cualquiera puede escribir) y
   `HX-Trigger` más JavaScript (la API de toasts de Basecoat no escapa el texto: ADR-0017).

## Consecuencias

- **El eco de un formulario deja de ser una tarea del handler**: añadir un campo es añadirlo
  al modelo y a la plantilla. `archcheck` no obliga a usar `validate_form`; la skill y los dos
  ejemplos vivos (`auth.py`, `notes.py`) lo enseñan.
- **Una cookie más** (`flash`) existe unos segundos después de un POST; no lleva datos del
  usuario más que el texto del aviso, y firma y caducidad impiden fabricarla o reutilizarla.
- **El aviso es de un navegador, no de una persona**: si la redirección acaba en otra pestaña
  o en un fragmento, se muestra en la primera página completa que se pida (o caduca).
- **`FormResult` es genérico (PEP 695)** y `form.data` es `None` si falló: se comprueba
  `if form.data is None`, que es lo que mypy entiende como estrechamiento.
