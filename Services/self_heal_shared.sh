#!/usr/bin/env bash

SHARED_DIR="/home/pi/shared"

mkdir -p "$SHARED_DIR" "$SHARED_DIR/images" "$SHARED_DIR/logs" 2>/dev/null || true
chown -R pi:pi "$SHARED_DIR" 2>/dev/null || true
find "$SHARED_DIR" -type d -exec chmod 777 {} + 2>/dev/null || true
find "$SHARED_DIR" -type f -exec chmod 666 {} + 2>/dev/null || true
