#!/usr/bin/env bash
set -uo pipefail

port=443
while (($#)); do
  case "$1" in
    --port) port="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$port" =~ ^[0-9]+$ ]] && ((port >= 1 && port <= 65535)) || { echo 'invalid --port' >&2; exit 2; }

fail=0
check() { if "$@"; then echo "PASS: $*"; else echo "FAIL: $*"; fail=1; fi; }
check systemctl is-enabled --quiet xray.service
check systemctl is-active --quiet xray.service
check /usr/local/bin/xray run -test -config /etc/xray/config.json
if ss -ltnH | awk '{print $4}' | grep -Eq "(:|])${port}$"; then echo "PASS: TCP ${port} listening"; else echo "FAIL: TCP ${port} not listening"; fail=1; fi
printf 'xray_version='; /usr/local/bin/xray version 2>/dev/null | sed -n '1p'
printf 'restart_count='; systemctl show xray.service -p NRestarts --value 2>/dev/null || true
journalctl -u xray.service -n 20 --no-pager 2>/dev/null | sed -E 's/[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}/<REDACTED_UUID>/g'
if ((fail)); then echo 'REMOTE_VERIFY_RESULT=FAIL'; exit 1; fi
echo 'REMOTE_VERIFY_RESULT=PASS'
echo 'SERVER_ONLY: still require an external Mihomo handshake, exit-IP check, target-site checks, and SSH loop test.'
