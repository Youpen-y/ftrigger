#!/bin/bash

#############################################################################
# ftrigger systemd Service Installation Script
#
# This script automatically detects the ftrigger installation location and
# installs a configured systemd user service.
#
# Usage:
#   ./install-service.sh [--config PATH] [--multi-instance]
#
# Options:
#   --config PATH    Custom config file path (default: ~/.config/ftrigger/config.yaml)
#   --multi-instance Install template service for multiple instances
#   --uninstall      Remove installed service
#   --help           Show this help message
#############################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
CONFIG_PATH=""
MULTI_INSTANCE=false
UNINSTALL=false
SERVICE_MODE=""  # "user" or "system"
SELECTED_MODE=""  # Global to store selected mode

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_PATH="$2"
            shift 2
            ;;
        --multi-instance)
            MULTI_INSTANCE=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        --mode)
            SERVICE_MODE="$2"
            shift 2
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --config PATH     Custom config file path (for user mode: ~/.config/ftrigger/config.yaml)
  --multi-instance  Install template service for multiple instances
  --mode MODE        Service mode: "user" or "system" (default: interactive prompt)
  --uninstall       Remove installed service
  --help, -h        Show this help message

Examples:
  # Install single instance service (interactive mode selection)
  $0

  # Install as user service
  $0 --mode user

  # Install as system service
  $0 --mode system

  # Install with custom config (user mode only)
  $0 --config /path/to/custom.yaml

  # Install multi-instance template
  $0 --multi-instance

  # Uninstall service
  $0 --uninstall
EOF
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Find ftrigger executable
find_ftrigger_executable() {
    local exec_path=""

    # Try to find ftrigger in PATH
    if command -v ftrigger &> /dev/null; then
        exec_path=$(command -v ftrigger)
        log_info "Found ftrigger in PATH: $exec_path" >&2
    elif [ -f "./venv/bin/ftrigger" ]; then
        exec_path="$(pwd)/venv/bin/ftrigger"
        log_info "Found ftrigger in local venv: $exec_path" >&2
    elif [ -f "./.venv/bin/ftrigger" ]; then
        exec_path="$(pwd)/.venv/bin/ftrigger"
        log_info "Found ftrigger in .venv: $exec_path" >&2
    elif [ -f "$HOME/.local/bin/ftrigger" ]; then
        exec_path="$HOME/.local/bin/ftrigger"
        log_info "Found ftrigger in ~/.local/bin: $exec_path" >&2
    else
        log_error "Cannot find ftrigger executable" >&2
        echo "" >&2
        echo "Please ensure ftrigger is installed:" >&2
        echo "  pip install ftrigger" >&2
        echo "  or" >&2
        echo "  pip install --user ftrigger" >&2
        exit 1
    fi

    echo "$exec_path"
}

# Get default config path based on service mode
get_default_config_path() {
    local mode="$1"  # "user" or "system"

    if [ -n "$CONFIG_PATH" ]; then
        echo "$CONFIG_PATH"
    elif [ "$mode" = "system" ]; then
        echo "/etc/ftrigger/config.yaml"
    else
        echo "$HOME/.config/ftrigger/config.yaml"
    fi
}

# Check if config exists
check_config() {
    local config_path="$1"

    if [ ! -f "$config_path" ]; then
        log_warning "Config file not found: $config_path"
        echo ""
        echo "Creating example config..."
        mkdir -p "$(dirname "$config_path")"
        cat > "$config_path" << EOF
# ftrigger configuration
log_level: INFO

watches:
  - path: /path/to/your/project
    events: ["created", "modified"]
    prompt: "Review the changed file {file} and suggest improvements."
    recursive: true
    permission_mode: acceptEdits
    extensions: [".py", ".js", ".ts", ".yaml", ".md"]
EOF
        log_success "Created example config: $config_path"
        log_warning "Please edit the config file before starting the service"
    fi
}

