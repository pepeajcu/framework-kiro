# Changelog

Todas las versiones notables de Kiro se documentan aquí.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versionado según [SemVer](https://semver.org/lang/es/).

> **Cómo leer este changelog si vas a actualizar un proyecto existente**
> (ver [`docs/upgrading.md`](docs/upgrading.md)). Cada entrada lleva una etiqueta:
>
> - `[SEGURO]` — se puede traer con `git checkout upstream/main -- <ruta>` sin más.
> - `[MIGRACIÓN]` — requiere pasos manuales; los pasos están descritos en la entrada.
> - `[RUPTURA]` — cambia contratos existentes. Leer antes de traer nada.

## [Sin publicar] · Plan v2: cimientos, diseño multifuente y kit iOS

Siete fases (`docs/optimizacion/plan-v2.md`, ADR-0016 a ADR-0023). Las entradas van de la más
reciente a la más antigua. También corrige: `405` y `422` devuelven una página (o un toast)
y no el JSON de Starlette.

### Cimientos: reglas comprobadas, errores de HTMX y escapado

#### Añadido (después)

- `[SEGURO]` **`app/static/js/kiro-htmx.js`**: un fallo de red, un timeout o la página de error de
  un proxy (502, 503, 504) dan un toast («Sin conexión», «El servidor no responde», «La petición
  tardó demasiado») en lugar de un botón que no hace nada. Solo lo que el servidor no cubre; sin
  `innerHTML` con texto variable; sin repetir el aviso. Cierra el hueco que dejó el ADR-0017.

Primera fase del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0016](docs/decisions/0016-make-check-es-ci-y-reglas-comprobadas.md) y
[ADR-0017](docs/decisions/0017-errores-y-avisos-de-htmx.md).

#### Añadido

- `[SEGURO]` **`make archcheck`** (`scripts/archcheck.py`, solo librería estándar):
  trece reglas con identificador que comprueban las de AGENTS.md: SQL fuera de un
  repositorio (K1), `commit` fuera de `app/db.py` (K2), `fastapi` en una capa
  interna (K3), un router que escribe por un repositorio (K4), el entorno leído
  fuera de `config.py` (K5), `async def` sin `await` (K6), un handler de página sin
  `user` (K7), un modelo sin importar (K8) y, en plantillas, `extends` mal
  puestos, POST sin CSRF, colores a mano, clases de Basecoat 0.x y scripts o
  recursos externos (J1-J5). Cada violación dice archivo, línea y cómo arreglarla;
  una excepción exige motivo (`# kiro: allow K6 — motivo`).
- `[SEGURO]` **`app/hypermedia.py`**: una llamada HTMX que falla recibe un *toast*
  (mismo código de estado) en lugar de una página entera; una navegación sigue
  recibiendo la página. `toast_response(request, title=...)` para mensajes propios.
- `[SEGURO]` `pages/400.html`: un parámetro mal formado (`DELETE /notes/abc`) ya no
  devuelve el JSON 422 de FastAPI.
- `[SEGURO]` `tests/test_archcheck.py`, `tests/test_hypermedia.py` y
  `tests/test_templating.py`: 129 tests nuevos.

#### Cambiado

- `[MIGRACIÓN]` **`make check` es ahora lo que corre CI**: `lint types css archcheck
  test migrations-check` más el contrato de diseño (`allow_defaults=1`). CI llama a
  `make check` y añade `pip-audit` y Docker. Un proyecto con violaciones de
  arquitectura verá fallos nuevos: cada uno trae su arreglo.
- `[MIGRACIÓN]` **Jinja escapa también los archivos `.jinja`** (macros de Basecoat y
  `components/form.html.jinja`). Un argumento que contenga HTML a propósito debe
  pasar por `| safe` dentro de la macro, como ya hacen las de Basecoat.
- `[MIGRACIÓN]` Las respuestas 400, 403, 404, 409, 422, 429 y 500 se intercambian en
  HTMX (`<meta name="htmx-config">` en `base.html`). Si tu proyecto emite otro
  código para HTMX, añádelo ahí.
- `[RUPTURA]` `has_marketing_consent(cookie_value)` recibe el valor de la cookie, no
  el `Request`: un servicio no ve objetos HTTP. Quien lo llame pasa
  `request.cookies.get(CONSENT_COOKIE)`.
- `[MIGRACIÓN]` Los handlers `POST /login`, `/register`, `/forgot-password` y
  `/reset-password/{token}`, y el GET del formulario de restablecimiento, declaran
  `user: OptionalUser` (regla 10). Los que tengan una variable local `user` en tus
  propios handlers deben renombrarla.
- `[SEGURO]` El hook de mypy de `pre-commit` es local (`uv run mypy`), sin la lista de
  dependencias desfasada que lo hacía fallar; se añade el hook de archcheck.
- `[SEGURO]` La skill `kiro-feature` corrige un ejemplo al que le faltaba el import
  de `NotFoundError`, aclara que las lecturas pueden saltarse el servicio y las
  escrituras no, y señala `app/routers/notes.py` como el recorrido completo.
- `[SEGURO]` Las referencias vendorizadas de taste-skill quedan fijadas a un commit
  (`9da1763`): `main` pasó a ser una v2 sin diales, incompatible con varios estilos.

#### Corregido

- `[SEGURO]` **Seguridad: una respuesta 500 salía sin `Content-Security-Policy`, sin
  `X-Frame-Options` y sin `X-Request-ID`.** Starlette contesta una excepción no
  capturada fuera de la pila de middleware; el manejador del 500 pone ahora esas
  cabeceras a mano.
- `[SEGURO]` **Seguridad: el texto de un campo de formulario y el de un toast salían
  sin escapar** (`autoescape` no cubría `.jinja`). Ahora sí.
- `[SEGURO]` Un 403 o un 404 contestados a `hx-delete` y similares no se veían: htmx
  no intercambia 4xx/5xx por defecto. Un formulario `hx-post` rechazado con 400 tampoco.
- `[SEGURO]` Los POST de autenticación que vuelven a pintar el formulario con un 400
  mostraban la cabecera como si nadie hubiera entrado.

