"""Retain SYS-5 full gates across one bounded authoring performance repair.

Reconstruct all three changed inputs, verify immutable evidence/dependencies and
package hashes, then run complete affected modules and journeys. This is retained
full execution plus affected rechecks, not a fresh clean full execution.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import importlib.metadata
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_sys_5 import inputs, digest

ORIGINAL = ROOT / '.baseline/sys-5/final-a'
OUT = ROOT / '.baseline/sys-5/validation-final-a'
WB = ROOT / 'workbench'
assert digest(ORIGINAL / 'inputs.json') == '935cda7bbfce529ee60e6e24d6d640d3f6a5f9db36455ccf6e1d8c9f1184beec'
assert digest(ORIGINAL / 'release.json') == '7d2a4151b953240b6fd5289a6ede47572a55655276ee8c6c86e47144497c2974'
old = json.loads((ORIGINAL / 'inputs.json').read_text())
full = json.loads((ORIGINAL / 'release.json').read_text())
assert full['finished_utc'] and full['source_stable']
assert full['revision'] == '591cacc207e1271c67ae93a53ce4f4ae4665f3b3'
assert sys.executable == full['environment']['python_executable']
assert sys.version == full['environment']['python']
assert all(importlib.metadata.version(k) == v for k, v in full['environment']['dependencies'].items())
for key, command in [('node', ['node', '--version']), ('cargo', ['cargo', '--version']), ('rustc', ['rustc', '--version'])]:
    assert subprocess.check_output(command, text=True).strip() == full['environment'][key]
by = {r['gate']: r for r in full['commands']}
assert len(by) == 19 and {k for k, r in by.items() if not r['passed']} == {'worker'}
assert {r['gate'] for r in by['worker']['modules'] if not r['passed']} == {'test_assignment', 'test_creatures_w5f'}
assert by['worker']['tests'] == 145 and len(by['worker']['cohort']) == 29
for gate, row in by.items():
    assert row['source_stable'] and digest(ORIGINAL / (gate + '.log')) == row['log_sha256']
    for module in row.get('modules', []):
        assert module['source_stable'] and digest(ORIGINAL / (module['gate'] + '.log')) == module['log_sha256']
assert 'Ran 726 tests' in (ORIGINAL / 'focused.log').read_text(encoding='utf8')
production_path = next((ORIGINAL / 'production-d').glob('*/results.json'))
production = json.loads(production_path.read_text())
assert production['passed'] and production['totals'] == dict(checks=3704, passed=3704, failed=0, workers=159)
assert production['only'] is None and production['case'] is None
assert all(old[k] == v for k, v in production['source'].items())
for package in [full['package'], *full['installers']]:
    assert digest(ROOT / package['path']) == package['sha256']

plan_path = ROOT / 'evidence/sys-5/validation-recheck-plan.json'
plan = json.loads(plan_path.read_text())
paths = {entry['path'] for entry in plan['changes']}
assert paths == {'roguelike/generation/authored_rooms.py', 'roguelike/engine/assignment_authoring.py', 'workbench/worker/test_creatures_w5f.py'}
for entry in plan['changes']:
    path = entry['path']
    current = (ROOT / path).read_bytes()
    assert digest(ROOT / path) == entry['after_sha256']
    for replacement in reversed(entry['replacements']):
        variants = [(replacement['before'].replace('\n', eol).encode(), replacement['after'].replace('\n', eol).encode()) for eol in ('\n', '\r\n')]
        before, after = next((a, b) for a, b in variants if current.count(b) == 1)
        current = current.replace(after, before, 1)
    assert hashlib.sha256(current).hexdigest() == old[path] == entry['before_sha256']
now = inputs()
assert len(now) == len(old) == 1303 and now.keys() == old.keys()
assert {path for path in old if old[path] != now[path]} == paths
assert 'timeout=20' in (WB / 'worker/test_bridge.py').read_text()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
assert subprocess.check_output(['git', 'rev-parse', 'HEAD^'], cwd=ROOT, text=True).strip() == full['revision']
assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() == 'main'
assert not OUT.exists(), 'Preserve prior evidence and declare a fresh boundary.'
OUT.mkdir(parents=True)
(OUT / 'focused').mkdir()
(OUT / 'inputs.json').write_text(json.dumps(now, indent=2), encoding='utf8')
report = dict(passed=False, revision=head, started_utc=datetime.now(timezone.utc).isoformat(),
    original_manifest_sha256=digest(ORIGINAL / 'inputs.json'), original_release_sha256=digest(ORIGINAL / 'release.json'),
    original_production_result_sha256=digest(production_path), input_manifest_sha256=digest(OUT / 'inputs.json'),
    script_sha256=digest(Path(__file__)), plan_sha256=digest(plan_path), commands=[], changes=plan['changes'],
    environment=full['environment'], package=full['package'], installers=full['installers'],
    retained_gates=[name for name in by if name not in {'worker', 'worker-dependency-control', 'native', 'play'}],
    interpretation='Full frozen final-a execution plus complete affected rechecks; not a fresh clean full execution. One lazy per-context reference catalogue replaces repeated identical UI-choice scans while every room still runs source/compiler/dependency/factory/native placement validation. Actual selector logic and all gameplay are unchanged. UI choice defaults are unchanged. Exact shipped creature count changes37 to39 with every per-creature and negative check retained. Original failures and all source/log hashes are retained; overlapping counts are not added.')
lock = threading.Lock()
def write():
    (OUT / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
write()
env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYGAME_HIDE_SUPPORT_PROMPT='1',
    PYTHONHASHSEED='20261020', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1',
    SYS1_RUNTIME_ONLY='1', SYS2_RUNTIME_ONLY='1', SYS3_RUNTIME_ONLY='1', SYS4_RUNTIME_ONLY='1', SYS5_RUNTIME_ONLY='1')

def execute(name, command, cwd=ROOT):
    command = [str(x) for x in command]
    began = time.perf_counter()
    log = OUT / (name + '.log')
    call_env = dict(env)
    if name == 'focused-affected':
        call_env.update(RESONANCE_GAME_ROOT=str(ROOT / 'roguelike'),
            RESONANCE_TEST_TOOLS=str(ROOT / 'tools/critical_fix_regressions/historical_tools'),
            RESONANCE_TEST_EVIDENCE_DIR=str(OUT / 'focused'),
            PYTHONPATH=os.pathsep.join(map(str, [ROOT / 'roguelike', ROOT / 'tools', ROOT / 'tools/critical_fix_regressions/tests'])))
    with log.open('w', encoding='utf8') as stream:
        try:
            code = subprocess.run(command, cwd=cwd, env=call_env, stdout=stream, stderr=subprocess.STDOUT,
                timeout=3600, creationflags=0x08000000).returncode
            error = None
        except subprocess.TimeoutExpired:
            code = 2
            error = 'finite timeout'
    row = dict(gate=name, command=command, cwd=str(cwd), exit_code=code, error=error, seconds=time.perf_counter()-began,
        source_stable=inputs() == now, log_sha256=digest(log),
        tests=sum(map(int, re.findall(r'Ran (\d+) tests?', log.read_text(encoding='utf8')))))
    row['passed'] = code == 0 and row['source_stable']
    with lock:
        report['commands'].append(row)
        write()
    print(json.dumps(row), flush=True)
    return row

py = [sys.executable, '-X', 'utf8', '-B']
with ThreadPoolExecutor(max_workers=3) as pool:
    jobs = [pool.submit(execute, 'focused-affected', py + ['-m', 'unittest', '-v', 'test_sys_5', 'test_sys_4', 'test_gameplay_g20', 'test_gameplay_g22', 'test_authored_assignment']),
        pool.submit(execute, 'play', py + [ROOT / 'tools/verify_sys_5_play.py', '--evidence', OUT / 'play']),
        pool.submit(execute, 'native', ['node', 'scripts/run-sys-5.mjs'], WB)]
    for job in jobs:
        job.result()
names = sorted(path.stem for path in (WB / 'worker').glob('test_*.py'))
assert names == by['worker']['cohort']
prior = {module['gate']: module for module in by['worker']['modules']}
with ThreadPoolExecutor(max_workers=2) as pool:
    workers = list(pool.map(lambda name: execute(name, prior[name]['command'], WB), names))
worker_log = OUT / 'worker.log'
worker_log.write_text(''.join((OUT / (name + '.log')).read_text(encoding='utf8') for name in names), encoding='utf8')
worker = dict(gate='worker', cohort=names, modules=workers, tests=sum(row['tests'] for row in workers),
    passed=all(row['passed'] for row in workers), source_stable=inputs() == now, log_sha256=digest(worker_log))
report['commands'] = [row for row in report['commands'] if row['gate'] not in names] + [worker]
write()
execute('worker-dependency-control', by['worker-dependency-control']['command'], WB)
report['source_stable'] = inputs() == now
report['package_stable'] = all(digest(ROOT / package['path']) == package['sha256'] for package in [full['package'], *full['installers']])
report['passed'] = report['source_stable'] and report['package_stable'] and all(row['passed'] for row in report['commands'])
report['finished_utc'] = datetime.now(timezone.utc).isoformat()
write()
print(json.dumps(dict(passed=report['passed'], revision=head)), flush=True)
raise SystemExit(0 if report['passed'] else 1)
