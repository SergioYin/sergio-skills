#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path
from xhs_harness import skill_dir
JOB_NAME='xiaohongshu-reader-cleanup'

def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=60)

def list_jobs():
    p=run(['openclaw','cron','list','--json'])
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout)
    data=json.loads(p.stdout)
    return data.get('jobs',[]), data

def find_jobs(jobs):
    return [j for j in jobs if j.get('name') == JOB_NAME]

def cleanup_message(days:int):
    # Keep the cron message portable. The agent/shell will expand ~ at run time.
    return f"Run exactly this local cleanup command and report only the JSON result: cd ~/.openclaw/workspace/skills/xiaohongshu-reader && python3 scripts/cleanup_media.py --days {days} --json"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('action', choices=['status','install','uninstall'])
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--cron', default='0 3 * * *')
    ap.add_argument('--disabled', action='store_true', help='Create disabled. Recommended for first install.')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    warnings=[]; errors=[]; actions=[]
    try:
        jobs, raw=list_jobs(); matches=find_jobs(jobs)
        if args.action == 'status':
            pass
        elif args.action == 'install':
            if matches:
                warnings.append('job already exists; not creating duplicate')
            else:
                cmd=['openclaw','cron','add','--name',JOB_NAME,'--cron',args.cron,'--message',cleanup_message(args.days),'--json']
                if args.disabled: cmd.append('--disabled')
                actions.append({'cmd':cmd[:-1]+['<json>']})
                if not args.dry_run:
                    p=run(cmd)
                    if p.returncode != 0: raise RuntimeError(p.stderr or p.stdout)
                    actions[-1]['result']=json.loads(p.stdout)
        elif args.action == 'uninstall':
            if not matches:
                warnings.append('job not found')
            for j in matches:
                jid=j.get('id') or j.get('jobId') or j.get('name')
                cmd=['openclaw','cron','rm',str(jid),'--json']
                actions.append({'cmd':cmd})
                if not args.dry_run:
                    p=run(cmd)
                    if p.returncode != 0: raise RuntimeError(p.stderr or p.stdout)
                    try: actions[-1]['result']=json.loads(p.stdout)
                    except Exception: actions[-1]['result']=p.stdout
        jobs2, _ = list_jobs()
        matches2=find_jobs(jobs2)
    except Exception as e:
        errors.append(str(e)); matches=[]; matches2=[]
    result={'success': not errors, 'name': JOB_NAME, 'action': args.action, 'dry_run': args.dry_run, 'existing_before': matches, 'existing_after': matches2, 'message': cleanup_message(args.days), 'actions': actions, 'warnings': warnings, 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result['success'] else 2)
if __name__=='__main__': main()
