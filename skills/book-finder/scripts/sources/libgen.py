"""Library Genesis (libgen.li mirror).

Why libgen.li specifically: among the LibGen mirrors we probed (.is, .rs,
.li, .bz, .gs), libgen.li is the only one reliably reachable from mainland
China without help, and it carries the full fiction+nonfiction database.
libgen.bz is kept as a fallback but uses the same parser.

Search results live in `/index.php?req=...&res=25`. The page renders an
HTML table identified by `tablelibgen`; each row encodes one book with the
columns: ID, Title, Author(s), Publisher, Year, Lang, Pages, Size, Ext,
plus a "Mirrors" cell with anchors to per-record detail pages. The detail
page (`ads.php?md5=...`) carries the actual GET link plus a few mirrors.
"""

from __future__ import annotations

import re
import urllib.parse
from html import unescape
from typing import Any

from . import HttpContext, make_result, parse_size_to_bytes


SOURCE = "libgen"
HOSTS = ["https://libgen.li", "https://libgen.bz"]


def _build_url(host: str, query: str, limit: int) -> str:
    params = {
        "req": query,
        "columns[]": "t",  # search title and author by default; libgen ORs them
        "objects[]": "f",
        "topics[]": "l",   # libgen non-fiction
        "res": str(limit),
        "covers": "on",
    }
    # urlencode doesn't like list-typed keys repeated unless we pass tuples
    pairs = []
    for k, v in params.items():
        pairs.append(f"{urllib.parse.quote(k)}={urllib.parse.quote(v)}")
    return f"{host}/index.php?" + "&".join(pairs)


_TABLE_RE = re.compile(r'<table[^>]*id="tablelibgen"[^>]*>(.*?)</table>', re.DOTALL | re.IGNORECASE)
_ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL | re.IGNORECASE)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_ADS_HREF_RE = re.compile(r'href="(/?ads\.php\?md5=[a-fA-F0-9]+)"', re.IGNORECASE)
_GET_LINK_RE = re.compile(r'href="(get\.php[^"]+)"', re.IGNORECASE)
_MD5_FROM_HREF = re.compile(r"md5=([a-fA-F0-9]+)", re.IGNORECASE)


def _strip(html: str) -> str:
    return unescape(_TAG_RE.sub(" ", html)).strip()


def _parse_row(host: str, row_html: str) -> dict[str, Any] | None:
    cells = _CELL_RE.findall(row_html)
    # Actual libgen.li layout (verified against live HTML):
    #   [0] cover thumbnail (img inside an edition.php link)
    #   [1] title cell (rich: anchor with title text + tooltip + meta badges)
    #   [2] author(s)
    #   [3] publisher
    #   [4] year
    #   [5] language
    #   [6] pages
    #   [7] size (anchor-wrapped, e.g. `<a>3 MB</a>`)
    #   [8] extension (e.g. epub, pdf, cbr)
    #   [9] mirrors (anchors to /ads.php?md5=..., randombook, etc.)
    if len(cells) < 10:
        return None

    md5_match = _ADS_HREF_RE.search(cells[9])
    if not md5_match:
        return None
    ads_href = md5_match.group(1)
    md5 = (_MD5_FROM_HREF.search(ads_href) or [None, None])[1]
    detail_url = urllib.parse.urljoin(host + "/", ads_href)

    # Title is the inner text of the anchor whose href is `edition.php?id=...`.
    # The anchor's `title="..."` attribute often contains `<br>`, so a naive
    # `[^>]*` regex matches inside that attribute and stops too early. We anchor
    # on the href being the *last* attribute (libgen always renders it last)
    # and require `\s*>` to close the tag cleanly.
    title_anchor = re.search(r'href="edition\.php[^"]+"\s*>(.*?)</a>', cells[1], re.DOTALL)
    title = _strip(title_anchor.group(1)) if title_anchor else _strip(cells[1])

    raw_authors = _strip(cells[2])
    authors: list[str] = []
    if raw_authors:
        # libgen separates multiple authors with ';' typically; fall back to ','
        parts = raw_authors.split(";") if ";" in raw_authors else raw_authors.split(",")
        authors = [a.strip() for a in parts if a.strip()]

    publisher = _strip(cells[3]) or None
    year = _strip(cells[4]) or None
    language = _strip(cells[5]) or None
    size_str = _strip(cells[7]) or None
    ext = _strip(cells[8]).lower() or None

    return make_result(
        title=title,
        authors=authors,
        year=year,
        language=language.lower() if language else None,
        fmt=ext,
        size_bytes=parse_size_to_bytes(size_str),
        md5=md5,
        publisher=publisher,
        source=SOURCE,
        source_url=detail_url,
        download_info={
            "type": "libgen_resolver",
            "host": host,
            "md5": md5,
            "detail_url": detail_url,
        },
    )


def search(query: str, *, ctx: HttpContext, limit: int = 25) -> list[dict[str, Any]]:
    """Try each mirror until one succeeds; aggregate results from the first."""
    last_err: Exception | None = None
    for host in HOSTS:
        url = _build_url(host, query, limit)
        try:
            html = ctx.fetch(url)
        except Exception as e:  # network problems are expected; try next mirror
            last_err = e
            continue
        table_match = _TABLE_RE.search(html)
        if not table_match:
            continue
        rows = _ROW_RE.findall(table_match.group(1))
        results: list[dict[str, Any]] = []
        for row in rows[1:]:  # row 0 is the header
            try:
                parsed = _parse_row(host, row)
            except Exception:
                continue
            if parsed:
                results.append(parsed)
        return results
    if last_err:
        # Don't crash the whole search if one source is down; let caller decide.
        return []
    return []


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    """Two-step resolution: open the detail page, find a `get.php?...&md5=...` link.

    libgen rotates between several download endpoints (`/ads.php` page, the
    `get.php` direct link, and a few rotating mirrors like cdn1.booksdl.org).
    The detail page is the source of truth for what's currently live.
    """
    info = item.get("download_info") or {}
    if info.get("type") != "libgen_resolver":
        return None
    detail_url = info.get("detail_url")
    if not detail_url:
        return None
    try:
        html = ctx.fetch(detail_url)
    except Exception:
        return None
    # Prefer get.php links; pick the first that includes the md5 to be safe.
    md5 = (info.get("md5") or "").lower()
    for href in _GET_LINK_RE.findall(html):
        if md5 and md5 in href.lower():
            return urllib.parse.urljoin(info["host"] + "/", unescape(href))
    # Some pages list mirrors as <a href="https://cdn1.booksdl.lc/get.php?...">; absolute URLs
    abs_get = re.search(r'href="(https?://[^"]+get\.php[^"]+)"', html, re.IGNORECASE)
    if abs_get:
        return unescape(abs_get.group(1))
    return None
