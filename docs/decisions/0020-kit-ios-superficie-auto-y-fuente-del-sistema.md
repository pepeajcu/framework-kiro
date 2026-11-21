# 0020 — Kit iOS, `surface = "auto"` y `fallback = "system"`

**Estado:** Aceptada · 2026-10-14 · Actualiza el [ADR-0014](0014-motor-de-diseno.md)

## Contexto

El usuario quería un estilo iOS "de verdad", no un color. Un preset cambia colores,
radio, fuentes y tema, pero lo que hace que algo se sienta iOS es otra cosa: la escala
tipográfica, las listas agrupadas con separadores sangrados, los materiales translúcidos,
la barra de pestañas, las hojas modales. Y tres hechos comprobados:

- **San Francisco no se puede alojar** (la licencia de Apple solo permite maquetas), pero
  `-apple-system` la usa en los dispositivos de Apple sin descargar nada.
- **El azul de sistema de Apple (`#007AFF`) no lleva texto blanco con contraste AA**
  (4.0:1; el compilador rechazaría el botón). El azul de los enlaces de apple.com,
  `#0066CC`, da 5.3:1.
- **El "vidrio" tiene límites que la propia guía de Apple fija**: va en la capa de
  navegación y controles, nunca en el contenido; los filtros SVG de refracción solo los
  pinta Chromium; `prefers-reduced-transparency` no existe en Safari.

Hasta ahora la superficie era fija (`light`, `cream` o `dark`), a propósito: un selector de
tema es algo más que mantener (ADR-0014). iOS, en cambio, sigue al dispositivo.

## Decisión

1. **`[structure] kit = "ios"`**: un kit es una pieza compilada (`app/design_engine/kits.py`,
   bloque `kiro:kit` de `input.css`), como el suelo de accesibilidad. Contiene solo tokens
   (ningún color escrito), la escala de Dynamic Type, márgenes de 16 y 20 px, filas de 44 px,
   lista agrupada, control segmentado, barra de pestañas, hoja y materiales. Sus componentes
   Jinja están en `components/ios.html.jinja` (del proyecto, editables) y la cabecera
   `ios-bar` conserva `brand_mark` y `nav_auth`.
2. **El CSS del kit va dentro del bloque, no en un archivo importado.** El compilador es
   puro (texto entra, texto sale) y un `@import` solo es válido antes del resto de reglas;
   así el bloque es idempotente y se puede borrar sin dejar nada. No se edita: se
   sobrescribe fuera de los marcadores.
3. **Opacidad calculada, no confiada**: `--kit-material-alpha` es la menor opacidad (entre
   el 50 % y el 100 %) con la que el texto llega a AA sobre un fondo blanco y sobre uno
   negro, para cada modo. Sin `backdrop-filter`, con `prefers-reduced-transparency` o con
   `prefers-contrast: more`, el material es el color de la página, sólido. Sin filtros SVG
   de refracción, sin `-apple-visual-effect` (privado) y sin SF Symbols (licencia).
4. **`surface = "auto"`**: claro por defecto, oscuro cuando el sistema lo pide, sin selector
   manual. Los tokens oscuros se emiten también bajo `prefers-color-scheme` y la variante
   `dark` de Tailwind se redefine para casar con la clase **o** con la consulta de medios
   (comprobado: Tailwind emite las dos formas). **No hace falta JavaScript**, ni hay parpadeo.
   `base.html` añade `<meta name="color-scheme" content="light dark">`.
5. **`fallback = "system"`** en una fuente: `-apple-system, BlinkMacSystemFont, "Inter",
   sans-serif`. `system-ui` no va en la lista (ganaría en Windows y Android y Inter no se
   usaría nunca). No se precarga la fuente: en Apple no se pide el archivo.
6. **Preset `ios`**: primario `#0066CC`, neutros fríos, `auto`, radio 0.75rem, tema `maia`
   (botón cápsula, tarjetas `rounded-2xl`), Inter 400/600, nivel de motion 5. Inter entra en
   el catálogo de parejas (fila 26) solo para este estilo y `institucional`.

## Consecuencias

- **Se añadieron cuatro opciones al contrato** (`surface` admite `auto`, `fallback` admite
  `system`, `header` admite `ios-bar`, `[structure] kit`), todas con valor por defecto: un
  proyecto existente no cambia. `kit` solo aparece en `design.toml` cuando se usa.
- **El kit no es completo**: hay lista, control, pestañas, hoja y barra; no hay selectores
  de fecha ni menús contextuales. Se añaden como componentes de `components/ios.html.jinja`
  cuando un proyecto los pida.
- **Un material en un navegador sin `backdrop-filter` es sólido**: se pierde la translucidez
  pero no la legibilidad. Esa es la decisión, no un defecto.
- **La barra de pestañas solo existe en móvil** (por debajo de 768 px) y reserva su alto en
  el `<body>`; en pantallas anchas se usa la cabecera. Una landing "al estilo apple.com" no
  la usa.
- **Verificado en un Chrome real** (emulación táctil y modo oscuro del sistema): cuerpo de
  17 px, fuente del sistema primero, claro y oscuro siguiendo al dispositivo, barra con
  desenfoque y opacidad calculada, filas de 44 px, pestañas solo en móvil, hoja que abre y
  cierra sin script propio, sin desbordamiento horizontal.
- La asignación de estilos de uupm a este preset (`Liquid Glass`, `glassmorphism`, `iOS`...) se
  regenera con `make vendor-uupm`.
