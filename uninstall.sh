#!/bin/bash

set -euo pipefail

readonly INSTALL_DIR="/opt/komari-lite"
readonly SERVICE_NAME="komari-agent-lite.service"
readonly SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

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
Komari Agent Lite uninstaller

Usage:
  wget -qO- https://ghfast.top/raw.githubusercontent.com/AlisaCat-S/komari-agent-webhost-lite/refs/heads/main/uninstall.sh | \\
    sudo bash

  sudo bash uninstall.sh

Options:
  -h, --help                            Show this help
EOF
}

stop_service() {
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "INFO" "Stopping service ${SERVICE_NAME}"
        systemctl stop "${SERVICE_NAME}"
    else
        log "INFO" "Service ${SERVICE_NAME} is not running"
    fi
}

disable_service() {
    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        log "INFO" "Disabling service ${SERVICE_NAME}"
        systemctl disable "${SERVICE_NAME}" >/dev/null
    else
        log "INFO" "Service ${SERVICE_NAME} is not enabled"
    fi
}

remove_service_file() {
    log "INFO" "Removing systemd unit ${SERVICE_FILE}"
    rm -f "${SERVICE_FILE}"
    systemctl daemon-reload
    systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true
}

remove_install_dir() {
    log "INFO" "Removing installation directory ${INSTALL_DIR}"
    rm -rf "${INSTALL_DIR}"
}

check_environment() {
    if [ "$(id -u)" -ne 0 ]; then
        log "ERROR" "This script must be run as root. Please use sudo."
        exit 1
    fi

    for cmd in systemctl rm; do
        if ! command -v "${cmd}" >/dev/null 2>&1; then
            log "ERROR" "Required command '${cmd}' is not installed."
            exit 1
        fi
    done
}

main() {
    case "${1:-}" in
        -h|--help)
            usage
            exit 0
            ;;
        "")
            ;;
        *)
            log "ERROR" "Unknown argument: $1"
            usage
            exit 1
            ;;
    esac

    check_environment

    if [ ! -d "${INSTALL_DIR}" ] && [ ! -f "${SERVICE_FILE}" ] \
        && ! systemctl is-active --quiet "${SERVICE_NAME}" 2>/dev/null; then
        log "WARN" "Komari Agent Lite does not appear to be installed. Nothing to uninstall."
        exit 0
    fi

    log "INFO" "Starting Komari Agent Lite uninstallation"

    stop_service
    disable_service
    remove_service_file
    remove_install_dir

    log "SUCCESS" "Komari Agent Lite has been uninstalled"
}

main "$@"
