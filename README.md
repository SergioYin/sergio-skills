# sergio-skills

Personal skill repository for OpenClaw / Claude-compatible agent skills.

This repository follows the same broad layout as `jimliu/baoyu-skills`: skills live under `skills/<skill-name>/`, and `.claude-plugin/marketplace.json` registers the repository as a single plugin bundle.

## Skills

### xiaohongshu-reader

Reads Xiaohongshu / RedNote links or share text, extracts note text and media metadata, downloads images into the OpenClaw workspace media tree, optionally runs image vision analysis, and returns structured text + image summaries.

Path:

```text
skills/xiaohongshu-reader/
```

Quick smoke tests:

```bash
cd skills/xiaohongshu-reader
python3 scripts/doctor.py --json
python3 scripts/smoke_test.py --no-vision --json
python3 scripts/smoke_test.py --vision --image-limit 1 --json
python3 scripts/cleanup_media.py --days 7 --dry-run --json
```

## Install As Plugin Marketplace

In a compatible agent runtime:

```text
/plugin marketplace add SergioYin/sergio-skills
/plugin install sergio-skills@sergio-skills
```

Direct GitHub installs should point at the individual skill directory when the installer supports a path:

```text
SergioYin/sergio-skills --path skills/xiaohongshu-reader
```

## Repository Rules

- Keep each skill self-contained under `skills/<skill-name>/`.
- Put executable harness scripts in `scripts/`.
- Put small examples in `examples/`.
- Keep generated outputs, caches, downloaded media, and local secrets out of Git.
- Prefer `doctor.py`, `smoke_test.py`, and dry-run cleanup flows for every skill that depends on local runtime state.

