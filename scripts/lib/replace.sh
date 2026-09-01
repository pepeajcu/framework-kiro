#!/usr/bin/env bash
# Sustitución de tokens del esqueleto por los valores del proyecto.
#
# ┌─ POR QUÉ ESTE ARCHIVO EXISTE ────────────────────────────────────────────┐
# │ El proyecto usa Jinja2, así que sus plantillas están llenas de {{ ... }}.│
# │ Si los tokens usaran esa misma sintaxis, un `sed` los destrozaría.       │
# │                                                                          │
# │ Por eso:                                                                 │
# │   1. Los tokens son __KIRO_ALGO__, sintaxis que Jinja nunca produce.     │
# │   2. La sustitución es LITERAL (vía Python), no regex: ningún valor con  │
# │      /, &, \ o saltos de línea puede corromper el resultado.             │
# │   3. Solo se tocan los archivos de la lista blanca. NUNCA recursivo.     │
# └──────────────────────────────────────────────────────────────────────────┘
#
# ┌─ DOS MECANISMOS, NO UNO ─────────────────────────────────────────────────┐
# │ El esqueleto clonado tiene que FUNCIONAR tal cual, antes de setup.sh:    │
# │ es la premisa del modelo git clone (ADR-0003). Un token dentro de        │
# │ pyproject.toml rompe `uv sync`: no es un nombre de paquete válido.       │
# │                                                                          │
# │ Por eso hay dos caminos:                                                 │
# │   · Archivos de PROSA (README, PROJECT.md, AGENTS.md) -> tokens.         │
# │     Un token sin sustituir se ve a simple vista y no rompe nada.         │
# │   · Archivos que lee una HERRAMIENTA (pyproject.toml) -> valores por     │
# │     defecto válidos, reescritos por clave con precisión quirúrgica.      │
# │                                                                          │
# │ compose.yml y alembic.ini no aparecen aquí a propósito: leen su          │
# │ configuración de .env, así que no hay nada que sustituir en ellos.       │
# └──────────────────────────────────────────────────────────────────────────┘

# Archivos donde se sustituyen tokens. Añadir aquí y solo aquí.
readonly KIRO_REPLACE_FILES=(
  "PROJECT.md"
  "README.md"
  "AGENTS.md"
  "LICENSE"
)

# Rutas que la sustitución no debe tocar jamás. Se verifica en tiempo de
# ejecución para que un descuido futuro falle ruidosamente y no en silencio.
readonly KIRO_FORBIDDEN_PREFIXES=(
  "app/templates/"
  "app/static/"
  "app/emails/templates/"
  "scripts/"
  "docs/"
  ".claude/"
  "migrations/"
)

# Comprueba que la lista blanca no invade territorio prohibido.
replace::assert_whitelist_safe() {
  local file prefix
  for file in "${KIRO_REPLACE_FILES[@]}"; do
    for prefix in "${KIRO_FORBIDDEN_PREFIXES[@]}"; do
      if [[ $file == "$prefix"* ]]; then
        log::die "bug en scripts/lib/replace.sh: '$file' está en la lista blanca pero '$prefix' es zona prohibida" \
          "las plantillas Jinja no pueden pasar por sustitución de tokens"
      fi
    done
  done
}

