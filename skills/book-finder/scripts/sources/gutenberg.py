"""Project Gutenberg — fully public-domain books in many formats.

The Gutendex JSON API (gutendex.com) was unreachable during probing, so we
fall back to scraping the canonical search page on gutenberg.org and using
the well-known cache URL pattern:

    https://www.gutenberg.org/cache/epub/<id>/pg<id>.epub
    https://www.gutenberg.org/files/<id>/<id>-0.txt

Each ebook page also exposes formats explicitly, but we save the round-trip
by trusting the cache pattern (which Gutenberg has guaranteed for years).
"""

from __future__ import annotations

import re
import urllib.parse
from html import unescape
from typing import Any

from . import HttpContext, make_result


SOURCE = "gutenberg"
BASE = "https://www.gutenberg.org"


_RESULT_RE = re.compile(
    r'<li class="booklink">.*?'
    r'<a [^>]*href="/ebooks/(\d+)"[^>]*>'
    r'.*?<span class="title">(.*?)</span>'
    r'(?:.*?<span class="subtitle">(.*?)</span>)?'
    r'.*?<span class="subtitle">(.*?)</span>'
    r'.*?</a>',
    re.DOTALL,
)


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s)).strip()


def search(query: str, *, ctx: HttpContext, limit: int = 10) -> list[dict[str, Any]]:
    url = f"{BASE}/ebooks/search/?query={urllib.parse.quote_plus(query)}"
    try:
        html = ctx.fetch(url)
    except Exception:
        return []

    # The search page lists results as <li class="booklink">. We pull each
    # block out and then extract the bits we need; the regex above is too
    # strict so we'll do a two-stage pass.
    out: list[dict[str, Any]] = []
    blocks = re.findall(r'<li class="booklink">(.*?)</li>', html, re.DOTALL)
    for block in blocks[:limit]:
        m = re.search(r'href="/ebooks/(\d+)"', block)
        if not m:
            continue
        ebook_id = m.group(1)
        title_match = re.search(r'<span class="title">(.*?)</span>', block, re.DOTALL)
        author_match = re.search(r'<span class="subtitle">(.*?)</span>', block, re.DOTALL)
        title = _strip_tags(title_match.group(1)) if title_match else f"Gutenberg #{ebook_id}"
        authors = []
        if author_match:
            txt = _strip_tags(author_match.group(1))
            if txt and txt.lower() != "no title":
                authors = [a.strip() for a in re.split(r"[;,]", txt) if a.strip()]

        # Surface EPUB and TXT for each hit. Gutenberg has both for ~all
        # English titles; we don't know about other languages without
        # inspecting the per-item page, but the URL fetch will 404 cleanly
        # if the format is missing.
        for ext in ("epub", "txt"):
            out.append(make_result(
                title=title,
                authors=authors,
                language="en",  # Gutenberg is overwhelmingly English; corrected at download time
                fmt=ext,
                source=SOURCE,
                source_url=f"{BASE}/ebooks/{ebook_id}",
                download_info={
                    "type": "gutenberg_cache",
                    "ebook_id": ebook_id,
                    "ext": ext,
                },
            ))
    return out


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    info = item.get("download_info") or {}
    if info.get("type") != "gutenberg_cache":
        return None
    eid = info["ebook_id"]
    ext = info["ext"]
    if ext == "epub":
        # `pg<id>.epub` is the modern URL; older `pg<id>-images.epub` also exists.
        return f"{BASE}/cache/epub/{eid}/pg{eid}.epub"
    if ext == "txt":
        return f"{BASE}/cache/epub/{eid}/pg{eid}.txt"
    if ext == "pdf":
        return f"{BASE}/cache/epub/{eid}/pg{eid}.pdf"
    return None
