"""Bound a G6 command to frozen source, exact argv/env, outputs and exit status."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=1800);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if command[:1]==['python']:command[0]=sys.executable
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    source=source_manifest();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    extra={}
    for value in command[1:]:
        path=Path(value)
        if not path.is_absolute():path=ROOT/path
        if path.is_file():extra[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    environment=dict(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONIOENCODING='utf-8',
        PYTHONHASHSEED='20261020',PYTHONDONTWRITEBYTECODE='1',RESONANCE_TEST_EVIDENCE_DIR=str(out),
        PYTHONPATH=os.pathsep.join([str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests'),str(ROOT/'tools')]))
    started=time.perf_counter();timed_out=False
    with (out/'output.txt').open('w',encoding='utf-8') as stream:
        try:code=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**environment),stdout=stream,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
        except subprocess.TimeoutExpired:code=124;timed_out=True
    outputs={str(path.relative_to(out)):dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in sorted(out.rglob('*')) if path.is_file()}
    stable=source==source_manifest();end_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    record=dict(command=command,cwd=str(ROOT),environment=environment,executable=sys.executable,python=sys.version,
        libraries={n:importlib.metadata.version(n) for n in ('pygame','tcod','numpy')},source=source,command_files=extra,
        input_commit=commit,end_commit=end_commit,source_stable=stable,exit_code=code,timeout=timed_out,timeout_seconds=a.timeout,
        seconds=time.perf_counter()-started,load='one gate at a time; no other test processes',outputs=outputs,
        passed=code==0 and stable and commit==end_commit)
    (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:record[k] for k in ('passed','input_commit','exit_code','source_stable','seconds','timeout')},indent=2))
    return 0 if record['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
