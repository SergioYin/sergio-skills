"""Multi-source book search — fan out, dedupe, rank, emit JSON.

Usage from the skill:

    python scripts/search.py "三体" --limit 30 --json

Design notes:

* Each source runs in its own thread (`ThreadPoolExecutor`) so a slow or
  hanging mirror can't block the whole search. We bound per-source time
  via the HTTP timeout in `HttpContext`.
* Results are deduplicated within a single (title, author) bucket; within
  a bucket we keep the best-format version per source so libgen.li's EPUB
  and PDF of the same book both stay visible.
* Final ranking favours the user's preferred languages and the configured
  `format_priority`. Sources are not re-ranked — every source's hits stay
  visible; format priority only affects ordering within a bucket.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

# Allow `python search.py` to import sibling modules.
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, ensure_config  # noqa: E402
from sources import HttpContext  # noqa: E402


# Source module names to import; matches keys in `Config.sources_enabled`.
SOURCE_MODULES = ["libgen", "archive_org", "gutenberg", "sobooks", "jiumodiary", "annas_archive"]


def _normalize(s: str) -> str:
    """Loose comparison key: NFKD-fold, lowercase, strip punctuation/whitespace."""
    s = unicodedata.normalize("NFKD", s).lower()
    s = re.sub(r"[^a-z0-9一-鿿]+", "", s)
    return s


def _bucket_key(item: dict[str, Any]) -> str:
    """Group results by (normalized title, normalized first author).

    Different sources spell author lists differently ("Cixin Liu" vs
    "Liu Cixin", "刘慈欣" with/without honorifics). Using just the first
    author + title is loose but works in practice; downstream, the user
    sees one row per source/format anyway.
    """
    title = _normalize(item.get("title") or "")
    authors = item.get("authors") or []
    first_author = _normalize(authors[0]) if authors else ""
    return f"{title}|{first_author}"


def _format_rank(fmt: str | None, priority: list[str]) -> int:
    if not fmt:
        return len(priority) + 1
    try:
        return priority.index(fmt.lower())
    except ValueError:
        return len(priority)


def _language_rank(lang: str | None, preferred: list[str]) -> int:
    if not lang:
        return len(preferred) + 1
    norm = lang.lower()[:2]
    for i, p in enumerate(preferred):
        if p.lower()[:2] == norm or p.lower() in lang.lower():
            return i
    return len(preferred)


def search_all(
    query: str,
    *,
    cfg: Config,
    limit_per_source: int = 25,
) -> dict[str, Any]:
    ctx = HttpContext(
        proxy=cfg.proxy,
        timeout=cfg.request_timeout,
        user_agent=cfg.user_agent,
    )

    enabled = [m for m in SOURCE_MODULES if cfg.sources_enabled.get(m, False)]
    raw_results: list[dict[str, Any]] = []
    errors: dict[str, str] = {}

    def call_source(name: str) -> tuple[str, list[dict[str, Any]] | Exception]:
        try:
            mod = importlib.import_module(f"sources.{name}")
        except Exception as e:
            return name, e
        try:
            hits = mod.search(query, ctx=ctx, limit=limit_per_source)
            return name, hits or []
        except Exception as e:
            return name, e

    with ThreadPoolExecutor(max_workers=max(1, len(enabled))) as pool:
        futures = {pool.submit(call_source, name): name for name in enabled}
        for f in as_completed(futures):
            name, payload = f.result()
            if isinstance(payload, Exception):
                errors[name] = f"{type(payload).__name__}: {payload}"
            else:
                raw_results.extend(payload)

    # Dedupe: keep one row per (bucket, source, format), prefer richer metadata.
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in raw_results:
        key = (
            _bucket_key(item),
            item.get("source") or "",
            (item.get("format") or "") or "_",
        )
        prev = seen.get(key)
        if not prev or _richness(item) > _richness(prev):
            seen[key] = item

    deduped = list(seen.values())

    # Sort: language preference, then format priority, then size desc, then year desc.
    pref_langs = [l.lower() for l in cfg.preferred_languages]
    fmt_prio = [f.lower() for f in cfg.format_priority]

    def sort_key(it: dict[str, Any]) -> tuple:
        return (
            _language_rank(it.get("language"), pref_langs),
            _format_rank(it.get("format"), fmt_prio),
            -(it.get("size_bytes") or 0),
            -int(it.get("year") or 0) if (it.get("year") or "").isdigit() else 0,
            it.get("source") or "",
        )

    deduped.sort(key=sort_key)

    return {
        "query": query,
        "result_count": len(deduped),
        "errors": errors,
        "results": deduped,
    }


def _richness(item: dict[str, Any]) -> int:
    """Score how "complete" a result is, used as a tiebreaker on dedupe."""
    score = 0
    if item.get("size_bytes"):
        score += 2
    if item.get("year"):
        score += 1
    if item.get("language"):
        score += 1
    if item.get("md5"):
        score += 2
    if item.get("authors"):
        score += 1
    return score


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Search for a book across enabled sources.")
    p.add_argument("query", help="Book title (and optionally author).")
    p.add_argument("--limit", type=int, default=25, help="Per-source result cap.")
    p.add_argument("--json", action="store_true", help="Emit raw JSON (default: human-readable).")
    args = p.parse_args(argv)

    cfg, first_run = ensure_config()
    payload = search_all(args.query, cfg=cfg, limit_per_source=args.limit)
    payload["first_run"] = first_run
    payload["config_path"] = str(Path("~/.config/book-finder/config.json").expanduser())

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    # Human-readable: Claude reads this and renders it for the user. The
    # JSON format is generally preferred because Claude can pick fields
    # cleanly; this branch is just for ad-hoc debugging from the shell.
    if first_run:
        print(f"# First run — wrote config at {payload['config_path']}")
        print(f"# Library root defaults to {cfg.library_root}")
        print()
    if payload["errors"]:
        print("# Source errors (the rest of the search continued):")
        for src, err in payload["errors"].items():
            print(f"#   {src}: {err}")
        print()
    print(f"Query: {args.query}  ·  {payload['result_count']} results\n")
    for i, item in enumerate(payload["results"], 1):
        title = item["title"]
        authors = ", ".join(item.get("authors") or []) or "—"
        year = item.get("year") or "—"
        lang = item.get("language") or "—"
        fmt = (item.get("format") or "—").upper()
        size = item.get("size_bytes")
        size_s = f"{size / 1024 / 1024:.1f} MB" if size else "—"
        src = item.get("source")
        print(f"[{i:>2}] {title}  —  {authors}  ({year}) [{lang}]")
        print(f"     {fmt} · {size_s} · {src}  ({item.get('source_url')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
