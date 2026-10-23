"""Enforced B2 gate. Run .\.venv\Scripts\python.exe tools/verify_b2.py.

--only is partial diagnosis; --before measures preserved B1 failures (exit 1).
Default: strict before controls, repaired B2 properties and complete B1 regressions.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from b1_support import ENV, SEED, dump, hashes, read
from verify_b1 import validate_worker

ROOT = Path(__file__).resolve().parents[1]
BASE = "9bb0db884b989bb9a21f25387b5772e3246ba978"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", action="store_true")
    parser.add_argument("--only", choices=("components", "items", "actors", "processing", "format", "journey"))
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--b1-baseline", type=Path, help="Verified Arc A export for nested B1 gate when Git history is unavailable")
    args = parser.parse_args()
    run_id = "b2-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    root = ROOT / ".baseline" / run_id
    root.mkdir(parents=True)
    dump(root / "disposable-b2.json", {"run_id": run_id, "seed": SEED})
    candidate, baseline = root / "source-candidate", root / "source-baseline"
    ignore = shutil.ignore_patterns("saves", "__pycache__", "*.pyc", "game_out.txt")
    for folder in ("roguelike", "tools"):
        shutil.copytree(ROOT / folder, candidate / folder, ignore=ignore)
    (candidate / "evidence").mkdir()
    if args.baseline:
        shutil.copytree(args.baseline / "roguelike", baseline / "roguelike", ignore=ignore)
    else:
        archive = root / "baseline.zip"
        repository = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT,
                                    check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        subprocess.run(["git", "archive", "--format=zip", "--output="+str(archive), BASE], cwd=repository, check=True, timeout=30)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            z.extractall(baseline)
    expected_baseline = read(ROOT / "tools/b2_baseline_manifest.json")
    assert hashes(baseline / "roguelike") == expected_baseline, "Wrong pre-B2 baseline source"
    report = {"run_id": run_id, "command": [sys.executable, *sys.argv], "cwd": str(ROOT), "environment": ENV,
              "baseline_commit": BASE, "baseline_verified": True, "candidate_source": hashes(candidate / "roguelike"),
              "test_source": hashes(candidate / "tools"), "workers": [], "checks": [], "before": args.before, "only": args.only}
    def check(case, name, expected, observed):
        report["checks"].append(dict(case=case, property=name, expected=expected, observed=observed, passed=expected == observed))
    def launch(command, cwd, timeout=180):
        started = time.monotonic()
        try:
            p = subprocess.run(command, cwd=cwd, env=dict(os.environ, **ENV), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=timeout)
            return dict(command=command, cwd=str(cwd), environment=ENV, exit_code=p.returncode,
                        stdout=p.stdout, stderr=p.stderr, elapsed_seconds=time.monotonic()-started, timeout=False)
        except subprocess.TimeoutExpired as error:
            return dict(command=command, cwd=str(cwd), exit_code=None, timeout=True,
                        stdout=str(error.stdout), stderr=str(error.stderr), elapsed_seconds=time.monotonic()-started)
    writers, planned = [], []
    def execute(flavor, scenario, variant, phase, writer=None):
        key = "-".join((flavor, scenario, variant, phase))
        planned.append(key)
        session = root / "workers" / key
        game = session / "roguelike"
        source = baseline if flavor == "before" else candidate
        shutil.copytree(source / "roguelike", game, ignore=ignore)
        job = dict(run_id=run_id, run_root=str(root), scenario=scenario, variant=variant, phase=phase,
                   flavor=flavor, game=str(game), result=str(session / "result.json"))
        if writer:
            wjob, wrecord = writer
            shutil.copytree(Path(wjob["game"]) / "saves", game / "saves")
            check("B2-H", key + " exact writer bytes", wrecord["checkpoint"], hashes(game / "saves/slot_0"))
            job["expected"] = wjob["result"]
        else:
            slot = game / "saves/slot_0"
            slot.mkdir(parents=True)
            dump(slot / "world.json", {"seed": SEED})
        dump(session / "job.json", job)
        proc = launch([sys.executable, str(candidate / "tools/b2_worker.py"), str(session / "job.json")], game)
        record = read(job["result"]) if Path(job["result"]).exists() else None
        if flavor == "before":
            error = None if (not proc["timeout"] and record and record.get("completed")
                and record.get("checks") and record.get("imported_sources")
                and all(record.get(k) == job[k] for k in ("run_id", "scenario", "phase", "flavor"))
                and proc["exit_code"] == (0 if record["passed"] else 1)) else "incomplete before control"
        else:
            error = validate_worker(record, job, proc["exit_code"], proc["timeout"])
        check("B2-H", key + " bounded complete process", None, error)
        if record and record.get("imported_sources"):
            for name, binding in record["imported_sources"].items():
                check("B2-H", key + " imported " + name,
                      hashlib.sha256((source / "roguelike" / binding["relative"]).read_bytes()).hexdigest(), binding["sha256"])
        if writer and record:
            check("B2-H", key + " independent reader process", True, record["pid"] != writer[1]["pid"])
        report["workers"].append(dict(key=key, job=job, process=proc, result=record, validation_error=error))
        dump(session / "process.json", proc)
        dump(root / "results.json", report)
        print(key, "COMPLETE" if error is None else "FAIL", (record or {}).get("error", ""), flush=True)
        if phase == "write" and error is None:
            writers.append((job, record))
        return (job, record) if error is None else None
    for flavor in (("before",) if args.before else ("before", "candidate") if args.only is None else ("candidate",)):
        for scenario, variants in (("components", ("filled", "empty")), ("items", ("distinct",)), ("actors", ("modified",))):
            if args.only not in (None, scenario):
                continue
            for variant in variants:
                writer = execute(flavor, scenario, variant, "write")
                if writer:
                    execute(flavor, scenario, variant, "read", writer)
                execute(flavor, scenario, variant, "same")
        if args.only in (None, "processing"):
            execute(flavor, "processing", "owners", "same")
        if flavor == "candidate":
            if args.only in (None, "format"):
                execute(flavor, "format", "contract", "same")
                if args.only is None:
                    old_writer = next((job, record) for job, record in writers
                        if job["flavor"] == "before" and job["scenario"] == "components" and job["variant"] == "filled")
                    execute(flavor, "format", "legacy", "read", old_writer)
            if args.only in (None, "journey"):
                for variant in ("effects", "needs", "rain", "processing"):
                    writer = execute(flavor, "journey", variant, "write")
                    if writer:
                        execute(flavor, "journey", variant, "read", writer)
    for job, record in writers:
        check("B2-H", job["flavor"] + job["scenario"] + job["variant"] + " writer immutable",
              record["checkpoint"], hashes(Path(job["game"]) / "saves/slot_0"))
    if not args.before and args.only is None:
        expected_workers = [f"{f}-{s}-{v}-{p}" for f in ("before", "candidate")
            for s, variants in (("components", ("filled", "empty")), ("items", ("distinct",)), ("actors", ("modified",)))
            for v in variants for p in ("write", "read", "same")]
        expected_workers += [f + "-processing-owners-same" for f in ("before", "candidate")]
        expected_workers += ["candidate-format-contract-same", "candidate-format-legacy-read"]
        expected_workers += [f"candidate-journey-{v}-{p}" for v in ("effects", "needs", "rain", "processing") for p in ("write", "read")]
        check("B2-H", "every independent required worker ran", sorted(expected_workers), sorted(planned))
    report["before_failures"] = [{"worker": w["key"], "case": c["case"], "property": c["property"],
        "expected": c["expected"], "observed": c["observed"]}
        for w in report["workers"] if w["job"]["flavor"] == "before"
        for c in (w["result"] or {}).get("checks", []) if not c["passed"]]
    if not args.before and args.only is None:
        check("B2-H", "exact preserved B1 failure signatures", read(ROOT / "tools/b2_before_expectations.json"), report["before_failures"])
        b1_command = [sys.executable, str(candidate / "tools/verify_b1.py"), "--runs-dir", str(ROOT / ".baseline")]
        if args.b1_baseline:
            b1_command += ["--baseline", str(args.b1_baseline.resolve())]
        proc = launch(b1_command, ROOT, timeout=900)
        pointer = read(candidate / "evidence/b1-latest.json") if (candidate / "evidence/b1-latest.json").exists() else {}
        b1 = read(pointer["result"]) if pointer.get("result") and Path(pointer["result"]).exists() else {}
        report["b1_regressions"] = {"process": proc, "result": b1}
        check("B2-09", "complete B1 regression process", [0, True], [proc["exit_code"], b1.get("passed")])
    required = {"B2-01", "B2-02", "B2-03", "B2-04", "B2-05", "B2-06", "B2-07", "B2-08", "B2-09", "B2-H"}
    checks = report["checks"] + [c for w in report["workers"] if w["job"]["flavor"] == "candidate" for c in (w["result"] or {}).get("checks", [])]
    report["coverage"] = {case: {"assertions": sum(c["case"] == case for c in checks),
        "passed": any(c["case"] == case for c in checks) and all(c["passed"] for c in checks if c["case"] == case)} for case in sorted(required)}
    report["assertion_totals"] = dict(total=len(checks), passed=sum(c["passed"] for c in checks), failed=sum(not c["passed"] for c in checks))
    report["planned_workers"] = planned
    report["selected_tests_passed"] = all(c["passed"] for c in checks)
    report["passed"] = not args.before and args.only is None and report["selected_tests_passed"] and all(v["passed"] for v in report["coverage"].values())
    dump(root / "results.json", report)
    dump(ROOT / "evidence/b2-latest.json", {"result": str(root / "results.json"), "passed": report["passed"]})
    print({"result": str(root / "results.json"), "passed": report["passed"], "selected_tests_passed": report["selected_tests_passed"], "before_failures": len(report["before_failures"]), "checks": report["assertion_totals"]}, flush=True)
    return 1 if args.before else 0 if report["passed"] or (args.only and report["selected_tests_passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
