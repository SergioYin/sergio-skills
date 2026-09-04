#!/usr/bin/env python3
"""Seal one aligned peak-window client/server observation for burn-in aggregation."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from summarize_burn_in import digest_value, in_peak_window, parse_iso, validate_plan


def load_private_json(path: Path, label: str) -> dict:
    if path.stat().st_mode & 0o077:
        raise ValueError(f"{label} must not be accessible by group/other")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--acceptance", required=True)
    parser.add_argument("--health", required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--windows-dir", required=True)
    parser.add_argument("--label", required=True, help="non-identifying ASCII window label")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,48}", args.label):
        raise SystemExit("--label must use 1-48 safe ASCII characters")

    try:
        plan = load_private_json(Path(args.plan).expanduser().resolve(), "plan")
        acceptance = load_private_json(Path(args.acceptance).expanduser().resolve(), "acceptance")
        health = load_private_json(Path(args.health).expanduser().resolve(), "health")
        context = load_private_json(Path(args.context).expanduser().resolve(), "context")
        tz = validate_plan(plan)
        approved_time = parse_iso(plan.get("approved_at"), "plan.approved_at")
        client_time = parse_iso(acceptance.get("checked_at"), "acceptance.checked_at")
        health_time = parse_iso(health.get("checked_at"), "health.checked_at")
    except (ValueError, json.JSONDecodeError, FileNotFoundError) as error:
        raise SystemExit(str(error)) from error

    difference_minutes = abs((client_time - health_time).total_seconds()) / 60
    if client_time < approved_time:
        raise SystemExit("client evidence predates burn-in plan approval")
    if difference_minutes > int(plan["maximum_alignment_minutes"]):
        raise SystemExit("client and server evidence are outside the approved alignment window")
    if not in_peak_window(client_time, plan, tz):
        raise SystemExit("client evidence was not collected in the approved local peak window")
    if acceptance.get("failures") != 0 or acceptance.get("exit_ip_match") is not True:
        raise SystemExit("client acceptance did not pass")
    if health.get("health_pass") is not True:
        raise SystemExit("server health did not pass")
    for key in ("rule_mode_pass", "global_mode_pass", "ssh_loop_pass", "business_checks_pass"):
        if context.get(key) is not True:
            raise SystemExit(f"context evidence is missing {key}=true")
    for key in ("client_profile_id", "client_network", "protocol"):
        value = context.get(key)
        if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
            raise SystemExit(f"context evidence must contain a non-placeholder {key}")

    local = client_time.astimezone(tz)
    unsigned = {
        "schema_version": 1,
        "window_id": f"{local.strftime('%Y%m%dT%H%M%S%z')}-{args.label}",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "local_date": local.date().isoformat(),
        "local_time": local.isoformat(),
        "alignment_minutes": round(difference_minutes, 3),
        "plan_sha256": digest_value(plan),
        "acceptance_sha256": digest_value(acceptance),
        "health_sha256": digest_value(health),
        "context_sha256": digest_value(context),
        "acceptance": acceptance,
        "health": health,
        "context": context,
    }
    payload = unsigned | {"sealed_sha256": digest_value(unsigned)}
    windows = Path(args.windows_dir).expanduser().resolve()
    windows.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(windows, 0o700)
    output = windows / f"{unsigned['window_id']}.json"
    if output.exists():
        raise SystemExit("refusing to overwrite an existing sealed burn-in window")
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o400)
    temporary.replace(output)
    print(json.dumps({"status": "sealed", "local_date": unsigned["local_date"], "alignment_minutes": unsigned["alignment_minutes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
