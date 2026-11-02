#!/usr/bin/env python3
"""Run repeatable HTTP and mandatory exit-IP checks through a local Mihomo port."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


FORMAT = "%{http_code}\t%{remote_ip}\t%{time_namelookup}\t%{time_connect}\t%{time_appconnect}\t%{time_starttransfer}\t%{time_total}\t%{size_download}"
METRIC_NAMES = (
    "http_code",
    "curl_connection_remote_ip",
    "curl_time_namelookup",
    "curl_time_connect",
    "curl_time_appconnect",
    "curl_time_starttransfer",
    "curl_time_total",
    "curl_size_download_bytes",
)


def parse_expected(args: argparse.Namespace) -> str:
    if args.expected_exit_file:
        path = Path(args.expected_exit_file).expanduser().resolve()
        if path.stat().st_mode & 0o077:
            raise SystemExit("expected exit file must not be accessible by group/other")
        raw = path.read_text().strip()
    else:
        raw = args.expected_exit_ip
    try:
        address = ipaddress.ip_address(raw)
    except ValueError as error:
        raise SystemExit("expected exit value must contain exactly one IP address") from error
    if not args.allow_documentation_ip and not address.is_global:
        raise SystemExit("expected exit IP must be global; documentation addresses are tests only")
    return str(address)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    parser.add_argument("--urls-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--exit-url", default="https://api.ipify.org", help="trusted HTTPS endpoint returning only the caller IP")
    expected = parser.add_mutually_exclusive_group(required=True)
    expected.add_argument("--expected-exit-ip", help="test/automation convenience; prefer the protected file for real addresses")
    expected.add_argument("--expected-exit-file", help="mode-0600 file containing the expected VPS exit IP")
    parser.add_argument("--allow-documentation-ip", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.repeat <= 20:
        parser.error("--repeat must be from 1 to 20")
    if not args.exit_url.startswith("https://"):
        raise SystemExit("--exit-url must use HTTPS")
    expected_exit = parse_expected(args)

    urls = []
    urls_path = Path(args.urls_file).expanduser().resolve()
    if urls_path.stat().st_mode & 0o077:
        raise SystemExit("URL list may reveal private browsing targets and must not be accessible by group/other")
    for line in urls_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            if not line.startswith("https://"):
                raise SystemExit(f"only HTTPS URLs are accepted: {line}")
            urls.append(line)
    if not urls:
        raise SystemExit("URL list is empty")

    rows = []
    failures = 0
    exit_result = subprocess.run(
        ["curl", "--silent", "--show-error", "--fail", "--proxy", args.proxy, "--connect-timeout", str(args.timeout), "--max-time", str(args.timeout), args.exit_url],
        text=True,
        capture_output=True,
    )
    observed_exit = None
    if exit_result.returncode == 0:
        try:
            observed_exit = str(ipaddress.ip_address(exit_result.stdout.strip()))
        except ValueError:
            failures += 1
    else:
        failures += 1
    exit_ip_match = observed_exit == expected_exit
    if not exit_ip_match:
        failures += 1

    for attempt in range(1, args.repeat + 1):
        for url in urls:
            command = [
                "curl", "--silent", "--show-error", "--output", os.devnull,
                "--proxy", args.proxy, "--connect-timeout", str(args.timeout),
                "--max-time", str(args.timeout), "--write-out", FORMAT, url,
            ]
            result = subprocess.run(command, text=True, capture_output=True)
            row = {"attempt": attempt, "url": url, "returncode": result.returncode, "checked_at": datetime.now(timezone.utc).isoformat()}
            if result.returncode == 0:
                fields = result.stdout.split("\t")
                if len(fields) == len(METRIC_NAMES):
                    row.update(dict(zip(METRIC_NAMES, fields)))
                    try:
                        http_ok = 200 <= int(row["http_code"]) < 400
                    except ValueError:
                        http_ok = False
                    if not http_ok:
                        row["error"] = "HTTP status outside 200-399"
                        failures += 1
                else:
                    row["error"] = "unexpected curl metrics"
                    failures += 1
            else:
                row["error"] = result.stderr.strip()[:300]
                failures += 1
            rows.append(row)

    payload = {
        "schema_version": 2,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "proxy": args.proxy,
        "exit_url": args.exit_url,
        "expected_exit_ip": expected_exit,
        "observed_exit_ip": observed_exit,
        "exit_ip_match": exit_ip_match,
        "metric_scope": "curl client-side timings via the local proxy; curl_connection_remote_ip may be the proxy endpoint rather than the target host",
        "checks": len(rows),
        "failures": failures,
        "results": rows,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.chmod(output, 0o600)
    print(json.dumps({"checks": len(rows), "failures": failures, "exit_ip_match": exit_ip_match}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