### Constitución de diseño y tubería única

Fase 2 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0018](docs/decisions/0018-constitucion-de-diseno-y-tuberia-unica.md).

#### Añadido

- `[SEGURO]` **`references/constitution.md`** y **`app/design_engine/rules.py`**: quién
  decide qué entre taste-skill, uupm, los presets, un brief y una web de
  referencia, con las diez categorías de la guía de uupm en su orden. Accesibilidad,
  uso táctil y rendimiento (el suelo) no se relajan; el resto se puede permitir.
  Los choques conocidos vienen resueltos.
- `[SEGURO]` **`[rules] allow = [...]`** en `design.toml` (opcional; no aparece hasta
  que se usa). `make design-set v="rules.allow=P1,P2"`. `design-check` lo recuerda
  en cada ejecución.
- `[SEGURO]` **Avisos `P1`-`P10` en `make design-check`** para los patrones que hacen
  que una página parezca generada: titular centrado con tres tarjetas, muro de
  logos, carrusel de testimonios, precios en tres columnas iguales, `h-screen`,
  desenfoque fuera de una barra, emoji, vocabulario de plantilla, raya larga y
  nombres de relleno.
- `[SEGURO]` **Preset `estandar-shadcn`**: el aspecto Basecoat elegido a propósito
  (permite los patrones genéricos). Doce estilos en total.
- `[SEGURO]` **`DesignBrief`, `propose()` y los comandos `make design-propose` /
  `make design-apply`**: toda fuente de dirección visual pasa por la misma
  tubería pura hacia el contrato, con un solo acento que pasa AA, fuentes de
  Fontsource, tema derivado del radio, y cada decisión anotada. `apply` guarda una
  copia, no pisa una identidad propia sin `force=1` y escribe lo decidido en
  `DESIGN.md`.
- `[SEGURO]` `DESIGN.md` gana las secciones **Decisiones de diseño** y **Procedencia**.
- `[SEGURO]` `.design/` (propuestas y copias) está en `.gitignore`.

#### Cambiado

- `[SEGURO]` La fixture `project` de los tests de diseño pasa a `tests/conftest.py`.

### uupm integrado y suelo de UX comprobado

Fase 3 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0019](docs/decisions/0019-uupm-vendorizado-con-solapamiento.md).

#### Añadido

- `[SEGURO]` **El asesor uupm** (nextlevelbuilder, MIT, v2.15.0) vendorizado en
  `.claude/skills/kiro-design/uupm/`: una lista cerrada de archivos pinada por commit y por
  SHA-256, Python estándar y CSV, sin red ni Node. **`make design-advise q="..."`** pide un
  sistema de diseño para el producto y lo guarda como propuesta; **`make design-ux q="..."
  domain=ux`** consulta sus guías. Su `SKILL.md` es `GUIDE.md`: `kiro-design` sigue siendo la
  única skill de diseño.
- `[SEGURO]` **`uupm-kiro/`**, uupm traducido una vez a lo que Kiro puede hacer: 91 fuentes
  suyas frente a Fontsource (con pesos), 192 paletas frente al compilador (AA, tono morado,
  saturación), 88 estilos frente a los presets. `make vendor-uupm` lo reconstruye.
- `[SEGURO]` **Suelo de accesibilidad compilado** (`kiro:a11y`, siempre emitido): zona de
  pulsación de 44 px con puntero grueso sin cambiar el tamaño visual del botón, foco visible
  de respaldo, `prefers-contrast: more` y `prefers-reduced-motion`. Enlace «Saltar al
  contenido» en `base.html`.
- `[MIGRACIÓN]` **`tests/test_ux_floor.py`**: renderiza cada ruta GET (anónimo y con sesión) y
  exige `lang`, `title`, un `h1`, un `main`, un nombre accesible para todo lo que se pulsa o
  se escribe, `alt`, `width` y `height` en las imágenes, zoom permitido y sin `tabindex`
  positivo. Una página que no los cumpla romperá `make check`. Las rutas con parámetro y los
  fragmentos HTMX se declaran al principio del archivo.
- `[SEGURO]` Regla `D6`: `design-check` avisa si hay otra skill de diseño que compite.
- `[SEGURO]` `/kiro-design-review` rehecho: tres pasadas (uupm, taste, kit) en un solo informe
  ordenado por la prioridad de uupm, a cuatro anchos (375, 768, 1024 y 1440 px). Un fallo del
  suelo bloquea sin límite de pasadas; el gusto tiene dos y se escala al usuario.
  `/kiro-redesign auditoría` solo informa. `/kiro-init` saca sus tres direcciones de la misma
  tubería.

#### Corregido

- `[SEGURO]` `propose` comprobaba el contraste del color secundario contra el primario *antes*
  de corregirlo, y por eso daba por irresolubles paletas válidas. Lo destapó el barrido de los
  192 tipos de producto.

### Kit iOS, `surface = "auto"` y fuente del sistema

Fase 4 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0020](docs/decisions/0020-kit-ios-superficie-auto-y-fuente-del-sistema.md).

#### Añadido

- `[SEGURO]` **Preset `ios`** y **kit iOS** (`[structure] kit = "ios"`): la escala de Dynamic
  Type de Apple HIG (17 px de cuerpo, 34 px de título grande), listas agrupadas, control
  segmentado, barra de pestañas, hoja modal y materiales translúcidos, más la cabecera
  `ios-bar`. Los componentes están en `components/ios.html.jinja` (HTML que funciona sin
  JavaScript, todo escapado). Referencia en `references/ios.md`; `/_design` enseña el kit.
- `[SEGURO]` **`surface = "auto"`**: claro por defecto y oscuro cuando el sistema lo pide, sin
  selector que mantener. Los tokens y los `dark:` de Basecoat siguen al sistema sin
  JavaScript (se redefine la variante `dark`).
- `[SEGURO]` **`fallback = "system"`** en una fuente: la del sistema primero (San Francisco en
  Apple, que una web no puede incluir) y la local después. No se precarga.
- `[SEGURO]` **Materiales con opacidad calculada**: la mínima que mantiene el texto en AA sobre
  un fondo blanco y sobre uno negro, porque Safari ignora `prefers-reduced-transparency`.
