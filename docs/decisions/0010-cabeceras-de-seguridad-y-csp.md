# 0010 — Cabeceras de seguridad, y por qué la CSP lleva `'unsafe-inline'`

**Estado:** Aceptada · 2026-09-03

## Contexto

Varias cabeceras cierran ataques que no necesitan ningún fallo en la aplicación
para funcionar: enmarcar la página dentro de otra, adivinar el tipo de un
archivo subido, enviar un formulario a otro dominio. Son gratis y van siempre.

La Content-Security-Policy es otra cosa. La versión que de verdad frena el XSS
es `script-src 'self'`, sin `'unsafe-inline'`. Y ahí hay un conflicto con una
decisión anterior: **Basecoat (ADR-0004) trae handlers `onclick` en línea** en
sus componentes de diálogo, command y toast. Con una CSP estricta, el navegador
se niega a ejecutarlos y no dice nada: el diálogo simplemente no se abre.

Las salidas posibles:

1. **Editar las plantillas de Basecoat.** Son vendorizadas y se sobreescriben al
   actualizar. Descartado.
2. **`'unsafe-hashes'` con el hash de cada handler.** Los macros de toast y
   diálogo aceptan un `onclick` que pasa el proyecto: el conjunto de handlers no
   se conoce al construir. Descartado.
3. **CSP solo en modo report-only.** Una cabecera que no bloquea nada es teatro.
   Descartado.
4. **`'unsafe-inline'` en `script-src`,** documentado, con el resto de la
   política apretada.

## Decisión

**Opción 4.** La CSP se define como un diccionario editable en
`app/middleware/security_headers.py`, con `'unsafe-inline'` en `script-src` y el
motivo escrito encima.

Lo que sigue protegiendo, que no es poco:

- `default-src 'self'` — no se puede cargar un script de otro dominio. Es la
  defensa frente a un CDN comprometido o a una etiqueta inyectada que apunte
  fuera.
- `form-action 'self'` — un formulario no puede enviarse a otro sitio.
- `frame-ancestors 'none'` — la página no se puede enmarcar (clickjacking).
- `base-uri 'self'` — un `<base>` inyectado no puede reescribir todas las URLs
  relativas de la página.

HSTS solo se manda en entorno desplegado. Prometerle a un navegador que este
host es solo HTTPS desde un `localhost` que sirve en claro deja a quien
desarrolla fuera de su propio servidor hasta que limpie la lista HSTS del
navegador. Y nunca con `preload`: salir de esa lista lleva meses y una versión
del navegador.

## Consecuencias

- **Coste real y explícito:** un `<script>` inyectado en una página se
  ejecutaría. La CSP no es aquí la última línea de defensa contra XSS; lo es el
  autoescapado de Jinja2, que está activo por defecto y no hay que desactivar.
- Un proyecto que no use los macros de diálogo, command ni toast puede quitar
  `'unsafe-inline'` de `script-src` y quedarse con una CSP estricta. Son dos
  palabras en un diccionario.
- Cuando entre la analítica (v0.3.0), GTM pedirá abrir `script-src` y
  `connect-src` a sus dominios. Ese cambio se hace en el mismo diccionario y
  toca actualizar este ADR.
- Si algún día Basecoat quita sus handlers en línea, esto se revisa.
