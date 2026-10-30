"""Frozen G20 release: unfiltered production gates, companion and ordinary loop.

Every worker owns disposable data/output. This script never changes source, Git,
campaigns or the desktop. Publication follows review of its source-bound receipt.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
WB=ROOT/'workbench'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    from verify_b3 import source_manifest
    result=source_manifest()
    files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    for name in files:
        if not name or not (ROOT/name).is_file():continue
        if (name.startswith(('workbench/src/','workbench/src-tauri/','workbench/scripts/','workbench/public/'))
                or name.startswith('workbench/worker/') and name.endswith('.py')
                or name in ('workbench/package.json','workbench/package-lock.json','workbench/tsconfig.json','workbench/vite.config.ts','workbench/src-tauri/Cargo.toml','workbench/src-tauri/Cargo.lock','workbench/src-tauri/build.rs','workbench/src-tauri/tauri.conf.json','workbench/src-tauri/tauri.bundle.conf.json','workbench/owner-defaults.json')):
            result[name]=digest(ROOT/name)
    for p in (WB/'worker/runtime').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:result[p.relative_to(ROOT).as_posix()]=digest(p)
    for name in ('AGENTS.md','docs/owner/TUNING_EXISTING_FEATURES.md','roguelike/docs/CREATURE_AUTHORING.md','roguelike/docs/ITEM_AUTHORING.md','roguelike/docs/AUTHORED_SUBMAP_SELECTION.md','workbench/README.md','evidence/gameplay-g20/seed-sample-declaration.json','evidence/gameplay-g20/policy-correction-1.json','evidence/gameplay-g20/scope-correction-2.json','evidence/gameplay-g20/workshop-fallback.json'):
        result[name]=digest(ROOT/name)
    return result


def git_binding(head,source):
    paths=[p for p in sorted(source) if not p.startswith('workbench/worker/runtime/')]
    stream=io.BytesIO(subprocess.check_output(['git','cat-file','--batch'],input=''.join(f'{head}:{p}\n' for p in paths).encode(),cwd=ROOT))
    result={}
    for path in paths:
        header=stream.readline().decode().strip().split();assert len(header)==3 and header[1]=='blob',(path,header)
        raw=stream.read(int(header[2]));assert stream.read(1)==b'\n'
        working=(ROOT/path).read_bytes();mode='exact'
        if raw!=working:
            assert raw.replace(b'\r\n',b'\n')==working.replace(b'\r\n',b'\n'),path
            mode='CRLF/LF only'
        result[path]=dict(blob=header[0],committed_sha256=hashlib.sha256(raw).hexdigest(),working_sha256=source[path],match=mode)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    assert sys.platform=='win32' and sys.version_info[:3]==(3,11,0),'Use tested Windows CPython 3.11.0'
    expected={'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6'}
    assert {k:importlib.metadata.version(k) for k in expected}==expected
    assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'release.json').exists(),'Use a fresh release evidence directory'
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    frozen=inputs();bindings=git_binding(head,frozen)
    (out/'inputs.json').write_text(json.dumps(dict(head=head,source=frozen,git_binding=bindings),indent=2)+'\n')
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    env.pop('RESONANCE_PYTHON',None)
    started=time.perf_counter();records=[];lock=threading.Lock()
    versions={name:subprocess.check_output([name,'--version'],text=True).strip() for name in ('node','rustc','cargo')}
    report=dict(passed=False,tested_revision=head,started_utc=datetime.now(timezone.utc).isoformat(),source_manifest='inputs.json',scope='A+B+C',processes=records,environment=dict(python=sys.version,executable=sys.executable,dependencies=expected,tools=versions),isolation='Production checkout in place. Independent gates and native/runtime fixtures own separate disposable save/output roots. No desktop input, campaign or source mutation.')
    def write():
        (out/'release.json').write_text(json.dumps(report,indent=2)+'\n')
    write()
    def execute(name,command,*,cwd=ROOT,timeout=3600,extra_env=None):
        begin=time.perf_counter();start_utc=datetime.now(timezone.utc).isoformat()
        command=[str(x) for x in command];log=out/(name+'-output.txt')
        print('G20 '+name,flush=True)
        with log.open('w',encoding='utf-8') as output:
            try:
                completed=subprocess.run(command,cwd=cwd,env=dict(env,**(extra_env or {})),stdout=output,stderr=subprocess.STDOUT,timeout=timeout,creationflags=0x08000000)
                code=completed.returncode;error=None
            except subprocess.TimeoutExpired:
                code=2;error='finite timeout'
        row=dict(name=name,command=command,cwd=str(cwd),start_utc=start_utc,end_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-begin,exit_code=code,error=error,log=log.name,log_sha256=digest(log),source_stable=inputs()==frozen)
        row['passed']=code==0 and row['source_stable']
        with lock:records.append(row);write()
        (out/(name+'-process.json')).write_text(json.dumps(row,indent=2)+'\n')
        return row
    py=[sys.executable,'-X','utf8','-B']
    production=ROOT/'.baseline'/('gameplay-g20-'+out.name)
    worker_python=WB/'worker/runtime/python.exe'
    failures=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        gates=[pool.submit(execute,'focused',py+[ROOT/'tools/critical_fix_regressions/verify_fixes.py','--timeout','3600','--evidence',out/'focused']),
               pool.submit(execute,'production-d',py+[ROOT/'tools/verify_d.py','--evidence',production]),
               pool.submit(execute,'workbench-worker',[worker_python,'-X','utf8','-B','-m','unittest','discover','-s','worker','-v'],cwd=WB)]
        try:
            checks=[('workbench-frontend',['npm.cmd','test']),('workbench-typecheck',['npm.cmd','run','typecheck']),
                    ('workbench-host',['cargo','test','--locked','--manifest-path','src-tauri/Cargo.toml']),
                    ('workbench-clippy',['cargo','clippy','--locked','--manifest-path','src-tauri/Cargo.toml','--','-D','warnings']),
                    ('workbench-bundle',['npm.cmd','run','bundle','--','--','--locked'])]
            for name,command in checks:assert execute(name,command,cwd=WB)['passed'],name
            # The separate missing-dependency control uses the production venv with -S.
            assert execute('worker-missing-dependency',py+['-m','unittest','discover','-s','worker','-p','test_bridge.py','-k','dependency_absence_structured','-v'],cwd=WB,extra_env={'RESONANCE_PYTHON':sys.executable})['passed']
            native=WB/'.artifacts/g20'/('hearing-'+out.name)
            assert execute('workbench-native-hearing',['node','scripts/run-hearing.mjs'],cwd=WB,extra_env={'G20_HEARING_OUTPUT':str(native)})['passed']
            retained=out/'workbench';retained.mkdir(exist_ok=True)
            for name in ('receipt.json','hearing-saved.png','hearing-minimum.png','hearing-0.json','hearing-4.json'):shutil.copy2(native/name,retained/name)
            report['package']=dict(executable=dict(path='workbench/src-tauri/target/release/resonance-workbench.exe',sha256=digest(WB/'src-tauri/target/release/resonance-workbench.exe')),installers=[dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p)) for p in (WB/'src-tauri/target/release/bundle/nsis').glob('*.exe')])
            for name,command in (
                ('historical-g14',py+[ROOT/'tools/g15_historical.py','--baseline',ROOT/'evidence/gameplay-g19/pre-edit-historical.json','--output',out/'historical-g14.json']),
                ('historical-g16',py+[ROOT/'tools/g17_historical.py','--baseline',ROOT/'evidence/gameplay-g17/pre-edit-historical.json','--output',out/'historical-g16.json']),
                ('g19-original-loop',py+[ROOT/'tools/verify_g19.py','--evidence',out/'g19-loop']),
                ('g20-sound-original-loop',py+[ROOT/'tools/verify_g20_sound.py','--evidence',out/'sound-loop']),
                ('content-sample',py+[ROOT/'tools/g20_content.py','--evidence',out/'content'])):
                assert execute(name,command,timeout=180)['passed'],name
            expedition=out/'expedition'
            def journey(name,stage,checkpoint=None,evidence=expedition):
                command=py+[ROOT/'tools/g20_journey.py','--stage',stage,'--evidence',evidence]
                if checkpoint:command+=['--resume',checkpoint]
                if stage!='preparation':command+=['--route',expedition/'route.json']
                assert execute(name,command,timeout=1000)['passed'],name
            journey('preparation-original-loop','preparation')
            prepared=expedition/'preparation/prepared-return.zip'
            assert execute('bounded-route-preview',py+[ROOT/'tools/g20_route.py','--checkpoint',prepared,'--output',expedition/'route.json'],timeout=180)['passed']
            journey('destination-original-loop','destination_entry',prepared)
            entry=expedition/'destination_entry/common-entry.zip'
            # Independent disposable continuations share only immutable input bytes.
            def branch(name):
                journey(name+'-original-loop',name,entry)
                exit_checkpoint=expedition/name/'altered-exit.zip'
                journey(name+'-cold-revisit-return','homeward',exit_checkpoint,expedition/(name+'-return'))
                returned=expedition/(name+'-return/homeward/returned-ward.zip')
                command=py+[ROOT/'tools/g20_owned_check.py','--checkpoint',returned,'--route',expedition/'route.json','--branch',name,'--output',expedition/(name+'-owned.json')]
                if name=='lure':command+=['--block']
                assert execute(name+'-cold-owned-block' if name=='lure' else name+'-cold-owned',command,timeout=120)['passed']
            with ThreadPoolExecutor(max_workers=2) as branches:
                tasks=[branches.submit(branch,name) for name in ('lure','musk')]
                for task in tasks:task.result()
        except Exception as error:
            failures.append(str(error));report['demonstration_failure']=repr(error);write()
        for future in gates:
            row=future.result()
            if not row['passed']:failures.append(row['name'])
    if (production/'latest.json').exists():
        latest=json.loads((production/'latest.json').read_text());shutil.copy2(latest['result'],out/'production-d.json')
        d=json.loads((out/'production-d.json').read_text())
        report['production']=dict(totals=d['totals'],runner_negative_controls=len(d.get('runner_negative_controls',[])),unfiltered=d['only'] is None and d['case'] is None,passed=d['passed'])
        assert report['production']['unfiltered'] and report['production']['runner_negative_controls']==7
    report.update(source_stable=inputs()==frozen,finished_utc=datetime.now(timezone.utc).isoformat(),final_wall_seconds=time.perf_counter()-started,failures=failures)
    report['passed']=not failures and report['source_stable'] and all(r['passed'] for r in records) and report.get('production',{}).get('passed',False)
    write();print(json.dumps(dict(passed=report['passed'],tested_revision=head,wall_seconds=report['final_wall_seconds'],failures=failures,evidence=str(out))))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
