#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from xhs_harness import default_media_root, skill_dir

def is_under(child: str, root: Path) -> bool:
    try:
        Path(child).resolve().relative_to(root.resolve()); return True
    except Exception: return False

def main():
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group()
    g.add_argument('--no-vision', action='store_true')
    g.add_argument('--vision', action='store_true')
    ap.add_argument('--image-limit', type=int, default=1)
    ap.add_argument('--input', default=str(skill_dir()/'examples'/'rag_note_input.txt'))
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    tests=[]; warnings=[]; errors=[]; artifacts={}
    text=Path(args.input).read_text().strip()
    cmd=[sys.executable, str(skill_dir()/'scripts'/'read_xhs_link.py')]
    if args.vision: cmd += ['--analyze-images']
    else: cmd += ['--download-images']
    cmd += ['--image-limit', str(args.image_limit), text]
    proc=subprocess.run(cmd, text=True, capture_output=True, cwd=str(skill_dir()), timeout=420)
    artifacts['command']=' '.join(cmd[:-1]+['<input>'])
    artifacts['returncode']=proc.returncode
    if proc.returncode != 0:
        errors.append(f'reader exited {proc.returncode}: {proc.stderr[-1000:]}')
    try:
        data=json.loads(proc.stdout)
    except Exception as e:
        data={}; errors.append(f'non-json reader output: {e}; stdout={proc.stdout[-1000:]}')
    artifacts['title']=data.get('text_payload',{}).get('title')
    artifacts['downloaded_images']=data.get('media_payload',{}).get('downloaded_images')
    artifacts['warnings']=data.get('warnings')
    def check(name, ok, detail=None):
        tests.append({'name':name,'ok':bool(ok),'detail':detail})
        if not ok: errors.append(detail or f'{name} failed')
    check('success_true', data.get('success') is True)
    check('text_payload_exists', isinstance(data.get('text_payload'), dict) and bool(data.get('text_payload')))
    check('media_payload_exists', isinstance(data.get('media_payload'), dict) and bool(data.get('media_payload')))
    imgs=[x for x in (data.get('media_payload',{}).get('downloaded_images') or []) if isinstance(x,str)]
    check('downloaded_images_exist', bool(imgs) and all(Path(x).is_file() for x in imgs), imgs)
    root=default_media_root()
    check('downloaded_images_under_workspace_media', bool(imgs) and all(is_under(x, root) for x in imgs), {'root':str(root),'images':imgs})
    combined=data.get('summaries',{}).get('combined_summary')
    check('combined_summary_nonempty', isinstance(combined,str) and len(combined.strip())>20, combined[:120] if isinstance(combined,str) else None)
    if args.vision:
        desc=data.get('image_descriptions') or []
        check('image_descriptions_success', any(x.get('status')=='success' and x.get('description') for x in desc), [{'status':x.get('status'),'error':x.get('error')} for x in desc])
    result={'success': not errors, 'tests': tests, 'warnings': warnings + (data.get('warnings') or []), 'errors': errors, 'artifacts': artifacts}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['success'] else 2)
if __name__=='__main__': main()
