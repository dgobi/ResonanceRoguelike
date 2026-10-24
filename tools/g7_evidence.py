"""Bind serial release gates to immutable inputs, raw/LF hashes and exact bytes."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from verify_b3 import source_manifest

ROOT=Path(__file__).resolve().parents[1]
TEXT={'.py','.js','.css','.json','.md','.html','.hex','.txt'}


def sha(blob):return hashlib.sha256(blob).hexdigest()
def lf(blob):return blob.replace(b'\r\n',b'\n').replace(b'\r',b'\n')


def reconciliation(source,revision,out=None):
    rows=subprocess.check_output(['git','ls-tree','-r',revision],cwd=ROOT).decode().splitlines()
    tree={line.split('\t',1)[1]:line.split()[2] for line in rows}
    selected=sorted({tree[p] for p in source if p in tree})
    blobs=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=('\n'.join(selected)+'\n').encode(),capture_output=True,check=True).stdout
    stream=io.BytesIO(blobs);objects={}
    for identifier in selected:
        header=stream.readline().decode().strip().split();size=int(header[2]);objects[identifier]=stream.read(size);assert stream.read(1)==b'\n'
    result={}
    for name,expected in source.items():
        path=ROOT/name;raw=path.read_bytes();committed=objects.get(tree.get(name));text=path.suffix in TEXT
        relation='not committed' if committed is None else 'exact' if raw==committed else 'line endings only' if text and lf(raw)==lf(committed) else 'content differs'
        reconstructable=committed is not None and (raw==committed or text and (raw==lf(committed) or raw==lf(committed).replace(b'\n',b'\r\n')))
        saved=None
        if out and text and not reconstructable:
            saved=out/'raw-tested'/name;saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(raw)
        result[name]=dict(bytes=len(raw),raw_sha256=sha(raw),canonical_lf_sha256=sha(lf(raw)) if text else None,
            git_blob=tree.get(name),committed_raw_sha256=sha(committed) if committed is not None else None,
            committed_canonical_lf_sha256=sha(lf(committed)) if committed is not None and text else None,
            relation=relation,uniform_line_endings_reconstructable=reconstructable,raw_preserved=str(saved) if saved else None,
            raw_manifest_matches=sha(raw)==expected)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=1800);p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);command=a.command[1:] if a.command[:1]==['--'] else a.command
    if command[:1]==['python']:command[0]=sys.executable
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();source=source_manifest();inputs=reconciliation(source,commit,out)
    env=dict(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONIOENCODING='utf-8',PYTHONHASHSEED='20261020',PYTHONDONTWRITEBYTECODE='1',RESONANCE_TEST_EVIDENCE_DIR=str(out),
             PYTHONPATH=os.pathsep.join([str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests'),str(ROOT/'tools')]))
    (out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n',encoding='utf-8')
    # Dirty development attempts remain reconstructable as a scoped patch plus
    # new authoring/test files; final frozen gates require no such differences.
    patch=subprocess.check_output(['git','diff','--binary',commit,'--','roguelike','tools','layout_painter.html'],cwd=ROOT)
    if patch:(out/'input-changes.patch').write_bytes(patch)
    for name in source:
        if inputs[name]['relation']=='not committed':
            target=out/'new-inputs'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    extra={}
    for arg in command[1:]:
        path=Path(arg);path=path if path.is_absolute() else ROOT/path
        if path.is_file():extra[str(path)]=sha(path.read_bytes())
    start=time.perf_counter();timed_out=False
    with (out/'output.txt').open('w',encoding='utf-8') as log:
        try:code=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**env),stdout=log,stderr=subprocess.STDOUT,timeout=a.timeout).returncode
        except subprocess.TimeoutExpired:code=124;timed_out=True
    stable=source==source_manifest();end=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    outputs={p.relative_to(out).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in sorted(out.rglob('*')) if p.is_file()}
    bound=all(r['relation'] in ('exact','line endings only') and r['raw_manifest_matches'] for r in inputs.values())
    receipt=dict(input_commit=commit,end_commit=end,source=source,command=command,command_files=extra,cwd=str(ROOT),environment=env,interpreter=sys.executable,python=sys.version,
                 libraries={n:importlib.metadata.version(n) for n in ('pygame','tcod','numpy')},canonical_rule='bytes: CRLF to LF, then remaining CR to LF; no other normalization; binary exact',
                 source_stable=stable,committed_inputs_reconciled=bound,exit_code=code,timeout=timed_out,timeout_seconds=a.timeout,seconds=time.perf_counter()-start,
                 load='one timed gate at a time; no other test processes',outputs=outputs,passed=code==0 and stable and commit==end)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('passed','input_commit','exit_code','source_stable','committed_inputs_reconciled','seconds')},indent=2))
    return 0 if receipt['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
