#!/usr/bin/env python3
"""Derive a deterministic burn-in verdict from sealed per-window evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_value(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_iso(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone offset")
    return parsed


def parse_clock(value: object, label: str) -> time:
    if not isinstance(value, str):
        raise ValueError(f"{label} must use HH:MM")
    try:
        return time.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must use HH:MM") from error


def validate_plan(plan: dict) -> ZoneInfo:
    required = {
        "approved_at",
        "timezone",
        "peak_window_start",
        "peak_window_end",
        "minimum_peak_dates",
        "maximum_alignment_minutes",
        "test_byte_budget",
        "max_cpu_steal_ratio",
        "min_memory_available_mb",
        "min_root_free_percent",
    }
    missing = sorted(required - plan.keys())
    if missing:
        raise ValueError(f"burn-in plan missing: {', '.join(missing)}")
    parse_iso(plan["approved_at"], "approved_at")
    try:
        timezone = ZoneInfo(plan["timezone"])
    except (ZoneInfoNotFoundError, TypeError) as error:
        raise ValueError("timezone must be a valid IANA timezone") from error
    parse_clock(plan["peak_window_start"], "peak_window_start")
    parse_clock(plan["peak_window_end"], "peak_window_end")
    numeric_rules = {
        "minimum_peak_dates": (int, 3, 31),
        "maximum_alignment_minutes": (int, 1, 180),
        "test_byte_budget": (int, 1, 10**12),
        "max_cpu_steal_ratio": ((int, float), 0, 1),
        "min_memory_available_mb": ((int, float), 0, 10**9),
        "min_root_free_percent": ((int, float), 0, 100),
    }
    for key, (kind, minimum, maximum) in numeric_rules.items():
        value = plan[key]
        if isinstance(value, bool) or not isinstance(value, kind) or not minimum <= value <= maximum:
            raise ValueError(f"invalid burn-in plan value: {key}")
    return timezone


def in_peak_window(moment: datetime, plan: dict, timezone: ZoneInfo) -> bool:
    local = moment.astimezone(timezone).timetz().replace(tzinfo=None)
    start = parse_clock(plan["peak_window_start"], "peak_window_start")
    end = parse_clock(plan["peak_window_end"], "peak_window_end")
    return start <= local <= end if start <= end else local >= start or local <= end


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return round(ordered[rank - 1], 6)


def build_summary(plan_path: Path, windows_dir: Path) -> dict:
    plan = json.loads(plan_path.read_text())
    if not isinstance(plan, dict):
        raise ValueError("burn-in plan must be a JSON object")
    timezone = validate_plan(plan)
    plan_digest = digest_value(plan)
    window_paths = sorted(windows_dir.glob("*.json"))
    if not window_paths:
        raise ValueError("no sealed burn-in windows found")

    reasons: list[str] = []
    local_dates: set[str] = set()
    expected_exits: set[str] = set()
    boot_ids: set[str] = set()
    routes: set[str] = set()
    restart_counts: set[int] = set()
    latencies: list[float] = []
    downloaded_bytes = 0
    sample_count = 0
    source_files = []

    for path in window_paths:
        mode = path.stat().st_mode
        if mode & 0o222 or mode & 0o077:
            reasons.append(f"window-not-sealed:{path.name}")
        window = json.loads(path.read_text())
        if not isinstance(window, dict):
            raise ValueError(f"window must be a JSON object: {path.name}")
        seal = window.get("sealed_sha256")
        unsigned = {key: value for key, value in window.items() if key != "sealed_sha256"}
        if seal != digest_value(unsigned):
            reasons.append(f"window-seal-mismatch:{path.name}")
        if window.get("plan_sha256") != plan_digest:
            reasons.append(f"window-plan-mismatch:{path.name}")
        source_files.append({"file": path.name, "sha256": sha256_file(path)})

        acceptance = window.get("acceptance", {})
        health = window.get("health", {})
        context = window.get("context", {})
        for label, payload in (("acceptance", acceptance), ("health", health), ("context", context)):
            if window.get(f"{label}_sha256") != digest_value(payload):
                reasons.append(f"embedded-{label}-hash-mismatch:{path.name}")
        checked = parse_iso(acceptance.get("checked_at"), f"{path.name}.acceptance.checked_at")
        health_checked = parse_iso(health.get("checked_at"), f"{path.name}.health.checked_at")
        approved = parse_iso(plan.get("approved_at"), "approved_at")
        alignment = abs((checked - health_checked).total_seconds()) / 60
        if checked < approved:
            reasons.append(f"predates-plan-approval:{path.name}")
        if alignment > int(plan["maximum_alignment_minutes"]):
            reasons.append(f"unaligned-client-server-evidence:{path.name}")
        if not in_peak_window(checked, plan, timezone):
            reasons.append(f"outside-peak-window:{path.name}")
        local_dates.add(checked.astimezone(timezone).date().isoformat())
        if acceptance.get("failures") != 0 or acceptance.get("exit_ip_match") is not True:
            reasons.append(f"client-acceptance-failed:{path.name}")
        expected_exit = acceptance.get("expected_exit_ip")
        if not isinstance(expected_exit, str) or acceptance.get("observed_exit_ip") != expected_exit:
            reasons.append(f"exit-ip-mismatch:{path.name}")
        else:
            expected_exits.add(expected_exit)

        results = acceptance.get("results")
        if not isinstance(results, list) or not results:
            reasons.append(f"no-client-samples:{path.name}")
        else:
            for row in results:
                sample_count += 1
                try:
                    latencies.append(float(row["curl_time_total"]))
                    downloaded_bytes += int(float(row["curl_size_download_bytes"]))
                except (KeyError, TypeError, ValueError):
                    reasons.append(f"invalid-client-metrics:{path.name}")

        if health.get("health_pass") is not True:
            reasons.append(f"server-health-failed:{path.name}")
        for key, expected in (
            ("service_active", True),
            ("listener_tcp", True),
            ("clock_synchronized", True),
            ("failed_units", 0),
        ):
            if health.get(key) != expected:
                reasons.append(f"health-{key}:{path.name}")
        try:
            if float(health["cpu_steal_ratio"]) > float(plan["max_cpu_steal_ratio"]):
                reasons.append(f"cpu-steal-threshold:{path.name}")
            if int(health["memory_available_bytes"]) < float(plan["min_memory_available_mb"]) * 1024 * 1024:
                reasons.append(f"memory-threshold:{path.name}")
            if float(health["root_free_percent"]) < float(plan["min_root_free_percent"]):
                reasons.append(f"disk-threshold:{path.name}")
            restart_counts.add(int(health["restart_count"]))
        except (KeyError, TypeError, ValueError):
            reasons.append(f"invalid-health-metrics:{path.name}")
        for key, bucket in (("boot_id", boot_ids), ("route_fingerprint", routes)):
            value = health.get(key)
            if not isinstance(value, str) or not value:
                reasons.append(f"missing-health-{key}:{path.name}")
            else:
                bucket.add(value)
        if health.get("route_fingerprint") and not isinstance(health.get("route_fingerprint"), str):
            reasons.append(f"invalid-route-fingerprint:{path.name}")
        elif health.get("route_fingerprint") and not re.fullmatch(r"[0-9a-f]{64}", health["route_fingerprint"]):
            reasons.append(f"invalid-route-fingerprint:{path.name}")
        for key in ("rule_mode_pass", "global_mode_pass", "ssh_loop_pass", "business_checks_pass"):
            if context.get(key) is not True:
                reasons.append(f"context-{key}:{path.name}")
        for key in ("client_profile_id", "client_network", "protocol"):
            value = context.get(key)
            if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
                reasons.append(f"context-{key}:{path.name}")

    if len(local_dates) < int(plan["minimum_peak_dates"]):
        reasons.append("insufficient-distinct-peak-dates")
    if len(expected_exits) != 1:
        reasons.append("exit-ip-drift")
    if len(boot_ids) != 1:
        reasons.append("boot-id-drift")
    if len(routes) != 1:
        reasons.append("route-drift")
    if len(restart_counts) != 1:
        reasons.append("service-restart-count-drift")
    if downloaded_bytes > int(plan["test_byte_budget"]):
        reasons.append("test-byte-budget-exceeded")

    unique_reasons = sorted(set(reasons))
    return {
        "schema_version": 2,
        "generator": "summarize_burn_in.py",
        "plan_sha256": plan_digest,
        "result": "PASS" if not unique_reasons else "FAIL",
        "failure_reasons": unique_reasons,
        "window_count": len(window_paths),
        "peak_dates": sorted(local_dates),
        "sample_count": sample_count,
        "downloaded_bytes": downloaded_bytes,
        "test_byte_budget": int(plan["test_byte_budget"]),
        "latency_seconds": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        },
        "expected_exit_ip_count": len(expected_exits),
        "boot_id_count": len(boot_ids),
        "route_fingerprint_count": len(routes),
        "restart_count_values": sorted(restart_counts),
        "source_files": source_files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--windows-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    plan = Path(args.plan).expanduser().resolve()
    windows = Path(args.windows_dir).expanduser().resolve()
    try:
        summary = build_summary(plan, windows)
    except (ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(output)
    print(json.dumps({"result": summary["result"], "windows": summary["window_count"], "samples": summary["sample_count"]}))
    return 0 if summary["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
