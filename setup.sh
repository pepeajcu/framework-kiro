#!/usr/bin/env bash
#
# Kiro — instalador del proyecto.
#
# Convierte el esqueleto clonado en un proyecto propio y lo deja corriendo:
# comprueba requisitos, pregunta lo imprescindible, genera secretos, sustituye
# los tokens del esqueleto y levanta la base de datos.
#
#   ./setup.sh                        # interactivo
#   ./setup.sh --non-interactive --name "Mi Proyecto"
#   ./setup.sh --help
#
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"

# shellcheck source=scripts/lib/log.sh
source "$SCRIPT_DIR/scripts/lib/log.sh"
# shellcheck source=scripts/lib/prompt.sh
source "$SCRIPT_DIR/scripts/lib/prompt.sh"
# shellcheck source=scripts/lib/preflight.sh
source "$SCRIPT_DIR/scripts/lib/preflight.sh"
# shellcheck source=scripts/lib/replace.sh
source "$SCRIPT_DIR/scripts/lib/replace.sh"

readonly MARKER_FILE=".kiro-setup-done"

# Se pone a true en cuanto el instalador empieza a modificar el proyecto. Si algo
# falla después de ese punto, el usuario se queda con un proyecto a medio
# configurar y necesita saber cómo salir de ahí.
MUTATED=false

# Se ejecuta ante cualquier salida distinta de cero, incluidas las de log::die.
on_failure() {
  local code=$?
  [[ $code -eq 0 ]] && return 0
  [[ $MUTATED != true ]] && return 0

  printf '\n%s%s  El instalador se detuvo a mitad.%s\n' "$C_BOLD" "$C_YELLOW" "$C_RESET" >&2
  printf '  El proyecto quedó configurado a medias. Para volver a empezar:\n\n' >&2
  printf '    rm -f .env .kiro-setup-done\n' >&2
  printf '    git checkout -- .        %s# descarta los archivos ya personalizados%s\n' \
    "$C_DIM" "$C_RESET" >&2
  printf '    ./setup.sh\n\n' >&2
  printf '  %sSi ya no tienes el historial de git, lo más rápido es borrar la\n' "$C_DIM" >&2
  printf '  carpeta y volver a clonar.%s\n\n' "$C_RESET" >&2
}
trap on_failure EXIT

# Archivos y carpetas que pertenecen al framework, no a los proyectos que
# nacen de él. Se ofrecen para borrar al final del setup.
readonly FRAMEWORK_ONLY=(
  "docs/framework"
  ".github/workflows/e2e-setup.yml"
  "setup.sh"
  "scripts/lib"
)

# --- Valores (por defecto vacíos; los llenan las flags o los prompts) -------
PROJECT_NAME=""
PROJECT_SLUG=""
PROJECT_DESCRIPTION=""
PROJECT_DOMAIN=""
AUTHOR=""
EMAIL_PROVIDER=""
ADMIN_EMAIL=""
ADMIN_PASSWORD=""
WITH_ANALYTICS=""
GIT_MODE=""
DB_PORT=""
APP_PORT=""

NON_INTERACTIVE=false
DO_BOOTSTRAP=true
KEEP_FRAMEWORK_FILES=false
FORCE=false

usage() {
  cat <<'USAGE'
Kiro — instalador del proyecto

USO
    ./setup.sh [opciones]

OPCIONES DE PROYECTO
    --name TEXTO             Nombre del proyecto (ej. "Mi Proyecto")
    --slug TEXTO             Identificador en minúsculas (por defecto: derivado del nombre)
    --description TEXTO      Descripción de una línea
    --domain TEXTO           Dominio de producción (ej. midominio.com)
    --author TEXTO           Autor, para LICENSE y metadatos
    --email-provider NOMBRE  resend | smtp | console   (por defecto: resend)
    --db-port NUMERO         Puerto del host para PostgreSQL (por defecto: primero libre desde 5432)
    --app-port NUMERO        Puerto del host para la app     (por defecto: primero libre desde 8000)
    --with-analytics         Incluir GTM/GA4/Meta CAPI (por defecto: sí)
    --no-analytics           Omitir el módulo de analítica

OPCIONES DE EJECUCIÓN
    -y, --non-interactive    No preguntar nada; usar flags y valores por defecto
    --git-mode MODO          fresh | upstream | keep   (por defecto: fresh)
                               fresh    = historial nuevo, sin vínculo al framework
                               upstream = conserva Kiro como remote 'upstream'
                                          (habilita `make upgrade`)
                               keep     = no tocar git
    --no-bootstrap           No levantar Docker ni correr migraciones
    --keep-framework-files   Conservar los archivos internos del framework
    --force                  Volver a correr aunque el setup ya se haya ejecutado
    -h, --help               Mostrar esta ayuda

EJEMPLOS
    ./setup.sh
    ./setup.sh --non-interactive --name "Mi Proyecto" --no-analytics
    ./setup.sh -y --name Demo --git-mode keep --no-bootstrap
USAGE
}

