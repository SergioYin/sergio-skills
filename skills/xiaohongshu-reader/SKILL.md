---
name: xiaohongshu-reader
description: Read Xiaohongshu/小红书 notes from xhslink.com short links, xiaohongshu.com note URLs, or copied 小红书口令. Use when the user shares a 小红书/RedNote/XHS link or asks to read/summarize a 小红书 note. Extracts note text and metadata, downloads note images into OpenClaw workspace media, optionally runs explicit vision analysis for images, produces combined text+image summaries, and includes doctor/smoke-test/cleanup harness scripts.
---

# Xiaohongshu Reader

Use this skill for 小红书 links, copied 小红书口令, `xhslink.com`, `xiaohongshu.com/discovery/item/...`, or `xiaohongshu.com/explore/...` notes.

## Quick Use

Text only:

```bash
python3 scripts/read_xhs_link.py "<user text containing xhs link>"
```

Download images:

```bash
python3 scripts/read_xhs_link.py --download-images "<user text containing xhs link>"
```

Download and visually analyze images:

```bash
python3 scripts/read_xhs_link.py --analyze-images --image-limit 1 "<user text containing xhs link>"
```

Defaults are HOME-based, not machine-specific:

- config: `~/.openclaw/openclaw.json`
- agent dir: `~/.openclaw/agents/main/agent`
- media root: `~/.openclaw/workspace/media/xiaohongshu/<feed_id>/`

Useful overrides:

```bash
python3 scripts/read_xhs_link.py \
  --analyze-images \
  --vision-model openai-codex/gpt-5.4 \
  --agent-dir ~/.openclaw/agents/main/agent \
  --config-path ~/.openclaw/openclaw.json \
  --openclaw-dist /path/to/openclaw/dist \
  "<user text containing xhs link>"
```

## Output Contract

The script prints JSON with stable fields:

- `text_payload`: title, author, desc, tags, time, IP location, type, interact info
- `media_payload`: image_count, images, downloaded_images, video_count, videos, download_dir
- `image_descriptions`: one item per analyzed image with `index`, `path`, `status`, `description`, `error`
- `summaries`: `text_summary`, `image_summary`, `combined_summary`
- `warnings`: partial failures such as image download/vision errors

## Response Rules

Do not dump raw JSON unless the user asks for JSON. Final user-facing answer should be:

1. One-sentence overview.
2. `正文要点`: summarize title, author, desc, tags, time/IP/interactions when available.
3. `图片信息`: summarize successful `image_descriptions`. Mention important images by index.
4. `综合总结 / 可行动结论`: use `summaries.combined_summary` and your own concise synthesis.

If images were downloaded but `image_descriptions` is empty or all failed, say: “图片已下载但视觉分析失败/未开启，不能声称已看过图片内容。” Downloaded files do not automatically enter vision context; this skill explicitly runs vision analysis when `--analyze-images` is used.

## Harness Scripts

Run environment diagnostics:

```bash
python3 scripts/doctor.py --json
```

Run smoke tests:

```bash
python3 scripts/smoke_test.py --no-vision --json
python3 scripts/smoke_test.py --vision --image-limit 1 --json
```

Examples live in `examples/`:

- `examples/rag_note_input.txt`
- `examples/expected_output_shape.json`
- `examples/sample_response.md`

## Media Cleanup

Clean only this skill's Xiaohongshu media tree:

```bash
python3 scripts/cleanup_media.py --days 7 --dry-run --json
python3 scripts/cleanup_media.py --days 7 --json
```

Safety rules in `cleanup_media.py`:

- default root is `~/.openclaw/workspace/media/xiaohongshu`
- `--root` must be that root or a child of it
- deletes files older than `--days`; then removes empty directories
- `--dry-run` reports planned deletions without deleting

## OpenClaw Cron Management

Cron is managed by this skill, not as an unrelated global job. Fixed job name:

```text
xiaohongshu-reader-cleanup
```

Check status:

```bash
python3 scripts/install_cleanup_cron.py status --json
```

Preview install without creating anything:

```bash
python3 scripts/install_cleanup_cron.py install --disabled --dry-run --json
```

Install disabled first, to avoid surprise background work:

```bash
python3 scripts/install_cleanup_cron.py install --disabled --json
```

Uninstall:

```bash
python3 scripts/install_cleanup_cron.py uninstall --json
```

The cron message is constrained to this skill cleanup entry:

```bash
cd ~/.openclaw/workspace/skills/xiaohongshu-reader && python3 scripts/cleanup_media.py --days 7 --json
```

## Feishu Image Return Strategy

Do not send every image by default. Send 1–3 key images only when the user asks or the image carries core information. Use native media send, not path text:

```bash
openclaw message send --channel feishu --account default --target 'user:<open_id>' --media '<absolute image path>' --json
```

Verify with Feishu readback/API where possible. Success requires `msg_type=image`.

## Failure Handling

- Missing `feed_id`/`xsec_token`: ask for the original share link/copy text.
- Page parse failure: report exact failure (`initial_state_not_found`, blocked/private/deleted).
- Single image download/vision failure: keep overall note successful and put failure in `warnings` and `image_descriptions[].error`.
- OpenClaw dist/runtime discovery failure: report it via doctor or `image_descriptions[].error`; set `OPENCLAW_DIST` or pass `--openclaw-dist` as the smallest repair.
