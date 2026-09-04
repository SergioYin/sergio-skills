#!/usr/bin/env bash
set -Eeuo pipefail

bundle=''
archive=''
expected_sha=''
apply=0
while (($#)); do
  case "$1" in
    --bundle) bundle="$2"; shift 2 ;;
    --archive) archive="$2"; shift 2 ;;
    --sha256) expected_sha="$2"; shift 2 ;;
    --apply) apply=1; shift ;;
    --plan) apply=0; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -d "$bundle/server" ]] || { echo 'missing --bundle server directory' >&2; exit 2; }
[[ -f "$archive" ]] || { echo 'missing --archive ZIP' >&2; exit 2; }
[[ "$expected_sha" =~ ^[0-9a-fA-F]{64}$ ]] || { echo '--sha256 must be 64 hexadecimal characters' >&2; exit 2; }
[[ "$(uname -s)" == Linux ]] || { echo 'this deployment slice supports Linux only' >&2; exit 1; }
command -v sha256sum >/dev/null || { echo 'sha256sum is required' >&2; exit 1; }
command -v unzip >/dev/null || { echo 'unzip is required' >&2; exit 1; }
command -v python3 >/dev/null || { echo 'python3 is required' >&2; exit 1; }
command -v systemctl >/dev/null || { echo 'systemd is required' >&2; exit 1; }

actual_sha="$(sha256sum "$archive" | awk '{print $1}')"
[[ "${actual_sha,,}" == "${expected_sha,,}" ]] || { echo 'Xray archive checksum mismatch' >&2; exit 1; }

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT
unzip -q "$archive" -d "$work_dir/release"
xray_candidate="$(find "$work_dir/release" -type f -name xray -perm -u+x -print -quit)"
[[ -n "$xray_candidate" ]] || { echo 'xray binary not found in archive' >&2; exit 1; }
config="$bundle/server/xray-config.json"
unit="$bundle/server/xray.service"
manifest="$bundle/manifest.json"
[[ -f "$config" && -f "$unit" && -f "$manifest" ]] || { echo 'rendered bundle is incomplete' >&2; exit 1; }
if grep -R -E '@@[A-Z0-9_]+@@|<[A-Z0-9_]+>' "$bundle" >/dev/null; then
  echo 'rendered bundle still contains placeholders' >&2
  exit 1
fi
"$xray_candidate" run -test -config "$config"

detected_version="$("$xray_candidate" version | awk 'NR==1 {gsub(/^v/,"",$2); print $2}')"
planned_version="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["xray_version"].lstrip("v"))' "$manifest")"
[[ "$detected_version" == "$planned_version" ]] || {
  echo "archive version $detected_version does not match rendered plan $planned_version" >&2; exit 1;
}
port="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["inbounds"][0]["port"])' "$config")"

cat <<EOF
PLAN: install Xray ${detected_version}
  binary: /usr/local/bin/xray
  config: /etc/xray/config.json
  unit: /etc/systemd/system/xray.service
  listener: TCP ${port}
  firewall: unchanged
  sshd: unchanged
EOF
if ((!apply)); then
  echo 'PLAN_ONLY: rerun with --apply after reviewing the plan and proving recovery/backup SSH access.'
  exit 0
fi

[[ "${ACK_RECOVERY_CONSOLE:-}" == yes ]] || { echo 'set ACK_RECOVERY_CONSOLE=yes only after verifying provider console/rescue' >&2; exit 1; }
[[ "${ACK_SSH_BACKUP_LOGIN:-}" == yes ]] || { echo 'set ACK_SSH_BACKUP_LOGIN=yes only after a separate key login succeeds' >&2; exit 1; }
((EUID == 0)) || { echo '--apply must run as root' >&2; exit 1; }

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_dir="/var/backups/vpn-vps-lifecycle/reality-${stamp}"
install -d -m 0700 "$backup_dir/previous"
touch "$backup_dir/cleanup-metadata-v1"
getent passwd xray >/dev/null && touch "$backup_dir/user.preexisting" || true
getent group xray >/dev/null && touch "$backup_dir/group.preexisting" || true
[[ -d /etc/xray ]] && touch "$backup_dir/etc-dir.preexisting" || true
[[ -d /var/lib/xray ]] && touch "$backup_dir/state-dir.preexisting" || true
for pair in '/usr/local/bin/xray:binary' '/etc/xray/config.json:config' '/etc/systemd/system/xray.service:unit'; do
  target="${pair%%:*}"
  label="${pair##*:}"
  if [[ -e "$target" || -L "$target" ]]; then
    touch "$backup_dir/${label}.present"
    cp -a "$target" "$backup_dir/previous/$label"
  fi
