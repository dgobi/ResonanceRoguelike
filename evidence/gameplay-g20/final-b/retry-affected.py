"""Rerun complete affected gates; explicitly bind unchanged release inputs."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from verify_g20 import inputs,git_binding,digest
old=json.loads((OUT.parent/'final-a/inputs.json').read_text())
frozen=inputs();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
changed={p for p in old['source']|frozen if old['source'].get(p)!=frozen.get(p)}
expected={'tools/critical_fix_regressions/tests/test_generation_g11_access.py','tools/critical_fix_regressions/tests/test_structure_access.py','tools/critical_fix_regressions/tests/test_structure_contract.py','workbench/worker/test_buildings_w5p.py','workbench/worker/test_pools_w5o.py'}
assert changed==expected,changed
bindings=git_binding(head,frozen)
(OUT/'inputs.json').write_text(json.dumps(dict(head=head,source=frozen,git_binding=bindings),indent=2)+'\n')
prior=json.loads((OUT.parent/'final-a/release.json').read_text())
retained=[r for r in prior['processes'] if r['name'] not in ('focused','workbench-worker')]
assert len(retained)==22 and all(r['passed'] for r in retained),(len(retained),[r['name'] for r in retained])
assert prior['source_stable'] and prior['production']['passed'] and prior['production']['unfiltered']
report=dict(passed=False,tested_revision=head,start_utc=datetime.now(timezone.utc).isoformat(),changed_inputs=sorted(changed),retained_revision=old['head'],retained_processes=retained,retained_boundary='Only five test expectations changed. Game/data, all runtime imports used by D and journeys, drivers, frontend, Rust, bundled bridge/runtime, package scripts/config/assets are byte-identical. The unfiltered focused and worker suites are fully rerun; no case is filtered, skipped or waived. Source guards remain frozen within each run.',processes=[])
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
env.pop('RESONANCE_PYTHON',None)
def run(name,command,cwd):
 start=time.perf_counter();utc=datetime.now(timezone.utc).isoformat();log=OUT/(name+'-output.txt')
 with log.open('w',encoding='utf-8') as f:
  result=subprocess.run([str(x) for x in command],cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600,creationflags=0x08000000)
 row=dict(name=name,command=[str(x) for x in command],cwd=str(cwd),start_utc=utc,end_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-start,exit_code=result.returncode,log=log.name,sha256=digest(log),source_stable=inputs()==frozen)
 row['passed']=result.returncode==0 and row['source_stable'];(OUT/(name+'-process.json')).write_text(json.dumps(row,indent=2)+'\n');return row
(OUT/'release.json').write_text(json.dumps(report,indent=2)+'\n')
start=time.perf_counter()
with ThreadPoolExecutor(max_workers=2) as pool:
 jobs=[pool.submit(run,'focused',[sys.executable,'-X','utf8','-B',ROOT/'tools/critical_fix_regressions/verify_fixes.py','--timeout','3600','--evidence',OUT/'focused'],ROOT),pool.submit(run,'workbench-worker',[ROOT/'workbench/worker/runtime/python.exe','-X','utf8','-B','-m','unittest','discover','-s','worker','-v'],ROOT/'workbench')]
 report['processes']=[job.result() for job in jobs]
report.update(end_utc=datetime.now(timezone.utc).isoformat(),wall_seconds=time.perf_counter()-start,source_stable=inputs()==frozen,artifact_sha256=digest(Path(__file__)))
report['passed']=all(r['passed'] for r in report['processes']) and report['source_stable']
(OUT/'release.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=report['passed'],head=head,seconds=report['wall_seconds'])))
raise SystemExit(0 if report['passed'] else 1)
