"""Bind scoped fixture corrections and complete their affected gates.

Retain all failed unfiltered executions. The exact edit plan permits only test
fixtures/expectations, never runtime, content or authoring behavior. Recheck all
five affected focused modules, five complete worker modules, all host tests and
the complete B2 format worker. This is not a fresh clean unfiltered run.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from verify_sys_2 import inputs,digest
ORIGINAL=ROOT/'.baseline/sys-2/final-a';OUT=ROOT/'.baseline/sys-2/expectation-final'
OUT.mkdir(parents=True,exist_ok=True)
old=json.loads((ORIGINAL/'inputs.json').read_text())
assert digest(ORIGINAL/'inputs.json')=='7ecabe4fe7eb38d7e52d9ef9d82671974aa0dece48c54debdd83a2e109a08738'
full=json.loads((ORIGINAL/'release.json').read_text())
assert 'finished_utc' in full and full['source_stable']
by={r['gate']:r for r in full['commands']}
assert {k for k,r in by.items() if not r['passed']}=={'host','production-d','focused','worker'}
for gate in ('host','production-d','focused','worker'):
    assert by[gate]['log_sha256']==digest(ORIGINAL/(gate+'.log'))
assert '70 passed; 1 failed' in (ORIGINAL/'host.log').read_text()
assert 'Ran 654 tests' in (ORIGINAL/'focused.log').read_text()
assert 'FAILED (failures=4, errors=1)' in (ORIGINAL/'focused.log').read_text()
assert {r['gate'] for r in by['worker']['modules'] if not r['passed']}=={'test_bridge','test_buildings_w5p','test_content_contracts','test_items','test_pools_w5o'}
original_results=next((ORIGINAL/'production-d').glob('*/results.json'))
result=json.loads(original_results.read_text())
assert result['totals']==dict(checks=3658,passed=3655,failed=3,workers=159)
invalid=[w for w in result['workers'] if not w['valid']]
assert len(invalid)==1 and invalid[0]['job']['scenario']=='format' and invalid[0]['job']['variant']=='contract'
plan=ROOT/'evidence/sys-2/expectation-edits.json';changes=json.loads(plan.read_text())
allowed={'workbench/src-tauri/src/authoring.rs','tools/b2_format_cases.py',
 'tools/critical_fix_regressions/tests/test_ai_4.py','tools/critical_fix_regressions/tests/test_ai_5.py',
 'tools/critical_fix_regressions/tests/test_gameplay_g17.py','tools/critical_fix_regressions/tests/test_gameplay_g21.py',
 'tools/critical_fix_regressions/tests/test_usable_supplies.py','workbench/worker/test_bridge.py',
 'workbench/worker/test_buildings_w5p.py','workbench/worker/test_content_contracts.py',
 'workbench/worker/test_items.py','workbench/worker/test_pools_w5o.py'}
assert set(changes)==allowed
for path,rows in changes.items():
    reconstructed=(ROOT/path).read_bytes()
    for row in reversed(rows):
        variants=[(row['before'].replace('\n',eol).encode(),row['after'].replace('\n',eol).encode()) for eol in ('\n','\r\n')]
        before,after=next((a,b) for a,b in variants if reconstructed.count(b)==1)
        if path.endswith('.rs'):assert reconstructed.index(after)>reconstructed.index(b'#[cfg(test)]')
        reconstructed=reconstructed.replace(after,before,1)
    assert hashlib.sha256(reconstructed).hexdigest()==old[path],path
now=inputs();changed={p for p in old.keys()|now.keys() if old.get(p)!=now.get(p)}
assert changed==allowed,changed
(OUT/'inputs.json').write_text(json.dumps(now,indent=2),encoding='utf8')
env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',
 PYTHONPATH=os.pathsep.join(map(str,[ROOT/'roguelike',ROOT/'tools/critical_fix_regressions/tests',ROOT/'tools'])))
def execute(row):
    name,cmd,cwd=row;cmd=[str(x) for x in cmd];began=time.perf_counter();log=OUT/(name+'.log')
    with log.open('w',encoding='utf8') as f:
        code=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600,creationflags=0x08000000).returncode
    result=dict(gate=name,command=cmd,cwd=str(cwd),exit_code=code,seconds=time.perf_counter()-began,source_stable=inputs()==now,log_sha256=digest(log),passed=code==0 and inputs()==now)
    print(json.dumps(result),flush=True);return result
py=[sys.executable,'-X','utf8','-B'];wb=ROOT/'workbench'
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(execute,[('host',['cargo','test','--locked','--manifest-path','src-tauri/Cargo.toml'],wb),
      ('production-format',py+[ROOT/'tools/verify_d.py','--only','b2','--case','format','--evidence',OUT/'production-format'],ROOT)]))
rows.append(execute(('focused-affected',py+['-m','unittest','-v','test_ai_4','test_ai_5','test_gameplay_g17','test_gameplay_g21','test_usable_supplies'],ROOT)))
worker_code="import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['test_bridge','test_buildings_w5p','test_content_contracts','test_items','test_pools_w5o']));sys.exit(not r.wasSuccessful())"
rows.append(execute(('worker-affected',[wb/'worker/runtime/python.exe','-X','utf8','-I','-B','-c',worker_code],wb)))
control="import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_bridge.BridgeTests.test_dependency_absence_structured'));sys.exit(not r.wasSuccessful())"
rows.append(execute(('worker-dependency-control',py+['-c',control],wb)))
selected=next((OUT/'production-format').glob('*/results.json'))
rechecked=json.loads(selected.read_text())
assert len(rechecked['workers'])==1 and rechecked['selected_tests_passed'] and not rechecked['passed']
worker=rechecked['workers'][0];assert worker['valid'] and worker['result']['completed']
assert any(c['property']=='all catalog rows retained in order' and c['passed'] for c in worker['result']['checks'])
report=dict(passed=all(r['passed'] for r in rows),revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 original_manifest_sha256=digest(ORIGINAL/'inputs.json'),original_production_result_sha256=digest(original_results),
 input_manifest_sha256=digest(OUT/'inputs.json'),source_stable=inputs()==now,script_sha256=digest(Path(__file__)),plan_sha256=digest(plan),
 commands=rows,format_totals=rechecked['totals'],format_worker_assertions=worker['result']['assertion_count'],
 changes={p:dict(before=old[p],after=now[p],edits=v) for p,v in changes.items()})
(OUT/'result.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(dict(passed=report['passed'])))
raise SystemExit(0 if report['passed'] else 1)
