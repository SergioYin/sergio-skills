#!/usr/bin/env python3
"""Shared path/runtime helpers for xiaohongshu-reader scripts."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

DEFAULT_VISION_MODEL = os.environ.get("XHS_VISION_MODEL", "openai-codex/gpt-5.4")

def home_dir() -> Path:
    return Path(os.environ.get("HOME", "~")).expanduser()

def openclaw_root() -> Path:
    return Path(os.environ.get("OPENCLAW_HOME", home_dir() / ".openclaw")).expanduser()

def default_config_path() -> Path:
    return Path(os.environ.get("OPENCLAW_CONFIG_PATH", openclaw_root() / "openclaw.json")).expanduser()

def default_agent_dir() -> Path:
    return Path(os.environ.get("OPENCLAW_AGENT_DIR", openclaw_root() / "agents" / "main" / "agent")).expanduser()

def default_media_root() -> Path:
    return Path(os.environ.get("XHS_MEDIA_ROOT", openclaw_root() / "workspace" / "media" / "xiaohongshu")).expanduser()

def skill_dir() -> Path:
    return Path(__file__).resolve().parents[1]

def _candidate_package_roots() -> list[Path]:
    candidates: list[Path] = []
    if os.environ.get("OPENCLAW_DIST"):
        candidates.append(Path(os.environ["OPENCLAW_DIST"]).expanduser().parent)
    if os.environ.get("OPENCLAW_PACKAGE_ROOT"):
        candidates.append(Path(os.environ["OPENCLAW_PACKAGE_ROOT"]).expanduser())

    exe = shutil.which("openclaw")
    if exe:
        try:
            real = Path(exe).resolve()
            if real.name == "openclaw.mjs":
                candidates.append(real.parent)
            candidates.append(real.parent.parent / "lib" / "node_modules" / "openclaw")
        except OSError:
            pass

    npm = shutil.which("npm")
    if npm:
        try:
            root = subprocess.check_output([npm, "root", "-g"], text=True, timeout=5).strip()
            if root:
                candidates.append(Path(root) / "openclaw")
        except Exception:
            pass

    # HOME-based fallback for fnm installs. This is not user-specific and only used
    # when command discovery fails.
    fnm_root = home_dir() / ".local" / "share" / "fnm" / "node-versions"
    if fnm_root.exists():
        for p in sorted(fnm_root.glob("*/installation/lib/node_modules/openclaw"), reverse=True):
            candidates.append(p)

    out: list[Path] = []
    seen: set[str] = set()
    for c in candidates:
        try:
            r = c.expanduser().resolve()
        except OSError:
            r = c.expanduser()
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def find_openclaw_dist(explicit: str | None = None) -> Path:
    if explicit:
        p = Path(explicit).expanduser()
        if p.name != "dist" and (p / "dist").is_dir():
            p = p / "dist"
        if p.is_dir():
            return p.resolve()
        raise FileNotFoundError(f"openclaw dist not found: {p}")
    for root in _candidate_package_roots():
        dist = root if root.name == "dist" else root / "dist"
        if dist.is_dir() and any(dist.glob("runtime-*.js")):
            return dist.resolve()
    raise FileNotFoundError("OpenClaw dist not found. Set OPENCLAW_DIST or pass --openclaw-dist.")

def probe_describe_runtime(dist: str | Path | None = None, timeout: int = 20) -> dict[str, Any]:
    try:
        dist_path = find_openclaw_dist(str(dist) if dist else None)
    except Exception as e:
        return {"ok": False, "error": str(e), "dist": str(dist) if dist else None}
    js = f"""
import fs from 'node:fs/promises';
import pathMod from 'node:path';
const distDir = {json.dumps(str(dist_path))};
try {{
  const names = await fs.readdir(distDir);
  const runtimeFiles = names.filter((name) => /^runtime-.*[.]js$/.test(name)).sort((a,b)=>a.localeCompare(b));
  const errors = [];
  for (const name of runtimeFiles) {{
    const full = pathMod.join(distDir, name);
    try {{
      const mod = await import(full);
      if (typeof mod.describeImageFileWithModel === 'function') {{
        console.log(JSON.stringify({{ ok: true, dist: distDir, modulePath: full, runtimeFiles: runtimeFiles.length }}));
        process.exit(0);
      }}
    }} catch (e) {{ errors.push(`${{name}}: ${{String(e && (e.message || e))}}`); }}
  }}
  console.log(JSON.stringify({{ ok: false, dist: distDir, runtimeFiles: runtimeFiles.length, error: `describeImageFileWithModel export not found. ${{errors.slice(0,5).join(' | ')}}` }}));
  process.exit(2);
}} catch (e) {{
  console.log(JSON.stringify({{ ok: false, dist: distDir, error: String(e && (e.stack || e.message) || e) }}));
  process.exit(1);
}}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        path = f.name
        f.write(js)
    try:
        proc = subprocess.run(["node", path], text=True, capture_output=True, timeout=timeout)
        raw = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
        if not raw:
            return {"ok": False, "dist": str(dist_path), "error": (proc.stderr or f"node exited {proc.returncode}").strip()}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "dist": str(dist_path), "error": f"non_json_probe_output: {raw[:500]}"}
        return data
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
