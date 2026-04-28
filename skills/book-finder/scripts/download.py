"""Download a chosen search result and record it in `library.json`.

Inputs come as JSON on stdin (the unified Result dict from search.py) or
via `--from-search` to look up the result inline. The download path is
chosen automatically: `<library_root>/<sanitized title>.<ext>`, with a
numeric suffix added if the path already exists. The user can override
with `--out`.

Source-aware behavior:
* libgen results require a follow-up fetch to resolve the actual `get.php`
  URL (the search page only carries an `ads.php?md5=...` shim).
* archive.org results need a metadata lookup to find the real filename.
* gutenberg results have a deterministic cache URL.
* sobooks/jiumodiary/manual_link results aren't downloadable here; we tell
  the user to open the page instead.

We try `aria2c` first if it's on PATH (for chunked, parallel downloads),
otherwise fall back to a streaming Python urlopen() — no extra deps.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import Any

# Make sibling imports work when invoked as a script.
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, load  # noqa: E402
from library import Library, hash_file  # noqa: E402
from sources import HttpContext  # noqa: E402


_SAFE_RE = re.compile(r"[^\w\s\-_.()\[\]一-鿿]+", re.UNICODE)


def _sanitize_filename(title: str, ext: str | None) -> str:
    base = _SAFE_RE.sub(" ", title).strip()
    base = re.sub(r"\s+", " ", base)[:120].rstrip(" .")
    if not base:
        base = "untitled"
    if ext:
        return f"{base}.{ext.lower()}"
    return base


def _unique_path(root: Path, name: str) -> Path:
    candidate = root / name
    if not candidate.exists():
        return candidate
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    for i in range(2, 1000):
        c = root / (f"{stem} ({i}).{ext}" if ext else f"{stem} ({i})")
        if not c.exists():
            return c
    raise FileExistsError(f"too many collisions for {name}")


def _aria2_available() -> bool:
    return shutil.which("aria2c") is not None


def _download_via_aria2(url: str, out_dir: Path, out_name: str, *, proxy: str | None) -> Path:
    cmd = [
        "aria2c",
        "--continue=true",
        "--max-connection-per-server=8",
        "--split=8",
        "--min-split-size=1M",
        f"--out={out_name}",
        f"--dir={out_dir}",
        "--allow-overwrite=false",
        "--auto-file-renaming=false",
        url,
    ]
    if proxy:
        cmd.insert(1, f"--all-proxy={proxy}")
    subprocess.run(cmd, check=True)
    return out_dir / out_name


def _download_via_python(url: str, out_path: Path, *, ctx: HttpContext) -> Path:
    """Streaming download with a 64 KiB buffer so we don't blow up RAM."""
    import urllib.request

    opener = ctx.opener()
    req = urllib.request.Request(url, headers={
        "User-Agent": ctx.user_agent,
        "Accept": "*/*",
    })
    with opener.open(req, timeout=ctx.timeout * 4) as r, out_path.open("wb") as f:
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return out_path


def _resolve_source_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    info = item.get("download_info") or {}
    type_ = info.get("type")
    if type_ == "direct":
        return info.get("url")
    if type_ == "manual_link":
        return None
    src = item.get("source")
    if not src:
        return None
    try:
        mod = importlib.import_module(f"sources.{src}")
    except Exception:
        return None
    fn = getattr(mod, "resolve_download_url", None)
    if fn is None:
        return None
    try:
        return fn(item, ctx=ctx)
    except Exception:
        return None


def download_item(item: dict[str, Any], *, cfg: Config, out: Path | None = None) -> dict[str, Any]:
    """Resolve, download, hash, and register a single result.

    Returns the library entry that was written. Raises on hard failures
    (resolution failed, HTTP error, file write error). The caller (the
    skill) is responsible for catching and showing the error to the user.
    """
    info = item.get("download_info") or {}
    if info.get("type") == "manual_link":
        return {
            "status": "manual_link",
            "url": info.get("url") or item.get("source_url"),
            "note": info.get("note") or "Open the page in a browser to download.",
        }

    ctx = HttpContext(proxy=cfg.proxy, timeout=cfg.request_timeout, user_agent=cfg.user_agent)
    resolved_url = _resolve_source_url(item, ctx=ctx)
    if not resolved_url:
        raise RuntimeError(f"could not resolve a direct download URL for source={item.get('source')}")

    library_root = Path(cfg.library_root)
    library_root.mkdir(parents=True, exist_ok=True)

    if out:
        target = Path(out).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
    else:
        name = _sanitize_filename(item.get("title") or "untitled", item.get("format"))
        target = _unique_path(library_root, name)

    # Per-source proxy decisions: jiumodiary/sobooks etc. never reach this
    # branch (manual_link short-circuits above), but archive.org's CDN can
    # be slow through a proxy, so we don't force one for that source.
    proxy_for_dl = cfg.proxy
    if item.get("source") == "archive_org":
        proxy_for_dl = cfg.proxy  # let the proxy stay; archive.org is fine

    if _aria2_available():
        downloaded = _download_via_aria2(resolved_url, target.parent, target.name, proxy=proxy_for_dl)
    else:
        downloaded = _download_via_python(resolved_url, target, ctx=ctx)

    if not downloaded.exists() or downloaded.stat().st_size == 0:
        raise RuntimeError(f"download produced empty file at {downloaded}")

    md5 = hash_file(downloaded, "md5")

    lib = Library.open(cfg)
    entry = {
        "title": item.get("title"),
        "authors": item.get("authors"),
        "year": item.get("year"),
        "language": item.get("language"),
        "format": item.get("format") or downloaded.suffix.lstrip(".").lower() or None,
        "size_bytes": downloaded.stat().st_size,
        "md5": md5,
        "publisher": item.get("publisher"),
        "isbn": item.get("isbn"),
        "source": item.get("source"),
        "source_url": item.get("source_url"),
        "resolved_url": resolved_url,
        "file_path": str(downloaded),
        "tags": [],
    }
    written = lib.add(entry)
    return {"status": "ok", "entry": written, "absolute_path": str(downloaded)}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Download a search result and update library.json.")
    p.add_argument(
        "--item-json",
        help="JSON string with the chosen result (the dict from search.py results[]).",
    )
    p.add_argument(
        "--item-stdin", action="store_true",
        help="Read the item JSON from stdin instead of --item-json.",
    )
    p.add_argument("--out", help="Override output path. Default: library_root/<title>.<ext>.")
    args = p.parse_args(argv)

    if args.item_stdin:
        item = json.loads(sys.stdin.read())
    elif args.item_json:
        item = json.loads(args.item_json)
    else:
        print("must pass --item-json or --item-stdin", file=sys.stderr)
        return 2

    cfg = load()
    try:
        result = download_item(item, cfg=cfg, out=Path(args.out) if args.out else None)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"{type(e).__name__}: {e}"}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
