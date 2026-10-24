"""Real worker positive and synthetic outside-root negative, never personal saves."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from b1_support import ENV,hashes

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/verify_d.py'),'--only','b1','--case','scenes/surface','--evidence',str(out/'allowed')]
    positive=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**ENV),capture_output=True,text=True,timeout=120)
    runs=list((out/'allowed').glob('*/results.json'));result=json.loads(runs[0].read_text()) if len(runs)==1 else {}
    passed=positive.returncode==0 and result.get('totals',{}).get('workers')==3 and all(w['valid'] for w in result.get('workers',[]))
    with tempfile.TemporaryDirectory(prefix='g7-synthetic-outside-guard-') as temporary:
        run=Path(temporary);saves=run/'saves';saves.mkdir();(saves/'sentinel.txt').write_text('synthetic disposable data only')
        (run/'disposable-b3.json').write_text(json.dumps(dict(kind='test saves and evidence only',production_source=str(ROOT/'roguelike'))))
        job=dict(run_root=str(run),save_root=str(saves),result=str(run/'result.json'));(run/'job.json').write_text(json.dumps(job));before=hashes(saves)
        negative_command=[sys.executable,str(ROOT/'tools/b3_worker.py'),str(run/'job.json')]
        negative=subprocess.run(negative_command,cwd=ROOT/'roguelike',env=dict(os.environ,**ENV),capture_output=True,text=True,timeout=30)
        rejected=negative.returncode!=0 and 'assert any(run.is_relative_to(base)' in negative.stderr and not (run/'result.json').exists() and hashes(saves)==before
        record=dict(passed=passed and rejected,allowed=dict(command=command,exit_code=positive.returncode,stdout=positive.stdout,stderr=positive.stderr,workers=result.get('totals')),
            rejected=dict(command=negative_command,cwd=str(ROOT/'roguelike'),exit_code=negative.returncode,stdout=negative.stdout,stderr=negative.stderr,save_inventory_before=before,save_inventory_after=hashes(saves),guard_before_game_save_access=rejected))
    (out/'guard.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(passed=record['passed'])))
    return 0 if record['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
