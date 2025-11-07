#!/bin/bash
# use ./install_komari_agent.sh "你的HTTP服务器地址" "你的Token"
# ==============================================================================
# Komari Agent Lite - Installation Script
#
# Description: This script downloads the latest version of Komari Agent Lite,
#              installs it as a systemd service, and starts it.
# Author: Senior Software Engineer
# Usage: sudo ./install_komari_agent.sh <http_server_address> <token>
# Example: sudo ./install_komari_agent.sh "http://192.168.1.100:8080" "your-secret-token"
# ==============================================================================

# --- Script Configuration ---
set -euo pipefail # -e: exit on error, -u: exit on unset variable, -o pipefail: fail pipeline on first error

# --- Variable Definitions ---
readonly REPO="AlisaCat-S/komari-agent-webhost-lite"
readonly INSTALL_DIR="/opt/komari-lite"
readonly EXECUTABLE_NAME="komari-agent-linux-x64"
readonly SERVICE_NAME="komari-agent-lite.service"
readonly SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"
readonly TMP_DIR=$(mktemp -d) # Create a secure temporary directory

# --- Function Definitions ---

# Function to print colored messages
log() {
    local type="$1"
    local msg="$2"
    local color_red='\033[0;31m'
    local color_green='\033[0;32m'
    local color_yellow='\033[0;33m'
    local color_blue='\033[0;34m'
    local color_nc='\033[0m' # No Color

    case "$type" in
        "INFO") echo -e "${color_blue}INFO:${color_nc} $msg" ;;
        "SUCCESS") echo -e "${color_green}SUCCESS:${color_nc} $msg" ;;
        "WARN") echo -e "${color_yellow}WARNING:${color_nc} $msg" ;;
        "ERROR") echo -e "${color_red}ERROR:${color_nc} $msg" >&2 ;;
        *) echo "$msg" ;;
    esac
}

# Function to clean up temporary files on exit
cleanup() {
    log "INFO" "Cleaning up temporary directory: ${TMP_DIR}"
    rm -rf "${TMP_DIR}"
}
trap cleanup EXIT # Register the cleanup function to be called on script exit

# --- Pre-flight Checks ---

# 1. Check for root privileges
if [ "$(id -u)" -ne 0 ]; then
   log "ERROR" "This script must be run as root. Please use 'sudo'."
   exit 1
fi

# 2. Check for required command-line arguments
if [ "$#" -ne 2 ]; then
    log "ERROR" "Invalid arguments provided."
    echo "Usage: $0 <http_server_address> <token>"
    echo "Example: $0 \"http://192.168.1.100:8080\" \"your-secret-token\""
    exit 1
fi
readonly HTTP_SERVER=$1
readonly TOKEN=$2

# 3. Check for necessary dependencies
for cmd in curl unzip; do
    if ! command -v $cmd &> /dev/null; then
        log "ERROR" "Required command '$cmd' is not installed. Please install it first."
        exit 1
    fi
done

# --- Main Installation Logic ---

main() {
    log "INFO" "Starting Komari Agent Lite installation..."

    # Step 1: Get the latest release download URL from GitHub API
    log "INFO" "Fetching the latest release information from GitHub..."
    local api_url="https://api.github.com/repos/${REPO}/releases/latest"
    # Using grep and cut for portability, as jq might not be installed
    local download_url=$(curl -s "$api_url" | grep "browser_download_url.*linux-x64.zip" | cut -d '"' -f 4)

    if [ -z "$download_url" ]; then
        log "ERROR" "Could not find the download URL for the latest linux-x64 release. Please check the repository."
        exit 1
    fi
    log "INFO" "Latest version download URL: $download_url"

    # Step 2: Download and extract the agent
    local zip_file="${TMP_DIR}/komari-agent-linux-x64.zip"
    log "INFO" "Downloading agent to ${zip_file}..."
    curl -L --progress-bar -o "$zip_file" "$download_url"

    log "INFO" "Extracting agent in ${TMP_DIR}..."
    unzip -q "$zip_file" -d "$TMP_DIR"

    # Step 3: Stop existing service if it's running, to prevent file lock issues
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "INFO" "Stopping existing service..."
        systemctl stop "$SERVICE_NAME"
    fi
    
    # Step 4: Install the binary
    log "INFO" "Installing executable to ${INSTALL_DIR}/${EXECUTABLE_NAME}..."
    mkdir -p "$INSTALL_DIR"
    mv "${TMP_DIR}/${EXECUTABLE_NAME}" "${INSTALL_DIR}/"
    chmod +x "${INSTALL_DIR}/${EXECUTABLE_NAME}"

    # Step 5: Create the systemd service file
    log "INFO" "Creating systemd service file at ${SERVICE_FILE}..."
    cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Komari Agent Service lite
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${INSTALL_DIR}/${EXECUTABLE_NAME} --http-server "${HTTP_SERVER}" --token "${TOKEN}" --disable-web-ssh --log-level 1
WorkingDirectory=${INSTALL_DIR}
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
EOF

    # Step 6: Reload systemd, enable and start the service
    log "INFO" "Reloading systemd daemon..."
    systemctl daemon-reload

    log "INFO" "Enabling service to start on boot..."
    systemctl enable "$SERVICE_NAME"

    log "INFO" "Starting the service..."
    systemctl start "$SERVICE_NAME"

    log "SUCCESS" "Installation complete!"
    log "INFO" "Checking the status of the service:"
    # Give the service a moment to start up before checking status
    sleep 2
    systemctl status --no-pager "$SERVICE_NAME"
}

# --- Run the main function ---
main
