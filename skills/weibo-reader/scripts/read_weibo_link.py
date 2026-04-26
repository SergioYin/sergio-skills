#!/usr/bin/env python3
"""Read a public Weibo status from t.cn/weibo.com/m.weibo.cn links.

No login. Uses Weibo mobile visitor cookies plus m.weibo.cn status endpoints.
"""
from __future__ import annotations

import argparse
import html
import http.cookiejar
import json
import os
import subprocess
import tempfile
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
try:
    from weibo_harness import default_agent_dir, default_config_path, default_media_root, find_openclaw_dist, DEFAULT_VISION_MODEL
except Exception:
    DEFAULT_VISION_MODEL = "openai-codex/gpt-5.4"
    def default_media_root():
        return Path.home() / ".openclaw" / "workspace" / "media" / "weibo"
    def default_agent_dir():
        return Path.home() / ".openclaw" / "agents" / "main" / "agent"
    def default_config_path():
        return Path.home() / ".openclaw" / "openclaw.json"
    def find_openclaw_dist(explicit=None):
        raise FileNotFoundError("OpenClaw dist not found. Set OPENCLAW_DIST or pass --openclaw-dist.")

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


def find_first_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s，。)）>]+", text)
    return m.group(0) if m else None


def strip_tags(value: str) -> str:
    value = re.sub(r"<\s*br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).replace("\r", "").strip()


def opener_with_cookies() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def request(opener: urllib.request.OpenerDirector, url: str, *, data: bytes | None = None, accept: str = "application/json,text/html,*/*", timeout: int = 25) -> tuple[str, str, str | None]:
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": UA, "Referer": "https://m.weibo.cn/", "Accept": accept},
    )
    resp = opener.open(req, timeout=timeout)
    body = resp.read().decode("utf-8", "replace")
    return body, resp.geturl(), resp.headers.get("content-type")


def resolve_url(opener: urllib.request.OpenerDirector, url: str) -> str:
    try:
        body, final, _ = request(opener, url, accept="text/html,*/*", timeout=20)
    except Exception:
        return url
    # Weibo visitor pages embed the real destination in url=...
    parsed = urllib.parse.urlparse(final)
    qs = urllib.parse.parse_qs(parsed.query)
    if "url" in qs and qs["url"]:
        return qs["url"][0]
    m = re.search(r'var\s+url\s*=\s*"([^"]+)"', body)
    if m:
        return html.unescape(m.group(1))
    return final


def extract_status_id(text: str) -> str | None:
    patterns = [
        r"(?:weibo\.com|m\.weibo\.cn)/(?:[^/\s]+/)?(?:status|detail)/([A-Za-z0-9]+)",
        r"[?&](?:id|mid)=([0-9A-Za-z]+)",
        r"/(\d{12,})\b",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1)
    return None


def ensure_visitor(opener: urllib.request.OpenerDirector, return_url: str) -> dict[str, Any] | None:
    url = "https://visitor.passport.weibo.cn/visitor/genvisitor2"
    payload = urllib.parse.urlencode(
        {
            "cb": "visitor_gray_callback",
            "ver": "20250916",
            "request_id": f"openclaw-{int(time.time() * 1000)}",
            "tid": "",
            "from": "weibo",
            "webdriver": "false",
            "rid": str(int(time.time() * 1000)),
            "return_url": return_url,
        }
    ).encode()
    try:
        body, _, _ = request(opener, url, data=payload, accept="text/javascript,*/*", timeout=20)
    except Exception:
        return None
    m = re.search(r"visitor_gray_callback\((.*)\);?", body)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def fetch_json(opener: urllib.request.OpenerDirector, url: str) -> dict[str, Any]:
    body, final, ctype = request(opener, url, accept="application/json,*/*", timeout=25)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Expected JSON but got {ctype or 'unknown'} from {final}: {body[:160]!r}") from exc


