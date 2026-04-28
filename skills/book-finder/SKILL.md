---
name: book-finder
description: Search the web for an ebook by title (and optional author), show every format/version found across multiple sources, and download whichever one the user picks into a managed local library with `library.json` metadata. Use this skill whenever the user wants to find, look up, or download a book — including casual phrasings like "找一下《三体》", "帮我下载这本", "do you have alice in wonderland", "where can I get a copy of X", "find me an ebook of Y", "搜一下XX的电子书". Trigger on any book-acquisition intent even when the user doesn't explicitly say "download".
---

# Book Finder

Personal book retrieval. Given a title (with optional author/year/language hints), the skill fans out to several online sources, ranks the results by language preference and format priority, lets the user pick one, downloads it via aria2c (or Python urllib fallback), and writes a metadata entry into `library.json` at the user's library root.

## Disclaimer

声明：本 skill 仅供个人使用，只做个人研究和阅读使用，不用于传播、分发、转售或任何公开分享用途。使用者应自行确认其获取和使用行为符合所在地法律法规及相关版权要求。

This is for personal research/reading use only. It does not republish, distribute, or share what it downloads.

## When to use

Trigger any time the user signals they want to obtain a book. Some phrasings to watch for:

- "find me [title]" / "do you have [title]" / "下载[书名]" / "搜一下[书名]"
- "I want to read [title]"
- "where can I get [title] in epub"
- a bare book title in context of reading/library/Kindle
- follow-ups like "another version", "find a chinese translation"

Don't trigger for: looking up information *about* a book (summary, reviews, metadata only) — that's a web-search task, not a download task.

## Workflow

The skill is a thin wrapper around three Python scripts: `search.py`, `download.py`, `library.py`. Run them via `python3` against `scripts/` inside the skill directory. All scripts emit JSON when given `--json` or by default for the search/download commands.

### Step 1 — Resolve config (first run only matters once)

```bash
python3 scripts/config.py show
```

The output is JSON containing `first_run`, `library_root`, `proxy`, `sources_enabled`, etc. If `first_run` is `true`, the defaults have just been written to `~/.config/book-finder/config.json`. Tell the user briefly:

> Set up book-finder config at `~/.config/book-finder/config.json`. Library root defaults to `~/Downloads/books/`. You can change this any time, e.g.:
> ```
> python3 scripts/config.py edit library_root /path/you/want
> ```

Then proceed without waiting unless the user wants to tweak something.

After the first run this step takes <50 ms and is silent.

### Step 2 — Search

```bash
python3 scripts/search.py "<query>" --limit 25 --json
```

`<query>` is what the user said, optionally augmented with author/year if the user gave them. Quote the whole thing — it's one CLI argument.

The output JSON has shape:

```json
{
  "query": "...",
  "result_count": 42,
  "errors": {"<source>": "<message>", ...},
  "results": [{"title": "...", "authors": [...], "year": "...", "language": "...",
               "format": "epub", "size_bytes": 1234567, "source": "libgen",
               "source_url": "https://...", "download_info": {...}, ...}, ...]
}
```

Results are pre-ranked by the user's preferred languages, then format priority (default: epub > pdf > mobi > azw3 > txt), then size desc. **Do not re-sort the array yourself** — the ranking already encodes the user's `format_priority` from config.

If `errors` is non-empty, mention those sources in passing ("LibGen mirror was unreachable") but don't dwell on it — the rest of the search still ran.

### Step 3 — Present the list to the user

Format a compact table. Show the first 10–15 results unless the user asked for "all". Always include the index, title, author(s), year, language, format, size, and source. Example:

```
Found 17 versions for "Alice in Wonderland":

  #  Title                                     Author          Yr    Lang  Fmt   Size    Source
  1  Alice's Adventures in Wonderland          Lewis Carroll   1865  en    epub  2.4 MB  libgen
  2  Alice's Adventures in Wonderland          Lewis Carroll   —     en    epub  —       gutenberg
  3  Alice in Wonderland                       Lewis Carroll   1951  en    pdf   25 MB   archive_org
  ...
```

Then ask: "Which one? Reply with a number (or 'more' to see the rest)." If the user gives a number, proceed to Step 4. If they pick `manual_link` source result (sobooks/jiumodiary), skip the download — see [§ Manual link sources](#manual-link-sources).

If the user said "best one" / "随便给我一个" / "the first one" — pick result `[1]` automatically.

### Step 4 — Download

Take the chosen result's full JSON object (don't strip fields — `download_info` is required) and feed it to download.py via stdin:

```bash
echo '<chosen-result-json>' | python3 scripts/download.py --item-stdin
```

The script:
1. Calls the matching source module's `resolve_download_url()` to turn `download_info` into a real URL (libgen needs a follow-up fetch; archive.org needs a metadata lookup; gutenberg builds a deterministic URL).
2. Downloads via `aria2c` if installed, else streams via Python.
3. Computes MD5, writes the file to `<library_root>/<sanitized title>.<ext>` (collision-resolved with `(2)`, `(3)`, ... suffixes).
4. Appends an entry to `library.json`.

