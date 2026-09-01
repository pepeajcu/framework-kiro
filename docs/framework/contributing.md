# Trabajar en el framework

**FRAMEWORK-ONLY** — no llega a los proyectos generados.

## La regla que lo gobierna todo

El repositorio **es** el esqueleto. Lo que clonas es lo que corre. Eso obliga a
algo poco habitual: el repo tiene que pasar su propia puerta de calidad *antes*
de que nadie ejecute `setup.sh`.

```bash
make check
```

Por eso `pyproject.toml` trae valores válidos por defecto (`kiro-app`) en vez de
tokens: un token ahí rompería `uv sync` en el propio repositorio.

## Los dos mecanismos de personalización

Están documentados en `scripts/lib/replace.sh`, y confundirlos rompe cosas de
formas confusas:

- **Archivos de prosa** (`README.md`, `PROJECT.md`, `AGENTS.md`) → tokens
  `__KIRO_ALGO__`. Un token sin sustituir se ve a simple vista y no rompe nada.
- **Archivos que lee una herramienta** (`pyproject.toml`) → valores por defecto
  válidos, reescritos por clave.

Nunca uses `{{ }}` como sintaxis de token: el proyecto está lleno de plantillas
Jinja2 y un `sed` las destrozaría.

## Antes de tocar `setup.sh`

Es el archivo más frágil del repositorio: un fallo deja al usuario con un
proyecto a medio construir. Después de cualquier cambio:

```bash
docker run --rm -v "$PWD:/mnt" -w /mnt koalaman/shellcheck:stable -x setup.sh scripts/lib/*.sh

# Y el ciclo completo sobre una copia limpia
rsync -a --exclude .venv --exclude .git --exclude .env ./ /tmp/gen/
cd /tmp/gen && ./setup.sh --non-interactive --name Test --no-bootstrap --git-mode keep
make check
```

Es lo mismo que corre `.github/workflows/e2e-setup.yml`.

## Añadir una decisión

Si cambias un valor por defecto del stack, escribe un ADR. La skill `kiro-adr`
tiene el formato. Sin eso, la siguiente sesión de IA propondrá deshacerlo.

## Cambiar de versión de Basecoat o HTMX

Ver [`../vendor.md`](../vendor.md). Actualiza la tabla de versiones y revisa
visualmente antes de commitear: son cambios que los tests no detectan.

## Antes de publicar una versión

1. `make check` en verde
2. E2E local con las tres combinaciones de `--email-provider`
3. `docker build --target production .`
4. Entrada en `CHANGELOG.md` **con su etiqueta** `[SEGURO]` / `[MIGRACIÓN]` /
   `[RUPTURA]` — es lo que hace viable la ruta de actualización de los proyectos
   existentes
5. Tag
