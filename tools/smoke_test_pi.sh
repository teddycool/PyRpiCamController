#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE_DEFAULT="${SCRIPT_DIR}/smoke_test_pi.env"

PI_HOST="${PI_HOST:-192.168.1.99}"
PI_USER="${PI_USER:-pi}"
PI_PORT="${PI_PORT:-22}"
PASSWORD_AUTH="${PASSWORD_AUTH:-0}"
PASSWORD_STORE="${PASSWORD_STORE:-0}"
SECRETS_FILE="${SECRETS_FILE:-${SECRETS_FILE_DEFAULT}}"
PI_PASSWORD="${PI_PASSWORD:-}"
PROJECT_NAME="PyRpiCamController"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage:
  tools/smoke_test_pi.sh [VERSION]

Environment overrides:
  PI_HOST (default: 192.168.1.99)
  PI_USER (default: pi)
  PI_PORT (default: 22)
  PASSWORD_AUTH (default: 0, set 1 to use standard password login)
  PASSWORD_STORE (default: 0, set 1 to use stored password from file)
  SECRETS_FILE (default: tools/smoke_test_pi.env)

Examples:
  tools/smoke_test_pi.sh 1.2.3
  PI_USER=psk PI_HOST=192.168.1.99 tools/smoke_test_pi.sh 1.2.3
  PASSWORD_AUTH=1 tools/smoke_test_pi.sh 1.2.3
  PASSWORD_STORE=1 tools/smoke_test_pi.sh 1.2.3

Stored password file format (chmod 600):
  PI_PASSWORD=your_password
EOF
  exit 0
fi

VERSION="${1:-}"
if [[ -z "${VERSION}" ]]; then
  VERSION_FILE="VERSION"
  if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "ERROR: VERSION file not found and no version argument given"
    exit 1
  fi
  VERSION="$(tr -d '[:space:]' < "${VERSION_FILE}")"
fi

TARBALL="dist/${PROJECT_NAME}-${VERSION}.tar.gz"
SHA_FILE="${TARBALL}.sha256"
RELEASE_NOTES="dist/release-notes-${VERSION}.md"
REMOTE_BASE="/home/${PI_USER}"
REMOTE_TARBALL="${REMOTE_BASE}/${PROJECT_NAME}-${VERSION}.tar.gz"
REMOTE_SHA="${REMOTE_BASE}/${PROJECT_NAME}-${VERSION}.tar.gz.sha256"
REMOTE_DIR="${REMOTE_BASE}/${PROJECT_NAME}"

for f in "${TARBALL}" "${SHA_FILE}"; do
  if [[ ! -f "${f}" ]]; then
    echo "ERROR: missing artifact ${f}"
    echo "Run: python3 build-scripts/release_manager.py release"
    exit 1
  fi
done

if ! command -v ssh >/dev/null 2>&1 || ! command -v scp >/dev/null 2>&1; then
  echo "ERROR: ssh/scp not found on local machine"
  exit 1
fi

SSH_OPTS=(-p "${PI_PORT}" -o ConnectTimeout=7)
SCP_OPTS=(-P "${PI_PORT}" -o ConnectTimeout=7)
SSH_CMD=(ssh)
SCP_CMD=(scp)
CONTROL_PATH="/tmp/smoke_test_pi_${PI_USER}_${PI_HOST}_${PI_PORT}.sock"
CONTROL_OPTS=(-o ControlMaster=auto -o ControlPersist=15m -o "ControlPath=${CONTROL_PATH}")

cleanup_mux() {
  if [[ -S "${CONTROL_PATH}" ]]; then
    "${SSH_CMD[@]}" "${SSH_OPTS[@]}" -O exit "${PI_USER}@${PI_HOST}" >/dev/null 2>&1 || true
    rm -f "${CONTROL_PATH}" >/dev/null 2>&1 || true
  fi
}

trap cleanup_mux EXIT

if [[ "${PASSWORD_STORE}" == "1" ]]; then
  if [[ -f "${SECRETS_FILE}" ]]; then
    if [[ "$(stat -c '%a' "${SECRETS_FILE}")" != "600" ]]; then
      echo "ERROR: ${SECRETS_FILE} must have permission 600"
      echo "Run: chmod 600 '${SECRETS_FILE}'"
      exit 1
    fi
    set -a
    # shellcheck disable=SC1090
    source "${SECRETS_FILE}"
    set +a
  fi

  if [[ -z "${PI_PASSWORD:-}" ]]; then
    echo "ERROR: PASSWORD_STORE=1 but PI_PASSWORD is empty."
    echo "Set PI_PASSWORD in ${SECRETS_FILE}"
    exit 1
  fi

  if ! command -v sshpass >/dev/null 2>&1; then
    echo "ERROR: PASSWORD_STORE=1 requires sshpass."
    echo "Install on Ubuntu/Debian: sudo apt-get install -y sshpass"
    exit 1
  fi

  PASSWORD_AUTH=1
  SSH_CMD=(sshpass -p "${PI_PASSWORD}" ssh)
  SCP_CMD=(sshpass -p "${PI_PASSWORD}" scp)
