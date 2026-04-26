#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from weibo_harness import default_example_input, default_media_root, skill_dir


def is_under(child: str, root: Path) -> bool:
    try:
        Path(child).resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--no-vision', action='store_true')
    g.add_argument('--vision', action='store_true')
    ap.add_argument('--input', default=str(default_example_input()))
    ap.add_argument('--no-download-images', action='store_true')
    ap.add_argument('--image-limit', type=int, default=1)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    tests=[]; warnings=[]; errors=[]; artifacts={}

    text = Path(args.input).read_text().strip()
    cmd = [sys.executable, str(skill_dir()/'scripts'/'read_weibo_link.py')]
    if args.vision:
        cmd += ['--analyze-images', '--image-limit', str(args.image_limit)]
    elif args.no_download_images:
        cmd.append('--no-download-images')
    cmd.append(text)
    proc = subprocess.run(cmd, text=True, capture_output=True, cwd=str(skill_dir()), timeout=420)
    artifacts['command'] = ' '.join(cmd[:-1] + ['<input>'])
    artifacts['returncode'] = proc.returncode
    if proc.returncode != 0:
        errors.append(f'reader exited {proc.returncode}: {proc.stderr[-1000:]}')
    try:
        data = json.loads(proc.stdout)
    except Exception as e:
        data = {}
        errors.append(f'non-json reader output: {e}; stdout={proc.stdout[-1000:]}')

    def check(name: str, ok: bool, detail=None):
        tests.append({'name': name, 'ok': bool(ok), 'detail': detail})
        if not ok:
            errors.append(detail or f'{name} failed')

    artifacts['status_id'] = data.get('status_id')
    artifacts['author'] = (data.get('author') or {}).get('screen_name')
    artifacts['text_length'] = data.get('text_length')
    artifacts['downloaded_images'] = data.get('downloaded_images')
    artifacts['warnings'] = data.get('warnings')

    check('success_true', data.get('success') is True)
    check('status_id_exists', bool(data.get('status_id')), data.get('status_id'))
    check('author_exists', bool((data.get('author') or {}).get('screen_name')), data.get('author'))
    check('text_nonempty', isinstance(data.get('text'), str) and len(data.get('text', '').strip()) > 50, (data.get('text') or '')[:120])
    check('text_payload_exists', isinstance(data.get('text_payload'), dict) and bool(data.get('text_payload')))
    check('media_payload_exists', isinstance(data.get('media_payload'), dict) and bool(data.get('media_payload')))
    check('summaries_exists', isinstance(data.get('summaries'), dict) and bool(data.get('summaries')))

    if not args.no_download_images:
        imgs = [x for x in (data.get('downloaded_images') or []) if isinstance(x, str)]
        root = default_media_root()
        check('downloaded_images_exist', bool(imgs) and all(Path(x).is_file() for x in imgs), imgs)
        check('downloaded_images_under_workspace_media', bool(imgs) and all(is_under(x, root) for x in imgs), {'root': str(root), 'images': imgs})

    if args.vision:
        desc = data.get('image_descriptions') or []
        check('image_descriptions_success', any(x.get('status') == 'success' and x.get('description') for x in desc), [{'status': x.get('status'), 'error': x.get('error')} for x in desc])

    result = {'success': not errors, 'tests': tests, 'warnings': warnings + (data.get('warnings') or []), 'errors': errors, 'artifacts': artifacts}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
