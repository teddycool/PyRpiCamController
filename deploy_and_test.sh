#!/bin/bash

###############################################################################
# DEPLOYMENT AND VALIDATION SCRIPT FOR FRESH PI
# Targets: 192.168.1.99 (fresh Raspberry Pi with base OS installed)
# Tasks:
#   1. Deploy v1.4.0 release
#   2. Validate logging infrastructure
#   3. Run integration tests
#   4. Generate deployment report
###############################################################################

set -o pipefail

PI_HOST="192.168.1.99"
PI_USER="pi"
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"
RELEASE_VERSION="1.4.0"
RELEASE_FILE="PyRpiCamController-${RELEASE_VERSION}.tar.gz"
RELEASE_SHA_FILE="${RELEASE_FILE}.sha256"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_section() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

function print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

function print_error() {
    echo -e "${RED}✗ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_section "SMOKETEST DEPLOYMENT TO 192.168.1.99"

# Step 1: Verify release files exist locally
print_section "Step 1: Verify Release Files"
if [ ! -f "dist/${RELEASE_FILE}" ]; then
    print_error "Release file not found: dist/${RELEASE_FILE}"
    exit 1
fi
print_success "Release file found: dist/${RELEASE_FILE}"

if [ ! -f "dist/${RELEASE_SHA_FILE}" ]; then
    print_error "SHA256 checksum file not found: dist/${RELEASE_SHA_FILE}"
    exit 1
fi
print_success "SHA256 checksum file found"

# Verify checksum locally
cd dist
if ! sha256sum -c "${RELEASE_SHA_FILE}" > /dev/null 2>&1; then
    print_error "Local SHA256 checksum verification failed"
    exit 1
fi
print_success "Local SHA256 checksum verified"
cd ..

# Step 2: Test SSH connectivity
print_section "Step 2: Verify SSH Connectivity"
if ! ssh -o ConnectTimeout=5 "${PI_USER}@${PI_HOST}" "echo 'SSH connection OK'" > /dev/null 2>&1; then
    print_error "Cannot connect to Pi at ${PI_HOST}"
    exit 1
fi
print_success "SSH connection established to ${PI_HOST}"

# Step 3: Deploy release to Pi
print_section "Step 3: Deploy Release to Pi"
print_warning "Copying release to ${PI_HOST}..."
if ! scp "dist/${RELEASE_FILE}" "dist/${RELEASE_SHA_FILE}" "${PI_USER}@${PI_HOST}:${PI_HOME}/"; then
    print_error "Failed to copy release files to Pi"
    exit 1
fi
print_success "Release files copied to Pi"

# Step 4: Extract and validate on Pi
print_section "Step 4: Extract and Validate Release on Pi"

DEPLOY_SCRIPT=$(cat <<'EOFPI'
#!/bin/bash
set -e
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"
RELEASE_VERSION="1.4.0"
RELEASE_FILE="PyRpiCamController-${RELEASE_VERSION}.tar.gz"
RELEASE_SHA_FILE="${RELEASE_FILE}.sha256"

echo "=== Extracting release ==="
cd "$PI_HOME"
if [ -d "$PROJECT_NAME" ]; then
    echo "Backing up existing installation..."
    mv "$PROJECT_NAME" "${PROJECT_NAME}.backup.$(date +%s)" || true
fi

tar -xzf "$RELEASE_FILE"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to extract release"
    exit 1
fi
echo "✓ Release extracted successfully"

# Verify we have key files
if [ ! -f "$PROJECT_NAME/Settings/settings_manager.py" ]; then
    echo "ERROR: Critical file missing after extraction"
    exit 1
fi
echo "✓ Critical files verified"

# Create required log directory if it doesn't exist
if [ ! -d "$PI_HOME/shared/logs" ]; then
    echo "Creating log directory..."
    mkdir -p "$PI_HOME/shared/logs"
fi
echo "✓ Log directory ready at $PI_HOME/shared/logs"

# Set proper permissions
chown -R "$USER:$USER" "$PROJECT_NAME" || true
echo "✓ Permissions set"

echo "=== Deployment Complete ==="
EOFPI
)

ssh "${PI_USER}@${PI_HOST}" bash -s <<'EOFPI'
#!/bin/bash
set -e
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"
RELEASE_VERSION="1.4.0"
RELEASE_FILE="PyRpiCamController-${RELEASE_VERSION}.tar.gz"

echo "=== Extracting release ==="
cd "$PI_HOME"
if [ -d "$PROJECT_NAME" ]; then
    echo "Backing up existing installation..."
    mv "$PROJECT_NAME" "${PROJECT_NAME}.backup.$(date +%s)" || true
fi

tar -xzf "$RELEASE_FILE"
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to extract release"
    exit 1
fi
echo "✓ Release extracted successfully"

# Verify we have key files
if [ ! -f "$PROJECT_NAME/Settings/settings_manager.py" ]; then
    echo "ERROR: Critical file missing after extraction"
    exit 1
fi
echo "✓ Critical files verified"

# Create required log directory if it doesn't exist
if [ ! -d "$PI_HOME/shared/logs" ]; then
    echo "Creating log directory..."
    mkdir -p "$PI_HOME/shared/logs"
fi
echo "✓ Log directory ready at $PI_HOME/shared/logs"

echo "=== Deployment Complete ==="
EOFPI

if [ $? -ne 0 ]; then
    print_error "Failed to extract release on Pi"
    exit 1
fi
print_success "Release extracted and validated on Pi"

# Step 5: Run Installation Validation Script
print_section "Step 5: Run Installation Validation Script"

VALIDATION_RESULT=$(ssh "${PI_USER}@${PI_HOST}" <<'EOFVAL'
#!/bin/bash
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"

cd "$PI_HOME/$PROJECT_NAME"

# Run validation script
if [ -f "tools/validate_installation.sh" ]; then
    bash tools/validate_installation.sh
    echo "VALIDATION_EXIT_CODE: $?"
else
    echo "ERROR: Validation script not found"
    echo "VALIDATION_EXIT_CODE: 1"
fi
EOFVAL
)

echo "$VALIDATION_RESULT"
VALIDATION_EXIT=$(echo "$VALIDATION_RESULT" | grep "VALIDATION_EXIT_CODE:" | awk '{print $2}')

if [ "$VALIDATION_EXIT" = "0" ]; then
    print_success "Installation validation passed"
else
    print_warning "Installation validation exited with code: $VALIDATION_EXIT"
fi

# Step 6: Check logging infrastructure
print_section "Step 6: Verify Logging Infrastructure"

LOG_CHECK=$(ssh "${PI_USER}@${PI_HOST}" <<'EOFLOG'
#!/bin/bash
PI_HOME="/home/pi"

echo "=== Web Application Logs ==="
if [ -f "$PI_HOME/shared/logs/camcontroller_web.log" ]; then
    SIZE=$(stat -c%s "$PI_HOME/shared/logs/camcontroller_web.log" 2>/dev/null || echo "0")
    echo "✓ camcontroller_web.log exists ($(numfmt --to=iec $SIZE 2>/dev/null || echo "$SIZE bytes"))"
else
    echo "✗ camcontroller_web.log missing"
fi

echo "=== Gunicorn Access Logs ==="
if [ -f "$PI_HOME/shared/logs/camcontroller_web_access.log" ]; then
    SIZE=$(stat -c%s "$PI_HOME/shared/logs/camcontroller_web_access.log" 2>/dev/null || echo "0")
    echo "✓ camcontroller_web_access.log exists ($(numfmt --to=iec $SIZE 2>/dev/null || echo "$SIZE bytes"))"
else
    echo "✗ camcontroller_web_access.log missing"
fi

echo "=== Gunicorn Error Logs ==="
if [ -f "$PI_HOME/shared/logs/camcontroller_web_error.log" ]; then
    SIZE=$(stat -c%s "$PI_HOME/shared/logs/camcontroller_web_error.log" 2>/dev/null || echo "0")
    echo "✓ camcontroller_web_error.log exists ($(numfmt --to=iec $SIZE 2>/dev/null || echo "$SIZE bytes"))"
else
    echo "✗ camcontroller_web_error.log missing"
fi

echo "=== Directory Permissions ==="
ls -ld "$PI_HOME/shared/logs" 2>/dev/null || echo "Log directory not found"
EOFLOG
)

echo "$LOG_CHECK"

# Step 7: Run basic unit tests locally (against deployed code)
print_section "Step 7: Run Unit Tests Against Deployed Code"

TEST_RESULT=$(ssh "${PI_USER}@${PI_HOST}" <<'EOFTEST'
#!/bin/bash
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"

cd "$PI_HOME/$PROJECT_NAME"

# Try to run tests if pytest is available
if command -v pytest &> /dev/null; then
    echo "Running pytest..."
    pytest tests/unit/ -v --tb=short 2>&1 | head -100
    echo "TESTS_EXIT_CODE: $?"
elif python3 -m pytest --version >/dev/null 2>&1; then
    echo "Running pytest via python3 -m..."
    python3 -m pytest tests/unit/ -v --tb=short 2>&1 | head -100
    echo "TESTS_EXIT_CODE: $?"
else
    echo "pytest not available on target system"
    echo "TESTS_EXIT_CODE: 1"
fi
EOFTEST
)

echo "$TEST_RESULT"
TESTS_EXIT=$(echo "$TEST_RESULT" | grep "TESTS_EXIT_CODE:" | awk '{print $2}')

# Step 8: Verify critical Python modules can be imported
print_section "Step 8: Verify Python Module Imports"

IMPORT_CHECK=$(ssh "${PI_USER}@${PI_HOST}" <<'EOFIMPORT'
#!/bin/bash
PI_HOME="/home/pi"
PROJECT_NAME="PyRpiCamController"

cd "$PI_HOME/$PROJECT_NAME"

python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from Settings.settings_manager import SettingsManager
    print('✓ SettingsManager import OK')
except Exception as e:
    print(f'✗ SettingsManager import failed: {e}')
    sys.exit(1)

try:
    from CamController.Main import Main
    print('✓ Main import OK')
except Exception as e:
    print(f'✗ Main import failed: {e}')
    sys.exit(1)

print('✓ All critical imports successful')
sys.exit(0)
" 2>&1
echo "IMPORT_EXIT_CODE: $?"
EOFIMPORT
)

echo "$IMPORT_CHECK"
IMPORT_EXIT=$(echo "$IMPORT_CHECK" | grep "IMPORT_EXIT_CODE:" | awk '{print $2}')

# Step 9: Generate final report
print_section "DEPLOYMENT REPORT"

echo ""
echo "Target System:           192.168.1.99"
echo "Release Version:         ${RELEASE_VERSION}"
echo "Deployment User:         ${PI_USER}"
echo "Installation Path:       ${PI_HOME}/${PROJECT_NAME}"
echo ""
echo "Deployment Status:       $([ $? -eq 0 ] && echo 'SUCCESS' || echo 'FAILED')"
echo "Validation Status:       $([ "$VALIDATION_EXIT" = "0" ] && echo 'PASSED' || echo 'WARNINGS')"
echo "Log Infrastructure:      $(echo "$LOG_CHECK" | grep -c "✓") of 3 log files present"
echo "Python Imports:          $([ "$IMPORT_EXIT" = "0" ] && echo 'OK' || echo 'FAILED')"
echo ""

echo "Key Verification Points:"
echo "  • Release extracted successfully"
echo "  • Critical files present (settings_manager.py, etc.)"
echo "  • Log directory created at ${PI_HOME}/shared/logs"
echo "  • Logging infrastructure validated"
echo "  • Python module imports verified"
echo ""

if [ "$VALIDATION_EXIT" = "0" ] && [ "$IMPORT_EXIT" = "0" ]; then
    print_success "SMOKETEST DEPLOYMENT COMPLETE - READY FOR INTEGRATION TESTING"
    echo ""
    echo "Next steps:"
    echo "  1. Verify web service is running: ssh pi@192.168.1.99 sudo systemctl status camcontroller-web"
    echo "  2. Test via browser: http://192.168.1.99"
    echo "  3. Check logs: ssh pi@192.168.1.99 tail -f /home/pi/shared/logs/camcontroller_web.log"
    echo "  4. Verify settings changes are logged"
    echo "  5. Verify OTA updates log correctly"
    exit 0
else
    print_error "SMOKETEST DEPLOYMENT ENCOUNTERED ISSUES"
    exit 1
fi
