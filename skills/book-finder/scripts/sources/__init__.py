"""Source modules: each exposes `search(query, *, ctx)` returning a list of
`Result` dicts. Modules are intentionally small so a broken upstream affects
only its own file.
"""

from __future__ import annotations

import gzip
import io
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


# Stable shape every source must produce.
ResultDict = dict[str, Any]


@dataclass
class HttpContext:
    """Per-request context shared across sources.

    Carrying the proxy and timeout here avoids each source reimplementing the
    same boilerplate. Sources that need their own headers can extend this.
    """

    proxy: str | None
    timeout: int
    user_agent: str
    verify_ssl: bool = False  # libgen.li often serves expired certs

    def opener(self) -> urllib.request.OpenerDirector:
        handlers: list[urllib.request.BaseHandler] = []
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
        ctx = ssl._create_unverified_context() if not self.verify_ssl else ssl.create_default_context()
        handlers.append(urllib.request.HTTPSHandler(context=ctx))
        return urllib.request.build_opener(*handlers)

    def fetch(self, url: str, *, headers: dict[str, str] | None = None) -> str:
        req = urllib.request.Request(url, headers={
            "User-Agent": self.user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "gzip",
            **(headers or {}),
        })
        opener = self.opener()
        with opener.open(req, timeout=self.timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            # Best-effort decode; sources may serve gbk for Chinese sites.
            for enc in ("utf-8", "gb18030", "latin-1"):
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace")


def make_result(
    *,
    title: str,
    source: str,
    source_url: str,
    download_info: dict[str, Any],
    authors: list[str] | None = None,
    year: str | None = None,
    language: str | None = None,
    fmt: str | None = None,
    size_bytes: int | None = None,
    md5: str | None = None,
    publisher: str | None = None,
    isbn: str | None = None,
    extra: dict[str, Any] | None = None,
) -> ResultDict:
    """Constructor for the unified result shape.

    `download_info` carries everything `download.py` needs to fetch this
    specific file: typically `{"type": "direct"|"libgen_resolver"|"archive_item"|...,
    "url": "...", ...source-specific fields}`. Keeping it source-tagged means
    download logic lives next to the source it knows how to crawl.
    """
    return {
        "title": title.strip(),
        "authors": authors or [],
        "year": year,
        "language": language,
        "format": (fmt or "").lower() or None,
        "size_bytes": size_bytes,
        "md5": md5,
        "publisher": publisher,
        "isbn": isbn,
        "source": source,
        "source_url": source_url,
        "download_info": download_info,
        "extra": extra or {},
    }


def safe_int(s: Any) -> int | None:
    """Best-effort string-to-int. Used for sizes and years parsed from HTML."""
    if s is None:
        return None
    try:
        return int(str(s).strip())
    except (ValueError, TypeError):
        return None


def parse_size_to_bytes(s: str | None) -> int | None:
    """Turn '2.4 MB', '512KB', '1,200,000' into a byte count.

    Suffixes must be checked longest-first: 'mb' shares its tail with 'b',
    so a naive iteration would match 'b' first and parse "2.4 m" as a number.
    """
    if not s:
        return None
    text = s.strip().replace(",", "").lower()
    units = [("gb", 1024**3), ("mb", 1024**2), ("kb", 1024), ("b", 1)]
    for suffix, mult in units:
        if text.endswith(suffix):
            try:
                return int(float(text[: -len(suffix)].strip()) * mult)
            except ValueError:
                return None
    try:
        return int(float(text))
    except ValueError:
        return None
