"""Invoke the documented focused runner from a parent with no PYTHONPATH."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--timeout',type=int,default=1200);a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ);env.pop('PYTHONPATH',None)
    command=[sys.executable,'-X','utf8',str(ROOT/'tools/critical_fix_regressions/verify_fixes.py'),'--game',str(ROOT/'roguelike'),'--evidence',str(a.evidence.resolve()),'--timeout',str(a.timeout)]
    (a.evidence/'parent.json').write_text(json.dumps(dict(command=command,cwd=str(ROOT),inherited_pythonpath=env.get('PYTHONPATH')),indent=2)+'\n')
    raise SystemExit(subprocess.run(command,cwd=ROOT,env=env,timeout=a.timeout+60).returncode)
