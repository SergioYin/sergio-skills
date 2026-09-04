#!/usr/bin/env bash
set -Eeuo pipefail

backup=''
apply=0
while (($#)); do
  case "$1" in
    --backup) backup="$2"; shift 2 ;;
    --apply) apply=1; shift ;;
    --plan) apply=0; shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ "$backup" == /var/backups/vpn-vps-lifecycle/reality-* && -d "$backup/previous" ]] || {
  echo 'backup must be an existing /var/backups/vpn-vps-lifecycle/reality-* directory' >&2; exit 2;
}
echo "PLAN: restore Xray binary/config/unit and prior enabled/active state from $backup"
[[ -f "$backup/cleanup-metadata-v1" ]] || echo 'PLAN_NOTE: legacy backup has no user/group/directory provenance; those resources will be retained safely'
if ((!apply)); then echo 'PLAN_ONLY: rerun with --apply after review'; exit 0; fi
((EUID == 0)) || { echo '--apply must run as root' >&2; exit 1; }
systemctl stop xray.service 2>/dev/null || true
cleanup_warn=0
for pair in '/usr/local/bin/xray:binary' '/etc/xray/config.json:config' '/etc/systemd/system/xray.service:unit'; do
  target="${pair%%:*}"
  label="${pair##*:}"
  rm -f -- "$target"
  [[ -f "$backup/${label}.present" ]] && cp -a "$backup/previous/$label" "$target"
done
systemctl daemon-reload
if [[ -f "$backup/cleanup-metadata-v1" && ! -f "$backup/user.preexisting" ]] && id -u xray >/dev/null 2>&1; then
  userdel xray 2>/dev/null || { echo 'WARN: could not remove deployment-created xray user' >&2; cleanup_warn=1; }
fi
if [[ -f "$backup/cleanup-metadata-v1" && ! -f "$backup/state-dir.preexisting" && -d /var/lib/xray ]]; then
  rmdir /var/lib/xray 2>/dev/null || { echo 'WARN: deployment-created /var/lib/xray is non-empty and was retained' >&2; cleanup_warn=1; }
fi
if [[ -f "$backup/cleanup-metadata-v1" && ! -f "$backup/etc-dir.preexisting" && -d /etc/xray ]]; then
  rmdir /etc/xray 2>/dev/null || { echo 'WARN: deployment-created /etc/xray is non-empty and was retained' >&2; cleanup_warn=1; }
fi
if [[ -f "$backup/cleanup-metadata-v1" && ! -f "$backup/group.preexisting" ]] && getent group xray >/dev/null; then
  groupdel xray 2>/dev/null || { echo 'WARN: could not remove deployment-created xray group' >&2; cleanup_warn=1; }
fi
if [[ -f "$backup/was-enabled" ]]; then systemctl enable xray.service; else systemctl disable xray.service 2>/dev/null || true; fi
if [[ -f "$backup/was-active" ]]; then systemctl start xray.service; else systemctl stop xray.service 2>/dev/null || true; fi
if ((cleanup_warn)); then
  echo 'ROLLBACK_RESULT=PARTIAL'
  exit 1
fi
echo 'ROLLBACK_RESULT=PASS'