# --- Parseo de argumentos --------------------------------------------------

parse_args() {
  while [[ $# -gt 0 ]]; do
    case $1 in
      --name) PROJECT_NAME=${2:?--name requiere un valor}; shift 2 ;;
      --slug) PROJECT_SLUG=${2:?--slug requiere un valor}; shift 2 ;;
      --description) PROJECT_DESCRIPTION=${2:?--description requiere un valor}; shift 2 ;;
      --domain) PROJECT_DOMAIN=${2:?--domain requiere un valor}; shift 2 ;;
      --author) AUTHOR=${2:?--author requiere un valor}; shift 2 ;;
      --email-provider) EMAIL_PROVIDER=${2:?--email-provider requiere un valor}; shift 2 ;;
      --db-port) DB_PORT=${2:?--db-port requiere un valor}; shift 2 ;;
      --app-port) APP_PORT=${2:?--app-port requiere un valor}; shift 2 ;;
      --with-analytics) WITH_ANALYTICS=true; shift ;;
      --no-analytics) WITH_ANALYTICS=false; shift ;;
      --git-mode) GIT_MODE=${2:?--git-mode requiere un valor}; shift 2 ;;
      -y | --non-interactive) NON_INTERACTIVE=true; shift ;;
      --no-bootstrap) DO_BOOTSTRAP=false; shift ;;
      --keep-framework-files) KEEP_FRAMEWORK_FILES=true; shift ;;
      --force) FORCE=true; shift ;;
      -h | --help) usage; exit 0 ;;
      *) log::error "opción desconocida: $1"; printf '\n' >&2; usage >&2; exit 2 ;;
    esac
  done
}

# --- Pasos -----------------------------------------------------------------

check_already_ran() {
  [[ -f $MARKER_FILE ]] || return 0
  [[ $FORCE == true ]] && {
    log::warn "el setup ya se ejecutó antes; continuando por --force"
    return 0
  }
  log::die "este proyecto ya fue configurado el $(cat "$MARKER_FILE" 2>/dev/null || echo '?')" \
    "volver a correrlo regeneraría .env con secretos nuevos y dejaría la base de datos inaccesible. Usa --force si es lo que quieres."
}

banner() {
  printf '\n%s  ██╗  ██╗██╗██████╗  ██████╗%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '%s  ██║ ██╔╝██║██╔══██╗██╔═══██╗%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '%s  █████╔╝ ██║██████╔╝██║   ██║%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '%s  ██╔═██╗ ██║██╔══██╗██║   ██║%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '%s  ██║  ██╗██║██║  ██║╚██████╔╝%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '%s  ╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝%s\n' "$C_BOLD$C_BLUE" "$C_RESET"
  printf '  %sPython · FastAPI · HTMX · PostgreSQL — listo para trabajar con IA%s\n' \
    "$C_DIM" "$C_RESET"
}

run_preflight() {
  log::section "Comprobando requisitos"
  preflight::require_cmd git "instálalo con el gestor de paquetes de tu sistema"
  preflight::require_python
  preflight::ensure_uv "$NON_INTERACTIVE"
  if [[ $DO_BOOTSTRAP == true ]]; then
    preflight::require_docker
  else
    log::info "docker omitido (--no-bootstrap)"
  fi
}

