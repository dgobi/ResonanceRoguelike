"""Finite G11 delivery: existing full gates plus the two disclosed journeys."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    result=source_manifest()
    for name in ('AGENTS.md','README.md','roguelike/docs/WILDERNESS_TERRAIN.md'):
        result[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'release.json').exists():p.error('Use a fresh evidence directory; do not overwrite a release')
    frozen=inputs();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    # Bind every raw input to its committed clean-filtered blob as well as SHA256.
    paths=sorted(frozen)
    actual=subprocess.check_output(['git','hash-object','--stdin-paths'],input='\n'.join(paths)+'\n',cwd=ROOT,text=True).splitlines()
    committed={line.split('\t',1)[1]:line.split()[1] for line in subprocess.check_output(['git','ls-tree','-r',head],cwd=ROOT,text=True).splitlines()}
    assert all(committed.get(path)==blob for path,blob in zip(paths,actual)),'Freeze all runtime/test inputs in a commit first'
    production=ROOT/'.baseline'/('g11-production-'+out.name)
    report=dict(passed=False,head=head,source=frozen,git_blobs=dict(zip(paths,actual)),checks=[],
        environment=dict(python=sys.version,executable=sys.executable,dependencies={k:importlib.metadata.version(k) for k in ('pygame','tcod','numpy')}),
        controls='Unfiltered focused and production gates; app-local journeys; disposable saves only; no wiki gate.')
    commands=[('focused',[sys.executable,'-X','utf8',str(ROOT/'tools/critical_fix_regressions/verify_fixes.py'),
                          '--game',str(ROOT/'roguelike'),'--timeout','1800','--evidence',str(out/'focused')],1900),
              ('production',[sys.executable,'-X','utf8',str(ROOT/'tools/verify_d.py'),'--evidence',str(production)],3600),
              ('access-journey',[sys.executable,'-X','utf8',str(ROOT/'tools/g11_journey.py'),'--evidence',str(out/'journey')],300),
              ('ordinary-excursion',[sys.executable,'-X','utf8',str(ROOT/'tools/g10_expedition.py'),'--evidence',str(out/'ordinary')],300)]
    for name,command,timeout in commands:
        print('G11 '+name,flush=True);start=time.perf_counter()
        try:
            with (out/(name+'-output.txt')).open('w',encoding='utf-8') as log:
                r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            row=dict(name=name,command=command,exit_code=r.returncode,passed=r.returncode==0)
        except subprocess.TimeoutExpired:
            row=dict(name=name,command=command,passed=False,error='finite timeout')
        row.update(seconds=time.perf_counter()-start,timeout=timeout)
        if name=='production' and (production/'latest.json').exists():
            latest=json.loads((production/'latest.json').read_text());result=Path(latest['result'])
            destination=out/'production';destination.mkdir(exist_ok=True)
            shutil.copy2(result,destination/'results.json')
            shutil.copy2(production/'latest.json',destination/'origin.json')
            row['receipt']='production/results.json'
            row['passed'] &= bool(latest['passed'])
        report['checks'].append(row);report['source_stable']=inputs()==frozen
        report['passed']=len(report['checks'])==len(commands) and all(c['passed'] for c in report['checks']) and report['source_stable']
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if not row['passed'] or not report['source_stable']:return 1
    print(json.dumps(dict(passed=True,head=head,evidence=str(out))))
    return 0


if __name__=='__main__':raise SystemExit(main())
