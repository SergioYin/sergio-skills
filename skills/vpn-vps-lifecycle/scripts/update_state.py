#!/usr/bin/env python3
"""Advance a VPN VPS task through evidence-gated, auditable transitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from summarize_burn_in import build_summary, validate_plan


TRANSITIONS = {
    "interview": {"research"},
    "research": {"plan-confirmed"},
    "plan-confirmed": {"preflight"},
    "preflight": {"rendered"},
    "rendered": {"server-deployed"},
    "server-deployed": {"client-tested", "rolled-back"},
    "client-tested": {"burn-in", "rolled-back"},
    "burn-in": {"accepted", "rolled-back"},
    "accepted": set(),
    "rolled-back": {"preflight"},
}

NEXT_STEPS = {
    "interview": "complete requirements-card.md",
    "research": "verify current providers, routes, versions, and protocol fit",
    "plan-confirmed": "run and save the read-only remote preflight",
    "preflight": "resolve or explicitly accept warnings, then render a private bundle",
    "rendered": "review the plan, record deploy authorization, deploy, and run remote verification",
    "server-deployed": "run real client, exit-IP, mode, business, and SSH-loop checks",
    "client-tested": "run the approved multi-window burn-in plan",
    "burn-in": "complete the acceptance report from burn-in evidence",
    "accepted": "operate using the recorded monitoring and review schedule",
    "rolled-back": "verify restored access, then start a new preflight before retrying",
}


def read_text(task: Path, relative: str) -> str:
    path = task / relative
    if not path.is_file():
        raise ValueError(f"required evidence is missing: {relative}")
    return path.read_text()


def read_json(task: Path, relative: str) -> dict:
    try:
        value = json.loads(read_text(task, relative))
    except json.JSONDecodeError as error:
        raise ValueError(f"required evidence is not valid JSON: {relative}") from error
    if not isinstance(value, dict):
        raise ValueError(f"required evidence must be a JSON object: {relative}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_no_placeholder(task: Path, relative: str) -> None:
    text = read_text(task, relative)
    if re.search(r"<[^>\n]+>", text):
        raise ValueError(f"complete all required fields before advancing: {relative}")


def validate_gate(task: Path, state: dict, destination: str) -> None:
    if destination == "plan-confirmed":
        require_no_placeholder(task, "public/requirements-card.md")
        require_no_placeholder(task, "public/decision-record.md")
    elif destination == "rendered":
        preflight = read_text(task, "evidence/remote-preflight.txt")
        if "PRECHECK_RESULT=FAIL" in preflight:
            raise ValueError("preflight failed")
        if "PRECHECK_RESULT=WARN" in preflight:
            accepted = read_text(task, "evidence/preflight-warnings-accepted.txt").strip()
            if not accepted:
                raise ValueError("preflight warnings require a written acceptance record")
        elif "PRECHECK_RESULT=PASS" not in preflight:
            raise ValueError("preflight evidence has no recognized result")
        manifest = read_json(task, "private/rendered/manifest.json")
        if not isinstance(manifest.get("client_count"), int) or manifest["client_count"] < 1:
            raise ValueError("rendered manifest has no client devices")
        mihomo = read_json(task, "evidence/mihomo-validation.json")
        if mihomo.get("failures") != 0 or mihomo.get("checked_files") != manifest["client_count"]:
            raise ValueError("not every rendered client config passed real Mihomo validation")
        if mihomo.get("mihomo_version") != str(manifest.get("mihomo_version", "")).lstrip("v"):
            raise ValueError("Mihomo validation version does not match the manifest")
        manifest_path = task / "private/rendered/manifest.json"
        if mihomo.get("manifest_sha256") != sha256_file(manifest_path):
            raise ValueError("Mihomo validation was produced for a different manifest")
        results = mihomo.get("results")
        if not isinstance(results, list) or len(results) != manifest["client_count"]:
            raise ValueError("Mihomo validation result count is incomplete")
        rendered_root = (task / "private/rendered").resolve()
        for result in results:
            relative = Path(str(result.get("relative_path", "")))
            config = (rendered_root / relative).resolve()
            if not config.is_relative_to(rendered_root) or not config.is_file():
                raise ValueError("Mihomo validation references an invalid client config")
            if result.get("passed") is not True or result.get("config_sha256") != sha256_file(config):
                raise ValueError("a rendered client config changed after Mihomo validation")
    elif destination == "server-deployed":
        if state.get("authorization", {}).get("deploy") is not True:
            raise ValueError("explicit deploy authorization is required")
        if not state.get("authorization_evidence", {}).get("deploy"):
            raise ValueError("deploy authorization must include a non-secret evidence reference")
        deploy = read_text(task, "evidence/deploy.txt")
        if "DEPLOY_RESULT=PASS" not in deploy or "BACKUP_DIR=" not in deploy:
            raise ValueError("deployment evidence must include PASS and a backup directory")
        if "REMOTE_VERIFY_RESULT=PASS" not in read_text(task, "evidence/remote-verify.txt"):
            raise ValueError("remote verification did not pass")
    elif destination == "client-tested":
        acceptance = read_json(task, "evidence/client-acceptance.json")
        if acceptance.get("failures") != 0 or acceptance.get("exit_ip_match") is not True:
            raise ValueError("client acceptance or expected exit-IP match did not pass")
        manual = read_text(task, "evidence/manual-client-checks.txt")
        for marker in ("rule_mode=PASS", "global_mode=PASS", "ssh_loop=PASS"):
            if marker not in manual:
                raise ValueError(f"manual client evidence is missing {marker}")
    elif destination == "burn-in":
        if state.get("authorization", {}).get("test-traffic") is not True:
            raise ValueError("explicit test-traffic authorization is required")
        if not state.get("authorization_evidence", {}).get("test-traffic"):
            raise ValueError("test-traffic authorization must include a non-secret evidence reference")
        plan = read_json(task, "private/burn-in-plan.json")
        try:
            validate_plan(plan)
        except ValueError as error:
            raise ValueError(f"invalid burn-in plan: {error}") from error
    elif destination == "accepted":
        summary = read_json(task, "evidence/burn-in/summary.json")
        try:
            expected = build_summary(task / "private/burn-in-plan.json", task / "evidence/burn-in/windows")
        except (ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"burn-in source evidence is invalid: {error}") from error
        if summary != expected:
            raise ValueError("burn-in summary does not match a fresh derivation from sealed windows")
        if summary.get("result") != "PASS":
            raise ValueError("derived burn-in summary did not pass")
        report = read_text(task, "reports/acceptance-report.md")
        if re.search(r"<[^>\n]+>", report):
            raise ValueError("acceptance report still appears to contain placeholders")
    elif destination == "rolled-back":
        if "ROLLBACK_RESULT=PASS" not in read_text(task, "evidence/rollback.txt"):
            raise ValueError("rollback evidence did not pass")


def save(path: Path, state: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    authorize = subparsers.add_parser("authorize")
    authorize.add_argument("--kind", choices=("purchase", "deploy", "reboot", "test-traffic"), required=True)
    authorize.add_argument("--value", choices=("true", "false"), required=True)
    authorize.add_argument("--evidence", required=True, help="non-secret reference to the user's current explicit decision")
    advance = subparsers.add_parser("advance")
    advance.add_argument("--to", required=True, choices=tuple(TRANSITIONS))
    args = parser.parse_args()

    task = Path(args.task).expanduser().resolve()
    path = task / "state.json"
    state = json.loads(path.read_text())
    phase = state.get("phase")
    if phase not in TRANSITIONS:
        raise SystemExit(f"unknown current phase: {phase!r}")
    if args.command == "status":
        print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    timestamp = datetime.now(timezone.utc).isoformat()
    state.setdefault("history", [])
    state.setdefault("authorization_evidence", {})
    if args.command == "authorize":
        evidence = args.evidence.strip()
        if not evidence:
            raise SystemExit("authorization evidence must not be empty")
        value = args.value == "true"
        state.setdefault("authorization", {})[args.kind] = value
        state["authorization_evidence"][args.kind] = {"value": value, "recorded_at": timestamp, "reference": evidence}
        state["history"].append({"event": "authorization", "kind": args.kind, "value": value, "at": timestamp})
    else:
        destination = args.to
        if destination not in TRANSITIONS[phase]:
            allowed = ", ".join(sorted(TRANSITIONS[phase])) or "none"
            raise SystemExit(f"invalid transition {phase} -> {destination}; allowed: {allowed}")
        try:
            validate_gate(task, state, destination)
        except ValueError as error:
            raise SystemExit(f"evidence gate failed: {error}") from error
        state["history"].append({"event": "phase-transition", "from": phase, "to": destination, "at": timestamp})
        state["phase"] = destination
        state["last_completed_step"] = phase
        state["next_step"] = NEXT_STEPS[destination]
    state["updated_at"] = timestamp
    save(path, state)
    print(json.dumps({"status": "updated", "phase": state["phase"], "next_step": state["next_step"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