The script returns JSON with either `{"status": "ok", "entry": {...}, "absolute_path": "..."}` or `{"status": "error", "error": "..."}`.

Report back: "Downloaded to `<absolute_path>` (`<size>`) and registered in `library.json`." If the file is small (<1 MB) and the user looks like they'd want to read it now, optionally offer to open it.

### Step 5 (optional) — List or look up

`library.py list` returns the full `library.json`. `library.py find --md5 X` checks for a duplicate before downloading; the workflow above doesn't auto-skip duplicates because the user might want a different format of the same book, but if you already see a matching `md5` on a fresh search hit, mention it: "you already have this MD5 from `<previous file_path>`."

## Sources

The skill ships with six source modules under `scripts/sources/`. Toggle them in config under `sources_enabled`. Their characteristics matter when you explain results to the user.

| Source | Status | Strength | Notes |
|---|---|---|---|
| `libgen` (libgen.li) | active | Large English + many Chinese | Two-step download (search → ads.php → get.php). Mirror falls back to libgen.bz. |
| `archive_org` | active | Public-domain books, scans of older editions | JSON API. Format list per item is precise; size is unknown until download. |
| `gutenberg` | active | Classic public-domain literature | Limited to English-major. Cache URLs are deterministic. |
| `sobooks` (sobooks.cc) | active, **manual** | Chinese ebooks | Returns article URLs only. Downloads are 百度网盘/夸克网盘 with extraction codes — user opens the page. |
| `jiumodiary` | active, **manual** | Chinese meta-search portal | SPA, JS-rendered. We surface a single "open this URL" entry. |
| `annas_archive` | disabled | Aggregated catalog | Currently unreachable from probing. Module is a stub. Toggle when network allows. |

### Manual link sources

When `download_info.type == "manual_link"`, the result is **not directly downloadable**. The download script will refuse with status `manual_link`. Tell the user:

> This one's only available via a webpage (often 百度网盘 with a code). Open this URL in your browser: `<source_url>`. Once downloaded, run:
> ```
> python3 scripts/library.py add --json '{"title": "...", "file_path": "/path/to/file.epub", "source": "sobooks", "source_url": "..."}'
> ```
> to register it in `library.json`.

Don't pretend you can download these.

## Common situations

**No results at all.** If `result_count == 0`, suggest broadening the query: drop the author, try the original-language title, simplify punctuation. If errors mention all enabled sources failing, the proxy might be down — point the user at `~/.config/book-finder/config.json`.

**The user wants a specific format.** Filter the results array by `r["format"] == "<ext>"` before presenting, and tell the user how many of each format you found.

**The user wants a translation/specific language.** Filter by `r["language"]` (or substring). The default ranking already prefers `cfg.preferred_languages`, but the user may want the opposite.

**They want to swap the chosen result.** Just present the list again or, if context is fresh, accept "no, the next one" and pick the next index.

**Duplicate already in library.** `library.py find --md5 <md5>` → if hit, ask before re-downloading.

**Slow / partial downloads.** aria2c resumes mid-file; the python fallback doesn't. If a download fails partway, just retry. The download path is deterministic so retries don't pile up files.

## Configuration cheat-sheet

```bash
# View current config:
python3 scripts/config.py show

# Change library root:
python3 scripts/config.py edit library_root /Volumes/External/Books

# Disable a source (e.g., libgen):
python3 scripts/config.py edit sources_enabled '{"libgen":false,"archive_org":true,"gutenberg":true,"sobooks":true,"jiumodiary":true,"annas_archive":false}'
# (Or just edit ~/.config/book-finder/config.json by hand — it's a tiny JSON file.)

# Change format priority:
python3 scripts/config.py edit format_priority epub,pdf,mobi,azw3,txt

# Disable proxy:
python3 scripts/config.py edit proxy null
# (`null` only works via direct JSON edit — the CLI passes strings; for falsy, hand-edit the file.)
```

## Files

```
skills/book-finder/
├── SKILL.md                  ← this file
└── scripts/
    ├── config.py             # ensure_config(), load(), save()
    ├── search.py             # multi-source fan-out, dedupe, rank
    ├── download.py           # resolve URL, fetch, hash, write library entry
    ├── library.py            # add/find/list/remove on library.json
    └── sources/
        ├── __init__.py       # HttpContext, make_result, parse helpers
        ├── libgen.py
        ├── archive_org.py
        ├── gutenberg.py
        ├── sobooks.py        # manual-link
        ├── jiumodiary.py     # manual-link
        └── annas_archive.py  # stub
```

`~/.config/book-finder/config.json` and `<library_root>/library.json` are user data; never check them into git.