- `[SEGURO]` Los estilos de uupm «Liquid Glass» y afines se asignan al preset `ios`.

#### Corregido

- `[SEGURO]` La sección de tipografía de `/_design` desbordaba en horizontal en móvil
  (hijos de una rejilla sin `min-w-0`).

### Referencias externas

Fase 5 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0021](docs/decisions/0021-referencias-externas-un-lector-y-candados.md).

#### Añadido

- `[SEGURO]` **`/kiro-style`** y **`make design-reference`**: una dirección visual de fuera
  (el «Copy .md» de Refero Styles, el `DESIGN.md` de una marca, una web, la salida de skillui)
  se reduce a un brief y termina en una **propuesta** que se lee antes de aplicar. Un solo
  lector tolerante (`app/design_engine/external_md.py`) cubre Refero, skillui y el formato
  Stitch; `skillui.py` lee sus `tokens/*.json`; `scripts/reference.py` lee el CSS de una web
  (solo texto: ni imágenes ni fuentes) o envuelve skillui.
- `[SEGURO]` skillui es **opcional y externo** (Node queda fuera, ADR-0005): se ejecuta siempre
  con `--out .design/reference/<nombre> --no-skill --format design-md`, porque sin `--out`
  escribiría `DESIGN.md` y `CLAUDE.md` en la raíz del proyecto.
- `[SEGURO]` `make design-brief-schema`: el esquema JSON de un brief, para que la IA convierta
  un texto libre en uno validado.
- `[SEGURO]` Solo se acepta `http(s)` como URL de referencia; la procedencia (URL y fecha) se
  anota en `DESIGN.md`.

### Formularios con memoria y avisos tras una redirección

Fase 6 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0022](docs/decisions/0022-formularios-con-memoria-y-avisos-tras-redireccion.md).

#### Añadido

- `[SEGURO]` **`validate_form(Modelo, campo=valor, ...)`** y **`FormResult`**
  (`app/schemas`): nunca lanza; devuelve el modelo o lo escrito (sin contraseñas, secretos ni
  tokens) y el primer error de cada campo. `form.with_errors({...})` añade un error que no es de
  un campo (credenciales, un email ya usado).
- `[SEGURO]` **Macros de formulario con memoria**: `field(..., form=form)` y las nuevas
  `textarea`, `select` y `checkbox` leen valor y error del `FormResult`, enlazan el error y la
  ayuda con `aria-describedby` y escapan todo. Los argumentos `value=` y `errors=` siguen
  funcionando. Una contraseña no se rellena nunca.
- `[SEGURO]` **`flash(response, settings, "Mensaje")`** (`app/hypermedia.py`): el toast de un
  POST/redirect/GET. Cookie firmada (sal propia, 2 minutos) que `render()` muestra una sola vez
  en el siguiente página completa y borra; un fragmento HTMX no la consume.
- `[SEGURO]` `toast_response(..., replace_target=True)`: el elemento desaparece (un botón de
  borrar) y el toast aparece.

#### Cambiado

- `[MIGRACIÓN]` Los formularios de autenticación y el de notas usan `validate_form`: las
  plantillas reciben `form` en lugar de `errors` y los valores sueltos (`email`, `title`...). El
  cuerpo de una nota es ahora un `textarea`. Crear una nota dice «Nota guardada» y borrarla,
  «Nota eliminada». Un proyecto que copió esos patrones sigue funcionando con `value=`/`errors=`.

### Densidad compilada y estados

Fase 7 del plan de `docs/optimizacion/plan-v2.md`. Ver
[ADR-0023](docs/decisions/0023-densidad-compilada-y-estados.md).

#### Añadido

- `[SEGURO]` **`[structure] density`** (1 a 10, por defecto 5): `VISUAL_DENSITY` deja de ser
  un número que nada lee. El compilador emite un bloque `kiro:rhythm` con `--kiro-section-y`,
  `--kiro-gap` y `--kiro-row-h` y las utilidades de Tailwind **`section-y`**, **`gap-rhythm`**
  y **`min-h-row`**; en móvil la sección se estrecha y una fila no baja de 44 px con puntero
  táctil. Los arquetipos de `archetypes.md` usan `section-y`. Cada preset lleva su densidad.
  `make design-check` avisa si `DESIGN.md` y el contrato difieren; `make design-set
  v="structure.density=8"`.
- `[SEGURO]` **`components/states.html.jinja`**: `loading` (esqueleto, `role="status"`), `empty`
  (dice cómo llenarlo) y `error_state` (con reintento HTMX opcional). El ejemplo de notas los usa.

#### Cambiado

- `[SEGURO]` El preset `estandar-shadcn` pasa a densidad 5 (el ritmo de serie de Basecoat).

## [1.2.0] — 2026-10-13 · Motor de diseño

Cierra el problema que dejó la 1.1: la identidad solo cambiaba tres de unos treinta
tokens y la estructura de la página era siempre la misma, así que dos proyectos
con intenciones distintas salían casi iguales. Ver
[ADR-0014](docs/decisions/0014-motor-de-diseno.md) y
[ADR-0015](docs/decisions/0015-motion-vendorizado-por-niveles.md).

### Añadido

- `[SEGURO]` **`design.toml`**, el contrato de máquina de la identidad (color,
  neutros, superficie, radio, fuentes, tema de Basecoat, cabecera, nivel de
  motion), y **`make design build`**, que lo compila a bloques delimitados de
  `input.css`, fuentes locales y scripts. Idempotente; `make design watch`,
  `make design-set v="…"`, `make design-init preset=<estilo>`.
- `[SEGURO]` **Paleta completa derivada en OKLCH** (unos treinta tokens, claro y
  oscuro) con el contraste WCAG AA *resuelto* por construcción. Si un color de
  marca no puede llevar el texto del botón, el build falla y propone el hex más
  cercano que sí. Neutros `pure|warm|cool|tinted`, superficie `light|cream|dark`
  (`dark` = solo oscuro), color secundario opcional.
