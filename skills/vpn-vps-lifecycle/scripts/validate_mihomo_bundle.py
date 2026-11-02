#!/usr/bin/env python3
"""Validate every rendered client config with the exact planned Mihomo binary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_version(output: str) -> str:
    match = re.search(r"\bv?(\d+\.\d+\.\d+)\b", output)
    if not match:
        raise ValueError("unable to parse Mihomo semantic version")
    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, help="private rendered bundle")
    parser.add_argument("--mihomo-bin", required=True, help="reviewed Mihomo executable")
    parser.add_argument("--output", required=True, help="mode-0600 validation evidence JSON")
    args = parser.parse_args()

    bundle = Path(args.bundle).expanduser().resolve()
    binary = Path(args.mihomo_bin).expanduser().resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise SystemExit("--mihomo-bin must be an executable file")
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    devices = manifest.get("devices")
    if not isinstance(devices, list) or not devices:
        raise SystemExit("rendered manifest contains no devices")

    version_result = subprocess.run([str(binary), "-v"], text=True, capture_output=True, timeout=30)
    if version_result.returncode != 0:
        raise SystemExit("Mihomo version command failed")
    try:
        detected_version = extract_version(version_result.stdout + "\n" + version_result.stderr)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    planned_version = str(manifest.get("mihomo_version", "")).lstrip("v")
    if detected_version != planned_version:
        raise SystemExit(f"Mihomo binary version {detected_version} does not match manifest {planned_version}")

    results = []
    failures = 0
    seen: set[str] = set()
    for device in devices:
        name = device.get("device_name") if isinstance(device, dict) else None
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name) or name in seen:
            raise SystemExit("manifest contains an invalid or duplicate device name")
        seen.add(name)
        relative = Path("client") / name / "mihomo.yaml"
        config = bundle / relative
        if not config.is_file():
            raise SystemExit(f"missing rendered client config for device index {len(results)}")
        if config.stat().st_mode & 0o077:
            raise SystemExit("rendered client configs must not be accessible by group/other")
        check = subprocess.run(
            [str(binary), "-t", "-f", str(config)],
            text=True,
            capture_output=True,
            timeout=60,
        )
        passed = check.returncode == 0
        failures += 0 if passed else 1
        results.append(
            {
                "device_name": name,
                "platform": device.get("platform"),
                "relative_path": str(relative),
                "config_sha256": sha256_file(config),
                "passed": passed,
                "returncode": check.returncode,
                "diagnostic": (check.stdout + "\n" + check.stderr).strip()[-1000:],
            }
        )

    payload = {
        "schema_version": 1,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "mihomo_version": detected_version,
        "mihomo_binary_sha256": sha256_file(binary),
        "manifest_sha256": sha256_file(manifest_path),
        "checked_files": len(results),
        "failures": failures,
        "results": results,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(output)
    print(json.dumps({"checked_files": len(results), "failures": failures, "version_match": True}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
