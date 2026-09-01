#!/usr/bin/env bash
# Salida por consola: colores, niveles y encabezados de sección.
# Se respeta NO_COLOR (https://no-color.org/) y se desactiva el color si no hay TTY.

# Guarda de inclusión: 'readonly' falla si el archivo se sourcea dos veces.
[[ -n ${_KIRO_LOG_SH_LOADED:-} ]] && return 0
_KIRO_LOG_SH_LOADED=1

if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
  readonly C_RESET=$'\033[0m'
  readonly C_BOLD=$'\033[1m'
  readonly C_DIM=$'\033[2m'
  readonly C_RED=$'\033[31m'
  readonly C_GREEN=$'\033[32m'
  readonly C_YELLOW=$'\033[33m'
  readonly C_BLUE=$'\033[34m'
else
  readonly C_RESET='' C_BOLD='' C_DIM='' C_RED='' C_GREEN='' C_YELLOW='' C_BLUE=''
fi

log::section() {
  printf '\n%s%s==>%s %s%s%s\n' "$C_BOLD" "$C_BLUE" "$C_RESET" "$C_BOLD" "$1" "$C_RESET"
}

log::info() { printf '    %s\n' "$1"; }
log::ok()   { printf '    %s✓%s %s\n' "$C_GREEN" "$C_RESET" "$1"; }
log::warn() { printf '    %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$1" >&2; }
log::hint() { printf '      %s%s%s\n' "$C_DIM" "$1" "$C_RESET"; }

log::error() { printf '\n%s%serror:%s %s\n' "$C_BOLD" "$C_RED" "$C_RESET" "$1" >&2; }

# Aborta con un mensaje de error y, opcionalmente, una pista accionable.
# Uso: log::die "no se encontró docker" "instálalo desde https://docs.docker.com/get-docker/"
log::die() {
  log::error "$1"
  [[ -n "${2:-}" ]] && printf '      %s%s%s\n\n' "$C_DIM" "$2" "$C_RESET" >&2
  exit 1
}
