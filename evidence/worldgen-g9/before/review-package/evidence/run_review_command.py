"""Execute bounded G8 review checks without editing the reviewed checkout."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def manifest(repo):
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=repo).decode().split('\0')
    return {p: hashlib.sha256((repo / p).read_bytes()).hexdigest()
            for p in paths if p and (repo / p).is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--check', choices=['focused', 'diagnostic-journey'], required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.evidence.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    inherited = env.pop('PYTHONPATH', None)
    overrides = dict(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                     PYGAME_HIDE_SUPPORT_PROMPT='1', PYTHONHASHSEED='20261020',
                     PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    env.update(overrides)
    if args.check == 'focused':
        command = [str(args.python), '-X', 'utf8', 'tools/critical_fix_regressions/verify_fixes.py',
                   '--game', str(repo / 'roguelike'), '--evidence', str(out / 'results')]
        limit = 1260
    else:
        command = [str(args.python), '-X', 'utf8', 'tools/worldgen_g8_diagnostic.py',
                   '--journey', '--evidence', str(out / 'results')]
        limit = 900
    before = manifest(repo)
    (out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    start = time.perf_counter()
    (out / 'started.json').write_text(json.dumps(dict(head=head, command=command, cwd=str(repo),
        parent_pythonpath=inherited, child_pythonpath=env.get('PYTHONPATH'), timeout_seconds=limit,
        explicit_environment=overrides), indent=2) + '\n')
    timed_out = False
    with (out / 'output.txt').open('wb') as log:
        try:
            run = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=limit)
            code = run.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = 124, True
    elapsed = time.perf_counter() - start
    after = manifest(repo)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    status = subprocess.check_output(['git', 'status', '--short'], cwd=repo, text=True)
    receipt = dict(check=args.check, head=head, command=command, cwd=str(repo),
        explicit_environment=overrides, parent_pythonpath=inherited, child_pythonpath=env.get('PYTHONPATH'),
        interpreter=str(args.python), python=sys.version,
        dependencies={m: importlib.metadata.version(m) for m in ('pygame', 'tcod', 'numpy')},
        seconds=elapsed, timeout=timed_out, timeout_seconds=limit, exit_code=code,
        tracked_file_count=len(before), changed_tracked_paths=changed, source_stable=before==after,
        git_status_after=status, passed=code==0 and before==after)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
