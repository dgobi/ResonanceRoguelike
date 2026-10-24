"""Run an exact G5 command with source, environment, exit and output receipts."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ['--']: command = command[1:]
    if command[:1] == ['python']: command[0] = sys.executable
    args.output.mkdir(parents=True, exist_ok=False)
    source = source_manifest()
    started = time.perf_counter()
    env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               PYGAME_HIDE_SUPPORT_PROMPT='1', PYTHONIOENCODING='utf-8', PYTHONHASHSEED='20261020')
    root = Path(__file__).resolve().parents[1]
    env['PYTHONPATH'] = os.pathsep.join([str(root/'roguelike'), str(root/'tools/critical_fix_regressions/tests'), env.get('PYTHONPATH','')])
    env['RESONANCE_TEST_EVIDENCE_DIR'] = str(args.output.resolve())
    with (args.output/'output.txt').open('w', encoding='utf-8') as out:
        result = subprocess.run(command, cwd=root, env=env, stdout=out, stderr=subprocess.STDOUT)
    record = dict(command=command, cwd=str(root), python=sys.version, executable=sys.executable,
                  dependencies={n:importlib.metadata.version(n) for n in ('pygame','tcod','numpy')},
                  source=source, source_stable=source==source_manifest(), exit_code=result.returncode,
                  elapsed_seconds=time.perf_counter()-started, concurrency='one suite; worker concurrency recorded by suite',
                  output_sha256=hashlib.sha256((args.output/'output.txt').read_bytes()).hexdigest())
    (args.output/'run.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='source'},indent=2))
    return result.returncode


if __name__ == '__main__': raise SystemExit(main())
