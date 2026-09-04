#!/usr/bin/env python3
"""Create or resume a private, recoverable VPN VPS task workspace."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="./vpn-vps-work")
    parser.add_argument("--name", required=True, help="lowercase task slug")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}", args.name):
        parser.error("--name must match [a-z0-9][a-z0-9-]{0,62}")

    skill_root = Path(__file__).resolve().parent.parent
    task = Path(args.root).expanduser().resolve() / args.name
    state_path = task / "state.json"
    if task.exists():
        if not state_path.is_file():
            raise SystemExit(f"refusing to reuse non-task directory: {task}")
        state = json.loads(state_path.read_text())
        print(json.dumps({"status": "resumed", "task_name": args.name, "phase": state.get("phase")}, ensure_ascii=False))
        return 0

    task.mkdir(parents=True, mode=0o700)
    os.chmod(task, 0o700)
    for rel in ("public", "private", "private/rendered", "evidence", "evidence/burn-in", "evidence/burn-in/windows", "reports"):
        path = task / rel
        path.mkdir(mode=0o700)

    copies = {
        "assets/requirements-card.md": "public/requirements-card.md",
        "assets/decision-record.md": "public/decision-record.md",
        "assets/claim-matrix.md": "public/claim-matrix.md",
        "assets/acceptance-report.md": "reports/acceptance-report.md",
        "assets/reality/reality-input.example.json": "private/reality-input.json",
        "assets/acceptance-urls.example.txt": "private/acceptance-urls.txt",
        "assets/expected-exit-ip.example.txt": "private/expected-exit-ip.txt",
        "assets/burn-in-plan.example.json": "private/burn-in-plan.json",
        "assets/burn-in-context.example.json": "private/burn-in-context.json",
    }
    for source, destination in copies.items():
        dst = task / destination
        shutil.copyfile(skill_root / source, dst)
        os.chmod(dst, 0o600)

    state = {
        "schema_version": 2,
        "task_name": args.name,
        "phase": "interview",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_completed_step": None,
        "next_step": "complete requirements-card.md",
        "authorization": {"purchase": False, "deploy": False, "reboot": False, "test-traffic": False},
        "authorization_evidence": {},
        "history": [],
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    os.chmod(state_path, 0o600)
    print(json.dumps({"status": "created", "task_name": args.name, "phase": "interview"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