# Uninstall service
uninstall_service() {
    local mode="$1"  # "user" or "system"

    if [ "$mode" = "system" ]; then
        local service_dir="/etc/systemd/system"
        local systemctl_cmd="systemctl"
    else
        local service_dir="$HOME/.config/systemd/user"
        local systemctl_cmd="systemctl --user"
    fi

    local service_name="ftrigger"

    log_info "Uninstalling ftrigger service (${mode} mode)..."

    # Stop and disable if running
    if $systemctl_cmd is-active --quiet "${service_name}.service" 2>/dev/null; then
        log_info "Stopping service..."
        $systemctl_cmd stop "${service_name}.service" || true
    fi

    if $systemctl_cmd is-enabled --quiet "${service_name}.service" 2>/dev/null; then
        log_info "Disabling service..."
        $systemctl_cmd disable "${service_name}.service" || true
    fi

    # Remove service files
    if [ -f "${service_dir}/${service_name}.service" ]; then
        sudo rm -f "${service_dir}/${service_name}.service"
        log_success "Removed ${service_dir}/${service_name}.service"
    fi

    if [ -f "${service_dir}/${service_name}@.service" ]; then
        sudo rm -f "${service_dir}/${service_name}@.service"
        log_success "Removed ${service_dir}/${service_name}@.service"
    fi

    # Reload systemd
    $systemctl_cmd daemon-reload
    log_success "Uninstall complete"
}

# Install single instance service
install_single_instance() {
    local ftrigger_exec="$1"
    local config_path="$2"
    local mode="$3"  # "user" or "system"

    if [ "$mode" = "system" ]; then
        local service_dir="/etc/systemd/system"
        local systemctl_cmd="systemctl"
    else
        local service_dir="$HOME/.config/systemd/user"
        local systemctl_cmd="systemctl --user"
    fi

    log_info "Installing single instance service (${mode} mode)..."

    # Create service directory
    if [ "$mode" = "system" ]; then
        sudo mkdir -p "$service_dir"
    else
        mkdir -p "$service_dir"
    fi

    # Get absolute path of config
    config_path="$(realpath "$config_path" 2>/dev/null || echo "$config_path")"

    # Generate service file
    local service_content="[Unit]
Description=File Trigger - Monitor file changes and trigger Claude CLI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${ftrigger_exec} --config ${config_path}
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ftrigger

[Install]
WantedBy=default.target
"

    if [ "$mode" = "system" ]; then
        echo "$service_content" | sudo tee "${service_dir}/ftrigger.service" > /dev/null
    else
        echo "$service_content" > "${service_dir}/ftrigger.service"
    fi

    log_success "Created ${service_dir}/ftrigger.service"
}

# Install multi-instance template service
install_multi_instance() {
    local ftrigger_exec="$1"
    local service_dir="$HOME/.config/systemd/user"

    log_info "Installing multi-instance template service..."

    # Create service directory
    mkdir -p "$service_dir"

    # Get current username
    local user_name="${USER:-$(whoami)}"

    # Generate template service file
    cat > "${service_dir}/ftrigger@.service" << EOF
[Unit]
Description=File Trigger - Monitor file changes and trigger Claude CLI (%i)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=${ftrigger_exec} --config ${HOME}/.config/ftrigger/%i.yaml
ExecReload=/bin/kill -HUP \$MAINPID
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ftrigger-%i

[Install]
WantedBy=default.target
EOF

    log_success "Created ${service_dir}/ftrigger@.service"

    # Create example configs
    log_info "Creating example configs..."

    cat > "$HOME/.config/ftrigger/project1.yaml" << EOF
# Example config for instance 1
log_level: INFO
watches:
  - path: /path/to/python/project
    events: ["created", "modified"]
    prompt: "Review {file}"
    permission_mode: acceptEdits
    extensions: [".py"]
EOF

    cat > "$HOME/.config/ftrigger/project2.yaml" << EOF
# Example config for instance 2
log_level: DEBUG
watches:
  - path: /path/to/javascript/project
    events: ["created", "modified"]
    prompt: "Analyze {file}"
    permission_mode: acceptEdits
    extensions: [".js", ".ts"]
EOF

    log_success "Created example configs:"
    echo "  - $HOME/.config/ftrigger/project1.yaml"
    echo "  - $HOME/.config/ftrigger/project2.yaml"
}

