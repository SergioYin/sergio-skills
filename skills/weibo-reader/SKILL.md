---
name: weibo-reader
description: Read public Weibo/微博 posts from t.cn short links, weibo.com status URLs, or m.weibo.cn links. Use when the user shares a Weibo link or asks to read/summarize/analyze a 微博 post. Extracts author, created time, full long-text content, interactions, and image URLs/downloads without login when the post is public. Includes doctor/smoke-test/cleanup harness scripts.
---

# Weibo Reader

Use this skill for `t.cn` short links, `weibo.com/.../{status_id}`, `m.weibo.cn/status/...`, `m.weibo.cn/detail/...`, or copied 微博 links/text.

## Quick Use

Read text and download images:

```bash
python3 scripts/read_weibo_link.py "<user text containing a Weibo link>"
```

Download and visually analyze images:

```bash
python3 scripts/read_weibo_link.py --analyze-images --image-limit 1 "<user text containing a Weibo link>"
```

Text only:

```bash
python3 scripts/read_weibo_link.py --no-download-images "<user text containing a Weibo link>"
```

Defaults are HOME-based, not machine-specific:

- config: `~/.openclaw/openclaw.json`
- agent dir: `~/.openclaw/agents/main/agent`
- media root: `~/.openclaw/workspace/media/weibo/<status_id>/`

Useful override:

```bash
python3 scripts/read_weibo_link.py \
  --analyze-images \
  --vision-model openai-codex/gpt-5.4 \
  --agent-dir ~/.openclaw/agents/main/agent \
  --config-path ~/.openclaw/openclaw.json \
  --openclaw-dist /path/to/openclaw/dist \
  "<user text containing a Weibo link>"
```

## Method

The script follows the lightweight mobile Weibo approach:

1. Resolve `t.cn` or desktop Weibo links to a status id.
2. Create a temporary mobile Weibo visitor session through `visitor.passport.weibo.cn/visitor/genvisitor2`.
3. Fetch `https://m.weibo.cn/api/statuses/show?id=<status_id>` for metadata and images.
4. Fetch `https://m.weibo.cn/statuses/extend?id=<status_id>` for full long text when available.
5. Download exposed images to the local media directory.

Avoid PC `weibo.com` pages for reading; they are more likely to hit login walls. Avoid bulk scraping and keep use scoped to user-provided public posts.

## Output Contract

The script prints JSON with stable top-level fields:

- `success`, `source_url`, `final_url`, `status_id`
- `author`: id, screen_name, verified_reason, followers_count, location
- `created_at`, `source`, `text`, `text_length`
- `interact`: reposts_count, comments_count, attitudes_count
- `images`, `download_dir`, `downloaded_images`, `raw_saved`
- `text_payload`, `media_payload`, `image_descriptions`, `summaries`, `warnings`

The `text_payload` / `media_payload` / `image_descriptions` fields are included to mirror reader skills such as `xiaohongshu-reader` and make downstream formatting easier.

## Response Rules

Do not dump raw JSON unless the user asks for JSON. Final user-facing answer should be:

1. One-sentence overview.
2. `微博信息`: author, time, source, interactions when available.
3. `正文要点`: summarize the full `text` field.
4. `图片信息`: mention image count/download path. Do not claim visual contents unless explicitly inspected with a vision/OCR step.
5. `综合分析 / 可行动结论`: concise synthesis when the user asks for analysis.

If images were downloaded but not visually analyzed, say: “图片已下载，但我还没有做视觉分析，不能声称已看过图片内容。”

## Harness Scripts

Run environment diagnostics:

```bash
python3 scripts/doctor.py --json
```

Run a smoke test using `examples/sample_weibo_input.txt`:

```bash
python3 scripts/smoke_test.py --no-vision --json
python3 scripts/smoke_test.py --vision --image-limit 1 --json
python3 scripts/smoke_test.py --no-download-images --json
```

Examples live in `examples/`:

- `examples/sample_weibo_input.txt`
- `examples/expected_output_shape.json`
- `examples/sample_response.md`

## Media Cleanup

Clean only this skill's Weibo media tree:

```bash
python3 scripts/cleanup_media.py --days 7 --dry-run --json
python3 scripts/cleanup_media.py --days 7 --json
```

Safety rules in `cleanup_media.py`:

- default root is `~/.openclaw/workspace/media/weibo`
- `--root` must be that root or a child of it
- deletes files older than `--days`; then removes empty directories
- `--dry-run` reports planned deletions without deleting

## OpenClaw Cron Management

Cron is managed by this skill, not as an unrelated global job. Fixed job name:

```text
weibo-reader-cleanup
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
cd ~/.openclaw/workspace/skills/weibo-reader && python3 scripts/cleanup_media.py --days 7 --json
```

## Failure Handling

- Missing status id: ask for the original Weibo link or copied text.
- Visitor/login wall: report the exact failure and suggest retrying later or using a logged-in/browser-based Weibo skill.
- Long text fetch failure: still answer from `api/statuses/show` text and mention partial extraction.
- Image download failure: keep text successful and report `warnings`.
