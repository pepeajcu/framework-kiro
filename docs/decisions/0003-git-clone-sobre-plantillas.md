# 0003 — `git clone` + `setup.sh` como mecanismo de distribución

**Estado:** Aceptada · 2026-09-01

## Contexto

Tres formas de distribuir el framework:

1. **`git clone` + `setup.sh`** — cero dependencias; lo que clonas es lo que
   corres.
2. **Copier** — plantilla con preguntas nativas y, sobre todo, `copier update`:
   propaga mejoras del framework a proyectos ya generados mediante una fusión a
   tres bandas.
3. **Paquete pip `kiro-core`** — el núcleo como librería versionada.

## Decisión

**`git clone` + `setup.sh`**, por decisión del autor: simplicidad y control
directo sobre cualquier automatización adicional.

## Consecuencias

- **El coste real y conocido:** un proyecto creado hoy no recibe automáticamente
  los arreglos que se hagan al framework mañana. Con varios proyectos de cliente
  activos, esto se acumula.
- Mitigación: `setup.sh --git-mode upstream` conserva el framework como remote
  `upstream`, y `make upgrade` muestra qué cambió en las rutas que Kiro posee.
  Traer un cambio es `git checkout upstream/main -- <ruta>`.
- Para que esa mitigación funcione, el `CHANGELOG.md` **debe** etiquetar cada
  entrada como `[SEGURO]`, `[MIGRACIÓN]` o `[RUPTURA]`. Sin esa disciplina, la
  ruta de actualización es adivinanza.
- `setup.sh` pasa a ser código crítico: es el único punto donde un fallo deja al
  usuario con un proyecto a medio construir. Por eso tiene modo
  `--non-interactive`, es idempotente, y CI lo ejecuta en cada push.
