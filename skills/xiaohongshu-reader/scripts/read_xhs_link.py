#!/usr/bin/env python3
"""Read Xiaohongshu notes from xhslink/xiaohongshu URLs.

Outputs structured JSON. The script extracts note text/metadata from
window.__INITIAL_STATE__, optionally downloads images into OpenClaw workspace
media, and can explicitly run OpenClaw vision analysis for downloaded images.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

UA_MOBILE = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.0"
UA_DESKTOP = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
from xhs_harness import default_agent_dir, default_config_path, default_media_root, find_openclaw_dist, DEFAULT_VISION_MODEL

WORKSPACE_MEDIA_ROOT = default_media_root()
DEFAULT_AGENT_DIR = str(default_agent_dir())
DEFAULT_CONFIG_PATH = str(default_config_path())

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError(newurl)

def extract_url(text: str) -> str:
    m = re.search(r'https?://[^\s，。]+', text)
    if not m:
        raise ValueError("no_url_found")
    return m.group(0).rstrip('.,;，。')

def expand_once(url: str) -> str:
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": UA_MOBILE})
    try:
        resp = opener.open(req, timeout=20)
        return resp.geturl()
    except RuntimeError as e:
        return str(e)
    except urllib.error.HTTPError as e:
        loc = e.headers.get('Location')
        if loc:
            return urllib.parse.urljoin(url, loc)
        raise

def parse_ids(final_url: str):
    u = urllib.parse.urlparse(final_url)
    qs = urllib.parse.parse_qs(u.query)
    token = (qs.get('xsec_token') or qs.get('xsecToken') or [None])[0]
    parts = [p for p in u.path.split('/') if p]
    feed_id = None
    for marker in ('item', 'explore'):
        if marker in parts:
            i = parts.index(marker)
            if i + 1 < len(parts):
                feed_id = parts[i + 1]
                break
    if not feed_id:
        for p in reversed(parts):
            if re.fullmatch(r'[0-9a-fA-F]{20,32}', p):
                feed_id = p
                break
    return feed_id, token

def fetch_html(feed_id: str, token: str, source: str = 'app_share') -> str:
    q = urllib.parse.urlencode({'xsec_token': token, 'xsec_source': source})
    url = f'https://www.xiaohongshu.com/discovery/item/{feed_id}?{q}'
    req = urllib.request.Request(url, headers={
        'User-Agent': UA_DESKTOP,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

def extract_state_with_node(html: str, feed_id: str):
    start = html.find('window.__INITIAL_STATE__=')
    if start < 0:
        raise ValueError('initial_state_not_found')
    end = html.find('</script>', start)
    if end < 0:
        raise ValueError('initial_state_script_end_not_found')
    js = html[start:end]
    with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
        path = f.name
        f.write('globalThis.window={};\n')
        f.write(js)
        f.write(f'''\nconst st = window.__INITIAL_STATE__;\nconst item = st?.note?.noteDetailMap?.[{json.dumps(feed_id)}];\nif (!item) {{ console.error("note_not_found"); process.exit(2); }}\nconsole.log(JSON.stringify(item, null, 2));\n''')
    try:
        out = subprocess.check_output(['node', path], text=True, timeout=20)
        return json.loads(out)
    finally:
        try: os.unlink(path)
        except OSError: pass

def normalize_interact(interact: dict[str, Any]) -> dict[str, Any]:
    return interact or {}

def build_text_payload(note: dict[str, Any], user: dict[str, Any], interact: dict[str, Any]) -> dict[str, Any]:
    return {
        'title': note.get('title'),
        'author': user.get('nickname'),
        'desc': note.get('desc'),
        'tags': [t.get('name') for t in note.get('tagList') or [] if t.get('name')],
        'time': note.get('time'),
        'ip_location': note.get('ipLocation'),
        'type': note.get('type'),
        'interact': normalize_interact(interact),
    }

def build_summaries(text_payload: dict[str, Any], image_descriptions: list[dict[str, Any]] | None = None) -> dict[str, str]:
    title = text_payload.get('title') or '未提取到标题'
    desc = (text_payload.get('desc') or '').strip()
    tags = text_payload.get('tags') or []
    tag_text = '、'.join(tags[:8]) if tags else '无明显标签'
    text_summary = f"《{title}》：{desc[:500] if desc else '正文为空或未提取到正文'}"
    if len(desc) > 500:
        text_summary += '…'
    text_summary += f" 标签：{tag_text}。"

    good = [x for x in (image_descriptions or []) if x.get('status') == 'success' and x.get('description')]
    if good:
        parts = []
        for x in good[:6]:
            d = ' '.join(str(x.get('description', '')).split())
            parts.append(f"图{x.get('index')}：{d[:280]}{'…' if len(d) > 280 else ''}")
        image_summary = '；'.join(parts)
        combined_summary = f"正文主要讲《{title}》。图片补充信息显示：{image_summary}。综合来看，这篇笔记的核心不是只看正文，而是正文主题与图片中的结构化信息共同构成主要内容。"
    else:
        image_summary = '暂无成功的视觉描述。若图片已下载，说明还需要开启或修复 --analyze-images 视觉链路。'
        combined_summary = f"正文主要讲《{title}》。目前没有可用图片视觉描述，综合总结只能基于正文与元数据，不能声称已看过图片内容。"
    return {
        'text_summary': text_summary,
        'image_summary': image_summary,
        'combined_summary': combined_summary,
    }

def simplify(item, source_url, final_url, feed_id, token):
    note = item.get('note', {})
    user = note.get('user', {})
    interact = note.get('interactInfo', {})
    images = []
    videos = []
    for img in note.get('imageList') or []:
        if img.get('urlDefault') or img.get('urlPre'):
            images.append(img.get('urlDefault') or img.get('urlPre'))
        stream = img.get('stream') or {}
        for codec in ('h264','h265','h266','av1'):
            for v in stream.get(codec) or []:
                if v.get('masterUrl'):
                    videos.append(v['masterUrl'])
    text_payload = build_text_payload(note, user, interact)
    media_payload = {
        'image_count': len(images),
        'images': images,
        'downloaded_images': [],
        'video_count': len(videos),
        'videos': videos,
    }
    result = {
        'success': True,
        'source_url': source_url,
        'final_url': final_url,
        'feed_id': feed_id,
        'xsec_token': token,
        # Backward-compatible top-level fields
        **text_payload,
        'image_count': len(images),
        'images': images,
        'video_count': len(videos),
        'videos': videos,
        'comments_count_extracted': len((item.get('comments') or {}).get('list') or []),
        # Stable productized payloads
        'text_payload': text_payload,
        'media_payload': media_payload,
        'image_descriptions': [],
        'summaries': build_summaries(text_payload, []),
        'warnings': [],
    }
    return result

def default_image_dir(feed_id: str | None) -> Path:
    safe = re.sub(r'[^0-9a-zA-Z_-]+', '_', feed_id or 'note')
    return WORKSPACE_MEDIA_ROOT / safe

def download_images(result: dict, out_dir: str | None = None, limit: int = 12):
    d = Path(out_dir) if out_dir else default_image_dir(result.get('feed_id'))
    d.mkdir(parents=True, exist_ok=True)
    paths = []
    warnings = result.setdefault('warnings', [])
    for i, url in enumerate((result.get('media_payload', {}).get('images') or result.get('images') or [])[:limit], 1):
        ext = '.jpg'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA_DESKTOP, 'Referer': 'https://www.xiaohongshu.com/'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                ctype = resp.headers.get('Content-Type','')
                if 'png' in ctype: ext = '.png'
                elif 'webp' in ctype: ext = '.webp'
                path = d / f'image_{i:02d}{ext}'
                path.write_bytes(resp.read())
                paths.append(str(path))
        except Exception as e:
            err = f'image_{i}_download_failed: {e}'
            paths.append({'index': i, 'status': 'error', 'error': str(e), 'url': url})
            warnings.append(err)
    result['download_dir'] = str(d)
    result['downloaded_images'] = paths
    result['media_payload']['download_dir'] = str(d)
    result['media_payload']['downloaded_images'] = paths
    return result

def parse_model_ref(model_ref: str):
    if '/' not in model_ref:
        raise ValueError('vision_model_must_be_provider/model')
    provider, model = model_ref.split('/', 1)
    if not provider or not model:
        raise ValueError('vision_model_must_be_provider/model')
    return provider, model

def describe_image(path: str, vision_model: str, agent_dir: str, config_path: str, prompt: str, timeout_sec: int = 180, openclaw_dist: str | None = None) -> dict[str, Any]:
    provider, model = parse_model_ref(vision_model)
    try:
        dist_dir = str(find_openclaw_dist(openclaw_dist))
    except Exception as e:
        return {'ok': False, 'error': str(e)}
    js = f"""
