#!/usr/bin/env bash
# Verificación de requisitos previos.
#
# Regla de esta librería: cada fallo debe decir QUÉ falta y CÓMO instalarlo.
# Un instalador que solo dice "command not found" no es un instalador.

# ¿Existe el comando en el PATH?
preflight::has() { command -v "$1" >/dev/null 2>&1; }

preflight::require_cmd() {
  local cmd=$1 hint=$2
  preflight::has "$cmd" || log::die "no se encontró '$cmd' en el PATH" "$hint"
  log::ok "$cmd"
}

# Python 3.12 o superior. Se compara con el propio intérprete para no
# depender de parsear texto de versión, que cambia entre distribuciones.
preflight::require_python() {
  local min_major=3 min_minor=12
  preflight::has python3 || log::die "no se encontró 'python3'" \
    "instálalo con el gestor de paquetes de tu sistema (apt install python3)"

  if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= ($min_major, $min_minor) else 1)"; then
    log::die "se requiere Python ${min_major}.${min_minor}+, se encontró $(python3 -V 2>&1)" \
      "instala una versión más reciente, o deja que uv gestione el intérprete"
  fi
  log::ok "$(python3 -V 2>&1)"
}

# Docker debe estar instalado Y con el daemon corriendo. Son dos fallos
# distintos con dos soluciones distintas.
preflight::require_docker() {
  preflight::has docker || log::die "no se encontró 'docker'" \
    "instálalo desde https://docs.docker.com/get-docker/"

  if ! docker compose version >/dev/null 2>&1; then
    log::die "'docker compose' no está disponible (¿plugin v2 sin instalar?)" \
      "instala el plugin docker-compose-v2 de tu distribución"
  fi

  if ! docker info >/dev/null 2>&1; then
    log::die "el daemon de Docker no responde" \
      "arráncalo con 'sudo systemctl start docker', o añade tu usuario al grupo 'docker'"
  fi
  log::ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '')"
}

# uv gestiona dependencias y la versión de Python. Si falta, se ofrece instalarlo:
# es la única dependencia que este script instala por su cuenta, y solo con permiso.
preflight::ensure_uv() {
  local auto_yes=${1:-false}

  if preflight::has uv; then
    log::ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"
    return 0
  fi

  log::warn "uv no está instalado (es el gestor de paquetes de Python que usa Kiro)"
  if [[ $auto_yes != true ]]; then
    prompt::yes_no "¿Instalar uv ahora?" "y" || log::die "uv es obligatorio para continuar" \
      "instálalo a mano: curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi

  log::info "instalando uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 \
    || log::die "falló la instalación de uv" "instálalo a mano desde https://docs.astral.sh/uv/"

  # El instalador de uv lo deja en ~/.local/bin, que puede no estar en el PATH
  # de esta sesión todavía.
  export PATH="$HOME/.local/bin:$PATH"
  preflight::has uv || log::die "uv se instaló pero no está en el PATH" \
    "añade \$HOME/.local/bin a tu PATH y vuelve a correr ./setup.sh"
  log::ok "uv instalado"
}

# preflight::port_free PUERTO — ¿está libre para escuchar?
#
# Se comprueba con Python en vez de con ss/lsof/netstat porque cada
# distribución trae uno distinto (o ninguno), y python3 ya es un requisito.
preflight::port_free() {
  python3 - "$1" <<'PORTCHECK'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    # SO_REUSEADDR replica lo que hace un servidor real: sin esto, un puerto en
    # TIME_WAIT se reportaría ocupado cuando en realidad sí se puede usar.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("127.0.0.1", port))
    except OSError:
        sys.exit(1)
sys.exit(0)
PORTCHECK
}

# preflight::find_free_port PUERTO_BASE [INTENTOS] — primer puerto libre desde
# el base. Devuelve el puerto por stdout.
#
# Existe porque una máquina de desarrollo real acumula proyectos: con varios
# Postgres y un panel de despliegue local, dar por hecho el 5432 o el 8000
# garantiza una colisión.
preflight::find_free_port() {
  local base=$1 attempts=${2:-20} port
  for ((port = base; port < base + attempts; port++)); do
    if preflight::port_free "$port"; then
      printf '%s' "$port"
      return 0
    fi
  done
  log::die "no se encontró ningún puerto libre entre $base y $((base + attempts - 1))" \
    "libera alguno o indica otro con --db-port / --app-port"
}
