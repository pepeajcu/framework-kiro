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

# Diagnóstico del último preflight::check_docker fallido. Se expone en vez de
# imprimirse y ya está porque el arreglo es distinto en cada caso, y quien llama
# necesita poder recomendarlo: un instalador que sabe cuál es la solución y no
# la dice está eligiendo por el usuario sin contárselo.
PREFLIGHT_DOCKER_PROBLEM=""
PREFLIGHT_DOCKER_FIX=()

# Docker instalado, con el plugin compose v2, y con el daemon respondiendo.
# Son tres fallos distintos con tres soluciones distintas, así que se separan.
#
# Avisa y devuelve 1 en vez de abortar: Docker solo hace falta para levantar
# PostgreSQL, y el instalador puede terminar su trabajo sin él. Quien llama
# decide si eso es fatal.
preflight::check_docker() {
  PREFLIGHT_DOCKER_PROBLEM=""
  PREFLIGHT_DOCKER_FIX=()

  if ! preflight::has docker; then
    PREFLIGHT_DOCKER_PROBLEM="Docker no está instalado"
    PREFLIGHT_DOCKER_FIX=(
      "sigue las instrucciones de https://docs.docker.com/engine/install/"
      "(en Ubuntu y Debian, el paquete de la distribución también sirve:"
      " sudo apt install docker.io docker-compose-v2)"
    )
    log::warn "$PREFLIGHT_DOCKER_PROBLEM"
    return 1
  fi

  if ! docker compose version >/dev/null 2>&1; then
    PREFLIGHT_DOCKER_PROBLEM="falta el plugin 'docker compose' v2"
    PREFLIGHT_DOCKER_FIX=(
      "sudo apt install docker-compose-v2   # o el equivalente de tu distribución"
    )
    log::warn "$PREFLIGHT_DOCKER_PROBLEM"
    return 1
  fi

  if ! docker info >/dev/null 2>&1; then
    PREFLIGHT_DOCKER_PROBLEM="el daemon de Docker no responde"
    # Dos causas con el mismo síntoma, y distinguirlas requiere leer el error
    # de docker info, así que se dan las dos en el orden más probable.
    PREFLIGHT_DOCKER_FIX=(
      "sudo systemctl enable --now docker"
      ""
      "si el servicio ya estaba corriendo, es que tu usuario no puede hablar"
      "con el socket. Añádelo al grupo (y vuelve a entrar en la sesión):"
      ""
      "sudo usermod -aG docker $USER && newgrp docker"
    )
    log::warn "$PREFLIGHT_DOCKER_PROBLEM"
    return 1
  fi

  log::ok "docker $(docker version --format '{{.Server.Version}}' 2>/dev/null || echo '')"
  return 0
}

# Imprime, indentado, el arreglo del último check_docker fallido.
preflight::docker_fix() {
  local line
  for line in "${PREFLIGHT_DOCKER_FIX[@]}"; do
    # Las líneas vacías separan párrafos: indentarlas deja espacios sueltos.
    if [[ -z $line ]]; then
      printf '\n' >&2
    else
      printf '    %s\n' "$line" >&2
    fi
  done
}

preflight::require_docker() {
  preflight::check_docker && return 0
  printf '\n' >&2
  preflight::docker_fix
  printf '\n' >&2
  log::die "$PREFLIGHT_DOCKER_PROBLEM" \
    "arréglalo, o corre './setup.sh --no-bootstrap' para configurar el proyecto sin levantar la base de datos"
}

# Directorios donde el instalador de uv puede haber dejado el binario, en el
# mismo orden de preferencia que usa él. No basta con ~/.local/bin: las
# variables XDG y una instalación vieja por cargo lo mueven a otro sitio.
preflight::uv_dirs() {
  printf '%s\n' \
    "${UV_INSTALL_DIR:-}" \
    "${XDG_BIN_HOME:-}" \
    "$HOME/.local/bin" \
    "${CARGO_HOME:-$HOME/.cargo}/bin"
}

