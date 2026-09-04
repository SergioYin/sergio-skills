#!/usr/bin/env python3
"""Exercise privacy, rendering, client acceptance, and state evidence gates."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True, env=env)


def run_fails(*args: str, contains: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, text=True, capture_output=True, env=env)
    assert result.returncode != 0
    assert contains in (result.stdout + result.stderr), result.stdout + result.stderr
    return result


def load_validator(root: Path):
    spec = importlib.util.spec_from_file_location("distribution_validator", root / "scripts" / "validate_distribution.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fill_public_forms(task: Path) -> None:
    for relative in ("public/requirements-card.md", "public/decision-record.md"):
        path = task / relative
        text = re.sub(r"<[^>\n]+>", "completed", path.read_text())
        path.write_text(text)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    run(sys.executable, str(root / "scripts" / "validate_distribution.py"))
    for script in root.joinpath("scripts").glob("*.sh"):
        run("bash", "-n", str(script))

    validator = load_validator(root)
    canary = "privacy-canary-" + secrets.token_hex(12)
    assert validator.scan_text(Path("synthetic.txt"), f"prefix {canary} suffix", (canary,))
    home_component = "Users"
    assert validator.scan_text(Path("synthetic.txt"), f"/{home_component}/sample/private.txt")

    with tempfile.TemporaryDirectory(prefix="vpn-vps-lifecycle-test-") as temporary:
        work = Path(temporary)
        run(sys.executable, str(root / "scripts" / "init_task.py"), "--root", str(work), "--name", "smoke")
        task = work / "smoke"
        state_cli = (sys.executable, str(root / "scripts" / "update_state.py"), "--task", str(task))
        run(*state_cli, "status")
        run(*state_cli, "advance", "--to", "research")
        run_fails(*state_cli, "advance", "--to", "plan-confirmed", contains="complete all required fields")
        fill_public_forms(task)
        run(*state_cli, "advance", "--to", "plan-confirmed")
        run(*state_cli, "advance", "--to", "preflight")

        input_path = task / "private" / "reality-input.json"
        data = {
            "schema_version": 2,
            "vps_ip": "192.0.2.10",
            "reality_port": 443,
            "reality_private_key": "A" * 43,
            "reality_public_key": "B" * 43,
            "server_name": "www.example.com",
            "target": "www.example.com:443",
            "xray_version": "25.6.8",
            "mihomo_version": "1.19.10",
            "allow_unverified_mihomo_compatibility": False,
            "clients": [
                {
                    "device_name": "smoke-desktop",
                    "platform": "desktop",
                    "uuid": "123e4567-e89b-42d3-a456-426614174000",
                    "short_id": "0123456789abcdef",
                },
                {
                    "device_name": "smoke-android",
                    "platform": "android",
                    "uuid": "123e4567-e89b-42d3-a456-426614174001",
                    "short_id": "1032547698badcfe",
                },
            ],
        }
        input_path.write_text(json.dumps(data))
        os.chmod(input_path, 0o600)
        rendered = task / "private" / "rendered"
        run(
            sys.executable,
            str(root / "scripts" / "render_reality_bundle.py"),
            "--input", str(input_path),
            "--output", str(rendered),
            "--allow-documentation-ip",
        )
        config = json.loads((rendered / "server" / "xray-config.json").read_text())
        reality = config["inbounds"][0]["streamSettings"]["realitySettings"]
        assert config["inbounds"][0]["port"] == 443
        assert reality["target"] == "www.example.com:443"
        assert len(config["inbounds"][0]["settings"]["clients"]) == 2
        assert len(reality["shortIds"]) == 2
        for path in rendered.rglob("*"):
            if path.is_file():
                text = path.read_text()
                assert "@@" not in text and "<VPS_IP>" not in text
        desktop = (rendered / "client" / "smoke-desktop" / "mihomo.yaml").read_text()
        android = (rendered / "client" / "smoke-android" / "mihomo.yaml").read_text()
        assert "192.0.2.10/32" in desktop
        assert "name: GLOBAL" in android and "name: PROXY" in android
        run_fails(
            sys.executable,
            str(root / "scripts" / "render_reality_bundle.py"),
            "--input", str(input_path),
            "--output", str(rendered),
            "--allow-documentation-ip",
            contains="refusing to overwrite",
        )

        duplicate = json.loads(json.dumps(data))
        duplicate["clients"][1]["uuid"] = duplicate["clients"][0]["uuid"]
        input_path.write_text(json.dumps(duplicate))
        os.chmod(input_path, 0o600)
        run_fails(
            sys.executable,
            str(root / "scripts" / "render_reality_bundle.py"),
            "--input", str(input_path),
            "--output", str(task / "private" / "duplicate-client"),
            "--allow-documentation-ip",
            contains="independent UUID",
        )
        incompatible = json.loads(json.dumps(data))
        incompatible["xray_version"] = "26.7.11"
        input_path.write_text(json.dumps(incompatible))
        os.chmod(input_path, 0o600)
        run_fails(
            sys.executable,
            str(root / "scripts" / "render_reality_bundle.py"),
            "--input", str(input_path),
            "--output", str(task / "private" / "incompatible"),
            "--allow-documentation-ip",
            contains="incompatibility",
        )
        os.chmod(input_path, 0o644)
        run_fails(
            sys.executable,
            str(root / "scripts" / "render_reality_bundle.py"),
            "--input", str(input_path),
            "--output", str(task / "private" / "unsafe-permissions"),
            "--allow-documentation-ip",
            contains="must not be accessible",
        )

        run_fails(*state_cli, "advance", "--to", "rendered", contains="remote-preflight.txt")
        (task / "evidence" / "remote-preflight.txt").write_text("PRECHECK_RESULT=PASS\n")
        run_fails(*state_cli, "advance", "--to", "rendered", contains="mihomo-validation.json")
        fake_bin = work / "fake-bin"
        fake_bin.mkdir()
        fake_mihomo = fake_bin / "mihomo"
        fake_mihomo.write_text(
            "#!/bin/sh\n"
            "if [ \"$1\" = '-v' ]; then printf 'Mihomo Meta v%s test\\n' \"${FAKE_MIHOMO_VERSION:-1.19.10}\"; exit 0; fi\n"
            "if [ \"$1\" = '-t' ] && [ \"$2\" = '-f' ] && [ -s \"$3\" ]; then exit 0; fi\n"
            "exit 2\n"
        )
        fake_mihomo.chmod(0o755)
        mihomo_evidence = task / "evidence" / "mihomo-validation.json"
        mismatch_env = os.environ | {"FAKE_MIHOMO_VERSION": "1.19.11"}
        run_fails(
            sys.executable,
            str(root / "scripts" / "validate_mihomo_bundle.py"),
            "--bundle", str(rendered),
            "--mihomo-bin", str(fake_mihomo),
            "--output", str(mihomo_evidence),
            contains="does not match manifest",
            env=mismatch_env,
        )
        run(
            sys.executable,
            str(root / "scripts" / "validate_mihomo_bundle.py"),
            "--bundle", str(rendered),
            "--mihomo-bin", str(fake_mihomo),
            "--output", str(mihomo_evidence),
        )
        changed_config = rendered / "client" / "smoke-desktop" / "mihomo.yaml"
        original_config = changed_config.read_bytes()
        changed_config.write_bytes(original_config + b"\n")
        os.chmod(changed_config, 0o600)
        run_fails(*state_cli, "advance", "--to", "rendered", contains="changed after Mihomo validation")
        changed_config.write_bytes(original_config)
        os.chmod(changed_config, 0o600)
        run(
            sys.executable,
            str(root / "scripts" / "validate_mihomo_bundle.py"),
            "--bundle", str(rendered),
            "--mihomo-bin", str(fake_mihomo),
            "--output", str(mihomo_evidence),
        )
        run(*state_cli, "advance", "--to", "rendered")
        run(*state_cli, "authorize", "--kind", "deploy", "--value", "true", "--evidence", "current-user-message-ref")
        (task / "evidence" / "deploy.txt").write_text("DEPLOY_RESULT=PASS\nBACKUP_DIR=/redacted/backup\n")
        (task / "evidence" / "remote-verify.txt").write_text("REMOTE_VERIFY_RESULT=PASS\n")
        run(*state_cli, "advance", "--to", "server-deployed")

        fake_curl = fake_bin / "curl"
        fake_curl.write_text(
            "#!/bin/sh\n"
            "case \"$*\" in\n"
            "  *api.ipify.org*) printf '%s' \"${FAKE_EXIT_IP:-198.51.100.20}\" ;;\n"
            "  *) printf '204\\t127.0.0.1\\t0.001\\t0.002\\t0.003\\t0.004\\t0.005\\t128' ;;\n"
            "esac\n"
        )
        fake_curl.chmod(0o755)
        client_env = os.environ | {"PATH": str(fake_bin) + os.pathsep + os.environ["PATH"]}
        urls = task / "private" / "acceptance-urls.txt"
        urls.write_text("https://www.example.com\n")
        mismatch = task / "evidence" / "client-mismatch.json"
        run_fails(
            sys.executable,
            str(root / "scripts" / "client_acceptance.py"),
            "--proxy", "http://127.0.0.1:7890",
            "--urls-file", str(urls),
            "--expected-exit-ip", "198.51.100.10",
            "--allow-documentation-ip",
            "--repeat", "1",
            "--output", str(mismatch),
            contains='"exit_ip_match": false',
            env=client_env,
        )
        assert json.loads(mismatch.read_text())["exit_ip_match"] is False
        accepted_client = task / "evidence" / "client-acceptance.json"
        run(
            sys.executable,
            str(root / "scripts" / "client_acceptance.py"),
            "--proxy", "http://127.0.0.1:7890",
            "--urls-file", str(urls),
            "--expected-exit-ip", "198.51.100.20",
            "--allow-documentation-ip",
            "--repeat", "1",
            "--output", str(accepted_client),
            env=client_env,
        )
        (task / "evidence" / "manual-client-checks.txt").write_text(
            "rule_mode=PASS\nglobal_mode=PASS\nssh_loop=PASS\n"
        )
        run(*state_cli, "advance", "--to", "client-tested")
        plan_path = task / "private" / "burn-in-plan.json"
        plan = {
            "schema_version": 1,
            "approved_at": "2026-07-31T12:00:00+08:00",
            "timezone": "Asia/Singapore",
            "peak_window_start": "18:00",
            "peak_window_end": "23:59",
            "minimum_peak_dates": 3,
            "maximum_alignment_minutes": 30,
            "test_byte_budget": 1000000,
            "max_cpu_steal_ratio": 0.1,
            "min_memory_available_mb": 128,
            "min_root_free_percent": 10,
        }
        plan_path.write_text(json.dumps(plan))
        os.chmod(plan_path, 0o600)
        run(*state_cli, "authorize", "--kind", "test-traffic", "--value", "true", "--evidence", "current-user-test-budget-ref")
        run(*state_cli, "advance", "--to", "burn-in")
        windows = task / "evidence" / "burn-in" / "windows"
        base_acceptance = json.loads(accepted_client.read_text())
        for day in range(1, 4):
            timestamp = f"2026-08-0{day}T20:00:00+08:00"
            acceptance = json.loads(json.dumps(base_acceptance))
            acceptance["checked_at"] = timestamp
            for row in acceptance["results"]:
                row["checked_at"] = timestamp
            acceptance_path = work / f"acceptance-{day}.json"
            acceptance_path.write_text(json.dumps(acceptance))
            os.chmod(acceptance_path, 0o600)
            health = {
                "schema_version": 1,
                "checked_at": f"2026-08-0{day}T20:05:00+08:00",
                "service_active": True,
                "service_enabled": True,
                "restart_count": 0,
                "listener_tcp": True,
                "clock_synchronized": True,
                "failed_units": 0,
                "boot_id": "synthetic-stable-boot",
                "route_fingerprint": "f" * 64,
                "cpu_steal_ratio": 0.01,
                "memory_available_bytes": 512 * 1024 * 1024,
                "root_free_percent": 40.0,
                "health_pass": True,
            }
            health_path = work / f"health-{day}.json"
            health_path.write_text(json.dumps(health))
            os.chmod(health_path, 0o600)
            context = {
                "client_profile_id": "synthetic-device",
                "client_network": "synthetic-network",
                "protocol": "VLESS-REALITY",
                "rule_mode_pass": True,
                "global_mode_pass": True,
                "ssh_loop_pass": True,
                "business_checks_pass": True,
            }
            context_path = work / f"context-{day}.json"
            context_path.write_text(json.dumps(context))
            os.chmod(context_path, 0o600)
            run(
                sys.executable,
                str(root / "scripts" / "record_burn_in.py"),
                "--plan", str(plan_path),
                "--acceptance", str(acceptance_path),
                "--health", str(health_path),
                "--context", str(context_path),
                "--windows-dir", str(windows),
                "--label", f"day-{day}",
            )
        summary_path = task / "evidence" / "burn-in" / "summary.json"
        summary_path.write_text(json.dumps({"schema_version": 2, "result": "PASS"}))
        os.chmod(summary_path, 0o600)
        run_fails(*state_cli, "advance", "--to", "accepted", contains="does not match a fresh derivation")
        run(
            sys.executable,
            str(root / "scripts" / "summarize_burn_in.py"),
            "--plan", str(plan_path),
            "--windows-dir", str(windows),
            "--output", str(summary_path),
        )
        summary = json.loads(summary_path.read_text())
        assert summary["result"] == "PASS" and summary["window_count"] == 3
        assert summary["downloaded_bytes"] == 384
        sealed = sorted(windows.glob("*.json"))[0]
        original_window = sealed.read_bytes()
        sealed.chmod(0o600)
        sealed.write_bytes(original_window.replace(b"synthetic-stable-boot", b"synthetic-changed-boot"))
        sealed.chmod(0o400)
        run_fails(*state_cli, "advance", "--to", "accepted", contains="does not match a fresh derivation")
        sealed.chmod(0o600)
        sealed.write_bytes(original_window)
        sealed.chmod(0o400)
        run(
            sys.executable,
            str(root / "scripts" / "summarize_burn_in.py"),
            "--plan", str(plan_path),
            "--windows-dir", str(windows),
            "--output", str(summary_path),
        )
        report = task / "reports" / "acceptance-report.md"
        report.write_text(re.sub(r"<[^>\n]+>", "completed", report.read_text()))
        run(*state_cli, "advance", "--to", "accepted")
        run_fails(*state_cli, "advance", "--to", "research", contains="invalid transition")

    print("Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