- `[SEGURO]` **`make font name=… weights=… role=display|body|mono`**: comprueba la
  familia en Fontsource, descarga el woff2 (validado por firma y longitud) y
  escribe `@font-face` y los tokens. Nunca CDN.
- `[SEGURO]` **Layouts**: `layouts/app.html` y `layouts/landing.html`;
  `base.html` expone `header`, `main` y `footer`. **Cuatro arquetipos de
  cabecera** (`sticky-blur`, `floating-pill`, `industrial-rule`, `terminal-bar`)
  más `custom`, que comparten `partials/nav_auth.html` (la lógica de sesión).
- `[SEGURO]` **Motion declarativo por niveles** con atributos `data-motion`:
  `motion.js` propio (reveal, stagger, split-reveal, count, marquee), Motion One
  10.18 (parallax, progress, muelle) y GSAP 3.15 con ScrollTrigger (pin, scrub,
  horizontal). `make design build` descarga la librería que el nivel pide, fijada
  por versión y SHA-256, con su `NOTICE.md`. Sin JS, o con
  `prefers-reduced-motion`, todo el contenido se ve. Funciona con HTMX.
- `[SEGURO]` **`/_design`** (solo desarrollo): tokens con su contraste, escala
  tipográfica, componentes, hero de prueba, modo oscuro y el vocabulario de motion
  del nivel; `?style=<estilo>` previsualiza una paleta sin escribir nada. Flag
  `DESIGN_PREVIEW`; no existe en producción.
- `[SEGURO]` **`make design-check`**: valida el contrato contra el proyecto
  (contraste, `input.css` al día, fuentes, librerías, cabecera, atributos de motion
  por encima del nivel, coherencia con `DESIGN.md`) y se pone en rojo si
  `design.toml` sigue en los valores por defecto. Corre en CI con `--allow-defaults`.
- `[SEGURO]` **Once estilos de partida** (los seis de 1.1 más `editorial`,
  `organico`, `neo-brutalista`, `retro-y2k`, `oscuro-tecnologico`): cada uno fija
  tema, radio, neutros, superficie, fuentes, cabecera y nivel de motion a la vez.
  Catálogos nuevos en la skill: `archetypes.md` (siete heroes, secciones,
  texturas, navegación), `type-pairings.md` (25 parejas instalables) y una
  referencia por estilo. Se vendorizan también `redesign-skill` y `brandkit` de
  taste-skill (MIT).
- `[SEGURO]` **`DESIGN.md`** gana **Firma visual** (2-3 gestos propios que el
  proyecto se compromete a repetir; la capa que ningún catálogo puede
  homogeneizar) y **Arquetipos**.
- `[SEGURO]` Comandos **`/kiro-design-review`** (capturas a 375 y 1280 px, contraste
  con `DESIGN.md` y con "¿se parece al default?", hasta dos pasadas) y
  **`/kiro-redesign`** (audita una app ya construida sin cambiar su comportamiento).
  `/kiro-init` propone ahora **tres direcciones contrastadas**.

### Cambiado

