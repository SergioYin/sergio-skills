"""鸠摩搜书 (jiumodiary.com) — meta-search engine, JS-rendered.

jiumodiary aggregates many Chinese ebook sources but renders all results
client-side via JavaScript, so a plain HTTP fetch returns an empty shell.
A proper integration would require a headless browser.

For now we ship this as a `manual_link` source: we send the user to the
search URL so they can browse results in a browser. Disabled by default in
config; flip to True once a server-rendered endpoint is found or we add
playwright/puppeteer support.
"""

from __future__ import annotations

import urllib.parse
from typing import Any

from . import HttpContext, make_result


SOURCE = "jiumodiary"
BASE = "https://www.jiumodiary.com"


def search(query: str, *, ctx: HttpContext, limit: int = 1) -> list[dict[str, Any]]:
    # We can't fetch results without JS. Surface a single "search portal"
    # result so the user sees the option and can click through.
    return [make_result(
        title=f"鸠摩搜书 · {query}",
        language="zh",
        source=SOURCE,
        source_url=f"{BASE}/?q={urllib.parse.quote(query)}",
        download_info={
            "type": "manual_link",
            "url": f"{BASE}/?q={urllib.parse.quote(query)}",
            "note": "Meta-search — opens jiumodiary in browser.",
        },
    )]


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    return None
