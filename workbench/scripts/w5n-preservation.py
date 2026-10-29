"""Scoped tracked-input inventory; never enumerate campaign save trees."""
import hashlib, json, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
output = root / 'workbench/.artifacts/w5n/preservation-before.json'
if sys.argv[1] == 'capture':
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    paths += ['RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md']
    rows = {p: dict(sha256=hashlib.sha256((root/p).read_bytes()).hexdigest(), mtime_ns=(root/p).stat().st_mtime_ns) for p in paths if p and (root/p).is_file()}
    output.write_text(json.dumps(rows, indent=2), encoding='utf-8')
    print(len(rows), 'captured')
else:
    changed = set(subprocess.check_output(['git', 'diff', '--name-only', 'checkpoint/workbench-w5n-start-20261029'], cwd=root).decode().splitlines())
    rows = json.loads(output.read_text(encoding='utf-8')); failures=[]
    for p, before in rows.items():
        if p in changed: continue
        file=root/p
        if not file.is_file() or dict(sha256=hashlib.sha256(file.read_bytes()).hexdigest(), mtime_ns=file.stat().st_mtime_ns)!=before: failures.append(p)
    result=dict(unchanged=len(rows)-len(set(rows)&changed), scoped_changes=sorted(changed), failures=failures)
    output.with_name('preservation-after.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result)); assert not failures
