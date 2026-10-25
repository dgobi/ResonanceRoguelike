"""Finite, source-bound G10 terrain/lifecycle, preview and ordinary-play gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    from verify_b3 import source_manifest
    result=source_manifest()
    for name in ('AGENTS.md','README.md','roguelike/docs/WILDERNESS_TERRAIN.md'):
        result[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    frozen=inputs();report=dict(passed=False,command=sys.argv,source=frozen,
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),checks=[])
    tests=ROOT/'tools/critical_fix_regressions/tests'
    env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'roguelike'),str(tests),str(ROOT/'tools')]),
        SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',
        PYTHONHASHSEED='20261024',PYTHONDONTWRITEBYTECODE='1',RESONANCE_TEST_EVIDENCE_DIR=str(out/'tests'))
    (out/'tests').mkdir(exist_ok=True)
    checks=[('terrain-lifecycle', [sys.executable,'-X','utf8','-m','unittest','test_generation_g10_terrain','test_generation_g10_lifecycle','-v'],600),
        ('diagnostic',[sys.executable,'-X','utf8',str(ROOT/'tools/worldgen_g10_diagnostic.py'),'--evidence',str(out/'diagnostic')],600),
        ('expedition',[sys.executable,'-X','utf8',str(ROOT/'tools/g10_expedition.py'),'--evidence',str(out/'expedition')],300)]
    for name,command,timeout in checks:
        print('G10 '+name,flush=True);start=time.perf_counter()
        try:
            with (out/(name+'-output.txt')).open('w',encoding='utf-8') as log:
                r=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            row=dict(name=name,command=command,timeout=timeout,seconds=time.perf_counter()-start,exit_code=r.returncode,passed=r.returncode==0)
        except subprocess.TimeoutExpired:
            row=dict(name=name,command=command,timeout=timeout,seconds=time.perf_counter()-start,passed=False,error='finite timeout')
        report['checks'].append(row);report['source_stable']=inputs()==frozen
        report['passed']=all(c['passed'] for c in report['checks']) and report['source_stable']
        (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if not row['passed'] or not report['source_stable']:return 1
    print(json.dumps(dict(passed=True,evidence=str(out))))
    return 0


if __name__=='__main__':raise SystemExit(main())