def image_urls(status: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    if status.get("original_pic"):
        urls.append(status["original_pic"])
    for pic in status.get("pics") or []:
        if isinstance(pic, dict):
            u = pic.get("large", {}).get("url") or pic.get("url") or pic.get("pid")
            if u and isinstance(u, str):
                if u.startswith("http"):
                    urls.append(u)
    # Fallback to lower-resolution variants only when no original/large images exist.
    if not urls:
        for u in [status.get("bmiddle_pic"), status.get("thumbnail_pic")]:
            if u and u not in urls:
                urls.append(u)
    dedup = []
    for u in urls:
        u = u.replace("\\/", "/")
        if u not in dedup:
            dedup.append(u)
    return dedup


def download(url: str, out: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://m.weibo.cn/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out.write_bytes(r.read())
    return str(out)


def read_status(input_text: str, *, download_images: bool = True, media_root: Path | None = None) -> dict[str, Any]:
    source_url = find_first_url(input_text) or input_text.strip()
    if not source_url:
        raise ValueError("No URL found in input")

    opener = opener_with_cookies()
    final_url = resolve_url(opener, source_url)
    status_id = extract_status_id(final_url) or extract_status_id(source_url)
    if not status_id:
        raise ValueError(f"Could not extract Weibo status id from {source_url!r} -> {final_url!r}")

    status_url = f"https://m.weibo.cn/status/{status_id}"
    ensure_visitor(opener, status_url)

    raw = fetch_json(opener, f"https://m.weibo.cn/api/statuses/show?id={urllib.parse.quote(status_id)}")
    if raw.get("ok") == -100:
        raise RuntimeError(f"Weibo login/visitor wall: {raw}")

    # The endpoint may return status object directly.
    status = raw.get("data") if isinstance(raw.get("data"), dict) and "user" in raw.get("data", {}) else raw

    long_text = None
    try:
        ext = fetch_json(opener, f"https://m.weibo.cn/statuses/extend?id={urllib.parse.quote(status_id)}")
        long_text = ((ext.get("data") or {}).get("longTextContent"))
    except Exception:
        long_text = None

    text = strip_tags(long_text or status.get("text", ""))
    user = status.get("user") or {}
    pics = image_urls(status)

    download_dir = None
    downloaded = []
    warnings: list[str] = []
    if download_images and pics:
        root = media_root or default_media_root()
        d = root / str(status_id)
        d.mkdir(parents=True, exist_ok=True)
        download_dir = str(d)
        for idx, u in enumerate(pics, 1):
            ext = Path(urllib.parse.urlparse(u).path).suffix or ".jpg"
            try:
                downloaded.append(download(u, d / f"image_{idx:02d}{ext}"))
            except Exception as e:
                err = f"image_download_failed {u}: {e}"
                warnings.append(err)
                downloaded.append({"url": u, "error": str(e)})

    overview = text.splitlines()[0] if text else ""
    text_payload = {
        "status_id": str(status_id),
        "author": {
            "id": user.get("idstr") or str(user.get("id", "")),
            "screen_name": user.get("screen_name") or user.get("name"),
            "verified_reason": user.get("verified_reason"),
            "followers_count": user.get("followers_count"),
            "location": user.get("location"),
        },
        "created_at": status.get("created_at"),
        "source": strip_tags(status.get("source", "")),
        "text": text,
        "text_length": len(text),
        "interact": {
            "reposts_count": status.get("reposts_count"),
            "comments_count": status.get("comments_count"),
            "attitudes_count": status.get("attitudes_count"),
        },
    }
    media_payload = {
        "image_count": len(pics),
        "images": pics,
        "download_dir": download_dir,
        "downloaded_images": downloaded,
    }

    return {
        "success": True,
        "source_url": source_url,
        "final_url": final_url,
        "status_id": str(status_id),
        "author": {
            "id": user.get("idstr") or str(user.get("id", "")),
            "screen_name": user.get("screen_name") or user.get("name"),
            "verified_reason": user.get("verified_reason"),
            "followers_count": user.get("followers_count"),
            "location": user.get("location"),
        },
        "created_at": status.get("created_at"),
        "source": strip_tags(status.get("source", "")),
        "text": text,
        "text_length": len(text),
        "interact": {
            "reposts_count": status.get("reposts_count"),
            "comments_count": status.get("comments_count"),
            "attitudes_count": status.get("attitudes_count"),
        },
        "images": pics,
        "download_dir": download_dir,
        "downloaded_images": downloaded,
        "text_payload": text_payload,
        "media_payload": media_payload,
        "summaries": build_summaries(text_payload, []),
        "image_descriptions": [],
        "warnings": warnings,
        "raw_saved": None,
    }


def build_summaries(text_payload: dict[str, Any], image_descriptions: list[dict[str, Any]] | None = None) -> dict[str, str]:
    text = (text_payload.get("text") or "").strip()
    title = text.splitlines()[0] if text else "未提取到正文"
    body = " ".join(text.split())
    text_summary = body[:500] + ("…" if len(body) > 500 else "")
    good = [x for x in (image_descriptions or []) if x.get("status") == "success" and x.get("description")]
    if good:
        parts = []
        for x in good[:6]:
            d = " ".join(str(x.get("description", "")).split())
            parts.append(f"图{x.get('index')}：{d[:280]}{'…' if len(d) > 280 else ''}")
        image_summary = "；".join(parts)
        combined_summary = f"微博正文主要是：{text_summary} 图片补充信息：{image_summary}"
    else:
        image_summary = "暂无成功的视觉描述。若图片已下载，说明还需要开启或修复 --analyze-images 视觉链路。"
        combined_summary = f"微博正文主要是：{text_summary} 目前没有可用图片视觉描述，不能声称已看过图片内容。"
    return {"text_summary": text_summary, "image_summary": image_summary, "combined_summary": combined_summary}


def parse_model_ref(model_ref: str) -> tuple[str, str]:
    if "/" not in model_ref:
        raise ValueError("vision_model_must_be_provider/model")
    provider, model = model_ref.split("/", 1)
    if not provider or not model:
        raise ValueError("vision_model_must_be_provider/model")
    return provider, model


def describe_image(path: str, vision_model: str, agent_dir: str, config_path: str, prompt: str, timeout_sec: int = 180, openclaw_dist: str | None = None) -> dict[str, Any]:
    provider, model = parse_model_ref(vision_model)
    try:
        dist_dir = str(find_openclaw_dist(openclaw_dist))
    except Exception as e:
        return {"ok": False, "error": str(e)}
    js = f"""
import fs from 'node:fs/promises';
import pathMod from 'node:path';
const cfg = JSON.parse(await fs.readFile({json.dumps(config_path)}, 'utf8'));
const distDir = {json.dumps(dist_dir)};
async function resolveDescribeImageFileWithModel() {{
  const names = await fs.readdir(distDir);
  const runtimeFiles = names.filter((name) => /^runtime-.*[.]js$/.test(name)).sort((a,b)=>a.localeCompare(b));
  const errors = [];
  for (const name of runtimeFiles) {{
    const full = pathMod.join(distDir, name);
    try {{
      const mod = await import(full);
      if (typeof mod.describeImageFileWithModel === 'function') return {{ fn: mod.describeImageFileWithModel, modulePath: full }};
    }} catch (e) {{ errors.push(`${{name}}: ${{String(e && (e.message || e))}}`); }}
  }}
  throw new Error(`describeImageFileWithModel export not found in ${{runtimeFiles.length}} runtime modules. ${{errors.slice(0,5).join(' | ')}}`);
}}
try {{
  const resolved = await resolveDescribeImageFileWithModel();
  const result = await resolved.fn({{
    filePath: {json.dumps(path)}, cfg, provider: {json.dumps(provider)}, model: {json.dumps(model)},
    prompt: {json.dumps(prompt)}, timeoutMs: {timeout_sec * 1000}, maxTokens: 900, agentDir: {json.dumps(agent_dir)}
  }});
  console.log(JSON.stringify({{ ok: true, provider: {json.dumps(provider)}, model: result?.model || {json.dumps(model)}, text: result?.text || '', runtimeModule: resolved.modulePath }}));
}} catch (e) {{
  console.log(JSON.stringify({{ ok: false, error: String(e && (e.stack || e.message) || e) }}));
  process.exitCode = 1;
}}
"""
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        script = f.name
        f.write(js)
    try:
        proc = subprocess.run(["node", script], text=True, capture_output=True, timeout=timeout_sec + 20)
        raw = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout.strip() else ""
        if not raw:
            return {"ok": False, "error": (proc.stderr or f"node exited {proc.returncode}").strip()}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "error": f"non_json_vision_output: stdout={proc.stdout[-1000:]} stderr={proc.stderr[-1000:]}"}
        if not data.get("ok"):
            return {"ok": False, "error": data.get("error") or proc.stderr or "vision_failed"}
        return data
    finally:
        try:
            os.unlink(script)
        except OSError:
            pass


def analyze_images(result: dict[str, Any], vision_model: str, agent_dir: str, config_path: str, limit: int | None = None, openclaw_dist: str | None = None) -> dict[str, Any]:
    warnings = result.setdefault("warnings", [])
    downloaded = result.get("media_payload", {}).get("downloaded_images") or result.get("downloaded_images") or []
    prompt = "请用中文描述这张微博配图的像素内容。重点识别图片里的文字、版式、主体对象、关键结论；如果是信息图/截图，请尽量提取可读文字和结构。不要编造看不到的内容。"
    descriptions = []
    image_items = downloaded[:limit] if limit else downloaded
    for idx, item in enumerate(image_items, 1):
        if isinstance(item, dict):
            descriptions.append({"index": idx, "path": item.get("path"), "status": "error", "description": "", "error": item.get("error") or "image_not_downloaded"})
            continue
        path = str(item)
        entry = {"index": idx, "path": path, "status": "pending", "description": "", "error": None}
        if not Path(path).is_file():
            entry.update({"status": "error", "error": "file_not_found"})
            warnings.append(f"image_{idx}_vision_failed: file_not_found {path}")
            descriptions.append(entry)
            continue
        data = describe_image(path, vision_model, agent_dir, config_path, prompt, openclaw_dist=openclaw_dist)
        if data.get("ok") and data.get("text"):
            entry.update({"status": "success", "description": data["text"], "provider": data.get("provider"), "model": data.get("model"), "error": None})
        else:
            err = data.get("error") or "empty_description"
            entry.update({"status": "error", "error": err})
            warnings.append(f"image_{idx}_vision_failed: {err}")
        descriptions.append(entry)
    result["image_descriptions"] = descriptions
    result["summaries"] = build_summaries(result.get("text_payload") or {}, descriptions)
    return result


def _media_ref(status_id: str, path: str | None) -> str | None:
    if not path:
        return None
    return f"media://weibo/{status_id}/{Path(path).name}"


def redact_local_paths(result: dict[str, Any]) -> dict[str, Any]:
    status_id = str(result.get("status_id") or "")
    result = json.loads(json.dumps(result, ensure_ascii=False))
    if result.get("download_dir"):
        result["download_dir"] = f"media://weibo/{status_id}/"
    if isinstance(result.get("downloaded_images"), list):
        result["downloaded_images"] = [
            _media_ref(status_id, x) if isinstance(x, str) else x for x in result["downloaded_images"]
        ]
    mp = result.get("media_payload") or {}
    if mp.get("download_dir"):
        mp["download_dir"] = f"media://weibo/{status_id}/"
    if isinstance(mp.get("downloaded_images"), list):
        mp["downloaded_images"] = [
            _media_ref(status_id, x) if isinstance(x, str) else x for x in mp["downloaded_images"]
        ]
    for item in result.get("image_descriptions") or []:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            item["path"] = _media_ref(status_id, item["path"])
    if result.get("raw_saved"):
        result["raw_saved"] = _media_ref(status_id, result["raw_saved"])
    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Read a public Weibo status from a link")
    p.add_argument("input", help="Text containing t.cn/weibo.com/m.weibo.cn link")
    p.add_argument("--no-download-images", action="store_true", help="Do not download images or analyze images")
    p.add_argument("--analyze-images", action="store_true", help="Deprecated compatibility flag; image analysis is on by default when images are downloaded")
    p.add_argument("--no-analyze-images", action="store_true", help="Download images but skip visual analysis")
    p.add_argument("--include-local-paths", action="store_true", help="Include absolute local paths in JSON output for debugging/tests")
    p.add_argument("--image-limit", type=int, default=12, help="Maximum images to download/analyze")
    p.add_argument("--vision-model", default=DEFAULT_VISION_MODEL)
    p.add_argument("--agent-dir", default=str(default_agent_dir()))
    p.add_argument("--config-path", default=str(default_config_path()))
    p.add_argument("--openclaw-dist", default=None)
    p.add_argument("--media-root", help="Media root directory")
    args = p.parse_args()
    try:
        should_download = not args.no_download_images
        should_analyze = should_download and not args.no_analyze_images
        result = read_status(
            args.input,
            download_images=should_download,
            media_root=Path(args.media_root).expanduser() if args.media_root else None,
        )
        if should_analyze:
            result = analyze_images(result, args.vision_model, args.agent_dir, args.config_path, args.image_limit, args.openclaw_dist)
        if result.get("download_dir"):
            raw_path = Path(result["download_dir"]) / "status.json"
            raw_path.write_text(json.dumps(redact_local_paths(result), ensure_ascii=False, indent=2), encoding="utf-8")
            result["raw_saved"] = str(raw_path)
        output = result if args.include_local_paths else redact_local_paths(result)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