done
systemctl is-enabled --quiet xray.service 2>/dev/null && touch "$backup_dir/was-enabled" || true
systemctl is-active --quiet xray.service 2>/dev/null && touch "$backup_dir/was-active" || true

rollback_on_error() {
  trap - ERR
  cleanup_warn=0
  echo "deployment failed; restoring $backup_dir" >&2
  systemctl stop xray.service 2>/dev/null || true
  for pair in '/usr/local/bin/xray:binary' '/etc/xray/config.json:config' '/etc/systemd/system/xray.service:unit'; do
    target="${pair%%:*}"
    label="${pair##*:}"
    rm -f -- "$target"
    [[ -f "$backup_dir/${label}.present" ]] && cp -a "$backup_dir/previous/$label" "$target"
  done
  systemctl daemon-reload || true
  if [[ -f "$backup_dir/cleanup-metadata-v1" && ! -f "$backup_dir/user.preexisting" ]] && id -u xray >/dev/null 2>&1; then
    userdel xray 2>/dev/null || { echo 'WARN: could not remove deployment-created xray user' >&2; cleanup_warn=1; }
  fi
  if [[ -f "$backup_dir/cleanup-metadata-v1" && ! -f "$backup_dir/state-dir.preexisting" && -d /var/lib/xray ]]; then
    rmdir /var/lib/xray 2>/dev/null || { echo 'WARN: deployment-created /var/lib/xray is non-empty and was retained' >&2; cleanup_warn=1; }
  fi
  if [[ -f "$backup_dir/cleanup-metadata-v1" && ! -f "$backup_dir/etc-dir.preexisting" && -d /etc/xray ]]; then
    rmdir /etc/xray 2>/dev/null || { echo 'WARN: deployment-created /etc/xray is non-empty and was retained' >&2; cleanup_warn=1; }
  fi
  if [[ -f "$backup_dir/cleanup-metadata-v1" && ! -f "$backup_dir/group.preexisting" ]] && getent group xray >/dev/null; then
    groupdel xray 2>/dev/null || { echo 'WARN: could not remove deployment-created xray group' >&2; cleanup_warn=1; }
  fi
  [[ -f "$backup_dir/was-enabled" ]] && systemctl enable xray.service >/dev/null 2>&1 || systemctl disable xray.service >/dev/null 2>&1 || true
  [[ -f "$backup_dir/was-active" ]] && systemctl start xray.service || true
  if ((cleanup_warn)); then
    echo 'automatic rollback restored prior files/service but retained deployment-created resources; inspect before retrying' >&2
  else
    echo 'automatic rollback completed; inspect service and SSH before retrying' >&2
  fi
}
trap rollback_on_error ERR

getent group xray >/dev/null || groupadd --system xray
id -u xray >/dev/null 2>&1 || useradd --system --gid xray --home-dir /var/lib/xray --shell /usr/sbin/nologin xray
install -d -m 0750 -o root -g xray /etc/xray
install -d -m 0750 -o xray -g xray /var/lib/xray
install -m 0755 -o root -g root "$xray_candidate" /usr/local/bin/xray
install -m 0640 -o root -g xray "$config" /etc/xray/config.json
install -m 0644 -o root -g root "$unit" /etc/systemd/system/xray.service
systemctl daemon-reload
systemctl enable --now xray.service
/usr/local/bin/xray run -test -config /etc/xray/config.json
systemctl is-active --quiet xray.service
ss -ltnH | awk '{print $4}' | grep -Eq "(:|])${port}$"
trap - ERR
echo "DEPLOY_RESULT=PASS"
echo "BACKUP_DIR=$backup_dir"
echo 'NEXT: apply the reviewed firewall rule, then run remote_verify.sh and a real Mihomo client acceptance.'
