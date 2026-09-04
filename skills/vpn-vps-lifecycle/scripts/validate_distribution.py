#!/usr/bin/env python3
"""Validate links, privacy boundaries, executable assets, and template invariants."""

from __future__ import annotations

import argparse
import ipaddress
import re
from pathlib import Path


ALLOWED_PUBLIC_TEST_IPS = {"38.244.33.1", "192.220.21.1", "216.36.109.1"}
DOCUMENTATION_RANGES = tuple(
    ipaddress.ip_network(value)
    for value in ("192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24")
)
INFRASTRUCTURE_LITERALS = {"0.0.0.0", "127.0.0.1"}


def scan_text(path: Path, text: str, canaries: tuple[str, ...] = ()) -> list[str]:
    """Return generic privacy findings without embedding anyone's real identifiers."""
    findings: list[str] = []
    patterns = {
        "absolute user home path": r"/(?:Users|home)/[A-Za-z0-9._-]+",
        "concrete SSH command port": r"\bssh\s+(?:[^\n]*?\s)?-p\s+\d{2,5}\b",
        "private key material": r"BEGIN (?:OPENSSH|RSA|EC|PRIVATE)[^\n]*PRIVATE KEY",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(f"{label}: {path}")

    for address in set(re.findall(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", text)):
        try:
            parsed = ipaddress.ip_address(address)
        except ValueError:
            continue
        allowed = (
            address in ALLOWED_PUBLIC_TEST_IPS
            or address in INFRASTRUCTURE_LITERALS
            or any(parsed in network for network in DOCUMENTATION_RANGES)
        )
        if not allowed:
            findings.append(f"unexpected concrete IPv4 {address}: {path}")

    for canary in canaries:
        if canary and canary in text:
            findings.append(f"caller-supplied privacy canary: {path}")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canary-file",
        action="append",
        default=[],
        help="mode-0600 file with one private value per line; values are read at runtime, never embedded",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    failures: list[str] = []
    canaries: list[str] = []
    for value in args.canary_file:
        canary_path = Path(value).expanduser().resolve()
        if canary_path.stat().st_mode & 0o077:
            raise SystemExit("canary file must not be accessible by group/other")
        canaries.extend(line.strip() for line in canary_path.read_text().splitlines() if line.strip())

    for path in root.rglob("*.md"):
        text = path.read_text()
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            destination = (path.parent / target.split("#", 1)[0]).resolve()
            if not destination.exists():
                failures.append(f"broken link: {path.relative_to(root)} -> {target}")

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        failures.extend(scan_text(path.relative_to(root), text, tuple(canaries)))

    for name in ("clash-meta-desktop.example.yaml", "clash-meta-android.example.yaml"):
        text = (root / "assets" / name).read_text()
        if 'server: "<VPS_IP>"' not in text or "192.0.2.10" in text:
            failures.append(f"unsafe server placeholder: assets/{name}")

    required = {
        "scripts/init_task.py",
        "scripts/render_reality_bundle.py",
        "scripts/remote_preflight.sh",
        "scripts/deploy_reality.sh",
        "scripts/rollback_reality.sh",
        "scripts/remote_verify.sh",
        "scripts/client_acceptance.py",
        "scripts/validate_mihomo_bundle.py",
        "scripts/collect_server_health.py",
        "scripts/record_burn_in.py",
        "scripts/summarize_burn_in.py",
        "references/deployment-reality-mihomo.md",
    }
    for relative in required:
        if not (root / relative).is_file():
            failures.append(f"missing required slice asset: {relative}")

    if failures:
        print("\n".join(f"FAIL: {item}" for item in failures))
        return 1
    print("Distribution validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