gather_answers() {
  log::section "Configuración del proyecto"
  if [[ $NON_INTERACTIVE == true ]]; then
    log::info "modo no interactivo: se usan las flags y los valores por defecto"
  fi

  [[ -n $PROJECT_NAME ]] || PROJECT_NAME=$(prompt::ask "Nombre del proyecto" "Mi Proyecto")
  [[ -n $PROJECT_SLUG ]] || PROJECT_SLUG=$(
    prompt::ask "Identificador (slug)" "$(prompt::slugify "$PROJECT_NAME")" validate::slug
  )
  [[ -n $PROJECT_DESCRIPTION ]] || PROJECT_DESCRIPTION=$(
    prompt::ask "Descripción corta" "Aplicación web construida con Kiro"
  )
  [[ -n $PROJECT_DOMAIN ]] || PROJECT_DOMAIN=$(
    prompt::ask "Dominio de producción (opcional)" "" validate::domain
  )
  [[ -n $AUTHOR ]] || AUTHOR=$(
    prompt::ask "Autor" "$(git config --get user.name 2>/dev/null || echo 'Anónimo')"
  )
  [[ -n $EMAIL_PROVIDER ]] || EMAIL_PROVIDER=$(
    prompt::choice "Proveedor de correo" "resend" "resend" "smtp" "console"
  )
  if [[ -z $WITH_ANALYTICS ]]; then
    if prompt::yes_no "¿Incluir analítica y SEO (GTM, GA4, Meta CAPI, sitemap)?" "y"; then
      WITH_ANALYTICS=true
    else
      WITH_ANALYTICS=false
    fi
  fi
  # Los valores por defecto son el primer puerto LIBRE, no el canónico: una
  # máquina de desarrollo con varios proyectos ya tiene el 5432 y el 8000
  # ocupados, y descubrirlo al arrancar es una pérdida de tiempo evitable.
  [[ -n $DB_PORT ]] || DB_PORT=$(
    prompt::ask "Puerto de PostgreSQL en el host" "$(preflight::find_free_port 5432)" validate::port
  )
  [[ -n $APP_PORT ]] || APP_PORT=$(
    prompt::ask "Puerto de la app en el host" "$(preflight::find_free_port 8000)" validate::port
  )

  [[ -n $GIT_MODE ]] || GIT_MODE=$(
    prompt::choice "Historial de git" "fresh" "fresh" "upstream" "keep"
  )

  # Saneado final. Las respuestas interactivas ya vienen limpias de
  # prompt::ask, pero los valores que llegan por flag no han pasado por ahí y
  # pueden traer caracteres de control si se pegaron desde otro sitio. Un solo
  # byte de escape aquí produce un pyproject.toml que `uv` no puede leer.
  PROJECT_NAME=$(prompt::sanitize "$PROJECT_NAME")
  PROJECT_SLUG=$(prompt::sanitize "$PROJECT_SLUG")
  PROJECT_DESCRIPTION=$(prompt::sanitize "$PROJECT_DESCRIPTION")
  PROJECT_DOMAIN=$(prompt::sanitize "$PROJECT_DOMAIN")
  AUTHOR=$(prompt::sanitize "$AUTHOR")

  # Los valores que llegan por flag no pasan por los validadores de las
  # preguntas, así que se comprueban aquí. Un valor inválido debe fallar AHORA,
  # antes de tocar nada, y no varios pasos más tarde con un error que no señala
  # su causa.
  validate::slug "$PROJECT_SLUG" || log::die "el slug '$PROJECT_SLUG' no es válido" \
    "solo minúsculas, números y guiones"

  case $EMAIL_PROVIDER in
    resend | smtp | console) ;;
    *) log::die "proveedor de correo no válido: '$EMAIL_PROVIDER'" "usa resend, smtp o console" ;;
  esac

  case $GIT_MODE in
    fresh | upstream | keep) ;;
    *) log::die "modo de git no válido: '$GIT_MODE'" "usa fresh, upstream o keep" ;;
  esac

  validate::port "$DB_PORT" || log::die "puerto de PostgreSQL no válido: '$DB_PORT'" \
    "debe ser un número entre 1024 y 65535"
  validate::port "$APP_PORT" || log::die "puerto de la app no válido: '$APP_PORT'" \
    "debe ser un número entre 1024 y 65535"

  # Valores derivados: PostgreSQL no acepta guiones en identificadores sin comillas.
  DB_NAME=$(prompt::to_snake "$PROJECT_SLUG")
  DB_USER=$DB_NAME
  YEAR=$(date +%Y)
  # El .env que se genera es el de DESARROLLO, así que BASE_URL apunta siempre a
  # localhost aunque haya dominio de producción. Si no, los enlaces de los
  # correos de recuperación saldrían apuntando a producción desde tu máquina.
  # El dominio real se configura en el panel de despliegue (ver docs/deploy-coolify.md).
  BASE_URL="http://localhost:$APP_PORT"

  log::ok "proyecto: $PROJECT_NAME ($PROJECT_SLUG)"
  log::ok "base de datos: $DB_NAME"
  log::ok "correo: $EMAIL_PROVIDER · analítica: $WITH_ANALYTICS · git: $GIT_MODE"
  log::ok "puertos: PostgreSQL $DB_PORT · app $APP_PORT"
}

