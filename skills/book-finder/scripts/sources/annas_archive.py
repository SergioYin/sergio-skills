"""Anna's Archive — disabled by default.

We left full search/parse logic out because every probed mirror failed SSL
during testing. If a working network path emerges (different proxy rules,
new mirror, official API key), this module is the obvious place to add it
without touching the rest of the skill.

The function signatures below match the rest of the source modules so
search.py can wire it up uniformly when the user flips it on.
"""

from __future__ import annotations

from typing import Any

from . import HttpContext


SOURCE = "annas_archive"


def search(query: str, *, ctx: HttpContext, limit: int = 25) -> list[dict[str, Any]]:
    return []


def resolve_download_url(item: dict[str, Any], *, ctx: HttpContext) -> str | None:
    return None
