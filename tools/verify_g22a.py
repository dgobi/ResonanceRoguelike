"""Freeze and verify the bounded G22A correction in the production checkout."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs():
    from verify_g22 import inputs as previous
    result=previous()
    result['evidence/gameplay-g22a/declaration.json']=digest(ROOT/'evidence/gameplay-g22a/declaration.json')
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args()
    assert sys.platform=='win32' and sys.version_info[:3]==(3,11,0)
    expected={'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6'}
    assert {k:importlib.metadata.version(k) for k in expected}==expected
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
    out=a.evidence.resolve()
    out.mkdir(parents=True,exist_ok=True)
    assert not (out/'release.json').exists(),'Fresh output required'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    frozen=inputs()
    from verify_g22 import git_binding
    (out/'inputs.json').write_text(json.dumps(dict(head=head,source=frozen,git_binding=git_binding(head,frozen)),indent=2)+'\n')
    old=json.loads((ROOT/'evidence/gameplay-g22/final-c/inputs.json').read_text())['source']
    changed=[p for p in old if p not in frozen or old[p]!=frozen[p]]
    assert changed==['tools/g22_journey.py'],changed
    retained=json.loads((ROOT/'evidence/gameplay-g22/final-c/release.json').read_text())
    retained_names=[n for n in retained['retained_gates'] if n not in ('g22-read','g22-preparation','production-d')]
    retained_names.append('workbench-worker (final-c full suite)')
    package=retained['package']
    assert digest(ROOT/package['executable']['path'])==package['executable']['sha256']
    for row in package['installers']:
        assert digest(ROOT/row['path'])==row['sha256']
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',
        PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    started=time.perf_counter()
    records=[]
    lock=threading.Lock()
    report=dict(passed=False,tested_revision=head,started_utc=datetime.now(timezone.utc).isoformat(),
        environment=dict(platform=sys.platform,python=sys.version,executable=sys.executable,dependencies=expected),
        source_manifest='inputs.json',changed_previous_inputs=changed,added_inputs=sorted(set(frozen)-set(old)),
        retained_gates=retained_names,retained_package=package,
        retained_boundary='All prior 2,881 inputs (1,072 committed-source bindings plus pinned worker runtime) except tools/g22_journey.py are byte-identical. New inputs are G22A test-player, release driver, focused tests and declaration. No runtime, data, Workbench worker/frontend/host/native/package input changed. Retained commands do not execute either G22 journey driver or the new focused test. Thus final-b frontend/typecheck/host/clippy/Windows NSIS/native/hearing/rivals/reports and historical G14/G16/G19-G21/metadata plus final-c full worker are retained only for their unchanged coverage. Current unfiltered focused/production-D and connected/cold checks run below. Retained Windows package hashes are checked, not called a rebuild.',
        processes=records,isolation='Original production checkout; disposable saves and headless app-local events. No desktop or owner campaign access.')
    def write():
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n')
    def execute(name,command,timeout=3600):
        begin=time.perf_counter()
        log=out/(name+'-output.txt')
        command=[str(v) for v in command]
        with log.open('w',encoding='utf-8') as stream:
            try:
                completed=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,
                    timeout=timeout,creationflags=0x08000000)
                code,error=completed.returncode,None
            except subprocess.TimeoutExpired:
                code,error=2,'finite timeout'
        row=dict(name=name,command=command,exit_code=code,error=error,seconds=time.perf_counter()-begin,
            log=log.name,log_sha256=digest(log),source_stable=inputs()==frozen)
        row['passed']=code==0 and row['source_stable']
        with lock:
            records.append(row)
            write()
        print(json.dumps(row),flush=True)
        return row
    write()
    py=[sys.executable,'-X','utf8','-B']
    production=ROOT/'.baseline'/('gameplay-g22a-'+out.name)
    with ThreadPoolExecutor(max_workers=3) as pool:
        focused=pool.submit(execute,'focused',py+[ROOT/'tools/critical_fix_regressions/verify_fixes.py','--timeout','3600','--evidence',out/'focused'])
        full=pool.submit(execute,'production-d',py+[ROOT/'tools/verify_d.py','--evidence',production])
        journey=execute('connected',py+[ROOT/'tools/g22a_journey.py','--evidence',out/'play'],1000)
        if journey['passed']:
            archive=out/'play/connected/returned-ward.zip'
            execute('cold-audit',py+[ROOT/'tools/g22a_journey.py','--cold',archive,'--evidence',out],180)
        focused.result()
        full.result()
    if (production/'latest.json').exists():
        latest=json.loads((production/'latest.json').read_text())
        shutil.copy2(latest['result'],out/'production-d.json')
        d=json.loads((out/'production-d.json').read_text())
        report['production']=dict(passed=d['passed'],totals=d['totals'],
            runner_negative_controls=len(d.get('runner_negative_controls',[])),unfiltered=d['only'] is None and d['case'] is None)
        assert report['production']['unfiltered'] and report['production']['runner_negative_controls']==7
    report.update(source_stable=inputs()==frozen,finished_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-started)
    report['journey_passed']=journey['passed']
    report['passed']=report['source_stable'] and len(records)==4 and all(r['passed'] for r in records)
    report['status']='complete bounded G22A witness' if report['passed'] else 'partial/blocked'
    write()
    print(json.dumps(dict(passed=report['passed'],status=report['status'],seconds=report['seconds'])))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