- `[MIGRACIÓN]` Las páginas extienden `layouts/app.html` (o `landing.html`) en
  vez de `base.html`. Una página que siga extendiendo `base.html` funciona igual.
  Ver la tabla de archivos a fusionar en
  [`docs/upgrading.md`](docs/upgrading.md#actualizar-el-motor-de-diseño).
- `[MIGRACIÓN]` `make brand-colors` es ahora un atajo que escribe `[brand]` en
  `design.toml` y recompila; acepta `neutral=`, `surface=`, `secondary=`. Un color
  que no pase AA con el texto del botón ya no solo avisa: el build falla.
- `[MIGRACIÓN]` El `Dockerfile` copia `design.toml` a la imagen de producción
  (las plantillas leen de ahí la cabecera, la superficie oscura y el motion).
- `[SEGURO]` `pages/home.html` y el ejemplo de `kiro-feature` son andamio
  explícito (titular y lista con separadores), no un molde que imitar.
- `[SEGURO]` El contraste del texto del botón se mide contra el color que se
  emite (`oklch(0.985)`), no contra blanco puro: en 1.1 podía informar 4.6:1
  cuando el real era 4.4:1.
- `[SEGURO]` La skill `kiro-design` se reescribe: motor, estructura, varianza,
  motion y bucle de percepción. Corrige la recomendación de Satoshi y Cabinet
  Grotesk (no están en Fontsource) y avisa de que la CSP bloquea las imágenes
  externas.

### Corregido

- `[SEGURO]` **Dependencias:** `urllib3` 2.7.0 a 2.8.0 (PYSEC-2026-4175, -4176 y
  -4177). Llegaba como dependencia transitiva de desarrollo (`pip-audit` →
  `requests`) y hacía fallar el paso `pip-audit` de CI. Se sube solo ese paquete
  en `uv.lock`; `make audit` queda limpio.
- `[SEGURO]` Un `<section class="dark">` dentro de una página clara conservaba los
  colores claros (los tokens `--color-*` de Tailwind se resuelven en `:root`). El
  compilador re-mapea el tema bajo `.dark`, así que una banda oscura funciona.

## [1.1.0] — 2026-10-12 · Identidad visual

### Añadido

- `[SEGURO]` **Identidad visual: `DESIGN.md` + skill `kiro-design`**, basada en
  [taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT). `/kiro-init`
  entrevista por colores de marca, estilo (minimalista, suave-premium,
  brutalista, institucional, expresivo, panel-de-datos) y logo, lo escribe en
  `DESIGN.md` y lo aplica. Ver ADR-0013.
- `[SEGURO]` `make logo src=<ruta|url>`: importa el logo (SVG, o PNG cuadrado
  1:1) a `app/static/brand/`, rechazando SVG con scripts. La cabecera y el
  favicon lo usan vía `brand_logo()`; sin logo, solo el nombre.
- `[SEGURO]` `make brand-colors primary="#hex"`: deriva `--primary`,
  `--primary-foreground` y `--ring` (claro y oscuro) y avisa si el contraste
  del botón baja de 4.5:1.

## [1.0.0] — 2026-09-07 · Listo para publicar

Cierra el roadmap inicial. Nada de lo que sigue cambia contratos existentes:
es documentación, un ejemplo opcional y una herramienta de auditoría.

### Añadido

- `[SEGURO]` **README bilingüe.** `README.md` pasa a inglés; `README.es.md`
  conserva el texto en español, cruzados con un enlace arriba de cada uno.
  El resto de la documentación (ADRs, guías, `docs/framework/`) se queda en
  español — es donde vive el razonamiento detallado, y mantener dos copias de
  cada página no compensaba. `AGENTS.md`, `PROJECT.md` y los ADRs ya estaban
  en inglés donde importa: lo que lee un agente de IA.
- `[MIGRACIÓN]` **Ejemplo de CRUD completo: "Notes".** Un proyecto que quiera
  traerlo copia `app/models/note.py` (+ su import en
  `app/models/__init__.py`), `app/repositories/note.py`,
  `app/schemas/note.py`, `app/services/note.py`, `app/routers/notes.py` (+ su
  registro en `app/main.py`), `app/templates/pages/notes/`, la línea de
  `partials/header.html`, `tests/test_notes.py`, y genera su propia migración
  con `make revision`. **Es opcional**: el docstring de `notes.py` trae la
  lista exacta de archivos a borrar si un proyecto no lo quiere, el mismo
  trato que ya recibía `demo_ping`. Demuestra las 8 capas del golden path más
  una regla de negocio real (solo el dueño de una nota puede borrarla) y los
  dos patrones de interacción del framework: formulario clásico
  post/redirect/get para crear, HTMX puro (`hx-delete` + `outerHTML`) para
  borrar.
- `[SEGURO]` **`pip-audit`** integrado: dependencia de desarrollo, `make
  audit`, y un paso en CI después de los tests. Sin hallazgos en esta
  versión.
- `[SEGURO]` `docs/architecture.md` documenta `app/analytics/` y `app/seo/`
  (añadidos en v0.3.0); `docs/getting-started.md` señala el ejemplo de notas.
- `[SEGURO]` [ADR-0006](docs/decisions/0006-nombre-kiro.md) resuelto: se
  conserva el nombre "Kiro". Era el único punto pendiente de decisión antes
  de esta versión.

## [0.3.0] — 2026-09-07 · Analítica y SEO

Todo lo de este hito es opt-in por variable de entorno: un proyecto que no
rellena nada no carga ni un script ni manda una sola petición de más. Ninguna
pieza necesita tabla ni migración.

### Añadido

- `[MIGRACIÓN]` Seis variables nuevas en `Settings`
  (`gtm_id`, `ga4_measurement_id`, `ga4_api_secret`, `meta_pixel_id`,
  `meta_capi_token`, `gsc_verification`), documentadas en `.env.example`.
  Un proyecto existente solo necesita traer las líneas nuevas de
  `.env.example` que quiera usar — todas son opcionales.
- `[SEGURO]` **Banner de consentimiento** (`GET/POST /consent`), HTMX puro,
  sin librería de terceros. Gatilla tanto el snippet de GTM en el `<head>`
  como los eventos server-side de GA4/Meta: sin `"accepted"`, ninguno de los
  dos se dispara. Ver [ADR-0011](docs/decisions/0011-consentimiento-y-analitica.md).
- `[SEGURO]` **GTM** condicionado a `GTM_ID` y al consentimiento, renderizado
  en `base.html` — cero JavaScript de terceros sin que el visitante lo acepte.
- `[SEGURO]` **`app/analytics/`**: GA4 Measurement Protocol y Meta Conversions
  API server-side, con hashing SHA-256 de PII para Meta
  (`app/analytics/hashing.py`). Ambos activos a la vez si están configurados;
  ninguno relanza sus errores de red, y se disparan con `BackgroundTasks`
  desde `login()`/`register()` para no sumar latencia a la respuesta. Ver
  ADR-0011.
- `[SEGURO]` **`sitemap.xml`** dinámico por registro de proveedores
  (`app/seo/sitemap.py`, `register_sitemap_provider`) y **`robots.txt`**
  fijo que oculta los formularios de auth. Ver
  [ADR-0012](docs/decisions/0012-registro-de-sitemap.md).
- `[SEGURO]` Verificación de Google Search Console vía `GSC_VERIFICATION`.
- `[SEGURO]` CSP actualizada para los dominios de GTM/GA4 — ver ADR-0010.
- `[SEGURO]` ADRs 0011 y 0012.

## [0.2.1] — 2026-09-03 · El instalador en una máquina que no es la tuya

Cuatro fallos que solo aparecen al clonar el repositorio en un equipo recién
formateado, donde `setup.sh` se cerraba —o se colgaba— sin dejar claro por qué.
Todo esto vive en `setup.sh` y `scripts/lib/`, que un proyecto generado ya no
tiene: **no hay nada que traer a un proyecto existente**.

### Corregido

- `[SEGURO]` **El slug se calculaba con `sed y/…/…/`, que cuenta bytes cuando la
  configuración regional no es UTF-8** (instalación mínima, contenedor, WSL sin
  locales generados). Ahí sed abortaba con *"strings for `y' command are
  different lengths"*, el slug salía vacío, y la pregunta se repetía con un
  valor por defecto que nunca pasaba la validación: un bucle infinito. Ahora la
  transliteración la hace `python3`, que ya es un requisito del instalador.
- `[SEGURO]` **`prompt::ask` se colgaba en bucle** cuando el valor por defecto no
  pasaba la validación y no había stdin para corregirlo. Ahora aborta con un
  mensaje que dice qué flag usar.
- `[SEGURO]` **uv se instalaba y el instalador no lo encontraba.** En Debian y
  Ubuntu, `~/.profile` añade `~/.local/bin` al PATH solo si ese directorio ya
  existía al iniciar sesión; en una máquina nueva no existe. El instalador
  descargaba uv, moría con *"uv se instaló pero no está en el PATH"*, y volver a
  correrlo repetía el ciclo entero. Ahora se fija el destino con
  `UV_INSTALL_DIR`, se busca también en `XDG_BIN_HOME` y `~/.cargo/bin`, se
  adopta un uv ya instalado fuera del PATH, y si el instalador de uv falla se
  enseña su salida en vez de taparla.
- `[SEGURO]` **Faltar Docker ya no aborta el instalador, pero tampoco se pasa de
  largo.** El diagnóstico distingue *no instalado*, *sin plugin compose v2* y
  *daemon caído* —tres arreglos distintos—, **recomienda el comando concreto**
  para el caso detectado y explica qué se gana con él (PostgreSQL levantado,
  esquema migrado, administrador sembrado, CSS compilado) frente a lo que
  tocaría hacer a mano. Solo entonces ofrece seguir sin base de datos, y con el
  **«no» por defecto**: si el instalador sabe cuál es la solución, ofrecer la
  salida de emergencia sin recomendarla primero es elegir por quien instala sin
  decírselo. También se comprueba `curl` antes de usarlo.
- `[SEGURO]` El mensaje final pone lo pendiente **antes** de `make dev`, que es
  lo primero que se lee y lo primero que falla sin base de datos.

### Añadido

- `[SEGURO]` Si el instalador falla y hay una terminal delante, espera a que
  pulses Enter antes de salir. Lanzado con doble clic desde el explorador de
  archivos, la ventana se cerraba con el error dentro y el síntoma que llegaba
  era "se cierra solo".
- `[SEGURO]` Job `entornos-hostiles` en el workflow de e2e: locale sin UTF-8,
  stdin cerrado, uv fuera del PATH y una máquina sin Docker. Son fallos que no
  se reproducen en el equipo de quien mantiene el framework.

## [0.2.0] — 2026-09-03 · Auth, correo y seguridad

Un proyecto generado ya sabe quién le está pidiendo las páginas. Registro,
login, sesiones revocables, recuperación de contraseña por correo, y el
endurecimiento que hace que todo eso no sea un juguete.

> **Si vienes de v0.1.0**, salta al final: *Cómo actualizar un proyecto
> existente*. Hay dos pasos manuales, y uno de ellos rompe formularios si se
> omite.

### Autenticación

- `[MIGRACIÓN]` Modelos `User`, `Role`, `UserSession` y `PasswordResetToken`,
  con su migración. Trae también los roles `admin` y `user` sembrados: el código
  los da por hechos, y `require_role("admin")` sobre una tabla vacía no falla —
  niega el acceso a todo el mundo, que es peor.
- `[SEGURO]` Contraseñas con **argon2id**. Nada fuera de `app/security.py`
  hashea ni firma: un solo sitio que auditar.
- `[SEGURO]` **Sesiones revocables**: la cookie lleva un token opaco firmado y
  la tabla guarda solo su SHA-256. Cambiar la contraseña cierra todas las
  sesiones de la cuenta, y rotar `SECRET_KEY` las cierra todas del sitio. Ver
  [ADR-0008](docs/decisions/0008-sesiones-en-base-de-datos.md) para por qué no
  es un JWT.
- `[SEGURO]` Recuperación de contraseña con enlace de un solo uso, hasheado en
  base de datos y con caducidad. Pedir uno nuevo invalida el anterior.
- `[SEGURO]` `CurrentUser`, `OptionalUser` y `require_role(...)` en `app/deps.py`.
  Anónimo → redirección a `/login?next=…`; identificado sin el rol → página 403.
  Son situaciones distintas y no deben colapsar en una: mandar a un formulario
  de login a alguien que ya entró es un bucle del que no sale.
- `[SEGURO]` Las peticiones de HTMX a una página protegida reciben `HX-Redirect`
  en vez de un 303, para que HTMX no incruste la página de login dentro de un
  fragmento.
- `[SEGURO]` **Nunca se revela si un email tiene cuenta.** Contraseña
  incorrecta, dirección desconocida y cuenta desactivada dan el mismo mensaje y
  el mismo tiempo de respuesta —hay un hash señuelo para que el reloj tampoco lo
  cuente—, y `/forgot-password` responde igual exista o no la cuenta.
- `[SEGURO]` `setup.sh` genera `ADMIN_EMAIL` / `ADMIN_PASSWORD`, siembra el
  administrador tras migrar y enseña las credenciales al terminar.
- `[SEGURO]` `ALLOW_REGISTRATION=false` hace que `/register` responda 404, para
  proyectos donde las cuentas las crea un administrador.

### Correo transaccional

- `[SEGURO]` `app/emails/` con `EmailSender` como `Protocol` y cuatro
  adaptadores: `console` (por defecto, imprime en stdout), `resend`, `smtp` y
  uno en memoria para tests, que **no** es seleccionable por `EMAIL_PROVIDER`
  para que un despliegue no pueda tragarse los correos en silencio.
- `[SEGURO]` Plantillas editables en `app/templates/emails/`, dos archivos por
  mensaje (`.html` y `.txt`). **El asunto vive dentro de la plantilla**, en su
  propio bloque: cambiar el texto de un correo no debe obligar a tocar un
  servicio.
- `[SEGURO]` La configuración del proveedor se valida **al arrancar**. Descubrir
  que faltaba `RESEND_API_KEY` en el primer correo de recuperación es un usuario
  encerrado fuera de su cuenta.

### Endurecimiento

- `[RUPTURA]` **CSRF de doble envío**, activo en todas las rutas. Todo
  formulario necesita `{% include "components/csrf_field.html" %}`; sin él, un
  403. HTMX no necesita nada: `base.html` manda el token en `hx-headers`. Ver
  [ADR-0009](docs/decisions/0009-csrf-doble-envio.md).
- `[SEGURO]` **Límites de intentos** en login y recuperación, contados en
  PostgreSQL por IP **y** por cuenta a la vez. En memoria del proceso no valen:
  se vacían en cada despliegue y cada worker lleva el suyo, así que con cuatro
  workers un límite de 10 son 40.
- `[SEGURO]` **Cabeceras de seguridad** en toda respuesta, con la CSP escrita
  como diccionario editable. Lleva `'unsafe-inline'` en `script-src` porque los
  macros de Basecoat traen handlers `onclick`; el porqué y cómo apretarla, en
  [ADR-0010](docs/decisions/0010-cabeceras-de-seguridad-y-csp.md). HSTS solo en
  entorno desplegado.
- `[SEGURO]` **Un identificador por petición**: en `X-Request-ID`, en cada línea
  de log y en la página 500, para que "no me funciona" se convierta en una línea
  concreta que buscar. Sustituye al log de acceso de uvicorn, que se emite fuera
  de la aplicación y por eso no lo lleva.
- `[SEGURO]` Logging estructurado: JSON por línea en entorno desplegado, línea
  legible en local. Lo que pases en `extra={...}` viaja como campos.

### Corregido

Los tres salieron de usar el framework, no de revisarlo.

- `[SEGURO]` **El hook de Alembic solo formateaba, no pasaba el linter.** La
  primera migración de *cualquier* proyecto rompía `make check` nada más
  generarse, por el orden de sus imports. Añadido `ruff check --fix` como hook
  previo en `alembic.ini`.
- `[SEGURO]` **`migrations/env.py` apagaba todos los loggers.** `fileConfig()`
  desactiva por defecto cualquier logger que ya existiera. En los tests dejaba
  mudo el `caplog` de cualquier proyecto; en producción, un proyecto que corra
  `alembic upgrade head` al arrancar pierde TODOS sus logs, sin un error que lo
  explique. Guarda de regresión en `tests/test_database_isolation.py`.
- `[SEGURO]` **El proveedor de correo `console` imprimía sin `flush`.** Con la
  salida redirigida a un archivo, a un gestor de procesos o a un contenedor sin
  `PYTHONUNBUFFERED`, el enlace de recuperación se quedaba en el buffer y
  parecía que no se enviaba nada.

### Infraestructura

- `[SEGURO]` El workflow e2e ahora **corre la suite entera** del proyecto
  generado: levanta PostgreSQL con el propio `setup.sh`, migra, siembra y pasa
  `make check`, además de arrancar la app y comprobar que sirve páginas con sus
  cabeceras. Antes solo pasaba lint y tipos, así que nada de lo que vive en la
  base de datos estaba cubierto.
- `[SEGURO]` Dos dependencias nuevas: `argon2-cffi` y el extra `pydantic[email]`.
  Ninguna trae Node ni rompe [ADR-0005](docs/decisions/0005-sin-nodejs.md). La
  imagen de producción pasa de ~390 a ~400 MB.

### Decisiones registradas

- [0008](docs/decisions/0008-sesiones-en-base-de-datos.md) — sesiones en base de
  datos, no JWT; argon2id para contraseñas.
- [0009](docs/decisions/0009-csrf-doble-envio.md) — CSRF de doble envío,
  validado como dependencia y no como middleware.
- [0010](docs/decisions/0010-cabeceras-de-seguridad-y-csp.md) — cabeceras de
  seguridad, y por qué la CSP lleva `'unsafe-inline'`.

### Cómo actualizar un proyecto existente

1. Trae el código nuevo:

   ```bash
   git checkout upstream/main -- app/security.py app/logs.py app/emails/ \
     app/middleware/ app/models/ app/repositories/ app/services/ app/schemas/ \
     app/routers/auth.py app/deps.py app/templating.py app/main.py \
     app/templates/emails/ app/templates/pages/auth/ \
     app/templates/components/csrf_field.html migrations/env.py alembic.ini
   uv add "argon2-cffi>=23.1" "pydantic[email]>=2.10"
   ```

2. **Migra.** Las tablas nuevas no existen en tu base:

   ```bash
   git checkout upstream/main -- migrations/versions/
   make migrate
   ```

3. **Añade el token CSRF a tus formularios.** Este es el paso que rompe cosas si
   se salta: todo `<form method="post">` que ya tuvieras empezará a recibir un
   403 hasta que lleve dentro
   `{% include "components/csrf_field.html" %}`. Si tu `base.html` está
   personalizado, cópiale también el `hx-headers` del `<body>`.

4. **Declara `user` en tus handlers de página.** `OptionalUser` en las públicas,
   `CurrentUser` en las privadas. Sin eso la cabecera renderiza como si no
   hubiera nadie identificado.

5. Añade al `.env` las variables nuevas (las tienes documentadas en
   `.env.example`) y corre `make seed` para crear el administrador.

6. `make check`.

## [0.1.0] — 2026-09-03 · Esqueleto

Primera versión utilizable. Un proyecto generado arranca, sirve páginas
renderizadas en servidor, habla con PostgreSQL y pasa su propia puerta de calidad.

### Instalador

- `[SEGURO]` `setup.sh` con preflight (docker, python, git, uv), preguntas
  interactivas, generación de secretos con `openssl`, sustitución de tokens,
  limpieza de archivos del framework y arranque de la base de datos.
- `[SEGURO]` Modo `--non-interactive` con una flag por pregunta. Es lo que
  permite que CI lo ejecute y que el instalador no se pudra en silencio.
- `[SEGURO]` **Detección de puertos libres.** Los valores por defecto de
  PostgreSQL y de la app son el primer puerto disponible, no el canónico: una
  máquina con varios proyectos ya tiene el 5432 y el 8000 ocupados.
- `[SEGURO]` Guarda de idempotencia: correr `setup.sh` dos veces aborta sin
  regenerar `.env` ni dejar la base de datos inaccesible.
- `[SEGURO]` Regenera `uv.lock` tras renombrar el proyecto, para que
  `uv sync --frozen` siga funcionando en CI y en el Dockerfile.

### Aplicación

- `[SEGURO]` `app/config.py` — Settings tipado, único punto que lee el entorno.
- `[SEGURO]` `app/db.py` — engine síncrono con `pool_pre_ping`, sesión por
  petición con commit/rollback automático.
- `[SEGURO]` `app/repositories/base.py` — `BaseRepository[ModelT]` genérico y
  tipado, que falla al importar si una subclase olvida declarar `model`.
- `[SEGURO]` `app/models/base.py` — convención de nombres de constraints y
  claves UUIDv7.
- `[SEGURO]` `app/templating.py` — Jinja2 configurado, helper `render()` y
  `asset()` con cache-busting por mtime.
- `[SEGURO]` `app/exceptions.py` — excepciones de dominio sin acoplar a FastAPI.
- `[SEGURO]` Páginas 404 y 500 renderizadas con el layout del sitio.

### Frontend

- `[SEGURO]` Basecoat 1.0.2 y HTMX 2.0.10 vendorizados. Cero Node.js: Tailwind
  v4 se compila con su CLI standalone vía `pytailwindcss`.
- `[SEGURO]` `base.html` con SEO de serie: título, descripción, canonical,
  Open Graph y Twitter Card, todo sobreescribible por bloque.
- `[SEGURO]` Página de inicio de ejemplo con una interacción HTMX real,
  pensada como referencia viva para la IA.

### Capa de IA

- `[SEGURO]` `AGENTS.md` con el stack, las capas, las reglas duras y lo
  prohibido. `CLAUDE.md` lo importa.
- `[SEGURO]` Plantilla `PROJECT.md` para el dominio de negocio.
- `[SEGURO]` Skills `kiro-feature`, `kiro-component`, `kiro-migration`, `kiro-adr`.
- `[SEGURO]` Comandos `/spec-new`, `/spec-design`, `/spec-tasks`, `/spec-build`,
  `/kiro-check`.

### Infraestructura y calidad

- `[SEGURO]` Dockerfile multi-etapa: usuario sin privilegios, healthcheck, y el
  CSS compilado en su propia etapa. Imagen de producción de ~390 MB.
- `[SEGURO]` `compose.yml` con PostgreSQL 18 y puertos configurables.
- `[SEGURO]` `make check` — lint, tipos, tests y detección de migraciones
  pendientes.
- `[SEGURO]` Tests con base de datos aislada (`<db>_test`) y rollback por test.
  El esquema se construye con las migraciones reales, no con `create_all()`.
- `[SEGURO]` CI: puerta de calidad + workflow e2e que genera un proyecto desde
  cero con tres combinaciones de opciones y corre su suite.
- `[SEGURO]` Pre-commit con ruff, mypy `--strict` y shellcheck.

### Corregido

Todos salieron de construir un catálogo real sobre el framework, no de
revisar el código: ninguno se detecta sin un proyecto de verdad encima.

- `[SEGURO]` **`make seed` estaba roto.** El Makefile invocaba `scripts.seed`,
  pero ni `scripts/seed.py` ni `scripts/__init__.py` existían — y `setup.sh`
  borra `scripts/lib/`, así que en un proyecto generado la carpeta quedaba
  vacía. Añadido un `seed.py` funcional y documentado, con el patrón idempotente
  (buscar por clave natural y actualizar) explicado en su docstring.
- `[SEGURO]` **La guía de personalización de `input.css` era incorrecta.** El
  ejemplo sugería sobreescribir `--color-primary` dentro de `@theme`. Basecoat
  mapea `--color-primary: var(--primary)` en su propio `@theme`, y el modo
  oscuro cambia la variable CRUDA: sobreescribir el token rompe esa indirección
  y el color deja de cambiar en modo oscuro. Corregido, separando qué va en
  `:root` (colores, radios) y qué en `@theme` (tipografías).
- `[SEGURO]` **La imagen de producción no incluía `scripts/`**, así que no se
  podía sembrar datos en el servidor. Ahora viaja, y `.dockerignore` excluye
  `scripts/lib/` y los `__pycache__` de cualquier profundidad, que sí se colaban.
- `[RUPTURA]` **El LICENSE del framework viajaba a todos los proyectos**, así
  que el sitio de un cliente nacía con el copyright del autor de Kiro. Ahora
  `setup.sh` instala un LICENSE propio con el autor y el año del proyecto. De
  paso, esto le da uso a `--author`, que hasta ahora se preguntaba y no se
  usaba en ningún sitio.
- `[SEGURO]` Ejemplos de la ayuda y de la documentación neutralizados: llevaban
  un dominio real y nombres de proyectos concretos del autor.
- `[SEGURO]` Aviso en `demo_ping` de que al borrarlo se pierde
  `test_htmx_fragment_is_not_a_full_document`, que vigila un invariante real:
  un endpoint HTMX devuelve un fragmento, nunca un documento completo.
- `[SEGURO]` **`migrations/env.py` pisaba la URL fijada por su llamador.** La
  suite de tests apunta Alembic a la base `<db>_test`, pero `env.py` la
  sobreescribía sin comprobarlo: `alembic upgrade` migraba la base de
  DESARROLLO y dejaba la de test vacía. Los tests seguían pasando —no había
  tablas que consultar todavía— y el fallo solo aparecía con la primera
  migración del proyecto, lejos de su causa. Encontrado al construir el primer
  catálogo real sobre el framework.
  Añadido `tests/test_database_isolation.py` como guarda de regresión.

### Decisiones registradas

ADRs 0001–0007. Tres contradicen el documento de visión original y son las que
más importa conocer:

- [0002](docs/decisions/0002-sqlalchemy-sincrono.md) — SQLAlchemy **síncrono**,
  no async: es donde más alucina la IA en este stack.
- [0005](docs/decisions/0005-sin-nodejs.md) — cero Node.js.
- [0007](docs/decisions/0007-sin-alpinejs.md) — sin Alpine.js; Basecoat ya cubre
  la interactividad con JS vanilla.

### Notas sobre dependencias externas

- **PostgreSQL 18** cambió el punto de montaje del volumen a
  `/var/lib/postgresql`. El idiom antiguo (`/var/lib/postgresql/data`) hace que
  el contenedor arranque en bucle.
- **Basecoat 1.0** sustituyó las clases modificadoras por atributos `data-*`:
  `<button class="btn" data-variant="primary">`, no `btn-primary`. Escribir la
  forma antigua no da error, simplemente renderiza sin estilo.
- **Starlette 1.6** marca `httpx` v1 como obsoleta para su `TestClient`. Kiro usa
  `httpx2`, que sirve además para las llamadas HTTP salientes.

[0.2.0]: https://github.com/pepeajcu/framework-kiro/releases/tag/v0.2.0
[0.1.0]: https://github.com/pepeajcu/framework-kiro/releases/tag/v0.1.0
