#!/usr/bin/env python3
"""Render a private Xray REALITY + Mihomo bundle from a mode-0600 JSON input."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import shutil
import uuid as uuidlib
from datetime import datetime, timezone
from pathlib import Path


REQUIRED = {
    "vps_ip",
    "reality_port",
    "reality_private_key",
    "reality_public_key",
    "server_name",
    "target",
    "xray_version",
    "mihomo_version",
    "clients",
}


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"invalid version: {value!r}")
    return tuple(int(part) for part in match.groups())


def validate(data: dict, allow_documentation_ip: bool) -> None:
    missing = sorted(REQUIRED - data.keys())
    if missing:
        raise ValueError(f"missing fields: {', '.join(missing)}")
    for key in REQUIRED:
        if isinstance(data[key], str) and (not data[key] or "<" in data[key] or ">" in data[key]):
            raise ValueError(f"unresolved value for {key}")

    address = ipaddress.ip_address(data["vps_ip"])
    if not allow_documentation_ip and not address.is_global:
        raise ValueError("vps_ip must be a real global address; use --allow-documentation-ip only for tests")
    port = data["reality_port"]
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("reality_port must be an integer from 1 to 65535")
    key_pattern = re.compile(r"[A-Za-z0-9_-]{43}")
    for key in ("reality_private_key", "reality_public_key"):
        if not key_pattern.fullmatch(data[key]):
            raise ValueError(f"{key} must be a 43-character X25519 value")
    hostname = r"(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}"
    if not re.fullmatch(hostname, data["server_name"]):
        raise ValueError("server_name must be a fully qualified DNS name")
    target_match = re.fullmatch(rf"({hostname}):(\d{{1,5}})", data["target"])
    if not target_match or not 1 <= int(target_match.group(2)) <= 65535:
        raise ValueError("target must be an FQDN followed by a valid port")
    clients = data["clients"]
    if not isinstance(clients, list) or not clients:
        raise ValueError("clients must be a non-empty list")
    if len(clients) > 32:
        raise ValueError("clients supports at most 32 devices")
    names: set[str] = set()
    uuids: set[str] = set()
    short_ids: set[str] = set()
    for index, client in enumerate(clients):
        if not isinstance(client, dict):
            raise ValueError(f"clients[{index}] must be an object")
        missing_client = {"device_name", "platform", "uuid", "short_id"} - client.keys()
        if missing_client:
            raise ValueError(f"clients[{index}] missing: {', '.join(sorted(missing_client))}")
        name = client["device_name"]
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", name):
            raise ValueError(f"clients[{index}].device_name must use 1-64 safe ASCII characters")
        if name in names:
            raise ValueError(f"duplicate device_name: {name}")
        names.add(name)
        if client["platform"] not in {"desktop", "android"}:
            raise ValueError(f"clients[{index}].platform must be desktop or android")
        parsed_uuid = str(uuidlib.UUID(client["uuid"]))
        if parsed_uuid in uuids:
            raise ValueError("every client must use an independent UUID")
        uuids.add(parsed_uuid)
        short_id = client["short_id"].lower()
        if not re.fullmatch(r"(?:[0-9a-f]{2}){1,8}", short_id):
            raise ValueError(f"clients[{index}].short_id must contain 2-16 even-count hexadecimal characters")
        if short_id in short_ids:
            raise ValueError("every client must use an independent short_id")
        short_ids.add(short_id)

    xray_version = version_tuple(data["xray_version"])
    version_tuple(data["mihomo_version"])
    if xray_version >= (26, 7, 11) and not data.get("allow_unverified_mihomo_compatibility", False):
        raise ValueError(
            "current Mihomo documentation warns of Xray v26.7.11+ incompatibility; "
            "choose a currently verified implementation/version or explicitly acknowledge the unverified combination"
        )


def render(template: Path, replacements: dict[str, str]) -> str:
    text = template.read_text()
    for key, value in replacements.items():
        text = text.replace(f"@@{key}@@", value)
    unresolved = sorted(set(re.findall(r"@@[A-Z0-9_]+@@", text)))
    if unresolved:
        raise ValueError(f"unresolved template fields in {template.name}: {unresolved}")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-documentation-ip", action="store_true", help="tests only")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    if input_path.stat().st_mode & 0o077:
        raise SystemExit("input contains secrets and must not be accessible by group/other")
    data = json.loads(input_path.read_text())
    validate(data, args.allow_documentation_ip)

    skill_root = Path(__file__).resolve().parent.parent
    templates = skill_root / "assets" / "reality"
    output = Path(args.output).expanduser().resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("refusing to overwrite a non-empty rendered bundle; use a new directory for credential rotation")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(output, 0o700)
    server = output / "server"
    client = output / "client"
    server.mkdir(exist_ok=True, mode=0o700)
    client.mkdir(exist_ok=True, mode=0o700)

    server_clients = [
        {"id": str(uuidlib.UUID(client["uuid"])), "flow": "xtls-rprx-vision", "email": client["device_name"]}
        for client in data["clients"]
    ]
    replacements = {
        "VPS_IP": data["vps_ip"],
        "REALITY_PORT": str(data["reality_port"]),
        "REALITY_PRIVATE_KEY": data["reality_private_key"],
        "REALITY_PUBLIC_KEY": data["reality_public_key"],
        "SERVER_NAME": data["server_name"],
        "TARGET": data["target"],
        "CLIENTS_JSON": json.dumps(server_clients, separators=(",", ":")),
        "SHORT_IDS_JSON": json.dumps([client["short_id"].lower() for client in data["clients"]], separators=(",", ":")),
    }
    server_config = server / "xray-config.json"
    server_config.write_text(render(templates / "xray-config.json.tmpl", replacements))
    os.chmod(server_config, 0o600)
    for item in data["clients"]:
        device_dir = client / item["device_name"]
        device_dir.mkdir(mode=0o700)
        client_replacements = replacements | {
            "UUID": str(uuidlib.UUID(item["uuid"])),
            "SHORT_ID": item["short_id"].lower(),
        }
        template = templates / f"mihomo-{item['platform']}.yaml.tmpl"
        destination = device_dir / "mihomo.yaml"
        destination.write_text(render(template, client_replacements))
        os.chmod(destination, 0o600)
    shutil.copyfile(templates / "xray.service", server / "xray.service")
    os.chmod(server / "xray.service", 0o600)

    json.loads((server / "xray-config.json").read_text())
    manifest = {
        "schema_version": 1,
        "rendered_at": datetime.now(timezone.utc).isoformat(),
        "xray_version": data["xray_version"],
        "mihomo_version": data["mihomo_version"],
        "reality_port": data["reality_port"],
        "client_count": len(data["clients"]),
        "devices": [{"device_name": item["device_name"], "platform": item["platform"]} for item in data["clients"]],
        "contains_secrets": True,
        "files": [str(path.relative_to(output)) for path in sorted(output.rglob("*")) if path.is_file()],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    os.chmod(output / "manifest.json", 0o600)
    print(json.dumps({"status": "rendered", "client_count": manifest["client_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
