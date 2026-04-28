"""Library metadata management — `library.json` lives at the library root.

This is the single source of truth for "what books do I have." Each entry
records canonical metadata plus how/where the file was acquired, so an
identical second download is detected and skipped, and so the user can
later answer "did I already grab this?" without scanning the filesystem.

Operations: `add`, `find`, `list`, `remove`. The CLI is meant to be called
by the SKILL.md workflow (`python library.py add ...`) after a successful
download, but is also useful standalone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make sibling imports work when invoked as a script.
sys.path.insert(0, str(Path(__file__).parent))

from config import Config, load  # noqa: E402


@dataclass
class Library:
    root: Path
    json_path: Path
    data: dict[str, Any]

    @classmethod
    def open(cls, cfg: Config) -> "Library":
        json_path = Path(cfg.library_json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        if json_path.exists():
            data = json.loads(json_path.read_text() or "{}")
        else:
            data = {"version": 1, "books": []}
        return cls(root=Path(cfg.library_root), json_path=json_path, data=data)

    def save(self) -> None:
        self.json_path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False)
        )

    def find_by_md5(self, md5: str) -> dict[str, Any] | None:
        for b in self.data.get("books", []):
            if b.get("md5") and b["md5"].lower() == md5.lower():
                return b
        return None

    def find_by_path(self, file_path: str) -> dict[str, Any] | None:
        rel = self._relative(file_path)
        for b in self.data.get("books", []):
            if b.get("file_path") == rel:
                return b
        return None

    def add(self, entry: dict[str, Any]) -> dict[str, Any]:
        entry = dict(entry)
        entry.setdefault("id", uuid.uuid4().hex)
        entry.setdefault("downloaded_at", datetime.now(timezone.utc).isoformat())
        if "file_path" in entry:
            entry["file_path"] = self._relative(entry["file_path"])
        self.data.setdefault("books", []).append(entry)
        self.save()
        return entry

    def remove(self, book_id: str) -> bool:
        before = len(self.data.get("books", []))
        self.data["books"] = [b for b in self.data.get("books", []) if b.get("id") != book_id]
        self.save()
        return len(self.data["books"]) < before

    def list_books(self) -> list[dict[str, Any]]:
        return list(self.data.get("books", []))

    def _relative(self, path: str) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(Path(path).resolve())


def hash_file(path: Path, algo: str = "md5", chunk: int = 1 << 16) -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Inspect and edit the local book library.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="Print all entries as JSON.")

    p_find = sub.add_parser("find", help="Find a book by MD5 or file path.")
    p_find.add_argument("--md5")
    p_find.add_argument("--path")

    p_add = sub.add_parser("add", help="Append a new entry (called by download.py).")
    p_add.add_argument("--json", required=True, help="JSON string with the entry fields.")

    p_remove = sub.add_parser("remove", help="Remove an entry by id.")
    p_remove.add_argument("id")

    args = p.parse_args(argv)
    cfg = load()
    lib = Library.open(cfg)

    if args.cmd == "list":
        print(json.dumps(lib.list_books(), indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "find":
        if args.md5:
            hit = lib.find_by_md5(args.md5)
        elif args.path:
            hit = lib.find_by_path(args.path)
        else:
            print("usage: find --md5 X | --path Y", file=sys.stderr)
            return 2
        print(json.dumps(hit, indent=2, ensure_ascii=False))
        return 0 if hit else 1
    if args.cmd == "add":
        entry = json.loads(args.json)
        added = lib.add(entry)
        print(json.dumps(added, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "remove":
        ok = lib.remove(args.id)
        print(json.dumps({"removed": ok, "id": args.id}, ensure_ascii=False))
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
