"""Repeat the entire affected gate after two inventory-only verifier corrections."""
from pathlib import Path
import datetime,hashlib,json,os,re,subprocess,sys,time
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'roguelike').is_dir())
sys.path.insert(0,str(ROOT/'tools'))
from verify_ai_8 import inputs
old=ROOT/'.baseline/ai-8/final-a';out=ROOT/'.baseline/ai-8/final-b';out.mkdir(parents=True,exist_ok=True)
original=json.loads((old/'release.json').read_text());assert len(original['commands'])==20
assert [r['gate'] for r in original['commands'] if not r['passed']]==['focused']
before=json.loads((old/'inputs.json').read_text());frozen=inputs()
changed=sorted(k for k in set(before)|set(frozen) if before.get(k)!=frozen.get(k))
expected=['tools/critical_fix_regressions/tests/test_gameplay_g17.py','tools/critical_fix_regressions/tests/test_structure_contract.py']
assert changed==expected,changed
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
(out/'inputs.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
delta=dict(runtime_content_editor_revision=original['revision'],verification_input_revision=revision,changed=changed,
    basis='Only catalogue expectations 88->91, authored_submap 20->23, and explicit AI-8 layout membership change. Runtime, content, editor, native scripts and all other verification inputs are byte-identical. The entire affected focused gate is newly rerun; nineteen other gates retain their exact original revision/input bindings.',
    patch=subprocess.check_output(['git','diff',original['revision'],revision,'--',*changed],cwd=ROOT,text=True),
    hashes={k:dict(before=before[k],after=frozen[k]) for k in changed})
(out/'verification-input-delta.json').write_text(json.dumps(delta,indent=2),encoding='utf8')
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
command=[sys.executable,'-X','utf8','-B',str(ROOT/'tools/critical_fix_regressions/verify_fixes.py'),'--timeout','3600','--evidence',str(out/'focused')]
report=dict(original);report.update(passed=False,revision=revision,runtime_content_editor_revision=original['revision'],verification_input_delta=changed,started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_sha256=hashlib.sha256((out/'inputs.json').read_bytes()).hexdigest())
report['commands']=[dict(r,retained=True,tested_revision=original['revision'],retention_basis=delta['basis']) for r in original['commands'] if r['gate']!='focused']
(out/'release.json').write_text(json.dumps(report,indent=2),encoding='utf8');start=time.perf_counter()
with (out/'focused.log').open('w',encoding='utf8') as stream:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=3660,creationflags=0x08000000)
stable=inputs()==frozen
row=dict(gate='focused',command=command,cwd=str(ROOT),exit_code=result.returncode,seconds=time.perf_counter()-start,source_stable=stable,log_sha256=hashlib.sha256((out/'focused.log').read_bytes()).hexdigest(),passed=result.returncode==0 and stable,tested_revision=revision)
report['commands'].append(row);report['source_stable']=stable
report['passed']=stable and len(report['commands'])==20 and all(r['passed'] for r in report['commands'])
report['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(out/'release.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(dict(passed=report['passed'],runtime_revision=original['revision'],verification_input_revision=revision,focused=row)),flush=True)
raise SystemExit(0 if report['passed'] else 1)
