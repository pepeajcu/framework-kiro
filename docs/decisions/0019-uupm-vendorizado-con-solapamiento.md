# 0019 — uupm vendorizado, traducido una vez a Kiro, y el suelo comprobado por una máquina

**Estado:** Aceptada · 2026-10-14

## Contexto

uupm (nextlevelbuilder, *ui-ux-pro-max*, 136k estrellas, MIT) es el mejor conocimiento
de UX, paletas por tipo de producto y parejas tipográficas que se puede llevar a un
proyecto: 192 tipos de producto, 88 estilos, 74 parejas, 119 guías de UX, una lista
de prioridades de diez categorías. El plan anterior pedía convertirlo en "juez
principal y bloqueante". Los hechos que cambian cómo:

- **Una revisión hecha por la IA no se puede ejecutar en CI**, y "bloqueante sin límite
  de pasadas" choca con el máximo de dos de `/kiro-design-review`.
- Sus datos **no encajan tal cual** con la plataforma: sus parejas tipográficas traen
  la URL y el `@import` de Google Fonts (la CSP los bloquea y ADR-0005 los prohíbe),
  algunas paletas no llegan a AA con nuestro compilador, y recomienda un carrusel de
  testimonios que taste prohíbe.
- Es **una skill completa**: instalada tal cual competiría con `kiro-design` por la
  misma pregunta, y su instalador usa Node.
- Su `search.py` es **Python estándar sin red** (BM25 sobre CSV), vendorizable.
- Los botones de Basecoat miden 28-40 px; la guía exige 44 px de zona táctil (categoría 2).

## Decisión

1. **Se vendoriza una lista cerrada de archivos** de un commit fijado (v2.15.0): el motor
   de búsqueda, los CSV que usamos y el de `html-tailwind`; se deja fuera el 60 % del
   peso (iconos, el catálogo de Google Fonts, el resto de stacks, sus tests). Cada
   archivo va fijado por SHA-256 en `uupm/vendor.lock.json` (los tarballs de GitHub no
   son estables byte a byte; los archivos sí) y un test falla si alguien edita uno.
   Su `SKILL.md` se guarda como `GUIDE.md`: **`kiro-design` es la única skill de
   diseño**, y `design-check` avisa (`D6`) si aparece otra que compita.
2. **Se traduce una vez**, en `uupm-kiro/`, no en cada conversación: qué fuentes suyas
   existen en Fontsource (y con qué pesos), qué paletas pasan AA con nuestro compilador
   y cuál es el hex más cercano que sí, a qué preset se parece cada estilo, qué filas
   de su guía de stack no se pueden seguir aquí. Lo reconstruye `make vendor-uupm`.
3. **uupm es la base, no el dueño**: `make design-advise` ejecuta su
   `--design-system` aislado (`python -I`) y convierte la respuesta en un `DesignBrief`
   (ADR-0018). Lo que choca con taste (el carrusel) viaja como nota para la revisión; la
   constitución dice quién gana.
4. **El cierre es por niveles**, y lo que se puede comprobar con una máquina se
   comprueba con una máquina:
   - **El suelo** (categorías 1-3) se garantiza en el compilador y en CI: el bloque
     `kiro:a11y` (zona de pulsación de 44 px con puntero grueso sin cambiar el tamaño
     visual, foco visible de respaldo, `prefers-contrast`, `prefers-reduced-motion`), un
     enlace de salto al contenido en `base.html` y `tests/test_ux_floor.py`, que
     renderiza cada ruta (anónimo y con sesión) y exige `lang`, `title`, un `h1`, un
     `main`, un nombre para todo lo que se pulsa o se escribe, `alt`, `width` y `height`
     en las imágenes, zoom permitido y ningún `tabindex` positivo. Bloquea siempre.
   - **El gusto** lo juzga `/kiro-design-review`, en un informe único ordenado por la
     prioridad de uupm, con dos pasadas y escalado al usuario con opciones; lo que decide
     se anota en `DESIGN.md`.

## Consecuencias

- **El proyecto lleva unos 850 KB más** (`uupm/`) y un script de mantenedor
  (`vendor_uupm.py`). A cambio, el asesor funciona sin red y sin Node, y no cuesta contexto:
  la IA pregunta con un comando y no lee los CSV.
- **Actualizar uupm es una decisión consciente**: cambiar el commit, ejecutar
  `make vendor-uupm`, leer el diff y pasar la suite; los tests del solapamiento dicen qué
  dejó de cumplirse (por ejemplo, una fuente que ya no está en Fontsource).
- **La zona táctil de un botón crece sin cambiar su tamaño visual** (un `::after`), así que
  dos botones muy juntos pueden solaparse en pantalla táctil; los de Basecoat llevan hueco
  entre sí. Los campos y las etiquetas de casillas sí crecen: no hay nada que ocultar.
- **`tests/test_ux_floor.py` viaja a cada proyecto y puede romper `make check` en uno ya
  existente** (una imagen sin `alt`, un formulario sin etiqueta). Es lo que tiene que hacer;
  las rutas con parámetro y los fragmentos HTMX se declaran en el propio archivo.
- **Un barrido de los 192 tipos de producto** pasa por el motor de uupm y por `propose` y
  exige un contrato válido: encontró un fallo de `propose` (comprobaba el secundario
  contra el primario sin corregir) que el test dirigido no habría visto.
- El estilo de uupm "Liquid Glass" y similares se asigna a un preset cuando exista el kit
  correspondiente (ADR-0020); hasta entonces cae en el más cercano o en ninguno.
