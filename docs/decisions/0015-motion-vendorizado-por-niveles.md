# 0015 — Motion declarativo, por niveles y vendorizado bajo demanda

**Estado:** Aceptada · 2026-10-13

## Contexto

El dial `MOTION_INTENSITY` existía en `DESIGN.md`, pero la skill decía "por encima
de 4, pregunta antes de vendorizar una librería", así que en la práctica toda
página se quedaba en transiciones CSS. Subir el movimiento exigía que la IA
escribiera JavaScript distinto por página: inmantenible, y con riesgos reales (una
página en blanco sin JS, contenido oculto que HTMX reemplaza, `prefers-reduced-motion`).

## Decisión

1. **API declarativa.** La página escribe atributos (`data-motion="reveal"`,
   `"stagger"`, `"split-reveal"`, `"count"`, `"marquee"`, y con niveles altos
   `"parallax"`, `"progress"`, `"pin"`, `"scrub"`, `"horizontal"`), nunca
   JavaScript propio.
2. **Cuatro niveles**, elegidos con `[motion] level` en `design.toml`:

   | Nivel | Motor | Peso (gzip) | Añade |
   |---|---|---|---|
   | 1-3 | transiciones CSS | 0 | nada |
   | 4-6 | `motion.js` (propio) + `motion.css` | 3.4 + 1.3 KB | reveal, stagger, split-reveal, count, marquee |
   | 7-8 | + Motion One 10.18 (vendorizado) | + 1.0 + 9.8 KB | parallax, progress, `data-motion-ease="spring"` |
   | 9-10 | + GSAP y ScrollTrigger 3.15 (vendorizados), en lugar de Motion | + 1.8 + 28.3 + 18.0 KB | pin, scrub, horizontal |

   Cada nivel entiende todo lo del anterior. Un valor por encima del nivel se
   ignora (el contenido se ve, quieto) y `make design-check` lo lista.
3. **Un núcleo con plugins.** `motion.js` es el orquestador (observador,
   limpieza, HTMX) y los adaptadores se registran con
   `kiroMotion.register(nombre, función)`. Los dos adaptadores (`motion-lib.js`,
   `motion-gsap.js`) son archivos del framework; la librería es lo único que se descarga.
4. **Degradación elegante, por construcción.** Un estado oculto existe **solo bajo
   la clase `js-motion`**, que pone el propio `motion.js` (síncrono, antes del CSS
   y del primer pintado) y solo si el visitante no pidió movimiento reducido y el
   navegador tiene `IntersectionObserver`. Sin JS, o con `prefers-reduced-motion`,
   todo el contenido se ve (regla 3 de `AGENTS.md`). Un test vigila que cada regla
   que oculta algo empiece por `.js-motion`.
5. **HTMX.** El contenido nuevo se arma en `htmx:load`; lo que sale se limpia en
   `htmx:beforeCleanupElement` (observadores y disparadores de ScrollTrigger).
6. **Las librerías no van en el repositorio del framework.** `make design build`
   (o `make motion level=motion|gsap`) las descarga al proyecto, **fijadas por
   versión y por SHA-256**, y escribe `app/static/js/vendor/NOTICE.md` con su
   licencia. Una discrepancia de hash se rechaza sin escribir nada.
7. **Carga solo en `layouts/landing.html`**, o en la página que ponga
   `{% set use_motion = true %}`. La CSP no cambia (`script-src 'self'`).

## Por qué así

- **Motion One 10.18 y no la línea actual.** Medido al vendorizar: el bundle de
  `motion` 14.2 pesa 154 KB (51 KB gzip), más que GSAP y ScrollTrigger juntos
  (46 KB gzip), porque desde la 11 el paquete incorpora Framer Motion. La 10.18
  pesa 24.6 KB (9.8 KB gzip), exporta `animate`, `scroll`, `spring`, `inView` y
  `stagger`, y es MIT. Es la que cumple la estimación de 5-20 KB del plan.
- **GSAP no se redistribuye.** Su licencia ("no charge") permite el uso comercial
  y gratuito, y prohíbe usarlo en herramientas que compitan con el constructor
  visual de Webflow y quitar sus avisos, pero **no aborda** redistribuir los
  `.min.js` dentro de un repositorio. Para no dejar esa duda en cada clon, el
  framework no los incluye: cada proyecto los descarga y acepta la licencia por su
  cuenta. Una vez descargados, el proyecto sí los comitea (como htmx): no están
  en el `.gitignore`.
- **Hash fijado.** Las versiones de npm son inmutables; si el origen sirve otra
  cosa, algo está mal y el archivo no se instala.
- **Estado oculto en CSS, no en JS.** Esconder desde JS, tras el primer pintado,
  hace un parpadeo (visible, oculto, revelado); esconder desde CSS bajo una clase
  que el script pone en `<head>` no.
- **`motion.js` pesa 3.4 KB gzip, no 1-2.** El plan lo estimó antes de escribirlo:
  son cinco comportamientos más la integración con HTMX y la limpieza. Sin paso de
  build no hay minificado; con gzip es una cifra aceptable.

## Excepción a ADR-0005 (y su alcance)

ADR-0005 dice "no cargues librerías desde un CDN: vendorízalas". Esto lo cumple:
nada se carga desde un CDN **en ejecución**; jsDelivr se usa una vez, al instalar,
igual que Fontsource para las fuentes, y lo instalado queda en `app/static/`. Lo
que cambia es *cuándo* se vendoriza: bajo demanda y por el motor, no por una
persona copiando archivos. La excepción no se extiende a otras librerías.

## Consecuencias

- La primera vez que un proyecto sube a nivel 7+ el build necesita red. Después
  funciona sin ella: un archivo presente con el hash correcto no se vuelve a bajar.
- Subir de versión una librería es una decisión explícita (cambiar versión y hash
  en `scripts/motion.py`), no un `@latest`.
- Lenis (scroll suave, opcional en el plan) no se incluye. Si un proyecto lo
  quiere, es una librería más en `LIBRARIES` con su hash.
- `pin` y `horizontal` actúan solo desde 768 px; en móvil el contenido fluye y la
  banda horizontal se recorre con su propio scroll.
- El elemento que es el LCP no debe llevar `reveal` (no se pintaría hasta que
  corra el script): la skill lo dice.
