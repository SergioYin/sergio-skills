#!/usr/bin/env bash
set -uo pipefail

reality_port=443
while (($#)); do
  case "$1" in
    --reality-port) reality_port="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$reality_port" =~ ^[0-9]+$ ]] && ((reality_port >= 1 && reality_port <= 65535)) || {
  echo "invalid --reality-port" >&2; exit 2;
}

fail=0
warn=0
section() { printf '\n[%s]\n' "$1"; }

section identity
printf 'uid=%s user=%s\n' "$(id -u)" "$(id -un)"
if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  printf 'os=%s version=%s\n' "${ID:-unknown}" "${VERSION_ID:-unknown}"
  [[ "${ID:-}" == ubuntu ]] || { echo 'FAIL: executable slice supports Ubuntu only'; fail=1; }
else
  echo 'FAIL: /etc/os-release unavailable'; fail=1
fi
printf 'kernel=%s arch=%s\n' "$(uname -r)" "$(uname -m)"
command -v systemctl >/dev/null || { echo 'FAIL: systemd unavailable'; fail=1; }
command -v ss >/dev/null || { echo 'FAIL: ss unavailable'; fail=1; }
command -v python3 >/dev/null || { echo 'FAIL: python3 unavailable'; fail=1; }
command -v unzip >/dev/null || { echo 'WARN: unzip unavailable; install it before deployment'; warn=1; }

section capacity
command -v nproc >/dev/null && printf 'vcpus=%s\n' "$(nproc)"
free -h 2>/dev/null || true
df -hT / 2>/dev/null || true
df -i / 2>/dev/null || true
systemd-detect-virt 2>/dev/null || true

section time_and_units
timedatectl show -p NTPSynchronized -p Timezone 2>/dev/null || true
systemctl --failed --no-pager 2>/dev/null || true

section network
ip -br address 2>/dev/null || true
ip route 2>/dev/null || true
if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "(:|])${reality_port}$"; then
  echo "FAIL: TCP port ${reality_port} is already listening"
  fail=1
else
  echo "PASS: TCP port ${reality_port} is not listening"
fi

section ssh
if command -v sshd >/dev/null; then
  sshd -T 2>/dev/null | grep -E '^(port|permitrootlogin|passwordauthentication|pubkeyauthentication) ' || true
elif [[ -x /usr/sbin/sshd ]]; then
  /usr/sbin/sshd -T 2>/dev/null | grep -E '^(port|permitrootlogin|passwordauthentication|pubkeyauthentication) ' || true
else
  echo 'WARN: sshd effective configuration unavailable'; warn=1
fi

section firewall
if command -v ufw >/dev/null; then ufw status verbose 2>/dev/null || true; else echo 'ufw=absent'; fi
if command -v nft >/dev/null; then nft list ruleset 2>/dev/null | sed -n '1,160p'; else echo 'nft=absent'; fi

section existing_proxy_services
for unit in xray hysteria-server hysteria wg-quick@wg0; do
  printf '%s enabled=%s active=%s\n' "$unit" "$(systemctl is-enabled "$unit" 2>/dev/null || true)" "$(systemctl is-active "$unit" 2>/dev/null || true)"
done

if ((fail)); then
  echo 'PRECHECK_RESULT=FAIL'
  exit 1
elif ((warn)); then
  echo 'PRECHECK_RESULT=WARN'
else
  echo 'PRECHECK_RESULT=PASS'
fi