# Enable and start service
enable_and_start() {
    local service_name="$1"
    local mode="$2"  # "user" or "system"

    if [ "$mode" = "system" ]; then
        local systemctl_cmd="systemctl"
    else
        local systemctl_cmd="systemctl --user"
    fi

    log_info "Reloading systemd daemon..."
    $systemctl_cmd daemon-reload

    log_info "Enabling service..."
    $systemctl_cmd enable "${service_name}"

    log_info "Starting service..."
    $systemctl_cmd start "${service_name}"

    log_success "Service installed and started!"
    echo ""
    echo "Management commands:"
    echo "  $systemctl_cmd status ${service_name}"
    echo "  $systemctl_cmd restart ${service_name}"
    echo "  $systemctl_cmd stop ${service_name}"
    if [ "$mode" = "system" ]; then
        echo "  journalctl -u ${service_name} -f"
    else
        echo "  journalctl --user -u ${service_name} -f"
    fi
}

# Prompt for service mode
prompt_service_mode() {
    if [ -n "$SERVICE_MODE" ]; then
        SELECTED_MODE="$SERVICE_MODE"
        return
    fi

    echo ""
    log_info "Select installation mode:"
    echo "  [0] User service  - Install for current user (~/.config/ftrigger/config.yaml)"
    echo "  [1] System service- Install system-wide (/etc/ftrigger/config.yaml)"
    echo ""
    read -p "Enter choice [0/1]: " choice

    case $choice in
        0|"user"|"u")
            SELECTED_MODE="user"
            log_success "Selected: User service"
            ;;
        1|"system"|"s")
            SELECTED_MODE="system"
            log_success "Selected: System service"
            ;;
        *)
            log_error "Invalid choice: $choice (enter 0 or 1)"
            exit 1
            ;;
    esac
}

# Main execution
main() {
    echo ""
    echo "=========================================="
    echo "  ftrigger systemd Service Installer"
    echo "=========================================="
    echo ""

    # Handle uninstall
    if [ "$UNINSTALL" = true ]; then
        prompt_service_mode
        uninstall_service "$SELECTED_MODE"
        exit 0
    fi

    # Find ftrigger executable
    local ftrigger_exec
    ftrigger_exec=$(find_ftrigger_executable)

    # Determine service mode (uses global SELECTED_MODE)
    prompt_service_mode
    local mode="$SELECTED_MODE"

    # Get config path based on mode
    local config_path
    config_path=$(get_default_config_path "$mode")

    echo ""
    log_info "Configuration:"
    echo "  ftrigger: ${ftrigger_exec}"
    echo "  mode:     ${mode}"
    echo "  config:   ${config_path}"
    echo ""

    # Check if config exists
    check_config "$config_path"

    # Install service
    if [ "$MULTI_INSTANCE" = true ]; then
        install_multi_instance "$ftrigger_exec"

        echo ""
        log_info "To start instances, use:"
        if [ "$mode" = "system" ]; then
            echo "  systemctl start ftrigger@project1"
            echo "  systemctl start ftrigger@project2"
        else
            echo "  systemctl --user start ftrigger@project1"
            echo "  systemctl --user start ftrigger@project2"
        fi
    else
        install_single_instance "$ftrigger_exec" "$config_path" "$mode"
        enable_and_start "ftrigger" "$mode"
    fi

    echo ""
    log_success "Installation complete!"
    echo ""
}

# Run main
main "$@"
