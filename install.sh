#!/bin/bash

set -euo pipefail

readonly REPO="AlisaCat-S/komari-agent-webhost-lite"
readonly BRANCH="main"
readonly INSTALL_DIR="/opt/komari-lite"
readonly SERVICE_NAME="komari-agent-lite.service"
readonly SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
readonly VENV_DIR="${INSTALL_DIR}/venv"
readonly APP_ENTRY="${INSTALL_DIR}/py/komari-agent-python.py"
readonly REQUIREMENTS_FILE="${INSTALL_DIR}/requirements.txt"
readonly DEFAULT_PIP_INDEXES=(
    "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    "https://mirrors.aliyun.com/pypi/simple/"
    "https://pypi.org/simple"
)

HTTP_SERVER=""
TOKEN=""
INSTALL_GHPROXY=""
INCLUDE_NICS=""
LOG_LEVEL="1"
DISABLE_WEB_SSH="true"
TMP_DIR=""
SELECTED_PIP_INDEX=""

log() {
    local type="$1"
    local msg="$2"
    local color_red='\033[0;31m'
    local color_green='\033[0;32m'
    local color_yellow='\033[0;33m'
    local color_blue='\033[0;34m'
    local color_nc='\033[0m'

    case "$type" in
        "INFO") echo -e "${color_blue}INFO:${color_nc} $msg" ;;
        "SUCCESS") echo -e "${color_green}SUCCESS:${color_nc} $msg" ;;
        "WARN") echo -e "${color_yellow}WARNING:${color_nc} $msg" ;;
        "ERROR") echo -e "${color_red}ERROR:${color_nc} $msg" >&2 ;;
        *) echo "$msg" ;;
    esac
}

usage() {
    cat <<EOF
Komari Agent Lite installer

Usage:
  Legacy:
    sudo bash install.sh <http_server_address> <token>

  Main project compatible:
    wget -qO- https://ghfast.top/raw.githubusercontent.com/${REPO}/refs/heads/${BRANCH}/install.sh | \\
      sudo bash -s -- -e https://km.example.com -t TokenXXXXXXXXXXXX \\
      --install-ghproxy https://ghfast.top --include-nics eth0

Options:
  -e, --endpoint, --http-server <url>   Komari server address
  -t, --token <token>                   Komari token
  --install-ghproxy <url>               Prefix GitHub/raw downloads with a proxy host
  --include-nics <list>                 Comma-separated NIC allowlist passed to the agent
  --log-level <level>                   Agent log level, default: 1
  --disable-web-ssh                     Disable remote control support, default behavior
  --enable-web-ssh                      Enable remote control support
  Environment:
    PIP_INDEX_URL                       Force a specific pip index URL
  -h, --help                            Show this help
EOF
}

cleanup() {
    if [ -n "${TMP_DIR:-}" ] && [ -d "${TMP_DIR}" ]; then
        log "INFO" "Cleaning up temporary directory: ${TMP_DIR}"
        rm -rf "${TMP_DIR}"
    fi
}
trap cleanup EXIT

require_value() {
    local option="$1"
    local value="${2:-}"
    if [ -z "$value" ] || [[ "$value" == -* ]]; then
        log "ERROR" "Option ${option} requires a value."
        usage
        exit 1
    fi
}

parse_args() {
    if [ "$#" -eq 2 ] && [[ "${1:-}" != -* ]] && [[ "${2:-}" != -* ]]; then
        HTTP_SERVER="$1"
        TOKEN="$2"
        return
    fi

    while [ "$#" -gt 0 ]; do
        case "$1" in
            -e|--endpoint|--http-server)
                require_value "$1" "${2:-}"
                HTTP_SERVER="$2"
                shift 2
                ;;
            -t|--token)
                require_value "$1" "${2:-}"
                TOKEN="$2"
                shift 2
                ;;
            --install-ghproxy)
                require_value "$1" "${2:-}"
                INSTALL_GHPROXY="$2"
                shift 2
                ;;
            --include-nics)
                require_value "$1" "${2:-}"
                INCLUDE_NICS="$2"
                shift 2
                ;;
            --log-level)
                require_value "$1" "${2:-}"
                LOG_LEVEL="$2"
                shift 2
                ;;
            --disable-web-ssh)
                DISABLE_WEB_SSH="true"
                shift
                ;;
            --enable-web-ssh)
                DISABLE_WEB_SSH="false"
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown argument: $1"
                usage
                exit 1
                ;;
        esac
    done

    if [ -z "${HTTP_SERVER}" ] || [ -z "${TOKEN}" ]; then
        log "ERROR" "Both endpoint and token are required."
        usage
        exit 1
    fi
}

apply_proxy() {
    local url="$1"
    if [ -z "${INSTALL_GHPROXY}" ]; then
        printf '%s\n' "${url}"
        return
    fi

    local normalized_proxy="${INSTALL_GHPROXY%/}"
    local normalized_url="${url#https://}"
    normalized_url="${normalized_url#http://}"
    printf '%s/%s\n' "${normalized_proxy}" "${normalized_url}"
}

