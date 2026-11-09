"""Fixed GUIDE-1 practice launcher. Never writes game definitions or campaign saves.

Run from the production repository root with the pinned game Python 3.11 runtime.
The temporary payload follows workbench/worker/test_authoring.py:data_fixture;
it is a bounded test input, never a development checkout. No network is used.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
EXAMPLES = HERE / 'examples/guide1'
LESSONS = tuple(f'L{n:02}' for n in range(1, 15))


def fingerprints(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def stage(root, lesson, draft=None, seed=20261109):
    payload = root / 'payload'
    game = payload / 'roguelike'
    # Same bounded copy contract as the existing Workbench runtime fixtures.
    for p in (REPO / 'roguelike').rglob('*.py'):
        if any(part in ('saves', '__pycache__') for part in p.parts):
            continue
        target = payload / p.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    shutil.copytree(REPO / 'roguelike/data', game / 'data')
    shutil.copytree(REPO / 'roguelike/assets', game / 'assets')
    shutil.copy2(REPO / 'requirements-baseline.txt', payload / 'requirements-baseline.txt')
    marker = payload / 'workbench/src-tauri/tauri.conf.json'
    marker.parent.mkdir(parents=True)
    shutil.copy2(REPO / 'workbench/src-tauri/tauri.conf.json', marker)
    for p in (EXAMPLES / 'data').rglob('*.json'):
        target = game / 'data' / p.relative_to(EXAMPLES / 'data')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
    if lesson == 'L07':
        for name in ('authored_submap_selection.json', 'settlement_profiles.json'):
            shutil.copy2(EXAMPLES / 'policies' / name, game / 'data/generation' / name)
    if lesson == 'L08':
        shutil.copy2(EXAMPLES / 'policies/typography.json', game / 'data/display/typography.json')
    if draft:
        editable = json.loads((EXAMPLES / 'draft-targets.json').read_text())
        if lesson not in editable:
            raise ValueError('This lesson uses the distributed Python solution; no JSON draft override')
        raw = json.loads(draft.read_text(encoding='utf-8-sig'))
        expected_id = 'game_typography' if lesson == 'L08' else Path(editable[lesson]).stem
        if raw.get('id') != expected_id:
            raise ValueError('Keep the fixture ID; change the requirement described in the lesson')
        shutil.copy2(draft, game / 'data' / editable[lesson])
    config = dict(state_root=str(root / 'state'), seed=seed,
                  room_path='roguelike/data/layouts/guide1_workroom.json',
                  session_id='GUIDE-1-' + lesson)
    (root / 'state').mkdir()
    if lesson in ('L05', 'L06', 'L09', 'L13'):
        config['room_path'] = 'roguelike/data/layouts/guide1_encounter.json'
    if int(lesson[1:]) >= 10:
        sys.path.insert(0,str(EXAMPLES))
        from patch_guard import apply
        apply(payload,root/'patch-recovery')
    (root / 'session.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    manifest = dict(schema=1, lesson=lesson, payload=str(payload), state_root=config['state_root'],
                    source_revision=subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                    solutions=fingerprints(EXAMPLES), inputs=fingerprints(game),
                    reset_scope='Only this newly created temporary directory. No production files or campaign saves.')
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def main():
    global REPO
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lesson', choices=LESSONS + ('all',))
    parser.add_argument('--repo', type=Path, default=REPO, help='Existing production checkout; required when the bundle is elsewhere')
    parser.add_argument('--output', type=Path, default=HERE / 'practice-results')
    parser.add_argument('--draft', type=Path, help='Complete JSON candidate; copied into disposable data only')
    parser.add_argument('--seed', type=int, help='L07 only: seed for a new disposable generated world')
    parser.add_argument('--keep', action='store_true', help='Keep the named temporary payload/state for inspection')
    parser.add_argument('--play', action='store_true', help='Open the selected practice room for manual play')
    args = parser.parse_args()
    REPO = args.repo.resolve()
    if not (REPO/'roguelike/engine/engine.py').is_file():
        parser.error('--repo must name the existing Resonance checkout')
    if args.lesson == 'all' and (args.draft or args.play):
        parser.error('--draft and --play require one lesson')
    if args.seed is not None and (args.lesson != 'L07' or not 0 <= args.seed <= 2147483647):
        parser.error('--seed requires L07 and an integer from 0 through 2147483647')
    output = args.output.resolve()
    if output == REPO or output.is_relative_to(REPO / 'roguelike'):
        parser.error('Choose a review-output directory outside production game data and saves')
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for lesson in LESSONS if args.lesson == 'all' else (args.lesson,):
        root = Path(tempfile.mkdtemp(prefix=f'resonance-guide-{lesson}-')).resolve()
        manifest = stage(root, lesson, args.draft.resolve() if args.draft else None,
                         args.seed if args.seed is not None else 20261109)
        print(json.dumps({k: manifest[k] for k in ('lesson', 'source_revision', 'payload', 'state_root', 'reset_scope')}), flush=True)
        command = [sys.executable, '-X', 'utf8', '-B', str(EXAMPLES / 'lesson_runtime.py'),
                   '--session', str(root / 'session.json'), '--lesson', lesson,
                   '--output', str(output / lesson)]
        if args.play:
            command.append('--play')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYGAME_HIDE_SUPPORT_PROMPT='1')
        if not args.play:
            env.update(SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
        try:
            result = subprocess.run(command, cwd=root / 'payload/roguelike', env=env,
                                    capture_output=not args.play, text=True, encoding='utf-8',
                                    timeout=3600 if args.play else 240)
            if not args.play:
                (output / (lesson + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
            row = dict(lesson=lesson, passed=result.returncode == 0, exit_code=result.returncode,
                       solution_fingerprints=manifest['solutions'], source_revision=manifest['source_revision'],
                       mode='manual practice' if args.play else 'automated bounded input scenario')
            rows.append(row)
            if result.returncode:
                print((result.stdout or '')[-2000:] + (result.stderr or '')[-4000:])
        finally:
            # Only remove the freshly allocated root, after resolving its boundary.
            if not args.keep and root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith('resonance-guide-'):
                shutil.rmtree(root)
            elif args.keep:
                print('Retained practice payload: ' + str(root))
    (output / 'practice.json').write_text(json.dumps(dict(passed=all(r['passed'] for r in rows), runs=rows), indent=2) + '\n', encoding='utf-8')
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