import fs from 'node:fs/promises';
import pathMod from 'node:path';
const cfg = JSON.parse(await fs.readFile({json.dumps(config_path)}, 'utf8'));
const distDir = {json.dumps(dist_dir)};
async function resolveDescribeImageFileWithModel() {{
  const names = await fs.readdir(distDir);
  const runtimeFiles = names
    .filter((name) => /^runtime-.*[.]js$/.test(name))
    .sort((a, b) => a.localeCompare(b));
  const errors = [];
  for (const name of runtimeFiles) {{
    const full = pathMod.join(distDir, name);
    try {{
      const mod = await import(full);
      if (typeof mod.describeImageFileWithModel === 'function') {{
        return {{ fn: mod.describeImageFileWithModel, modulePath: full }};
      }}
    }} catch (e) {{
      errors.push(`${{name}}: ${{String(e && (e.message || e))}}`);
    }}
  }}
  throw new Error(`describeImageFileWithModel export not found in ${{runtimeFiles.length}} runtime modules. ${{errors.slice(0, 5).join(' | ')}}`);
}}
try {{
  const resolved = await resolveDescribeImageFileWithModel();
  const result = await resolved.fn({{
    filePath: {json.dumps(path)},
    cfg,
    provider: {json.dumps(provider)},
    model: {json.dumps(model)},
    prompt: {json.dumps(prompt)},
    timeoutMs: {timeout_sec * 1000},
    maxTokens: 900,
    agentDir: {json.dumps(agent_dir)}
  }});
  console.log(JSON.stringify({{ ok: true, provider: {json.dumps(provider)}, model: result?.model || {json.dumps(model)}, text: result?.text || '', runtimeModule: resolved.modulePath }}));
}} catch (e) {{
  console.log(JSON.stringify({{ ok: false, error: String(e && (e.stack || e.message) || e) }}));
  process.exitCode = 1;
}}
"""
    with tempfile.NamedTemporaryFile('w', suffix='.mjs', delete=False) as f:
        script = f.name
        f.write(js)
    try:
        proc = subprocess.run(['node', script], text=True, capture_output=True, timeout=timeout_sec + 20)
        raw = (proc.stdout or '').strip().splitlines()[-1] if proc.stdout.strip() else ''
        if not raw:
            return {'ok': False, 'error': (proc.stderr or f'node exited {proc.returncode}').strip()}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {'ok': False, 'error': f'non_json_vision_output: stdout={proc.stdout[-1000:]} stderr={proc.stderr[-1000:]}'}
        if not data.get('ok'):
            return {'ok': False, 'error': data.get('error') or proc.stderr or 'vision_failed'}
        return data
    finally:
        try: os.unlink(script)
        except OSError: pass

def analyze_images(result: dict, vision_model: str, agent_dir: str, config_path: str, limit: int | None = None, openclaw_dist: str | None = None):
    warnings = result.setdefault('warnings', [])
    downloaded = result.get('media_payload', {}).get('downloaded_images') or result.get('downloaded_images') or []
    prompt = '请用中文描述这张小红书图片的像素内容。重点识别图片里的文字、版式、主体对象、关键结论；如果是信息图/截图，请尽量提取可读文字和结构。不要编造看不到的内容。'
    descriptions = []
    image_items = downloaded[:limit] if limit else downloaded
    for idx, item in enumerate(image_items, 1):
        if isinstance(item, dict):
            descriptions.append({'index': idx, 'path': item.get('path'), 'status': 'error', 'description': '', 'error': item.get('error') or 'image_not_downloaded'})
            continue
        path = str(item)
        entry = {'index': idx, 'path': path, 'status': 'pending', 'description': '', 'error': None}
        if not Path(path).is_file():
            entry.update({'status': 'error', 'error': 'file_not_found'})
            warnings.append(f'image_{idx}_vision_failed: file_not_found {path}')
            descriptions.append(entry)
            continue
        data = describe_image(path, vision_model, agent_dir, config_path, prompt, openclaw_dist=openclaw_dist)
        if data.get('ok') and data.get('text'):
            entry.update({'status': 'success', 'description': data['text'], 'provider': data.get('provider'), 'model': data.get('model'), 'error': None})
        else:
            err = data.get('error') or 'empty_description'
            entry.update({'status': 'error', 'error': err})
            warnings.append(f'image_{idx}_vision_failed: {err}')
        descriptions.append(entry)
    result['image_descriptions'] = descriptions
    result['summaries'] = build_summaries(result.get('text_payload') or {}, descriptions)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('text')
    ap.add_argument('--download-images', action='store_true')
    ap.add_argument('--image-dir', default=None)
    ap.add_argument('--image-limit', type=int, default=12)
    ap.add_argument('--analyze-images', action='store_true')
    ap.add_argument('--vision-model', default=DEFAULT_VISION_MODEL)
    ap.add_argument('--agent-dir', default=DEFAULT_AGENT_DIR)
    ap.add_argument('--config-path', default=DEFAULT_CONFIG_PATH)
    ap.add_argument('--openclaw-dist', default=None)
    args = ap.parse_args()
    try:
        src = extract_url(args.text)
        final = expand_once(src) if 'xhslink.com' in src else src
        feed_id, token = parse_ids(final)
        if not feed_id or not token:
            raise ValueError('feed_id_or_xsec_token_not_found')
        html = fetch_html(feed_id, token)
        item = extract_state_with_node(html, feed_id)
        result = simplify(item, src, final, feed_id, token)
        if args.download_images or args.analyze_images:
            result = download_images(result, args.image_dir, args.image_limit)
        if args.analyze_images:
            result = analyze_images(result, args.vision_model, args.agent_dir, args.config_path, args.image_limit, args.openclaw_dist)
        else:
            result['summaries'] = build_summaries(result.get('text_payload') or {}, [])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e), 'warnings': [str(e)]}, ensure_ascii=False, indent=2))
        sys.exit(2)

if __name__ == '__main__':
    main()
