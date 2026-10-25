"""Run existing G9 checks against an unchanged checkout with bounded subprocesses."""
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
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=repo).decode().split('\0')
    return {name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
            for name in names if name and (repo / name).is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--python', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--check', choices=['g9-tests', 'diagnostic-journey'], required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.evidence.resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = out / 'results'
    results.mkdir(exist_ok=True)
    env = dict(os.environ)
    inherited = env.pop('PYTHONPATH', None)
    overrides = dict(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
                     PYGAME_HIDE_SUPPORT_PROMPT='1', PYTHONHASHSEED='20261020',
                     PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
    env.update(overrides)
    if args.check == 'g9-tests':
        search = [repo / 'roguelike', repo / 'tools/critical_fix_regressions/tests', repo / 'tools']
        env.update(PYTHONPATH=os.pathsep.join(map(str, search)),
                   RESONANCE_GAME_ROOT=str(repo / 'roguelike'),
                   RESONANCE_TEST_TOOLS=str(repo / 'tools/critical_fix_regressions/historical_tools'),
                   RESONANCE_TEST_EVIDENCE_DIR=str(results))
        command = [str(args.python), '-X', 'utf8', '-m', 'unittest', '-v',
                   'test_generation_g9_network', 'test_generation_g9_lifecycle']
        limit = 1200
    else:
        command = [str(args.python), '-X', 'utf8', 'tools/worldgen_g9_diagnostic.py',
                   '--journey', '--evidence', str(results)]
        limit = 1800
    before = manifest(repo)
    (out / 'source-before.json').write_text(json.dumps(before, indent=2) + '\n')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    start_record = dict(head=head, command=command, cwd=str(repo),
                        parent_pythonpath_removed=inherited is not None,
                        child_pythonpath=env.get('PYTHONPATH'), timeout_seconds=limit,
                        explicit_environment=overrides)
    (out / 'started.json').write_text(json.dumps(start_record, indent=2) + '\n')
    started = time.perf_counter()
    timed_out = False
    with (out / 'output.txt').open('wb') as log:
        try:
            run = subprocess.run(command, cwd=repo, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, timeout=limit)
            code = run.returncode
        except subprocess.TimeoutExpired:
            code, timed_out = 124, True
    elapsed = time.perf_counter() - started
    after = manifest(repo)
    changed = sorted(name for name in before.keys() | after.keys()
                     if before.get(name) != after.get(name))
    status = subprocess.check_output(['git', 'status', '--short'], cwd=repo, text=True)
    receipt = dict(start_record, check=args.check, interpreter=str(args.python),
                   python=sys.version,
                   dependencies={name: importlib.metadata.version(name)
                                 for name in ('pygame', 'tcod', 'numpy')},
                   seconds=elapsed, timeout=timed_out, exit_code=code,
                   tracked_file_count=len(before), changed_tracked_paths=changed,
                   source_stable=before == after, git_status_after=status,
                   passed=code == 0 and before == after and not status)
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
