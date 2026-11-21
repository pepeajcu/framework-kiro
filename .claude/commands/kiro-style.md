---
description: Turn a visual reference into a design proposal for this project: a pasted style brief (Refero "Copy .md", a brand's DESIGN.md), free text, a website, or skillui's output. Proposes first; nothing changes until you apply it
---

# Estilo desde una referencia

Para cuando el usuario trae **una dirección visual de fuera**: un export de Refero Styles, el
`DESIGN.md` de una marca, una descripción en sus palabras, una web que le gusta o la salida de
skillui. Todas entran por el mismo camino (`references/constitution.md`): se reducen a un
*brief*, `propose` lo traduce al contrato, y **solo se aplica cuando alguien lo ha leído**.

Argumento: lo que el usuario pega o señala. Léelo y decide la entrada:

| Lo que trae | Qué haces |
|---|---|
| Un texto largo con tablas de colores, tipografía, radios (Refero "Copy .md", un `DESIGN.md` de marca) | Guárdalo en un archivo y `make design-reference md=<archivo> name=<nombre>` |
| Una URL | `make design-reference url=<url> name=<nombre>` lee el CSS de la página (solo texto: ni imágenes ni fuentes). Si la web se pinta con JavaScript y no trae CSS, usa skillui |
| Una URL y tiene skillui instalado (`npm i -g skillui`, opcional) | `make design-reference skillui=<url> [mode=ultra]`. Nunca ejecutes `skillui` a mano: sin `--out` escribe `DESIGN.md` y `CLAUDE.md` en la raíz del proyecto |
| La carpeta que ya escribió skillui | `make design-reference skillui_dir=<carpeta>` |
| Una descripción en palabras ("cálido, artesanal, tierra y verdes, serif amable") | Mira `make design-brief-schema`, **rellena tú el JSON** de un brief con valores reales (hex, familias, un radio) y `make design-propose from=<brief.json> name=<nombre>`. La IA extrae; el código valida y traduce |
| Refero conectado por MCP | `refero_get_style` devuelve el mismo contenido que el "Copy .md": guárdalo como archivo y trátalo como la primera fila |

Añade `base=.design/briefs/<x>.json` si hay un asesor de uupm para el producto
(`make design-advise q="..." name=x`): la referencia se **viste sobre** esa base. Sin base, la
referencia es todo.

## Pasos

1. Lee `PROJECT.md`, `DESIGN.md` y `design.toml`. Si `DESIGN.md` tiene `TODO`, esto no sustituye
   a `/kiro-init`: sigue sin haber firma visual ni diales, y la referencia solo da el lenguaje.
2. Corre el comando de la tabla. Termina con una **propuesta** en `.design/proposals/<nombre>.md`.
3. **Léela con el usuario.** Dile con claridad:
   - qué acento quedó (**uno solo**; los demás se descartan y se anotan);
   - qué fuentes son las de la referencia y cuáles se **sustituyeron** por una de Fontsource, y
     por qué (las propietarias, como SF Pro o Helvetica Neue, nunca se copian);
   - qué cambió para llegar a contraste AA (regla `D1`);
   - lo que quedó **sin resolver** y necesita una persona.
4. Si el usuario la acepta, `make design-apply proposal=<nombre>` (con `force=1` si el proyecto ya
   tiene identidad propia: se guarda una copia en `.design/backup/`). Eso escribe `design.toml`,
   anota en `DESIGN.md` las decisiones (*Decisiones de diseño*) y la procedencia con la URL y la
   fecha (*Procedencia*), compila y corre `make design-check`.
5. Enséñaselo: `make dev` y `/_design`. Después, `/kiro-design-review` al construir páginas.

## Los candados

- **Se toma el lenguaje, no los activos.** Nada de logos, imágenes, textos ni código de
  componentes de la referencia, y ninguna fuente de pago o propietaria. Si la referencia es de
  otra marca, el proyecto sigue necesitando su **propia firma visual**: dos o tres gestos suyos
  que no salen de la referencia. Un clon de Linear o de Notion con otro nombre no es un
  resultado válido.
- **Lo que una referencia no puede cambiar**: accesibilidad, uso táctil y rendimiento
  (el suelo). Si sus colores no llegan a AA, se mueven al hex más cercano que sí.
- skillui no se redistribuye ni es una dependencia (Node queda fuera del proyecto, ADR-0005; su
  licencia no está en su repositorio). Es una herramienta que el usuario instala si quiere.
- No apliques nada sin que se haya leído la propuesta. No hagas commit.
