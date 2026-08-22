#!/usr/bin/env bash

# Best-effort unit repair helper.
# Copies updated service files from the project tree into /etc/systemd/system
# and reloads systemd so the new unit definitions are visible.
# This script must never block boot, so it logs and continues on errors.

PROJECT_ROOT="/home/pi/PyRpiCamController"
TARGET_DIR="/etc/systemd/system"
LOG_DIR="/home/pi/shared/logs"
LOG_FILE="$LOG_DIR/camcontroller_unit_repair.log"
SERVICE_FILES=(
    "camcontroller.service"
    "camcontroller-web.service"
    "camcontroller-update.service"
)

mkdir -p "$LOG_DIR" 2>/dev/null || true

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log "Starting unit repair helper"

if [[ ! -d "$PROJECT_ROOT/Services" ]]; then
    log "Project Services directory not found: $PROJECT_ROOT/Services"
    exit 0
fi

changed=0
for unit in "${SERVICE_FILES[@]}"; do
    source_file="$PROJECT_ROOT/Services/$unit"
    target_file="$TARGET_DIR/$unit"

    if [[ ! -f "$source_file" ]]; then
        log "Skipping missing source unit: $source_file"
        continue
    fi

    if [[ -f "$target_file" ]] && cmp -s "$source_file" "$target_file"; then
        log "Unit unchanged: $unit"
        continue
    fi

    if install -m 644 "$source_file" "$target_file"; then
        changed=1
        log "Synced unit: $unit"
    else
        log "WARNING: Failed to sync unit: $unit"
    fi
done

if [[ "$changed" -eq 1 ]]; then
    if systemctl daemon-reload; then
        log "systemctl daemon-reload completed"
    else
        log "WARNING: systemctl daemon-reload failed"
    fi
else
    log "No unit changes detected"
fi

log "Unit repair helper complete"
exit 0
