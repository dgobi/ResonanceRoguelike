"""Run one bounded gate; retain command/runtime/source identity and bulky local log."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'workbench/.artifacts/w5q'
ART.mkdir(parents=True,exist_ok=True)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def inputs():
    paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    return {p:digest(ROOT/p) for p in sorted(set(paths)) if p and (ROOT/p).is_file() and (
        p.startswith(('workbench/src/','workbench/src-tauri/src/','workbench/worker/','workbench/scripts/')) or
        p.startswith('roguelike/') and (p.endswith('.py') or p.startswith('roguelike/data/') and p.endswith('.json')) or
        p in ('workbench/package.json','workbench/package-lock.json','workbench/src-tauri/Cargo.toml','workbench/src-tauri/Cargo.lock','workbench/src-tauri/build.rs'))}


if __name__=='__main__':
    name,cwd,*command=sys.argv[1:];before=inputs();started=time.perf_counter()
    receipt=dict(command=command,cwd=str(ROOT/cwd),started_utc=datetime.now(timezone.utc).isoformat(),
                 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),inputs=before)
    env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
    with (ART/(name+'.log')).open('wb') as output:
        run=subprocess.run(command,cwd=ROOT/cwd,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=3600,
                           creationflags=0x08000000 if os.name=='nt' else 0)
    receipt.update(exit_code=run.returncode,seconds=time.perf_counter()-started,source_stable=inputs()==before,
                   log=dict(path='workbench/.artifacts/w5q/'+name+'.log',sha256=digest(ART/(name+'.log'))),
                   passed=run.returncode==0 and inputs()==before)
    (ART/(name+'.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k!='inputs'}))
    sys.exit(0 if receipt['passed'] else 1)
