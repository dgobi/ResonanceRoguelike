from pathlib import Path
import argparse,datetime,hashlib,importlib.metadata,json,os,re,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from verify_g21 import inputs,git_binding,digest
out=ROOT/'evidence/gameplay-g21/final-e';out.mkdir(parents=True,exist_ok=True)
assert not (out/'release.json').exists()
old=json.loads((ROOT/'evidence/gameplay-g21/final-c/inputs.json').read_text())
prior=json.loads((ROOT/'evidence/gameplay-g21/final-c/release.json').read_text())
frozen=inputs();head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
changed=sorted(k for k in set(frozen)|set(old['source']) if frozen.get(k)!=old['source'].get(k))
expected=['tools/critical_fix_regressions/tests/test_generation_g10_lifecycle.py','tools/critical_fix_regressions/tests/test_generation_g11_lifecycle.py']
assert changed==expected,changed
assert prior['source_stable'] and prior['production']['passed'] and prior['production']['unfiltered'] and prior['production']['runner_negative_controls']==7
retained=[r for r in prior['processes'] if r['name']!='focused'];assert all(r['passed'] for r in retained)
assert sys.platform=='win32' and sys.version_info[:3]==(3,11,0)
versions={k:importlib.metadata.version(k) for k in ('pygame','tcod','numpy')};assert versions=={'pygame':'2.6.1','tcod':'19.3.0','numpy':'2.4.6'}
shutil.copy2(__file__,out/'recheck.py');driver_hash=digest(Path(__file__))
(out/'inputs.json').write_text(json.dumps(dict(head=head,source=frozen,git_binding=git_binding(head,frozen),changed_since_final_c=changed,unchanged_input_boundary='Only these two focused historical test inputs differ. All game runtime/data, guides, original-loop/runtime probes, release/production drivers, worker/frontend/Rust/bridge/bundled runtime/package inputs are byte-identical. None of the retained gates imports these regression modules; only focused discovery executes them. The immutable archives and fingerprint validator are unchanged.',retained=[dict(name=r['name'],receipt='../final-c/'+r['name']+'-process.json',receipt_sha256=digest(ROOT/'evidence/gameplay-g21/final-c'/(r['name']+'-process.json')),command=r['command']) for r in retained],recheck_driver_sha256=driver_hash),indent=2)+'\n')
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1');env.pop('RESONANCE_PYTHON',None)
command=[sys.executable,'-X','utf8','-B',str(ROOT/'tools/critical_fix_regressions/verify_fixes.py'),'--timeout','3600','--evidence',str(out/'focused')]
started=time.perf_counter();report=dict(passed=False,tested_input_revision=head,retained_runtime_input_revision=old['head'],started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,cwd=str(ROOT),environment=dict(python=sys.version,executable=sys.executable,dependencies=versions),retained_release='../final-c/release.json',source_manifest='inputs.json',production=prior['production'],package=prior['package'])
def write():(out/'release.json').write_text(json.dumps(report,indent=2)+'\n')
write()
with (out/'focused-output.txt').open('w',encoding='utf-8') as log:
 result=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=3650,creationflags=0x08000000)
run=json.loads((out/'focused/run.json').read_text());text=(out/'focused-output.txt').read_text(encoding='utf-8');count=re.search(r'Ran (\d+) tests',text)
report.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),rerun_wall_seconds=time.perf_counter()-started,exit_code=result.returncode,source_stable=inputs()==frozen and digest(Path(__file__))==driver_hash,focused_tests=int(count.group(1)) if count else None,focused_log_sha256=digest(out/'focused-output.txt'),retained_gate_count=len(retained),retained_worker_skip='One pre-existing embedded-interpreter dependency control skip; separate production-interpreter control passed.')
report['passed']=result.returncode==0 and run['passed'] and report['source_stable'] and report['focused_tests']==429
write();print(json.dumps(report));raise SystemExit(0 if report['passed'] else 1)