download_source_files() {
    local python_url
    local requirements_url
    python_url=$(apply_proxy "https://raw.githubusercontent.com/${REPO}/refs/heads/${BRANCH}/py/komari-agent-python.py")
    requirements_url=$(apply_proxy "https://raw.githubusercontent.com/${REPO}/refs/heads/${BRANCH}/py/requirements.txt")

    log "INFO" "Downloading lite agent source files"
    mkdir -p "${INSTALL_DIR}/py"
    curl -fL --progress-bar -o "${APP_ENTRY}" "${python_url}"
    curl -fL --progress-bar -o "${REQUIREMENTS_FILE}" "${requirements_url}"
}

find_python_command() {
    local candidates=("python3" "python")
    local candidate
    for candidate in "${candidates[@]}"; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done

    return 1
}

can_reach_url() {
    local url="$1"
    curl -fsSI --connect-timeout 5 --max-time 10 "${url}" >/dev/null 2>&1
}

pick_pip_indexes() {
    if [ -n "${PIP_INDEX_URL:-}" ]; then
        printf '%s\n' "${PIP_INDEX_URL}"
        return
    fi

    local index
    for index in "${DEFAULT_PIP_INDEXES[@]}"; do
        printf '%s\n' "${index}"
    done
}

run_pip_with_fallback() {
    local pip_bin="$1"
    shift

    local index_url
    local attempted=0
    while IFS= read -r index_url; do
        [ -n "${index_url}" ] || continue
        attempted=1

        if ! can_reach_url "${index_url}"; then
            log "WARN" "pip source unreachable, skipping: ${index_url}"
            continue
        fi

        log "INFO" "Trying pip source: ${index_url}"
        if "${pip_bin}" "$@" -i "${index_url}"; then
            SELECTED_PIP_INDEX="${index_url}"
            return 0
        fi

        log "WARN" "pip command failed with source: ${index_url}"
    done < <(pick_pip_indexes)

    if [ "${attempted}" -eq 0 ]; then
        log "ERROR" "No pip source candidates were available."
    else
        log "ERROR" "Failed to install dependencies from all configured pip sources."
    fi
    return 1
}

build_exec_start() {
    local args=(
        "${VENV_DIR}/bin/python"
        "${APP_ENTRY}"
        "--http-server" "${HTTP_SERVER}"
        "--token" "${TOKEN}"
        "--log-level" "${LOG_LEVEL}"
    )

    if [ "${DISABLE_WEB_SSH}" = "true" ]; then
        args+=("--disable-web-ssh")
    fi

    if [ -n "${INCLUDE_NICS}" ]; then
        args+=("--include-nics" "${INCLUDE_NICS}")
    fi

    local rendered=""
    local arg
    for arg in "${args[@]}"; do
        rendered+="$(printf '%q' "${arg}") "
    done

    printf '%s\n' "${rendered% }"
}

install_app() {
    local python_cmd="$1"

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "INFO" "Stopping existing service"
        systemctl stop "${SERVICE_NAME}"
    fi

    log "INFO" "Preparing installation directory ${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}"
    rm -rf "${INSTALL_DIR}/py" "${REQUIREMENTS_FILE}"
    download_source_files

    log "INFO" "Creating virtual environment"
    rm -rf "${VENV_DIR}"
    "${python_cmd}" -m venv "${VENV_DIR}"

    log "INFO" "Installing Python dependencies with automatic pip source fallback"
    run_pip_with_fallback "${VENV_DIR}/bin/pip" install --upgrade pip
    run_pip_with_fallback "${VENV_DIR}/bin/pip" install -r "${REQUIREMENTS_FILE}"
    log "INFO" "Selected pip source: ${SELECTED_PIP_INDEX}"
}

write_service() {
    local exec_start
    exec_start=$(build_exec_start)

    log "INFO" "Writing systemd service to ${SERVICE_FILE}"
    cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Komari Agent Lite
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${exec_start}
WorkingDirectory=${INSTALL_DIR}
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
EOF
}

check_environment() {
    if [ "$(id -u)" -ne 0 ]; then
        log "ERROR" "This script must be run as root. Please use sudo."
        exit 1
    fi

    for cmd in curl systemctl mktemp rm mkdir; do
        if ! command -v "${cmd}" >/dev/null 2>&1; then
            log "ERROR" "Required command '${cmd}' is not installed."
            exit 1
        fi
    done

    if ! find_python_command >/dev/null; then
        log "ERROR" "Python 3 is required but was not found in PATH."
        exit 1
    fi
}

main() {
    parse_args "$@"
    check_environment
    TMP_DIR=$(mktemp -d)

    log "INFO" "Starting Komari Agent Lite installation"
    if [ -n "${INSTALL_GHPROXY}" ]; then
        log "INFO" "Using GitHub proxy: ${INSTALL_GHPROXY}"
    fi
    if [ -n "${INCLUDE_NICS}" ]; then
        log "INFO" "Restricting network statistics to NICs: ${INCLUDE_NICS}"
    fi

    local python_cmd
    python_cmd=$(find_python_command)
    log "INFO" "Using Python command: ${python_cmd}"

    install_app "${python_cmd}"
    write_service

    log "INFO" "Reloading systemd daemon"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}" >/dev/null
    systemctl restart "${SERVICE_NAME}"

    log "SUCCESS" "Installation complete"
    sleep 2
    systemctl status --no-pager "${SERVICE_NAME}"
}

main "$@"
