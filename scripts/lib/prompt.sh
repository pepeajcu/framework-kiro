#!/usr/bin/env bash
# Preguntas interactivas con valores por defecto y validación.
#
# Contrato: las preguntas y los errores van a stderr; SOLO el valor final va a
# stdout. Así el llamador puede hacer `x=$(prompt::ask ...)` sin capturar ruido.
# Se evitan namerefs (`local -n`) a propósito: bash 3.2 de macOS no los soporta.
#
# Si NON_INTERACTIVE=true, toda pregunta devuelve su valor por defecto sin parar.

# --- Validadores -----------------------------------------------------------
# Devuelven 0 si el valor es aceptable; si no, explican el problema en stderr.

validate::nonempty() {
  [[ -n ${1:-} ]] && return 0
  log::warn "no puede quedar vacío"
  return 1
}

validate::any() { return 0; }

validate::slug() {
  local value=${1:-}
  if [[ $value =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
    return 0
  fi
  log::warn "solo minúsculas, números y guiones; debe empezar y terminar en alfanumérico"
  return 1
}

validate::port() {
  local value=${1:-}
  # Por debajo de 1024 hacen falta privilegios de root para escuchar.
  if [[ $value =~ ^[0-9]+$ ]] && ((value >= 1024 && value <= 65535)); then
    return 0
  fi
  log::warn "debe ser un número entre 1024 y 65535"
  return 1
}

validate::domain() {
  local value=${1:-}
  # Vacío es válido: el dominio es opcional hasta que haya despliegue.
  [[ -z $value ]] && return 0
  if [[ $value =~ ^[a-z0-9]([a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}$ ]]; then
    return 0
  fi
  log::warn "no parece un dominio válido (ej. midominio.com), o déjalo vacío"
  return 1
}

# --- Saneado ---------------------------------------------------------------

# prompt::sanitize — deja un valor apto para escribirse en un archivo.
#
# Existe por un fallo real: al escribir una descripción, pulsar las flechas del
# teclado inserta bytes de escape (\x1b[C) en el valor. TOML prohíbe caracteres
# de control dentro de una cadena, así que ese pyproject.toml quedaba inválido y
# `uv` se negaba a leerlo.
#
# El primer paso elimina la secuencia ANSI COMPLETA (\033[...letra). Borrar
# solo el byte de control dejaría el resto visible como texto: '[C'.
#
# Se aplica a TODOS los valores, vengan de una pregunta o de una flag: una flag
# también puede traer basura si el valor se pegó desde otro sitio.
prompt::sanitize() {
  printf '%s' "$1" \
    | sed -E $'s/\033\\[[0-9;]*[a-zA-Z]//g' \
    | tr -d '[:cntrl:]' \
    | tr -s '[:space:]' ' ' \
    | sed -e 's/^ *//' -e 's/ *$//'
}

# --- Transformaciones ------------------------------------------------------

# "Mi Proyecto Web" -> "mi-proyecto-web"
#
# Lo hace Python, no sed, porque `sed y/áé…/ae…/` cuenta BYTES cuando la
# configuración regional no es UTF-8 (una instalación mínima, un contenedor o
# un WSL sin locales generados). Ahí los dos conjuntos dejan de medir lo mismo,
# sed aborta con "strings for `y' command are different lengths", y el slug
# salía vacío: la pregunta se repetía sin default válido para siempre.
# python3 ya es un requisito del instalador y normaliza Unicode de verdad.
prompt::slugify() {
  python3 - "$1" <<'SLUGIFY'
import re
import sys
import unicodedata

# NFKD separa la letra base de su diacrítico; descartar los diacríticos deja
# el ASCII equivalente ('ñ' -> 'n', 'ç' -> 'c') sin tablas escritas a mano.
text = unicodedata.normalize("NFKD", sys.argv[1])
text = "".join(ch for ch in text if not unicodedata.combining(ch))
sys.stdout.write(re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower())
SLUGIFY
}

# Un slug con guiones no sirve como nombre de base de datos ni de rol en
# PostgreSQL sin comillas: se convierte a snake_case.
prompt::to_snake() { printf '%s' "$1" | tr '-' '_'; }

# --- Preguntas -------------------------------------------------------------

# prompt::ask "Pregunta" "valor-por-defecto" [validador]
prompt::ask() {
  local question=$1 default=${2:-} validator=${3:-validate::nonempty}
  local answer="" stdin_closed=false

  if [[ ${NON_INTERACTIVE:-false} == true ]]; then
    printf '%s' "$default"
    return 0
  fi

  while true; do
    local prompt_text="    $question: "
    [[ -n $default ]] && prompt_text="    $question [$default]: "

    # -e activa readline: las flechas mueven el cursor en vez de insertar
    # secuencias de escape en el valor. -p escribe el prompt a stderr, así que
    # no contamina el stdout que captura el llamador.
    # Si stdin se cierra (pipe, Ctrl-D) se acepta el valor por defecto.
    if ! IFS= read -r -e -p "$prompt_text" answer; then
      stdin_closed=true
      answer=$default
      printf '\n' >&2
    fi
    answer=$(prompt::sanitize "${answer:-$default}")

    if "$validator" "$answer"; then
      printf '%s' "$answer"
      return 0
    fi

    # Sin stdin, repetir la pregunta es un bucle infinito: el default ya falló
    # la validación y no hay forma de escribir otro. Pasaba de verdad cuando el
    # default salía vacío, y el instalador se quedaba escupiendo el mismo aviso.
    if [[ $stdin_closed == true ]]; then
      log::die "«$question» no tiene una respuesta válida y no hay entrada para pedirla" \
        "pásala por flag (./setup.sh --help) o ejecuta el instalador en una terminal interactiva"
    fi
  done
}

# prompt::yes_no "Pregunta" "y"|"n"  -> código de salida 0 si sí
prompt::yes_no() {
  local question=$1 default=${2:-y} answer=""
  local hint="[Y/n]"
  [[ $default == n ]] && hint="[y/N]"

  if [[ ${NON_INTERACTIVE:-false} == true ]]; then
    [[ $default == y ]]
    return
  fi

  while true; do
    printf '    %s %s: ' "$question" "$hint" >&2
    if ! IFS= read -r answer; then
      answer=$default
      printf '\n' >&2
    fi
    answer=${answer:-$default}
    case $(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]') in
      y | yes | s | si | sí) return 0 ;;
      n | no) return 1 ;;
      *) log::warn "responde 'y' o 'n'" ;;
    esac
  done
}

# Elección entre opciones fijas. Devuelve la opción elegida por stdout.
# prompt::choice "Pregunta" "resend" "resend" "smtp" "console"
prompt::choice() {
  local question=$1 default=$2
  shift 2
  local options=("$@") answer=""

  if [[ ${NON_INTERACTIVE:-false} == true ]]; then
    printf '%s' "$default"
    return 0
  fi

  while true; do
    printf '    %s (%s) [%s]: ' "$question" "$(
      IFS='/'
      printf '%s' "${options[*]}"
    )" "$default" >&2
    if ! IFS= read -r answer; then
      answer=$default
      printf '\n' >&2
    fi
    answer=${answer:-$default}

    local opt
    for opt in "${options[@]}"; do
      if [[ $answer == "$opt" ]]; then
        printf '%s' "$answer"
        return 0
      fi
    done
    log::warn "opción no válida"
  done
}