# Un secreto criptográficamente seguro. openssl es lo habitual, pero no está
# garantizado en toda imagen base; Python siempre está (lo exige el preflight).
generate_secret() {
  if preflight::has openssl; then
    openssl rand -hex 32
  else
    python3 -c 'import secrets; print(secrets.token_hex(32))'
  fi
}

# La contraseña del primer administrador. Más corta que un secreto de firma
# porque alguien la va a teclear: 24 caracteres base64 siguen siendo ~140 bits.
generate_password() {
  if preflight::has openssl; then
    openssl rand -base64 18 | tr -d '\n'
  else
    python3 -c 'import secrets; print(secrets.token_urlsafe(18))'
  fi
}

write_env() {
  log::section "Generando .env con secretos nuevos"

  if [[ -f .env && $FORCE != true ]]; then
    log::die ".env ya existe" "bórralo o usa --force si de verdad quieres regenerarlo"
  fi

  local secret_key db_password
  secret_key=$(generate_secret)
  db_password=$(generate_secret)

  # Globales: final_message las enseña al terminar, porque nadie va a abrir el
  # .env a buscar con qué entrar la primera vez.
  ADMIN_EMAIL="admin@${PROJECT_DOMAIN:-example.com}"
  ADMIN_PASSWORD=$(generate_password)

  cat > .env <<ENVEOF
# Generado por ./setup.sh el $(date -Iseconds)
# NUNCA se comitea. Los valores de producción se configuran en el panel de deploy.

# --- Aplicación ---
APP_NAME="$PROJECT_NAME"
ENVIRONMENT=local
LOG_LEVEL=INFO
# En producción: https://${PROJECT_DOMAIN:-tu-dominio.com} (se configura en el panel de deploy)
BASE_URL=$BASE_URL

# --- Seguridad ---
# Firma cookies de sesión y tokens de un solo uso.
# Rotarlo cierra todas las sesiones e invalida los enlaces de recuperación.
SECRET_KEY=$secret_key

# --- Base de datos ---
# Desde el host (migraciones, tests): localhost.
# Desde el contenedor de la app: compose sobreescribe el host por 'db'.
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$db_password
POSTGRES_DB=$DB_NAME

# Puertos del HOST. Dentro de la red de compose los servicios siempre usan sus
# puertos internos (5432, 8000); esto solo controla por dónde se exponen fuera.
POSTGRES_PORT=$DB_PORT
APP_PORT=$APP_PORT

DATABASE_URL=postgresql+psycopg://$DB_USER:$db_password@localhost:$DB_PORT/$DB_NAME

# --- Autenticación ---
# Duración de la cookie de sesión.
SESSION_LIFETIME_DAYS=14

# Vida del enlace de recuperación de contraseña.
PASSWORD_RESET_TTL_MINUTES=30

# Longitud mínima. Es la única regla: las de composición ('una mayúscula, un
# símbolo') llevan a 'Password1!' y ya no las recomienda el NIST.
PASSWORD_MIN_LENGTH=12

# false = /register no existe y las cuentas las crea un administrador.
ALLOW_REGISTRATION=true

# El primer administrador, creado por 'make seed'. Si la cuenta ya existe, el
# seed NO le cambia la contraseña.
ADMIN_EMAIL="$ADMIN_EMAIL"
ADMIN_PASSWORD="$ADMIN_PASSWORD"

# --- Correo transaccional ---
# 'console' imprime los correos en stdout: es el valor seguro en local.
# console | resend | smtp
EMAIL_PROVIDER=$EMAIL_PROVIDER
EMAIL_FROM="no-reply@${PROJECT_DOMAIN:-example.com}"
EMAIL_FROM_NAME="$PROJECT_NAME"
RESEND_API_KEY=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ENVEOF

  if [[ $WITH_ANALYTICS == true ]]; then
    cat >> .env <<'ENVEOF'

# --- Analítica y SEO ---
# Cada variable vacía desactiva su integración: nada se renderiza sin ID.
# Los comentarios van en su propia línea: Docker Compose no los separa del
# valor, así que 'GTM_ID=  # GTM-XXX' acabaría valiendo "# GTM-XXX".

# GTM-XXXXXXX
GTM_ID=

# G-XXXXXXXXXX
GA4_MEASUREMENT_ID=

# Necesario para el Measurement Protocol server-side
GA4_API_SECRET=

META_PIXEL_ID=

# Necesario para la Conversions API server-side
META_CAPI_TOKEN=

# Contenido del meta tag de verificación de Search Console
GSC_VERIFICATION=
ENVEOF
  fi

  chmod 600 .env
  MUTATED=true
  log::ok ".env creado (permisos 600)"
  log::hint "secretos generados con $(preflight::has openssl && echo 'openssl' || echo 'secrets de Python')"
}

