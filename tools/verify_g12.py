"""Finite G12 delivery: existing unfiltered gates and the bounded real-event journey."""
import argparse
import hashlib
import importlib.metadata
import io
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
    for name in ('AGENTS.md','README.md','roguelike/docs/SYSTEMS.md','roguelike/docs/DATA_REFERENCE.md'):
        result[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'release.json').exists():p.error('Use a fresh evidence directory')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
    frozen=inputs();paths=sorted(frozen)
    stream=io.BytesIO(subprocess.check_output(['git','cat-file','--batch'],
        input=''.join(f'{head}:{path}\n' for path in paths).encode(),cwd=ROOT))
    bindings={}
    for path in paths:
        blob,kind,size=stream.readline().decode().strip().split();assert kind=='blob',path
        committed=stream.read(int(size));assert stream.read(1)==b'\n'
        raw=(ROOT/path).read_bytes();mode='exact'
        if raw!=committed:
            assert Path(path).suffix in ('.py','.js','.css','.json','.md','.hex','.html'),path
            assert raw.replace(b'\r\n',b'\n')==committed.replace(b'\r\n',b'\n'),path
            mode='CRLF-only'
        bindings[path]=dict(blob=blob,committed_sha256=hashlib.sha256(committed).hexdigest(),match=mode)
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    report=dict(passed=False,head=head,source=frozen,git_binding=bindings,checks=[],
        environment=dict(python=sys.version,executable=sys.executable,dependencies={k:importlib.metadata.version(k) for k in ('pygame','tcod','numpy')}),
        controls='Established production interpreter; full focused discovery and unfiltered D gate. Existing event driver, normal FOV/AI/survival, disclosed controlled setup, disposable saves. No wiki gate.')
    production=ROOT/'.baseline'/('g12-production-'+out.name)
    commands=[('focused',[sys.executable,'-X','utf8',str(ROOT/'tools/critical_fix_regressions/verify_fixes.py'),
        '--game',str(ROOT/'roguelike'),'--timeout','1800','--evidence',str(out/'focused')],1900),
        ('production',[sys.executable,'-X','utf8',str(ROOT/'tools/verify_d.py'),'--evidence',str(production)],3600),
        ('reward-journey',[sys.executable,'-X','utf8',str(ROOT/'tools/g12_journey.py'),'--evidence',str(out/'journey')],360)]
    for name,command,timeout in commands:
        print('G12 '+name,flush=True);start=time.perf_counter()
        try:
            with (out/(name+'-output.txt')).open('w',encoding='utf-8') as log:
                r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,env=env)
            row=dict(name=name,command=command,exit_code=r.returncode,passed=r.returncode==0)
        except subprocess.TimeoutExpired:
            row=dict(name=name,command=command,passed=False,error='finite timeout')
        row.update(seconds=time.perf_counter()-start,timeout=timeout)
        if name=='production' and (production/'latest.json').exists():
            latest=json.loads((production/'latest.json').read_text());destination=out/'production';destination.mkdir(exist_ok=True)
            shutil.copy2(Path(latest['result']),destination/'results.json')
            shutil.copy2(production/'latest.json',destination/'origin.json')
            row['receipt']='production/results.json';row['passed'] &= bool(latest['passed'])
        report['checks'].append(row);report['source_stable']=inputs()==frozen
        report['passed']=len(report['checks'])==len(commands) and all(c['passed'] for c in report['checks']) and report['source_stable']
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if not row['passed'] or not report['source_stable']:return 1
    print(json.dumps(dict(passed=True,head=head,evidence=str(out))))
    return 0


if __name__=='__main__':raise SystemExit(main())
