#!/usr/bin/env bash
set -euo pipefail

# Wait until a real client network connection is active.
# This prevents camera/web services from starting while ComitUp AP portal
# owns port 80 during initial WiFi setup.

SLEEP_SECONDS="${CAM_WAIT_NET_SLEEP_SECONDS:-5}"
TIMEOUT_SECONDS="${CAM_WAIT_NET_TIMEOUT_SECONDS:-0}"
START_TS="$(date +%s)"

is_real_network_connected() {
  if command -v nmcli >/dev/null 2>&1; then
    # Accept:
    # - any connected ethernet interface
    # - connected wifi whose connection name is not ComitUp/AP hotspot
    while IFS=: read -r device type state connection; do
      [[ "${state}" == "connected" ]] || continue

      if [[ "${type}" == "ethernet" ]]; then
        return 0
      fi

      if [[ "${type}" == "wifi" ]]; then
        conn_lc="$(printf '%s' "${connection}" | tr '[:upper:]' '[:lower:]')"
        if [[ "${conn_lc}" == *comitup* ]] || [[ "${conn_lc}" == *hotspot* ]]; then
          continue
        fi
        return 0
      fi
    done < <(nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null || true)

    return 1
  fi

  # Fallback: require a default route.
  ip route show default >/dev/null 2>&1
}

while true; do
  if is_real_network_connected; then
    exit 0
  fi

  if [[ "${TIMEOUT_SECONDS}" -gt 0 ]]; then
    now_ts="$(date +%s)"
    elapsed="$((now_ts - START_TS))"
    if [[ "${elapsed}" -ge "${TIMEOUT_SECONDS}" ]]; then
      echo "Timed out waiting for real network connectivity (${TIMEOUT_SECONDS}s)" >&2
      exit 1
    fi
  fi

  sleep "${SLEEP_SECONDS}"
done
