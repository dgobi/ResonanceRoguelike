"""Retain full SYS-4 gates across one inspection-only placement-preview guard.

Inverse-reconstruct the only changed consumed input, then run complete SYS-4/G20
modules, ordinary play, packaged SYS-4, every worker module and dependency control.
This is full execution plus complete affected rechecks, not a clean full rerun.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
import hashlib,importlib.metadata,json,os,re,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from verify_sys_4 import inputs,digest
ORIGINAL=ROOT/'.baseline/sys-4/final-b';OUT=ROOT/'.baseline/sys-4/guard-final-a'
old=json.loads((ORIGINAL/'inputs.json').read_text())
assert digest(ORIGINAL/'inputs.json')=='e2e291d71dac3b949c787708cb875a93624f087a4cea19b47807721749b60e6a'
full=json.loads((ORIGINAL/'release.json').read_text())
assert full.get('finished_utc') and full['source_stable']
assert full['revision']=='4f1e41ebc3ca85cc0ac1b476693198b957d24fa3'
assert sys.executable==full['environment']['python_executable'] and sys.version==full['environment']['python']
assert all(importlib.metadata.version(k)==v for k,v in full['environment']['dependencies'].items())
by={r['gate']:r for r in full['commands']}
assert len(by)==18 and {k for k,r in by.items() if not r['passed']}=={'worker'}
assert {r['gate'] for r in by['worker']['modules'] if not r['passed']}=={'test_furnishings'}
assert by['worker']['tests']==141 and len(by['worker']['cohort'])==28
for gate,row in by.items():
    assert row['source_stable'] and digest(ORIGINAL/(gate+'.log'))==row['log_sha256']
    for m in row.get('modules',[]):
        assert m['source_stable'] and digest(ORIGINAL/(m['gate']+'.log'))==m['log_sha256']
assert 'Ran 691 tests' in (ORIGINAL/'focused.log').read_text(encoding='utf8')
production_path=next((ORIGINAL/'production-d').glob('*/results.json'))
production=json.loads(production_path.read_text())
assert production['passed'] and production['totals']==dict(checks=3704,passed=3704,failed=0,workers=159)
assert production['only'] is None and production['case'] is None
assert all(old[k]==v for k,v in production['source'].items())
for package in [full['package'],*full['installers']]:assert digest(ROOT/package['path'])==package['sha256']
plan_path=ROOT/'evidence/sys-4/guard-recheck-plan.json';plan=json.loads(plan_path.read_text())
path=plan['path'];assert path=='roguelike/generation/authored_rooms.py' and plan['before_sha256']==old[path]
reconstructed=(ROOT/path).read_bytes()
variants=[(plan['before'].replace('\n',eol).encode(),plan['after'].replace('\n',eol).encode()) for eol in ('\n','\r\n')]
before,after=next((a,b) for a,b in variants if reconstructed.count(b)==1)
assert hashlib.sha256(reconstructed.replace(after,before,1)).hexdigest()==old[path]
now=inputs();assert len(now)==1284 and {p for p in old.keys()|now.keys() if old.get(p)!=now.get(p)}=={path}
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert subprocess.check_output(['git','rev-parse','HEAD^'],cwd=ROOT,text=True).strip()==full['revision']
assert not OUT.exists(),'Preserve previous evidence; declare a fresh boundary.'
OUT.mkdir(parents=True);(OUT/'focused').mkdir()
(OUT/'inputs.json').write_text(json.dumps(now,indent=2),encoding='utf8')
started=datetime.now(timezone.utc).isoformat()
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',
    PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
    SYS1_RUNTIME_ONLY='1',SYS2_RUNTIME_ONLY='1',SYS3_RUNTIME_ONLY='1',SYS4_RUNTIME_ONLY='1')
def execute(name,command,cwd=ROOT):
    command=[str(x) for x in command];began=time.perf_counter();log=OUT/(name+'.log')
    call_env=dict(env)
    if name=='focused-affected':
        call_env.update(RESONANCE_GAME_ROOT=str(ROOT/'roguelike'),
            RESONANCE_TEST_TOOLS=str(ROOT/'tools/critical_fix_regressions/historical_tools'),
            RESONANCE_TEST_EVIDENCE_DIR=str(OUT/'focused'),
            PYTHONPATH=os.pathsep.join(map(str,[ROOT/'roguelike',ROOT/'tools',ROOT/'tools/critical_fix_regressions/tests'])))
    with log.open('w',encoding='utf8') as stream:
        try:
            code=subprocess.run(command,cwd=cwd,env=call_env,stdout=stream,stderr=subprocess.STDOUT,
                timeout=3600,creationflags=0x08000000).returncode;error=None
        except subprocess.TimeoutExpired:code=2;error='finite timeout'
    row=dict(gate=name,command=command,cwd=str(cwd),exit_code=code,error=error,seconds=time.perf_counter()-began,
        source_stable=inputs()==now,log_sha256=digest(log),tests=sum(map(int,re.findall(r'Ran (\d+) tests?',log.read_text(encoding='utf8')))))
    row['passed']=code==0 and row['source_stable'];print(json.dumps(row),flush=True);return row
py=[sys.executable,'-X','utf8','-B'];wb=ROOT/'workbench'
with ThreadPoolExecutor(max_workers=3) as pool:
    jobs=[pool.submit(execute,'focused-affected',py+['-m','unittest','-v','test_sys_4','test_gameplay_g20']),
          pool.submit(execute,'play',py+[ROOT/'tools/verify_sys_4_play.py','--evidence',OUT/'play']),
          pool.submit(execute,'native',['node','scripts/run-sys-4.mjs'],wb)]
    rows=[job.result() for job in jobs]
names=sorted(p.stem for p in (wb/'worker').glob('test_*.py'))
assert names==by['worker']['cohort']
prior={m['gate']:m for m in by['worker']['modules']}
with ThreadPoolExecutor(max_workers=2) as pool:
    workers=list(pool.map(lambda name:execute(name,prior[name]['command'],wb),names))
worker_log=OUT/'worker.log';worker_log.write_text(''.join((OUT/(name+'.log')).read_text(encoding='utf8') for name in names),encoding='utf8')
worker=dict(gate='worker',cohort=names,modules=workers,tests=sum(r['tests'] for r in workers),
    passed=all(r['passed'] for r in workers),source_stable=inputs()==now,log_sha256=digest(worker_log))
rows.append(worker)
rows.append(execute('worker-dependency-control',by['worker-dependency-control']['command'],wb))
report=dict(passed=all(r['passed'] for r in rows),revision=head,started_utc=started,
    finished_utc=datetime.now(timezone.utc).isoformat(),source_stable=inputs()==now,
    original_manifest_sha256=digest(ORIGINAL/'inputs.json'),original_release_sha256=digest(ORIGINAL/'release.json'),
    original_production_result_sha256=digest(production_path),input_manifest_sha256=digest(OUT/'inputs.json'),
    script_sha256=digest(Path(__file__)),plan_sha256=digest(plan_path),commands=rows,
    changes={path:dict(before=old[path],after=now[path],reason=plan['reason'],before_text=plan['before'],after_text=plan['after'])},
    retained_gates=[name for name in by if name not in {'worker','worker-dependency-control','native','play'}],
    interpretation='Retained complete final-b execution plus complete affected rechecks. Only one guard in the game-owned authoring validator changed: placement preview requires a compiled structure catalogue. Production DataLoader instances already have that catalogue; diagnostic partial snapshots cannot run placement. Original failures and all source/log hashes are retained. The full worker cohort, complete SYS-4/G20 modules, ordinary journey and packaged SYS-4 are rerun; overlapping test counts are not added. This is not a fresh clean unfiltered full execution.')
(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':report['passed'],'revision':head}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
