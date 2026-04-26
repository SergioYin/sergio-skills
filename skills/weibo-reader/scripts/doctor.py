#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, platform, shutil, subprocess, sys
from pathlib import Path
from weibo_harness import default_agent_dir, default_config_path, default_media_root, find_openclaw_dist, probe_describe_runtime, DEFAULT_VISION_MODEL


def check_writable_dir(path: Path) -> tuple[bool, str | None]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".write-test"
        test.write_text("ok")
        test.unlink()
        return True, None
    except Exception as e:
        return False, str(e)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--config-path', default=str(default_config_path()))
    ap.add_argument('--agent-dir', default=str(default_agent_dir()))
    ap.add_argument('--media-root', default=str(default_media_root()))
    ap.add_argument('--openclaw-dist', default=None)
    ap.add_argument('--vision-model', default=DEFAULT_VISION_MODEL)
    args = ap.parse_args()
    checks=[]; warnings=[]; errors=[]; paths={}

    def add(name: str, ok: bool, **extra):
        checks.append({'name': name, 'ok': bool(ok), **extra})
        if not ok:
            errors.append(extra.get('error') or f'{name} failed')

    add('python', sys.version_info >= (3, 10), version=platform.python_version(), executable=sys.executable, error=None if sys.version_info >= (3, 10) else 'python>=3.10 recommended')
    node = shutil.which('node')
    if node:
        try:
            ver = subprocess.check_output([node, '--version'], text=True, timeout=5).strip()
            add('node', True, path=node, version=ver)
        except Exception as e:
            add('node', False, path=node, error=str(e))
    else:
        add('node', False, error='node not found in PATH')

    config = Path(args.config_path).expanduser(); paths['config_path'] = str(config)
    add('openclaw_config', config.is_file(), path=str(config), error=None if config.is_file() else 'config file not found')
    agent = Path(args.agent_dir).expanduser(); paths['agent_dir'] = str(agent)
    add('agent_dir', agent.is_dir(), path=str(agent), error=None if agent.is_dir() else 'agent dir not found')
    media = Path(args.media_root).expanduser(); paths['media_root'] = str(media)
    ok, err = check_writable_dir(media); add('media_root_writable', ok, path=str(media), error=err)

    try:
        dist = find_openclaw_dist(args.openclaw_dist); paths['openclaw_dist'] = str(dist); add('openclaw_dist', True, path=str(dist))
    except Exception as e:
        dist = None; add('openclaw_dist', False, error=str(e))
    probe = probe_describe_runtime(dist if dist else args.openclaw_dist)
    paths['describe_runtime_module'] = probe.get('modulePath')
    add('describeImageFileWithModel_export', probe.get('ok'), **{k:v for k,v in probe.items() if k!='ok'})

    model_ok = '/' in args.vision_model and all(args.vision_model.split('/', 1))
    add('vision_model_configurable', model_ok, vision_model=args.vision_model, error=None if model_ok else 'vision model must be provider/model')

    result = {'success': not errors, 'checks': checks, 'warnings': warnings, 'errors': errors, 'paths': paths}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['success'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