# El README.md del repositorio es la portada de Kiro en GitHub. El proyecto
# generado necesita el suyo propio, así que se instala desde la plantilla antes
# de sustituir tokens.
install_project_readme() {
  local template="docs/framework/project-README.md"
  [[ -f $template ]] && mv -f "$template" README.md

  # El LICENSE del repositorio es el de Kiro. Un proyecto generado necesita el
  # suyo: sin esto, el sitio de un cliente nacería con el copyright del autor
  # del framework, que además de incorrecto es un problema legal real.
  local license_template="docs/framework/project-LICENSE"
  [[ -f $license_template ]] && mv -f "$license_template" LICENSE

  return 0
}

substitute_tokens() {
  log::section "Personalizando archivos del proyecto"

  install_project_readme

  export KIRO_PROJECT_NAME="$PROJECT_NAME"
  export KIRO_PROJECT_SLUG="$PROJECT_SLUG"
  export KIRO_PROJECT_DESCRIPTION="$PROJECT_DESCRIPTION"
  export KIRO_PROJECT_DOMAIN="${PROJECT_DOMAIN:-localhost}"
  export KIRO_DB_NAME="$DB_NAME"
  export KIRO_AUTHOR="$AUTHOR"
  export KIRO_YEAR="$YEAR"

  replace::apply
  replace::pyproject
  replace::verify || log::die "la sustitución de tokens dejó marcadores sin reemplazar" \
    "es un bug del esqueleto, no de tus respuestas"
  replace::assert_templates_intact

  # uv.lock guarda el nombre del proyecto, así que renombrarlo lo invalida.
  # Sin este paso, `uv sync --frozen` falla tanto en CI como en el Dockerfile
  # con "Missing workspace member". Se regenera aquí, no en el bootstrap,
  # porque forma parte de personalizar el proyecto, no de arrancarlo.
  if [[ -f uv.lock ]]; then
    uv lock --quiet 2>/dev/null || uv lock
    log::ok "uv.lock actualizado con el nombre del proyecto"
  fi

  log::ok "archivos personalizados"
}

cleanup_framework_files() {
  [[ $KEEP_FRAMEWORK_FILES == true ]] && {
    log::info "archivos del framework conservados (--keep-framework-files)"
    return 0
  }

  log::section "Limpiando archivos internos del framework"
  if ! prompt::yes_no "¿Eliminar el instalador y la documentación interna de Kiro?" "y"; then
    log::info "conservados"
    return 0
  fi

  local target
  for target in "${FRAMEWORK_ONLY[@]}"; do
    if [[ -e $target ]]; then
      rm -rf -- "$target"
      log::info "· $target"
    fi
  done
  log::ok "el proyecto ya no arrastra el andamiaje del framework"
}

