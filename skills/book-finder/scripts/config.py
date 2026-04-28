"""Configuration management for book-finder.

First-run experience:
- The skill calls `ensure_config()`. If `~/.config/book-finder/config.json`
  is missing, this writes a default config and returns it together with
  a flag indicating that the user should be informed and given the chance
  to customize.

Defaults are tuned for a macOS user behind a Clash-style proxy on
127.0.0.1:7897, but every field is overridable.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "book-finder"
CONFIG_PATH = CONFIG_DIR / "config.json"
DEFAULT_LIBRARY_ROOT = Path.home() / "Downloads" / "books"


def _resolved_config_path() -> Path:
    """Honor `BOOK_FINDER_CONFIG` env var so evals (and any test harness)
    can swap in an isolated config without touching the user's real one.
    """
    override = os.environ.get("BOOK_FINDER_CONFIG")
    return Path(override).expanduser() if override else CONFIG_PATH


# Source IDs the skill knows about. Sources marked False are kept around
# (the modules exist) but disabled by default because they are unreliable
# from mainland China without a working proxy. The user can toggle them in
# config.json.
DEFAULT_SOURCES_ENABLED: dict[str, bool] = {
    "libgen": True,         # libgen.li / libgen.bz mirrors
    "archive_org": True,    # archive.org advanced search API
    "gutenberg": True,      # gutenberg.org search page
    "jiumodiary": True,     # 鸠摩搜书 (Chinese)
    "sobooks": True,        # sobooks.cc (Chinese)
    "annas_archive": False,  # often unreachable; flip on if you can hit it
}

# Lower index = higher priority when picking a default version.
DEFAULT_FORMAT_PRIORITY: list[str] = ["epub", "pdf", "mobi", "azw3", "txt"]


@dataclass
class Config:
    version: int = 1
    library_root: str = str(DEFAULT_LIBRARY_ROOT)
    library_json: str = ""  # filled in `__post_init__` if blank
    format_priority: list[str] = field(default_factory=lambda: list(DEFAULT_FORMAT_PRIORITY))
    preferred_languages: list[str] = field(default_factory=lambda: ["zh", "en"])
    sources_enabled: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_SOURCES_ENABLED))
    proxy: str | None = "http://127.0.0.1:7897"  # set to null to disable
    request_timeout: int = 15
    download_timeout: int = 600
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    annas_archive_api_key: str | None = None  # only used when source enabled

    def __post_init__(self) -> None:
        if not self.library_json:
            self.library_json = str(Path(self.library_root) / "library.json")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _write_default(path: Path) -> Config:
    cfg = Config()
    path.parent.mkdir(parents=True, exist_ok=True)
    Path(cfg.library_root).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))
    return cfg


def load(path: Path | None = None) -> Config:
    if path is None:
        path = _resolved_config_path()
    """Load config from disk. Falls back to defaults for missing keys."""
    if not path.exists():
        return _write_default(path)
    raw = json.loads(path.read_text())
    # Be permissive: unknown keys are ignored, missing keys filled by defaults.
    cfg = Config()
    for key, value in raw.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    cfg.__post_init__()
    return cfg


def ensure_config() -> tuple[Config, bool]:
    """Return (config, is_first_run).

    `is_first_run` is True when the config file did not previously exist.
    The skill uses this to surface a one-time prompt to the user so they
    can override the defaults before searches start.
    """
    first_run = not CONFIG_PATH.exists()
    cfg = load(CONFIG_PATH)
    return cfg, first_run


def save(cfg: Config) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path(cfg.library_root).mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False))


# CLI for the skill / user to inspect or initialize the config without
# touching JSON by hand: `python config.py show | init | edit KEY VALUE`.
def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("show", "get"):
        cfg, first = ensure_config()
        out = {"first_run": first, "config_path": str(CONFIG_PATH), **cfg.to_dict()}
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if argv[0] == "init":
        cfg, first = ensure_config()
        print(json.dumps({
            "first_run": first,
            "config_path": str(CONFIG_PATH),
            "library_root": cfg.library_root,
        }, indent=2, ensure_ascii=False))
        return 0
    if argv[0] == "edit" and len(argv) >= 3:
        key, value = argv[1], argv[2]
        cfg = load(CONFIG_PATH)
        if not hasattr(cfg, key):
            print(f"unknown key: {key}", file=sys.stderr)
            return 2
        # Coerce booleans and lists for convenience.
        current = getattr(cfg, key)
        if isinstance(current, bool):
            value = value.lower() in ("1", "true", "yes", "on")
        elif isinstance(current, list):
            value = [v.strip() for v in value.split(",") if v.strip()]
        elif isinstance(current, int) and not isinstance(current, bool):
            value = int(value)
        setattr(cfg, key, value)
        save(cfg)
        print(json.dumps({"updated": key, "value": value}, ensure_ascii=False))
        return 0
    print("usage: config.py [show|init|edit KEY VALUE]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
