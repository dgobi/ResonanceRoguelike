"""Bind six test corrections and one guide clarification to the full execution.

This completes affected modules; it is not a fresh clean unfiltered run.
Runtime, data, editor, historical fixtures and all other inputs must be identical.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from verify_sys_3 import inputs, digest

ORIGINAL = ROOT / ".baseline/sys-3/final-a"
OUT = ROOT / ".baseline/sys-3/expectation-final"
old = json.loads((ORIGINAL / "inputs.json").read_text())
assert digest(ORIGINAL / "inputs.json") == "0da8bf97c9422df69232b95ef2c748de87bf3285d2887c1ccfa75eeb0de6f5b0"
full = json.loads((ORIGINAL / "release.json").read_text())
assert "finished_utc" in full and full["source_stable"]
assert full["revision"] == "c0c0c83349384d0afc2d78f77b764e3906f0dd53"
by = {r["gate"]: r for r in full["commands"]}
assert len(by) == 17
assert {k for k, r in by.items() if not r["passed"]} == {"focused", "worker"}
for gate, row in by.items():
    assert row["source_stable"] and row["log_sha256"] == digest(ORIGINAL / (gate + ".log"))
focused_log = (ORIGINAL / "focused.log").read_text(encoding="utf8")
assert "Ran 675 tests" in focused_log and "FAILED (failures=6)" in focused_log
assert {r["gate"] for r in by["worker"]["modules"] if not r["passed"]} == {"test_authoring", "test_bridge"}
assert len(by["worker"]["modules"]) == 27
for row in by["worker"]["modules"]:
    assert row["source_stable"] and row["log_sha256"] == digest(ORIGINAL / (row["gate"] + ".log"))
production_path = next((ORIGINAL / "production-d").glob("*/results.json"))
production = json.loads(production_path.read_text())
assert production["passed"] and production["totals"] == dict(checks=3704, passed=3704, failed=0, workers=159)

plan_path = ROOT / "evidence/sys-3/expectation-recheck-plan.json"
plan = json.loads(plan_path.read_text())
allowed = {
    "tools/critical_fix_regressions/tests/test_gameplay_g13.py",
    "tools/critical_fix_regressions/tests/test_gameplay_g15.py",
    "tools/critical_fix_regressions/tests/test_gameplay_g16.py",
    "tools/critical_fix_regressions/tests/test_structure_access.py",
    "workbench/worker/test_authoring.py",
    "workbench/worker/test_bridge.py",
    "roguelike/docs/MATERIAL_WEAPON_PREPARATIONS.md",
}
assert set(plan) == allowed
for path, change in plan.items():
    reconstructed = (ROOT / path).read_bytes()
    assert change["before_sha256"] == old[path]
    for row in reversed(change["edits"]):
        variants = [(row["before"].replace("\n", eol).encode(), row["after"].replace("\n", eol).encode())
                    for eol in ("\n", "\r\n")]
        before, after = next((a, b) for a, b in variants if reconstructed.count(b) == 1)
        reconstructed = reconstructed.replace(after, before, 1)
    assert hashlib.sha256(reconstructed).hexdigest() == old[path], path
now = inputs()
assert {p for p in old.keys() | now.keys() if old.get(p) != now.get(p)} == allowed
assert not OUT.exists(), "Use a new declared evidence boundary; retain previous runs."
OUT.mkdir(parents=True)
(OUT / "focused").mkdir()
(OUT / "inputs.json").write_text(json.dumps(now, indent=2), encoding="utf8")
started = datetime.now(timezone.utc).isoformat()
env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
           PYGAME_HIDE_SUPPORT_PROMPT="1", PYTHONHASHSEED="20261020",
           PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1",
           RESONANCE_GAME_ROOT=str(ROOT / "roguelike"),
           RESONANCE_TEST_TOOLS=str(ROOT / "tools/critical_fix_regressions/historical_tools"),
           RESONANCE_TEST_EVIDENCE_DIR=str(OUT / "focused"),
           PYTHONPATH=os.pathsep.join(map(str, [ROOT / "roguelike", ROOT / "tools",
                                               ROOT / "tools/critical_fix_regressions/tests"])))


def execute(spec):
    name, cmd, cwd = spec
    cmd = [str(x) for x in cmd]
    began = time.perf_counter()
    log = OUT / (name + ".log")
    with log.open("w", encoding="utf8") as stream:
        code = subprocess.run(cmd, cwd=cwd, env=env, stdout=stream,
                              stderr=subprocess.STDOUT, timeout=3600,
                              creationflags=0x08000000).returncode
    stable = inputs() == now
    result = dict(gate=name, command=cmd, cwd=str(cwd), exit_code=code,
                  seconds=time.perf_counter() - began, source_stable=stable,
                  log_sha256=digest(log), passed=code == 0 and stable)
    result["tests"] = sum(map(int, re.findall(r"Ran (\d+) tests?", log.read_text(encoding="utf8"))))
    print(json.dumps(result), flush=True)
    return result


py = [sys.executable, "-X", "utf8", "-B"]
wb = ROOT / "workbench"
worker = "import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(['test_authoring','test_bridge']));sys.exit(not r.wasSuccessful())"
with ThreadPoolExecutor(max_workers=2) as pool:
    rows = list(pool.map(execute, [
        ("focused-affected", py + ["-m", "unittest", "-v", "test_gameplay_g13", "test_gameplay_g15",
                                  "test_gameplay_g16", "test_structure_access"], ROOT),
        ("worker-affected", [wb / "worker/runtime/python.exe", "-X", "utf8", "-I", "-B", "-c", worker], wb),
    ]))
control = "import sys,unittest;sys.path.insert(0,'worker');r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_bridge.BridgeTests.test_dependency_absence_structured'));sys.exit(not r.wasSuccessful())"
rows.append(execute(("worker-dependency-control", py + ["-c", control], wb)))
report = dict(
    passed=all(row["passed"] for row in rows),
    interpretation="Retained original full execution plus complete affected modules; not a fresh clean unfiltered run.",
    revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    started_utc=started, finished_utc=datetime.now(timezone.utc).isoformat(),
    original_manifest_sha256=digest(ORIGINAL / "inputs.json"),
    original_release_sha256=digest(ORIGINAL / "release.json"),
    original_production_result_sha256=digest(production_path),
    input_manifest_sha256=digest(OUT / "inputs.json"), source_stable=inputs() == now,
    script_sha256=digest(Path(__file__)), plan_sha256=digest(plan_path), commands=rows,
    changes={p: dict(before=old[p], after=now[p], reason=v["reason"], edits=v["edits"]) for p, v in plan.items()},
)
(OUT / "result.json").write_text(json.dumps(report, indent=2), encoding="utf8")
print(json.dumps(dict(passed=report["passed"])), flush=True)
raise SystemExit(0 if report["passed"] else 1)
