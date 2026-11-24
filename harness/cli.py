"""Independent Sah scaffold/harness. Offline inventory != application conformance."""
import argparse, json, os, re, subprocess, sys, time, pathlib, datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parent
STAGES=tuple(range(1,13))

def emit_report(repo,report):
    out=repo/'runs'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True,exist_ok=True)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Report:',out/'report.json')

def check(repo):
    problems=[]
    required=['README.md','FACTORY.md','MASTER_PROMPT.md','AGENTS.md','agents/roster.json','challenges/sah/manifest.json','docs/git-protocol.md']
    required += [f'challenges/sah/spec/stage-{n:02d}.md' for n in STAGES]
    required += [f'stage-{n:02d}/RUN.md' for n in STAGES]
    for p in required:
        if not (repo/p).is_file():problems.append('missing: '+p)
    try:
        manifest=json.loads((repo/'challenges/sah/manifest.json').read_text())
        assert len(manifest['stages'])==12
        seats=json.loads((repo/'agents/roster.json').read_text())
        for seat in seats:
            n=seat['seat']; p=repo/'mandates'/f'{n}.md'
            if not p.exists():problems.append(f'missing mandate: {n}')
            else:
                s=p.read_text();
                if not re.search(r'(?m)^Harness: .+',s) or not re.search(r'(?m)^Model: .+',s):problems.append(f'mandate runtime/model missing: {n}')
    except Exception as e:problems.append(f'bad manifest or roster: {e}')
    # Restrict scan to tracked-like source files only and exclude .git, runs, vendor packages.
    from fnmatch import fnmatch
    secret_patterns=[('github PAT',r'gh[pousr]_[A-Za-z0-9]{20,}'),('AWS access key',r'AKIA[A-Z0-9]{16}'),('OpenAI-style key',r'sk-[A-Za-z0-9_-]{20,}')]
    for p in repo.rglob('*'):
        if not p.is_file() or any(x in p.parts for x in ('.git','runs','node_modules','.venv','__pycache__','test-results')): continue
        if p.name.startswith('.env') and p.name!='.env.example':problems.append(f'secrets file exists: {p.relative_to(repo)}');continue
        if p.suffix not in ('.md','.json','.py','.yml','.yaml','.js','.ts','.txt','.sh','.ps1') and p.name not in ('Dockerfile',): continue
        if p.stat().st_size>500_000:continue
        s=p.read_text(encoding='utf-8',errors='ignore')
        for label,regex in secret_patterns:
            if re.search(regex,s):problems.append(f'potential {label}: {p.relative_to(repo)}')
    return problems

def get_json(base,path):
    with urlopen(Request(base.rstrip('/')+path,headers={'Accept':'application/json'}),timeout=5) as response:
        body=response.read(524288)
        return response.status,json.loads(body.decode())

def stage_test(base,stage):
    # This is intentionally the starter smoke only. Product-specific acceptance tests
    # MUST be written independently before a stage may be certified PASS.
    result={'stage':stage,'smoke':'fail','acceptance':'UNIMPLEMENTED','reasons':[]}
    try:
        code,data=get_json(base,'/health')
        if code==200 and isinstance(data,dict) and data.get('status')=='ok':result['smoke']='pass'
        else:result['reasons'].append('/health must return 200 {"status":"ok"}')
    except Exception as e:result['reasons'].append('/health unreachable or invalid JSON: '+str(e))
    if stage==1:
        try:
            code,data=get_json(base,'/version')
            if code!=200 or not isinstance(data,dict):result['reasons'].append('/version must return JSON object')
        except Exception as e:result['reasons'].append('/version missing or invalid: '+str(e))
    # No stage is certified with placeholders, even when smoke works.
    result['status']='INCOMPLETE'
    return result

def main():
    parser=argparse.ArgumentParser(prog='python -m harness',description='Sah staged factory scaffold')
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('check');p.add_argument('--repo',default='.')
    p=sub.add_parser('run');p.add_argument('--repo',default='.');p.add_argument('--stage',type=int,choices=STAGES);p.add_argument('--all',action='store_true');p.add_argument('--base-url',default='http://127.0.0.1:8080')
    args=parser.parse_args();repo=pathlib.Path(args.repo).resolve()
    if args.action=='check':
        issues=check(repo)
        if issues:
            for x in issues:print('FAIL',x)
            return 1
        print('PASS scaffold integrity only. This does NOT test the application.')
        return 0
    if not args.all and args.stage is None:parser.error('run requires --stage N or --all')
    stages=STAGES if args.all else tuple(range(1,args.stage+1))
    start=time.time();results=[stage_test(args.base_url,i) for i in stages]
    report={'schema_version':1,'track':'sah','type':'starter-smoke-NOT-acceptance','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'results':results,'highest_contiguous_certified_stage':0,'elapsed_seconds':round(time.time()-start,3),'warning':'Stage-specific independent acceptance suites have not yet been implemented. No stage may be marked PASS based on this harness scaffold.'}
    emit_report(repo,report)
    for r in results:print(f"stage {r['stage']:02d}: {r['status']}; smoke={r['smoke']}; acceptance={r['acceptance']}")
    print('No certified passing stage: acceptance tests still required.')
    return 2

if __name__=='__main__':raise SystemExit(main())
