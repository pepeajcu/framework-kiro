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

# --- Transformaciones ------------------------------------------------------

# "Wedding Planner GT" -> "wedding-planner-gt"
# Se transliteran los acentos del español a mano en vez de depender de
# `iconv //TRANSLIT`, cuyo comportamiento difiere entre glibc y macOS.
prompt::slugify() {
  printf '%s' "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -e 'y/áàäâãéèëêíìïîóòöôõúùüûñç/aaaaaeeeeiiiiooooouuuunc/' \
          -e 's/[^a-z0-9]\+/-/g' \
          -e 's/^-\+//' -e 's/-\+$//'
}

# Un slug con guiones no sirve como nombre de base de datos ni de rol en
# PostgreSQL sin comillas: se convierte a snake_case.
prompt::to_snake() { printf '%s' "$1" | tr '-' '_'; }

# --- Preguntas -------------------------------------------------------------

# prompt::ask "Pregunta" "valor-por-defecto" [validador]
prompt::ask() {
  local question=$1 default=${2:-} validator=${3:-validate::nonempty}
  local answer=""

  if [[ ${NON_INTERACTIVE:-false} == true ]]; then
    printf '%s' "$default"
    return 0
  fi

  while true; do
    if [[ -n $default ]]; then
      printf '    %s [%s]: ' "$question" "$default" >&2
    else
      printf '    %s: ' "$question" >&2
    fi

    # Si stdin se cierra (pipe, Ctrl-D) se acepta el valor por defecto en vez
    # de entrar en un bucle infinito.
    if ! IFS= read -r answer; then
      answer=$default
      printf '\n' >&2
    fi
    answer=${answer:-$default}

    if "$validator" "$answer"; then
      printf '%s' "$answer"
      return 0
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
