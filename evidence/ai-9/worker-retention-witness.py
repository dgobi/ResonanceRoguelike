"""Repeat the complete affected worker cohort after the exact five-room list fix.

Preserve successful frozen gates on their original inputs. This report artifact
binds its own source separately and permits exactly one consumed test-file delta.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import argparse, hashlib, json, os, re, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];WB=ROOT/'workbench'
sys.path.insert(0,str(ROOT/'tools'))
from verify_ai_9 import inputs


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True)
    args=ap.parse_args();original=args.original.resolve();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'worker.json').exists()
    read=lambda p:json.loads(p.read_bytes());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    release=read(original/'release.json');before=read(original/'inputs.json');frozen=inputs()
    assert release['finished_utc'] and release['source_stable'] and len(release['commands'])==22
    assert [r['gate'] for r in release['commands'] if not r['passed']]==['worker']
    initial_worker=next(r for r in release['commands'] if r['gate']=='worker')
    assert [r['gate'] for r in initial_worker['modules'] if not r['passed']]==['test_authoring']
    changed=[p for p in sorted(set(before)|set(frozen)) if before.get(p)!=frozen.get(p)]
    assert changed==['workbench/worker/test_authoring.py'],changed
    old=subprocess.check_output(['git','show',release['revision']+':'+changed[0]],cwd=ROOT,text=True)
    new=(ROOT/changed[0]).read_text(encoding='utf8')
    expected=old.replace('"roguelike/data/layouts/barrow_ward_store_a.json"',
        '"roguelike/data/layouts/ai9_lateral_lane.json", "roguelike/data/layouts/ai9_shadow_lane.json", "roguelike/data/layouts/ai9_venom_lane.json", "roguelike/data/layouts/barrow_ward_store_a.json"')
    expected=expected.replace('"roguelike/data/layouts/barrow_ward_store_c.json"',
        '"roguelike/data/layouts/barrow_ward_store_c.json", "roguelike/data/layouts/barrow_ward_store_d.json", "roguelike/data/layouts/barrow_ward_store_e.json"')
    assert new==expected,'Only the five explicit new authored layout members may change'
    (out/'inputs.json').write_text(json.dumps(frozen,indent=2),encoding='utf8')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    started=datetime.now(timezone.utc).isoformat();begin=time.perf_counter()
    def execute(name):
        command=[str(WB/'worker/runtime/python.exe'),'-X','utf8','-I','-B','-c',"import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(["+repr(name)+"]));sys.exit(not r.wasSuccessful())"]
        log=out/(name+'.log');t=time.perf_counter()
        with log.open('w',encoding='utf8') as f:
            code=subprocess.run(command,cwd=WB,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=3600,creationflags=0x08000000).returncode
        stable=inputs()==frozen
        row=dict(gate=name,command=command,cwd=str(WB),exit_code=code,seconds=time.perf_counter()-t,source_stable=stable,passed=code==0 and stable,log_sha256=sha(log))
        print(json.dumps(row),flush=True);return row
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(execute,initial_worker['cohort']))
    log=out/'worker.log';log.write_text(''.join((out/(name+'.log')).read_text(encoding='utf8') for name in initial_worker['cohort']),encoding='utf8')
    result=dict(passed=all(r['passed'] for r in rows),revision=head,runtime_content_editor_revision=release['revision'],
        started_utc=started,finished_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-begin,
        witness_sha256=sha(Path(__file__)),original_release_sha256=sha(original/'release.json'),inputs_sha256=sha(out/'inputs.json'),
        changed_inputs=[dict(path=p,before=before[p],after=frozen[p]) for p in changed],
        retained_gates=[r['gate'] for r in release['commands'] if r['passed']],
        retention='All runtime/content/editor and other verifier inputs unchanged; only explicit expected room membership grows by the five commissioned layouts. The test file is excluded from Tauri resources, which ship bridge.py and the pinned runtime.',
        gate='worker',cohort=initial_worker['cohort'],modules=rows,tests=sum(map(int,re.findall(r'Ran (\d+) tests?',log.read_text(encoding='utf8')))),
        source_stable=inputs()==frozen,log_sha256=sha(log))
    result['passed']=result['passed'] and result['source_stable']
    (out/'worker.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(passed=result['passed'],revision=head)))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