# replace::apply — sustituye los tokens en los archivos de la lista blanca.
# Los valores se leen del entorno (los exporta setup.sh).
replace::apply() {
  replace::assert_whitelist_safe

  local existing=()
  local file
  for file in "${KIRO_REPLACE_FILES[@]}"; do
    [[ -f $file ]] && existing+=("$file")
  done

  if [[ ${#existing[@]} -eq 0 ]]; then
    log::warn "no se encontró ningún archivo de la lista blanca; nada que sustituir"
    return 0
  fi

  # Sustitución literal en Python: sin regex, sin escapado, sin sorpresas.
  KIRO_FILES="$(printf '%s\n' "${existing[@]}")" python3 - <<'PY'
import os
import pathlib

TOKENS = (
    "__KIRO_PROJECT_NAME__",
    "__KIRO_PROJECT_SLUG__",
    "__KIRO_PROJECT_DESCRIPTION__",
    "__KIRO_PROJECT_DOMAIN__",
    "__KIRO_DB_NAME__",
    "__KIRO_AUTHOR__",
    "__KIRO_YEAR__",
)

missing = [t for t in TOKENS if os.environ.get(t.strip("_")) is None]
if missing:
    raise SystemExit(f"error: faltan valores para los tokens: {', '.join(missing)}")

values = {token: os.environ[token.strip("_")] for token in TOKENS}

for name in os.environ["KIRO_FILES"].splitlines():
    path = pathlib.Path(name)
    original = path.read_text(encoding="utf-8")
    updated = original
    for token, value in values.items():
        updated = updated.replace(token, value)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        print(f"    · {name}")
PY
}

# replace::pyproject — reescribe name y description en pyproject.toml.
#
# Se edita POR CLAVE, no por búsqueda de texto: así no hay forma de que el
# valor por defecto ("kiro-app") se sustituya por accidente donde aparezca
# como parte de otra cosa.
#
# El resultado se VALIDA parseando el TOML antes de dar el paso por bueno.
# Un pyproject.toml corrupto rompe uv, y el error aparece varios pasos más
# tarde, lejos de su causa.
replace::pyproject() {
  [[ -f pyproject.toml ]] || return 0

  python3 - <<'TOMLEDIT'
import os
import pathlib
import re
import tomllib

path = pathlib.Path("pyproject.toml")
text = path.read_text(encoding="utf-8")

# El nombre del paquete debe cumplir PEP 508. validate::slug ya lo comprueba,
# pero se repite aquí porque este archivo podría invocarse desde otro sitio.
slug = os.environ["KIRO_PROJECT_SLUG"]
if not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", slug):
    raise SystemExit(f"error: '{slug}' no es un nombre de paquete válido")


def toml_escape(value: str) -> str:
    """Prepara un texto para meterlo en una cadena básica de TOML.

    Los caracteres de control se ELIMINAN, no se escapan: TOML los prohíbe
    dentro de una cadena básica, y llegan aquí cuando alguien pulsa las
    flechas del teclado al responder una pregunta (queda un \\x1b[C literal).
    """
    cleaned = "".join(ch for ch in value if ch.isprintable())
    return cleaned.replace("\\", "\\\\").replace('"', '\\"')


description = toml_escape(os.environ["KIRO_PROJECT_DESCRIPTION"])

# Anclado a inicio de línea y limitado a la primera aparición: el bloque
# [project] es el primero del archivo.
text, n_name = re.subn(
    r'^name = ".*"$', f'name = "{slug}"', text, count=1, flags=re.M
)
text, n_desc = re.subn(
    r'^description = ".*"$', f'description = "{description}"', text, count=1, flags=re.M
)

if not (n_name and n_desc):
    raise SystemExit("error: no se encontraron name/description en pyproject.toml")

# Validar ANTES de escribir: si el resultado no parsea, el archivo original
# se queda intacto y el error señala su causa real.
try:
    tomllib.loads(text)
except tomllib.TOMLDecodeError as exc:
    raise SystemExit(f"error: la personalización produjo un TOML inválido: {exc}") from exc

path.write_text(text, encoding="utf-8")
print("    · pyproject.toml")
TOMLEDIT
}

# replace::verify — red de seguridad posterior a la sustitución.
#
# Detecta dos fallos distintos:
#   a) tokens sin sustituir en los archivos de la lista blanca (valor olvidado);
#   b) tokens colocados en archivos que NO están en la lista blanca — el bug
#      silencioso: el proyecto se genera con un "__KIRO_ALGO__" literal dentro.
replace::verify() {
  local leftovers
  # 'scripts' y 'docs' se excluyen porque ahí los tokens aparecen como
  # documentación y como definición, no como marcadores a sustituir.
  leftovers=$(grep -rIl \
    --exclude-dir=.git --exclude-dir=.venv --exclude-dir=scripts --exclude-dir=docs \
    -e '__KIRO_[A-Z_]*__' . 2>/dev/null || true)

  if [[ -n $leftovers ]]; then
    log::error "quedaron tokens sin sustituir en:"
    printf '%s\n' "$leftovers" | sed 's/^/        /' >&2
    log::hint "añade esos archivos a KIRO_REPLACE_FILES en scripts/lib/replace.sh"
    return 1
  fi
  return 0
}

# replace::assert_templates_intact — confirma que las plantillas Jinja siguen
# teniendo su sintaxis. Si la sustitución se volviera recursiva por error, esto
# es lo que lo detecta.
replace::assert_templates_intact() {
  local dir="app/templates"
  [[ -d $dir ]] || return 0

  if ! grep -rqI -- '{[{%]' "$dir" 2>/dev/null; then
    log::warn "no se detectó sintaxis Jinja en $dir (¿plantillas aún vacías?)"
    return 0
  fi
  log::ok "plantillas Jinja intactas"
}
