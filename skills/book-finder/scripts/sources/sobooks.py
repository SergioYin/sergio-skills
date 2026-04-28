"""sobooks.cc — Chinese ebook aggregator (reference-only).

sobooks lists download links indirectly: the search page returns article
URLs, and each article embeds links to 百度网盘 / 夸克网盘 with extraction
codes. We can't `wget` those without a logged-in browser session, so we
deliberately don't try.

Instead we surface each hit as a `manual_link` result. The download step
will skip these and tell the user to open the page in a browser. This keeps
sobooks useful for Chinese books while being honest about the constraint.
"""

from __future__ import annotations

import re
import urllib.parse
from html import unescape
from typing import Any

from . import HttpContext, make_result


SOURCE = "sobooks"
BASE = "https://sobooks.cc"


def search(query: str, *, ctx: HttpContext, limit: int = 10) -> list[dict[str, Any]]:
    url = f"{BASE}/?s={urllib.parse.quote(query)}"
    try:
        html = ctx.fetch(url)
    except Exception:
        return []

    # Search results live under `<article>` blocks; each contains an <h3>
    # with the article title and link. Authors appear in a sub-paragraph
    # like <p class="cat">作者: 刘慈欣 ...</p> on some templates.
    out: list[dict[str, Any]] = []
    article_re = re.compile(
        r"<article[^>]*>(.*?)</article>",
        re.DOTALL | re.IGNORECASE,
    )
    title_re = re.compile(
        r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    author_re = re.compile(r"作者[:：]\s*([^<\n]+)")

    for block in article_re.findall(html)[:limit]:
        title_match = title_re.search(block)
        if not title_match:
            continue
        href = title_match.group(1)
        title = unescape(re.sub(r"<[^>]+>", "", title_match.group(2))).strip()
        if not href.startswith("http"):
            href = urllib.parse.urljoin(BASE, href)

        authors: list[str] = []
        a = author_re.search(block)
        if a:
            authors = [s.strip() for s in re.split(r"[/、,，]", a.group(1)) if s.strip()]

        out.append(make_result(
            title=title,
            authors=authors,
            language="zh",
            fmt=None,  # we don't know format until the user opens the page
            source=SOURCE,
            source_url=href,
            download_info={
                "type": "manual_link",
                "url": href,
                "note": "Opens in browser. Download links use 百度网盘/夸克网盘 with extraction codes.",
            },
        ))
    return out


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    """sobooks doesn't expose direct download URLs we can fetch."""
    return None