fi

if [[ "${PASSWORD_AUTH}" == "1" ]]; then
  AUTH_OPTS=(
    -o BatchMode=no
    -o PreferredAuthentications=password,keyboard-interactive
    -o PubkeyAuthentication=no
  )
  SSH_OPTS+=("${AUTH_OPTS[@]}")
  SCP_OPTS+=("${AUTH_OPTS[@]}")
  SSH_OPTS+=("${CONTROL_OPTS[@]}")
  SCP_OPTS+=("${CONTROL_OPTS[@]}")
  echo "Using password authentication mode (one prompt expected per run)."
else
  SSH_OPTS+=( -o BatchMode=yes )
fi

if [[ "${PASSWORD_AUTH}" == "1" && "${PASSWORD_STORE}" != "1" ]]; then
  echo "Establishing reusable SSH session (enter password once)..."
  "${SSH_CMD[@]}" "${SSH_OPTS[@]}" -Nf "${PI_USER}@${PI_HOST}"
fi

echo "[1/8] Connectivity check to ${PI_USER}@${PI_HOST}:${PI_PORT}"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "echo ok" >/dev/null

echo "[2/8] Upload release artifacts"
"${SCP_CMD[@]}" "${SCP_OPTS[@]}" "${TARBALL}" "${SHA_FILE}" "${PI_USER}@${PI_HOST}:${REMOTE_BASE}/"
if [[ -f "${RELEASE_NOTES}" ]]; then
  "${SCP_CMD[@]}" "${SCP_OPTS[@]}" "${RELEASE_NOTES}" "${PI_USER}@${PI_HOST}:${REMOTE_BASE}/" || true
fi

echo "[3/8] Verify artifact checksum on Pi"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "cd '${REMOTE_BASE}' && sha256sum -c '$(basename "${REMOTE_SHA}")'"

echo "[4/8] Extract release"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "cd '${REMOTE_BASE}' && rm -rf '${REMOTE_DIR}' && mkdir -p '${REMOTE_DIR}' && tar xzf '$(basename "${REMOTE_TARBALL}")' -C '${REMOTE_DIR}'"

echo "[5/8] Install/update services"
"${SSH_CMD[@]}" -t "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "cd '${REMOTE_DIR}' && sudo python3 tools/install-all-optimized.py"

echo "[6/8] Service health summary"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "\
  set -e; \
  for svc in camcontroller camcontroller-web camcontroller-update smbd nmbd; do \
    state=\$(systemctl is-active \"\$svc\" 2>/dev/null || true); \
    printf '%-24s %s\n' \"\$svc\" \"\$state\"; \
  done\
"

echo "[7/8] HTTP and Samba checks"
"${SSH_CMD[@]}" "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "\
  set -e; \
  echo -n 'http://localhost -> '; \
  curl -sS -o /dev/null -w '%{http_code}\n' http://localhost || true; \
  if command -v smbclient >/dev/null 2>&1; then \
    echo -n '//localhost/shared -> '; \
    if timeout 10 smbclient //localhost/shared -U% -c 'ls; quit' >/dev/null 2>&1; then echo OK; else echo FAIL; fi; \
  else \
    echo 'smbclient not installed on Pi (skip)'; \
  fi\
"

echo "[8/8] Existing project tests + recent logs"
"${SSH_CMD[@]}" -t "${SSH_OPTS[@]}" "${PI_USER}@${PI_HOST}" "\
  set -e; \
  cd '${REMOTE_DIR}'; \
  python3 tools/test_camera_service.py || true; \
  python3 tools/test_web_service.py || true; \
  python3 tools/test_smb_service.py || true; \
  echo; echo 'Recent camcontroller logs:'; sudo journalctl -u camcontroller --no-pager -n 20 || true; \
  echo; echo 'Recent web logs:'; sudo journalctl -u camcontroller-web --no-pager -n 20 || true; \
  echo; echo 'Recent update logs:'; sudo journalctl -u camcontroller-update --no-pager -n 20 || true\
"

echo

echo "Smoke test completed for ${PROJECT_NAME}-${VERSION} on ${PI_HOST}"
