#!/usr/bin/env bash
set -euo pipefail

# Exit 0 only when no real client network is connected.
# Used as comitup.service ExecCondition so ComitUp is skipped when LAN/Wi-Fi is already up.

is_real_network_connected() {
  if command -v nmcli >/dev/null 2>&1; then
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

  ip route show default >/dev/null 2>&1
}

if is_real_network_connected; then
  exit 1
fi

exit 0
