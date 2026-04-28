"""Internet Archive — public-domain texts and openly-shared scans.

archive.org exposes a stable JSON API at /advancedsearch.php. Each item has
an `identifier`; the file list per item is at `/metadata/<identifier>` and
download URLs are `https://archive.org/download/<identifier>/<filename>`.

We expand each search hit into one Result per format we care about, so
when the caller asks for, e.g., "alice in wonderland" they see EPUB and PDF
as separate options ranked together with libgen results.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from . import HttpContext, make_result


SOURCE = "archive_org"
BASE = "https://archive.org"


# Map archive.org's "format" labels to our canonical extensions.
FORMAT_TO_EXT: dict[str, str] = {
    "EPUB": "epub",
    "Text PDF": "pdf",
    "PDF": "pdf",
    "Plain Text": "txt",
    "DjVu": "djvu",
    "DjVuTXT": "txt",
    "Kindle": "mobi",
}

# Formats we'll surface to the user. ACS / LCP encrypted files are useless
# without a DRM key, so we skip them; same for OCR JSON, page tiles, etc.
USEFUL_EXTS = {"epub", "pdf", "mobi", "azw3", "txt"}


def _build_search_url(query: str, limit: int) -> str:
    q = f'title:"{query}" AND mediatype:texts'
    fields = ["identifier", "title", "creator", "year", "language", "format"]
    parts = [
        ("q", q),
        ("output", "json"),
        ("rows", str(limit)),
    ] + [("fl[]", f) for f in fields]
    return f"{BASE}/advancedsearch.php?" + urllib.parse.urlencode(parts)


_FILE_NAME_RE = re.compile(r"[^A-Za-z0-9._\- ]+")


def _list_item_files(identifier: str, ctx: HttpContext) -> list[dict[str, Any]]:
    """Get the file list for a single item via the metadata endpoint."""
    url = f"{BASE}/metadata/{urllib.parse.quote(identifier)}"
    try:
        text = ctx.fetch(url)
        data = json.loads(text)
    except Exception:
        return []
    return data.get("files") or []


def search(query: str, *, ctx: HttpContext, limit: int = 10) -> list[dict[str, Any]]:
    try:
        text = ctx.fetch(_build_search_url(query, limit))
        payload = json.loads(text)
    except Exception:
        return []

    docs = payload.get("response", {}).get("docs", [])
    out: list[dict[str, Any]] = []
    for doc in docs:
        identifier = doc.get("identifier")
        if not identifier:
            continue
        title = doc.get("title") or identifier
        creator = doc.get("creator")
        if isinstance(creator, list):
            authors = creator
        elif creator:
            authors = [creator]
        else:
            authors = []
        year = str(doc.get("year")) if doc.get("year") else None
        language = doc.get("language")
        if isinstance(language, list):
            language = language[0] if language else None

        # The advancedsearch `format` is a coarse list (e.g. ["EPUB","Text PDF"]).
        # That tells us what files exist but not their sizes or names. For a
        # responsive UX we surface one row per ext we care about, then resolve
        # the actual filename lazily at download time. This keeps search fast
        # (1 HTTP per query) instead of N+1.
        listed_formats = doc.get("format") or []
        seen_exts: set[str] = set()
        for f in listed_formats:
            ext = FORMAT_TO_EXT.get(f)
            if not ext or ext not in USEFUL_EXTS or ext in seen_exts:
                continue
            seen_exts.add(ext)
            out.append(make_result(
                title=title,
                authors=authors,
                year=year,
                language=(language or "").lower()[:3] if language else None,
                fmt=ext,
                source=SOURCE,
                source_url=f"{BASE}/details/{identifier}",
                download_info={
                    "type": "archive_item",
                    "identifier": identifier,
                    "ext": ext,
                },
            ))
    return out


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    info = item.get("download_info") or {}
    if info.get("type") != "archive_item":
        return None
    identifier = info["identifier"]
    ext = info["ext"]
    files = _list_item_files(identifier, ctx)
    # Prefer a file whose extension matches and whose name doesn't include
    # words like "encrypted" / "djvu" (which slipped past our format filter).
    candidates = []
    for f in files:
        name = f.get("name", "")
        lower = name.lower()
        if not lower.endswith(f".{ext}"):
            continue
        if "encrypted" in lower or "_lcp" in lower or "_acs" in lower:
            continue
        size = int(f.get("size") or 0)
        candidates.append((size, name))
    if not candidates:
        return None
    candidates.sort(reverse=True)  # biggest matching file = the actual book
    name = candidates[0][1]
    return f"{BASE}/download/{urllib.parse.quote(identifier)}/{urllib.parse.quote(name)}"
