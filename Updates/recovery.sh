#!/bin/bash
# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

# Emergency Recovery Script for PyRpiCamController OTA Updates
# This script can be used when OTA updates fail and manual recovery is needed

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="/home/pi/PyRpiCamController"
BACKUP_DIR="/home/pi/Updates/backup"
LOG_FILE="/home/pi/shared/logs/camcontroller_update_recovery.log"
SERVICE_NAME="camcontroller.service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}ERROR: $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}SUCCESS: $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Run as pi user with sudo when needed."
        exit 1
    fi
}

# Stop the camera service safely
stop_service() {
    log "Stopping camera service: $SERVICE_NAME"
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        sudo systemctl stop "$SERVICE_NAME"
        sleep 5
        
        if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
            warning "Service still running, force stopping..."
            sudo systemctl kill "$SERVICE_NAME"
            sleep 5
        fi
        success "Service stopped"
    else
        log "Service is already stopped"
    fi
}

# Start the camera service
start_service() {
    log "Starting camera service: $SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    sleep 10
    
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Service started successfully"
    else
        error "Service failed to start"
        sudo systemctl status "$SERVICE_NAME"
        return 1
    fi
}

# List available backups
list_backups() {
    log "Available backups in $BACKUP_DIR:"
    if [ -d "$BACKUP_DIR" ]; then
        ls -la "$BACKUP_DIR"/*.tar.gz 2>/dev/null || log "No backup files found"
    else
        error "Backup directory does not exist: $BACKUP_DIR"
    fi
}

# Restore from specific backup
restore_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring from backup: $backup_file"
    
    # Stop service
    stop_service
    
    # Create emergency backup of current state
    emergency_backup_dir="/home/pi/ota/emergency_$(date +%Y%m%d_%H%M%S)"
    if [ -d "$PROJECT_ROOT" ]; then
        log "Creating emergency backup of current state: $emergency_backup_dir"
        mkdir -p "$emergency_backup_dir"
        cp -r "$PROJECT_ROOT" "$emergency_backup_dir/"
    fi
    
    # Remove current installation
    if [ -d "$PROJECT_ROOT" ]; then
        log "Removing current installation"
        rm -rf "$PROJECT_ROOT"
    fi
    
    # Extract backup
    log "Extracting backup to $(dirname "$PROJECT_ROOT")"
    cd "$(dirname "$PROJECT_ROOT")"
    tar -xzf "$backup_file"
    
    # Set permissions
    log "Setting correct permissions"
    sudo chown -R pi:pi "$PROJECT_ROOT"
    sudo chmod +x "$PROJECT_ROOT/CamController/Main.py" 2>/dev/null || true
    
    # Start service
    start_service
    
    success "Backup restored successfully"
}

# Restore from latest backup
restore_latest() {
    log "Finding latest backup..."
    
    if [ ! -d "$BACKUP_DIR" ]; then
        error "Backup directory does not exist: $BACKUP_DIR"
        return 1
    fi
    
    # Find the most recent backup
    latest_backup=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -n 1)
    
    if [ -z "$latest_backup" ]; then
        error "No backup files found in $BACKUP_DIR"
        return 1
    fi
    
    log "Latest backup found: $latest_backup"
    restore_backup "$latest_backup"
}

# Check system health
check_health() {
    log "Performing system health check..."
    
    # Check if service is running
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        success "Camera service is running"
    else
        error "Camera service is not running"
        sudo systemctl status "$SERVICE_NAME"
    fi
    
    # Check disk space
    disk_usage=$(df /home | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        warning "Disk space is low: ${disk_usage}% used"
    else
        success "Disk space OK: ${disk_usage}% used"
    fi
    
    # Check if project directory exists
    if [ -d "$PROJECT_ROOT" ]; then
        success "Project directory exists: $PROJECT_ROOT"
    else
        error "Project directory missing: $PROJECT_ROOT"
    fi
    
    # Check key files
    key_files=(
        "$PROJECT_ROOT/CamController/Main.py"
        "$PROJECT_ROOT/Settings/settings_manager.py"
        "$PROJECT_ROOT/Settings/settings_schema.json"
    )
    
    for file in "${key_files[@]}"; do
        if [ -f "$file" ]; then
            success "Key file exists: $file"
        else
            error "Key file missing: $file"
        fi
    done
}

# Clean up failed installations
cleanup() {
    log "Cleaning up temporary files and failed installations..."
    
    # Clean OTA temp directory
    if [ -d "/home/pi/ota/temp" ]; then
        rm -rf /home/pi/ota/temp/*
        success "Cleaned OTA temp directory"
    fi
    
    # Clean old emergency backups (keep last 3)
    emergency_dirs=($(ls -dt /home/pi/ota/emergency_* 2>/dev/null || true))
    if [ ${#emergency_dirs[@]} -gt 3 ]; then
        for dir in "${emergency_dirs[@]:3}"; do
            rm -rf "$dir"
            log "Removed old emergency backup: $dir"
        done
    fi
    
    success "Cleanup completed"
}

# Reset OTA system
reset_ota() {
    log "Resetting OTA system..."
    
    # Stop OTA daemon if running
    if sudo systemctl is-active --quiet "camcontroller-update.service"; then
        sudo systemctl stop "camcontroller-update.service"
        log "Stopped OTA daemon"
    fi
    
    # Clear OTA temp files
    cleanup
    
    # Reset OTA settings (disable OTA)
    if [ -f "$PROJECT_ROOT/Settings/user_settings.json" ]; then
        # This is a simple approach - in a real scenario you might want to use the settings manager
        sed -i 's/"OtaEnable": true/"OtaEnable": false/g' "$PROJECT_ROOT/Settings/user_settings.json"
        log "Disabled OTA in settings"
    fi
    
    success "OTA system reset completed"
}

# Show usage
show_usage() {
    echo "PyRpiCamController Emergency Recovery Script"
    echo ""
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  list              List available backups"
    echo "  restore-latest    Restore from the most recent backup"
    echo "  restore FILE      Restore from specific backup file"
    echo "  health            Check system health"
    echo "  cleanup           Clean up temporary files"
    echo "  reset-ota         Reset OTA system and disable OTA"
    echo "  stop-service      Stop camera service"
    echo "  start-service     Start camera service"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 restore-latest"
    echo "  $0 restore /home/pi/ota/backups/backup_1.0.0_20231114_120000.tar.gz"
    echo "  $0 health"
}

# Main script logic
main() {
    # Ensure log directory exists
    mkdir -p "$(dirname "$LOG_FILE")"
    
    log "=== PyRpiCamController Emergency Recovery Started ==="
    log "Command: $0 $*"
    
    check_permissions
    
    case "${1:-}" in
        "list")
            list_backups
            ;;
        "restore-latest")
            restore_latest
            ;;
        "restore")
            if [ -z "$2" ]; then
                error "Please specify backup file to restore"
                show_usage
                exit 1
            fi
            restore_backup "$2"
            ;;
        "health")
            check_health
            ;;
        "cleanup")
            cleanup
            ;;
        "reset-ota")
            reset_ota
            ;;
        "stop-service")
            stop_service
            ;;
        "start-service")
            start_service
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        "")
            error "No command specified"
            show_usage
            exit 1
            ;;
        *)
            error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
    
    log "=== Recovery operation completed ==="
}

# Run main function
main "$@"