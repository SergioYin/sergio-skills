#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path
from weibo_harness import default_media_root


def safe_root(path: Path) -> Path:
    root = path.expanduser().resolve()
    expected = default_media_root().resolve()
    try:
        root.relative_to(expected)
    except ValueError:
        if root != expected:
            raise ValueError(f'unsafe root: {root}; must be {expected} or a child')
    if 'weibo' not in root.parts:
        raise ValueError(f'unsafe root missing weibo segment: {root}')
    return root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=float, default=7)
    ap.add_argument('--root', default=str(default_media_root()))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    warnings=[]; errors=[]; deleted_files=[]; deleted_dirs=[]; bytes_freed=0
    try:
        root = safe_root(Path(args.root))
        cutoff = time.time() - args.days * 86400
        if root.exists():
            for p in sorted(root.rglob('*'), key=lambda x: len(x.parts), reverse=True):
                try:
                    if p.is_file() and p.stat().st_mtime < cutoff:
                        size = p.stat().st_size
                        deleted_files.append(str(p)); bytes_freed += size
                        if not args.dry_run:
                            p.unlink()
                except Exception as e:
                    warnings.append(f'file_skip {p}: {e}')
            for p in sorted([x for x in root.rglob('*') if x.is_dir()], key=lambda x: len(x.parts), reverse=True):
                try:
                    if not any(p.iterdir()):
                        deleted_dirs.append(str(p))
                        if not args.dry_run:
                            p.rmdir()
                except Exception as e:
                    warnings.append(f'dir_skip {p}: {e}')
        else:
            warnings.append('root does not exist')
    except Exception as e:
        errors.append(str(e)); root = Path(args.root).expanduser()
    result = {'success': not errors, 'root': str(root), 'days': args.days, 'dry_run': args.dry_run, 'deleted_files': deleted_files, 'deleted_dirs': deleted_dirs, 'bytes_freed': bytes_freed, 'warnings': warnings, 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
