"""Synthetic outside-root worker must reject before opening its save directory."""
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from b1_support import ENV,hashes
out=Path(__file__).parent
run=out/'synthetic-outside-allowed';run.mkdir(exist_ok=True)
saves=run/'saves';saves.mkdir(exist_ok=True)
(saves/'sentinel.txt').write_text('synthetic test data only')
(run/'disposable-b3.json').write_text(json.dumps(dict(kind='test saves and evidence only',production_source=str(ROOT/'roguelike'))))
job=dict(run_root=str(run),save_root=str(saves),result=str(run/'result.json'))
(run/'job.json').write_text(json.dumps(job));before=hashes(saves)
command=[sys.executable,str(ROOT/'tools/b3_worker.py'),str(run/'job.json')]
p=subprocess.run(command,cwd=ROOT/'roguelike',env=dict(os.environ,**ENV),capture_output=True,text=True,timeout=30)
record=dict(command=command,cwd=str(ROOT/'roguelike'),exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,
            saves_before=before,saves_after=hashes(saves),passed=p.returncode!=0 and 'AssertionError' in p.stderr and before==hashes(saves) and not (run/'result.json').exists())
(out/'root-negative.json').write_text(json.dumps(record,indent=2)+'\n')
assert record['passed'],record
