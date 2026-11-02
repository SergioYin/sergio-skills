#!/usr/bin/env python3
"""Collect a read-only Linux server-health snapshot for one burn-in window."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def command(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(args, text=True, capture_output=True, timeout=20)
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, "", "command unavailable")


def meminfo() -> tuple[int, int]:
    values = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, raw = line.split(":", 1)
        values[key] = int(raw.strip().split()[0]) * 1024
    return values["MemTotal"], values["MemAvailable"]


def cpu_steal_ratio() -> float:
    fields = [int(value) for value in Path("/proc/stat").read_text().splitlines()[0].split()[1:]]
    total = sum(fields)
    steal = fields[7] if len(fields) > 7 else 0
    return round(steal / total, 8) if total else 0.0


def network_totals() -> tuple[int, int]:
    rx = tx = 0
    for interface in Path("/sys/class/net").iterdir():
        if interface.name == "lo":
            continue
        try:
            rx += int((interface / "statistics/rx_bytes").read_text())
            tx += int((interface / "statistics/tx_bytes").read_text())
        except (FileNotFoundError, ValueError):
            continue
    return rx, tx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", default="xray.service")
    parser.add_argument("--port", type=int, default=443)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if platform.system() != "Linux":
        raise SystemExit("server-health collection supports Linux only")
    if not re.fullmatch(r"[A-Za-z0-9@_.-]{1,128}", args.service):
        raise SystemExit("invalid service unit name")
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be from 1 to 65535")

    active = command("systemctl", "is-active", "--quiet", args.service).returncode == 0
    enabled = command("systemctl", "is-enabled", "--quiet", args.service).returncode == 0
    restart_raw = command("systemctl", "show", args.service, "-p", "NRestarts", "--value")
    try:
        restart_count = int(restart_raw.stdout.strip())
    except ValueError:
        restart_count = -1
    sockets = command("ss", "-ltnH")
    listener = sockets.returncode == 0 and any(
        re.search(rf"(?:\]|:){args.port}$", line.split()[3])
        for line in sockets.stdout.splitlines()
        if len(line.split()) >= 4
    )
    ntp = command("timedatectl", "show", "-p", "NTPSynchronized", "--value")
    clock_synchronized = ntp.returncode == 0 and ntp.stdout.strip().lower() == "yes"
    failed = command("systemctl", "--failed", "--plain", "--no-legend")
    failed_units = len([line for line in failed.stdout.splitlines() if line.strip()]) if failed.returncode in {0, 1} else -1
    routes = command("ip", "route", "show")
    route_fingerprint = hashlib.sha256(routes.stdout.encode()).hexdigest() if routes.returncode == 0 and routes.stdout else ""
    boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    memory_total, memory_available = meminfo()
    disk = shutil.disk_usage("/")
    root_free_percent = round(disk.free / disk.total * 100, 3) if disk.total else 0.0
    rx_bytes, tx_bytes = network_totals()
    health_pass = all(
        (
            active,
            enabled,
            listener,
            clock_synchronized,
            failed_units == 0,
            restart_count >= 0,
            bool(route_fingerprint),
            bool(boot_id),
        )
    )
    payload = {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "service_unit": args.service,
        "service_active": active,
        "service_enabled": enabled,
        "restart_count": restart_count,
        "listener_tcp": listener,
        "listener_port": args.port,
        "clock_synchronized": clock_synchronized,
        "failed_units": failed_units,
        "boot_id": boot_id,
        "route_fingerprint": route_fingerprint,
        "cpu_steal_ratio": cpu_steal_ratio(),
        "memory_total_bytes": memory_total,
        "memory_available_bytes": memory_available,
        "root_free_bytes": disk.free,
        "root_free_percent": root_free_percent,
        "network_rx_bytes": rx_bytes,
        "network_tx_bytes": tx_bytes,
        "health_pass": health_pass,
    }
    if args.output == "-":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        output = Path(args.output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        os.chmod(temporary, 0o600)
        temporary.replace(output)
        print(json.dumps({"health_pass": health_pass, "service_active": active, "listener_tcp": listener, "failed_units": failed_units}))
    return 0 if health_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
