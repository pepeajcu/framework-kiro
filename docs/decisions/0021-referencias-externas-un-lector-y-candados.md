# 0021 — Referencias externas: un lector tolerante, skillui como herramienta opcional y candados

**Estado:** Aceptada · 2026-10-14

## Contexto

El usuario quiere partir de lo que ya le gusta: un estilo de Refero, el sistema de diseño de una
marca, una web, un texto suyo. Los hechos verificados:

- **Refero Styles** exporta un `DESIGN.md` con tablas (colores `Name | Value | Token | Role`,
  escala tipográfica, radios, componentes, Do y Don't) y tiene un MCP de pago. **skillui** (CLI
  de Node, 2.4k estrellas) escribe un `DESIGN.md` en el formato de nueve secciones de Google
  Stitch más `tokens/*.json`. **awesome-design-md** sigue el mismo formato.
- skillui **escribe por defecto en `./`**: en la raíz de un proyecto machaca `DESIGN.md` y
  `CLAUDE.md`. Su repositorio **no tiene archivo de licencia** (el README dice MIT). Necesita Node.
- Una web de terceros trae logos, imágenes, textos, fuentes propietarias y código con derechos.

Alternativas: un parser por fuente (tres sitios con tres conjuntos de bugs), o depender de
skillui (Node dentro del proyecto, ADR-0005, y una licencia sin verificar).

## Decisión

1. **Un lector tolerante para el formato Stitch/Refero** (`external_md.py`): busca la *forma*
   (una tabla bajo un encabezado de color con un hex en la fila; una lista de «Display: Fuente»)
   y no títulos exactos, porque el formato no está versionado por sus autores. Lo que no sabe
   leer lo deja fuera y `propose` lo lista como sin resolver: nunca se inventa.
2. **skillui queda fuera del repositorio** como herramienta opcional que la persona instala.
   `scripts/reference.py` la ejecuta siempre con `--out .design/reference/<n>`, `--no-skill` y
   `--format design-md`, y lee su salida (`skillui.py`). Sin skillui, `make design-reference
   url=...` lee el CSS de la página directamente: colores usados en botones y enlaces (el
   acento), familias por selector (titulares, texto, código), el radio más repetido y una
   estimación del movimiento. Ninguna de las dos vías descarga imágenes ni fuentes.
3. **Texto libre**: la IA rellena el JSON de un `DesignBrief` (`make design-brief-schema`
   imprime su esquema) y Pydantic lo valida. La IA extrae; el código valida y traduce.
4. **Candados**: se toma el lenguaje visual, no los activos (ni logos, ni imágenes, ni código
   de componentes, ni fuentes: se mapean a Fontsource por categoría); solo se acepta `http(s)`;
   tamaños y tiempos acotados; la URL y la fecha van a *Procedencia*; la firma visual del
   proyecto sigue siendo obligatoria; **se propone y se aplica en dos pasos**.
5. Todo desemboca en la misma tubería que el resto (ADR-0018): un solo acento que pasa AA, una
   fuente de Fontsource o la del catálogo de su categoría, el tema derivado del radio.

## Consecuencias

- **Es una heurística sobre texto ajeno.** Un `DESIGN.md` con un formato muy distinto puede
  dar un brief pobre; entonces el comando lo dice («no encuentro colores ni fuentes») y la salida
  es el texto libre. Un test por formato (Refero, Stitch en prosa, skillui) fija lo que se lee.
- **Una web que se pinta con JavaScript no trae CSS que leer**: el comando lo dice y propone
  skillui, que sí renderiza.
- **Las fuentes propietarias** (SF Pro, Helvetica Neue) no existen en Fontsource: el brief las
  deja y la propuesta las sustituye por la del catálogo de su categoría, anotado.
- **No se captura de la web su movimiento real**: se estima por bibliotecas y declaraciones
  (`gsap` o `lottie` suben a nivel 8; sin nada, nivel 2). La persona lo ajusta en la propuesta.
- **El parser nunca ejecuta ni sigue lo que lee**: ni enlaces del Markdown ni `@import` del CSS.
  Solo hojas enlazadas desde la página (hasta ocho).