# Encuentra un uv ya instalado que no esté en el PATH y lo añade al de esta
# sesión. Devuelve 0 si lo consiguió.
#
# Existe por un fallo real: en Debian y Ubuntu, ~/.profile añade ~/.local/bin
# al PATH solo si ese directorio YA existía al iniciar sesión. En una máquina
# recién instalada no existe, así que uv se instala ahí y sigue invisible hasta
# el siguiente login. El instalador lo descargaba, no lo encontraba, y moría;
# volver a correrlo repetía el ciclo entero.
preflight::adopt_uv() {
  local dir
  while IFS= read -r dir; do
    [[ -n $dir && -x "$dir/uv" ]] || continue
    export PATH="$dir:$PATH"
    hash -r 2>/dev/null || true
    return 0
  done < <(preflight::uv_dirs)
  return 1
}

# uv está en el PATH de ESTE proceso, no en el de la terminal de quien llama.
preflight::hint_uv_path() {
  local dir=$1
  log::hint "si 'uv' no aparece en una terminal nueva, añade a tu ~/.bashrc:"
  log::hint "  export PATH=\"$dir:\$PATH\""
}

# uv gestiona dependencias y la versión de Python. Si falta, se ofrece instalarlo:
# es la única dependencia que este script instala por su cuenta, y solo con permiso.
preflight::ensure_uv() {
  local auto_yes=${1:-false}

  if preflight::has uv; then
    log::ok "uv $(uv --version 2>/dev/null | awk '{print $2}')"
    return 0
  fi

  if preflight::adopt_uv; then
    log::ok "uv $(uv --version 2>/dev/null | awk '{print $2}') (estaba instalado fuera del PATH)"
    preflight::hint_uv_path "$(dirname "$(command -v uv)")"
    return 0
  fi

  log::warn "uv no está instalado (es el gestor de paquetes de Python que usa Kiro)"
  if [[ $auto_yes != true ]]; then
    prompt::yes_no "¿Instalar uv ahora?" "y" || log::die "uv es obligatorio para continuar" \
      "instálalo a mano: curl -LsSf https://astral.sh/uv/install.sh | sh"
  fi

  # curl no se comprueba en el preflight general porque solo hace falta aquí,
  # pero una imagen mínima de Debian no lo trae y sin él el mensaje de error
  # sería "falló la instalación de uv", que no señala la causa.
  preflight::has curl || log::die "hace falta 'curl' para descargar el instalador de uv" \
    "instálalo (sudo apt install curl) y vuelve a correr ./setup.sh"

  # Se fija el destino en vez de dejar que lo elija el instalador: si elige una
  # ruta que después no miramos, el setup muere sin decir dónde quedó el binario.
  local install_dir="${UV_INSTALL_DIR:-$HOME/.local/bin}"
  local out
  out=$(mktemp)

  log::info "instalando uv en $install_dir…"
  if ! curl -LsSf https://astral.sh/uv/install.sh \
      | env UV_INSTALL_DIR="$install_dir" sh >"$out" 2>&1; then
    # La salida del instalador es lo único que explica POR QUÉ falló. Taparla
    # deja un "falló la instalación" que no se puede depurar.
    sed -e 's/^/      /' "$out" >&2
    rm -f "$out"
    log::die "falló la instalación de uv" "instálalo a mano desde https://docs.astral.sh/uv/"
  fi
  rm -f "$out"

  export PATH="$install_dir:$PATH"
  hash -r 2>/dev/null || true

  preflight::has uv || preflight::adopt_uv || log::die \
    "uv se instaló pero no aparece en $install_dir" \
    "instálalo a mano desde https://docs.astral.sh/uv/ y vuelve a correr ./setup.sh"

  log::ok "uv instalado en $install_dir"
  preflight::hint_uv_path "$install_dir"
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
