"""G22 exact-input follow-up. Retain untouched runtime/package gates, rerun changed tests/driver."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time,threading
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
root=a.root.resolve();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
assert not (out/'release.json').exists()
sys.path.insert(0,str(root/'tools'))
from verify_g22 import inputs,git_binding
from verify_g21 import digest
prior_path=root/'evidence/gameplay-g22/final-b/release.json';prior=json.loads(prior_path.read_text())
before=json.loads((prior_path.parent/'inputs.json').read_text())
frozen=inputs();changed=sorted(k for k in set(frozen)|set(before['source']) if frozen.get(k)!=before['source'].get(k))
expected=sorted(['tools/critical_fix_regressions/tests/'+name for name in ('historical_start.py','test_authored_assignment.py','test_gameplay_g17.py','test_generation_g11_access.py','test_generation_g3_plans.py','test_generation_g4.py','test_structure_access.py','test_structure_contract.py')]+['workbench/worker/test_buildings_w5p.py','workbench/worker/test_pools_w5o.py'])
assert changed==expected,changed
assert prior['source_stable'] and prior['production']['passed']
excluded={'focused','workbench-worker','g22-ward'}
retained=[r for r in prior['processes'] if r['name'] not in excluded]
assert all(r['passed'] for r in retained),[(r['name'],r['exit_code']) for r in retained]
assert digest(root/prior['package']['executable']['path'])==prior['package']['executable']['sha256']
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
self_copy=out/'followup-driver.py';shutil.copy2(__file__,self_copy)
additional={str(p.relative_to(root)).replace('\\','/'):digest(p) for p in (root/'evidence/gameplay-g22/recovery-input').iterdir() if p.is_file()}
manifest=dict(additional_inputs=additional,head=head,source=frozen,git_binding=git_binding(head,frozen),driver=dict(path=self_copy.name,sha256=digest(self_copy)),retained_release=dict(path='../final-b/release.json',sha256=digest(prior_path)),changed_inputs=changed)
(out/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1');env.pop('RESONANCE_PYTHON',None)
start=time.perf_counter();rows=[];write_lock=threading.RLock()
report=dict(passed=False,g22_acceptance='partial/blocked',tested_revision=head,started_utc=datetime.now(timezone.utc).isoformat(),source_manifest='inputs.json',retained_gates=[r['name'] for r in retained],retained_boundary='Only historical factory fixture bindings and explicit catalogue counts changed, in the ten listed test inputs. Full unfiltered focused and worker suites rerun. Retained production-D, genuine historical/G19-G21 loops, metadata, frontend/typecheck, host/clippy, bundle and native proofs do not execute the changed unittest fixture/count bodies. The G22 journey driver is byte-identical, and its final-b timing-guard failure remains failed. The package contains bridge.py and pinned runtime, not worker tests. All runtime/data/other driver/package hashes are exact. Separate genuine G22 checkpoint branches certify treatment/report persistence and retain the failed last return strategy; they are not stitched to the final-b fresh journey.',processes=rows,package=prior['package'],production=prior['production'],environment=prior['environment'])
def write():
    with write_lock:(out/'release.json').write_text(json.dumps(report,indent=2)+'\n')
def execute(name,command,cwd=root,timeout=3600):
    command=list(map(str,command));t=time.perf_counter();stamp=datetime.now(timezone.utc).isoformat();log=out/(name+'-output.txt');print(name,flush=True)
    with log.open('w',encoding='utf-8') as f:
        try:r=subprocess.run(command,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=0x08000000);code=r.returncode;error=None
        except subprocess.TimeoutExpired:code=2;error='bounded timeout'
    row=dict(name=name,command=command,cwd=str(cwd),start_utc=stamp,end_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-t,exit_code=code,error=error,log=log.name,log_sha256=digest(log),source_stable=inputs()==frozen)
    row['passed']=code==0 and row['source_stable']
    with write_lock:rows.append(row);write()
    return row
py=[sys.executable,'-X','utf8','-B'];write()
with ThreadPoolExecutor(max_workers=3) as pool:
    focused=pool.submit(execute,'focused',py+[root/'tools/critical_fix_regressions/verify_fixes.py','--timeout','3600','--evidence',out/'focused'])
    worker=pool.submit(execute,'workbench-worker',[root/'workbench/worker/runtime/python.exe','-X','utf8','-B','-m','unittest','discover','-s','worker','-v'],cwd=root/'workbench')
    try:
        play=out/'play'
        def stage(name,checkpoint=None):
            command=py+[root/'tools/g22_journey.py','--stage',name,'--evidence',play]
            if checkpoint:command+=['--resume',checkpoint]
            return execute('g22-'+name,command,timeout=1000)
        checkpoint=root/'evidence/gameplay-g22/recovery-input/treated.zip'
        context=root/'evidence/gameplay-g22/recovery-input/continuation-context.json'
        assert stage('revisit',checkpoint)['passed']
        command=py+[root/'tools/g22_journey.py','--stage','return','--resume',checkpoint,'--context',context,'--evidence',play]
        branch=execute('g22-return-certification',command,timeout=1000)
        report['independent_return_passed']=branch['passed']
        report['journey_passed']=False
        report['fresh_journey_failure']='final-b/play/ward: same position/HP, four-phase timing drift before local revision; no completed integrated return. Original death branches remain separately disclosed.'
    except Exception as error:report['demonstration_failure']=repr(error)
    worker_row=worker.result();focused_row=focused.result()
report.update(finished_utc=datetime.now(timezone.utc).isoformat(),final_wall_seconds=time.perf_counter()-start,source_stable=inputs()==frozen)
# A failed integrated journey remains failed; it is not relabeled a passing gate.
report['scoped_verification_passed']=focused_row['passed'] and worker_row['passed'] and report['source_stable'] and not report.get('demonstration_failure') and all(r['passed'] for r in rows if r['name']!='g22-return-certification')
report['passed']=False  # Integrated G22 acceptance remains unresolved.
report['g22_acceptance']='complete' if report['passed'] else 'partial/blocked'
write();print(json.dumps({k:report[k] for k in ('passed','scoped_verification_passed','g22_acceptance','tested_revision','final_wall_seconds')}))
raise SystemExit(0 if report['scoped_verification_passed'] else 1)