setup_git() {
  log::section "Configurando git"
  case $GIT_MODE in
    keep)
      log::info "sin cambios en git (--git-mode keep)"
      ;;
    fresh)
      rm -rf .git
      git init -q
      git add -A
      git -c user.name="${AUTHOR:-Kiro}" -c user.email="setup@kiro.local" \
        commit -q -m "chore: proyecto inicial desde Kiro" || true
      log::ok "historial nuevo, sin vínculo con el framework"
      ;;
    upstream)
      if git remote get-url origin >/dev/null 2>&1; then
        git remote rename origin upstream 2>/dev/null || true
        log::ok "el framework quedó como remote 'upstream'"
        log::hint "trae mejoras después con 'make upgrade'"
        log::hint "añade tu repo con: git remote add origin <url>"
      else
        log::warn "no había remote 'origin'; nada que renombrar"
      fi
      ;;
    *)
      log::die "modo de git no válido: '$GIT_MODE'" "usa fresh, upstream o keep"
      ;;
  esac
}

bootstrap() {
  [[ $DO_BOOTSTRAP == true ]] || {
    log::info "bootstrap omitido (--no-bootstrap)"
    return 0
  }

  log::section "Instalando dependencias"
  uv sync --quiet || log::die "falló 'uv sync'" "revisa el error de arriba y vuelve a correr con --force"
  log::ok "entorno virtual listo en .venv/"

  if [[ -f compose.yml ]]; then
    log::section "Levantando PostgreSQL"
    docker compose up -d db
    wait_for_db || log::die "PostgreSQL no llegó a estar disponible" \
      "revisa los logs con 'docker compose logs db'"
    log::ok "base de datos disponible"
  else
    log::info "aún no hay compose.yml; se omite la base de datos"
  fi

  if [[ -d migrations/versions ]] && compgen -G "migrations/versions/*.py" >/dev/null; then
    log::section "Aplicando migraciones"
    uv run alembic upgrade head
    log::ok "esquema al día"

    if [[ -f scripts/seed.py ]]; then
      log::section "Creando el primer administrador"
      uv run python -m scripts.seed
    fi
  else
    log::info "aún no hay migraciones que aplicar"
  fi

  if [[ -f app/static/css/input.css ]]; then
    log::section "Compilando CSS"
    uv run tailwindcss -i app/static/css/input.css -o app/static/css/app.css --minify \
      && log::ok "app.css generado"
  fi
}

# PostgreSQL tarda unos segundos en aceptar conexiones tras arrancar el
# contenedor. Se espera al healthcheck en vez de dormir un tiempo fijo.
wait_for_db() {
  local attempts=30
  log::info "esperando a que PostgreSQL acepte conexiones…"
  while ((attempts-- > 0)); do
    if docker compose exec -T db pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

write_marker() {
  date -Iseconds > "$MARKER_FILE"
}

final_message() {
  printf '\n%s%s  ✓ %s está listo.%s\n\n' "$C_BOLD" "$C_GREEN" "$PROJECT_NAME" "$C_RESET"
  printf '  %sSiguientes pasos%s\n' "$C_BOLD" "$C_RESET"
  printf '    make dev            arrancar en http://localhost:%s\n' "$APP_PORT"
  printf '    make check          lint + tipos + tests\n'
  printf '    make help           ver todos los comandos\n\n'
  if [[ $DO_BOOTSTRAP == true && -n $ADMIN_PASSWORD ]]; then
    printf '  %sTu cuenta de administrador%s\n' "$C_BOLD" "$C_RESET"
    printf '    %s / %s\n' "$ADMIN_EMAIL" "$ADMIN_PASSWORD"
    printf '    Está también en .env. Cámbiala antes de desplegar.\n\n'
  fi

  printf '  %sAntes de pedirle una feature a la IA%s\n' "$C_BOLD" "$C_RESET"
  printf '    Rellena %sPROJECT.md%s con las entidades y reglas de negocio.\n' "$C_BOLD" "$C_RESET"
  printf '    Es lo que el agente lee para no inventarse tu dominio.\n\n'
}

main() {
  parse_args "$@"
  check_already_ran
  banner
  run_preflight
  gather_answers
  write_env
  substitute_tokens
  bootstrap
  # La limpieza va ANTES de git: así el commit inicial captura el proyecto ya
  # depurado, en vez de dejar los archivos del framework en el historial.
  cleanup_framework_files
  setup_git
  write_marker
  final_message
}

main "$@"
