"""Default enforced B1 acceptance, including immutable baseline comparison.

Run: .\.venv\Scripts\python.exe tools/verify_b1.py
--only is development diagnosis and never certifies the full matrix.
All processes have private CWD/saves and dummy SDL. No desktop input is used.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from b1_support import ENV, SEED, dump, hashes, read

ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "1b9531bda0ba593631ce7af4cb728165d7f4a7a9"


def validate_worker(record, job, code, timeout=False):
    if timeout:
        return "bounded child timeout"
    if code != 0:
        return "child nonzero/crash"
    if record is None:
        return "missing worker result"
    for field in ("run_id", "scenario", "phase", "flavor"):
        if record.get(field) != job[field]:
            return "stale or wrong " + field
    if not record.get("checks"):
        return "zero assertions collected"
    if not all(c.get("passed") is True for c in record["checks"]):
        return "false required assertion"
    if not record.get("completed"):
        return "incomplete worker"
    if not record.get("imported_sources"):
        return "missing source binding"
    return None


def selfcheck_child(mode, path, job):
    if mode == "timeout":
        time.sleep(3)
        return
    if mode == "crash":
        raise RuntimeError("deliberate bounded crash control")
    if mode == "missing":
        return
    r = {**job, "completed": True, "checks": [{"passed": True}], "imported_sources": {"main": {}}}
    if mode == "zero":
        r["checks"] = []
    elif mode == "stale":
        r["run_id"] = "old-run"
    elif mode == "phase":
        r["phase"] = "old-phase"
    elif mode == "false":
        r["checks"][0]["passed"] = False
    dump(path, r)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["scenes", "gear", "lurker", "format", "journey", "characterize"])
    parser.add_argument("--baseline", type=Path, help="Reviewed baseline export if its Git commit is unavailable")
    parser.add_argument("--selfcheck-child", nargs=3, metavar=("MODE", "OUTPUT", "JOB"))
    parser.add_argument("--validate-evidence", nargs=4, metavar=("OUTPUT", "JOB", "EXIT_CODE", "TIMEOUT"))
    args = parser.parse_args()
    if args.validate_evidence:
        output, job, exit_code, timeout = args.validate_evidence
        error = validate_worker(read(output) if Path(output).exists() else None,
                                json.loads(job), None if exit_code == "None" else int(exit_code), timeout == "True")
        print(error or "valid worker evidence")
        return 1 if error else 0
    if args.selfcheck_child:
        mode, path, job = args.selfcheck_child
        selfcheck_child(mode, path, json.loads(job))
        return 0
    run_id = "b1-" + time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run = ROOT / ".baseline" / run_id
    run.mkdir(parents=True, exist_ok=False)
    dump(run / "disposable-b1.json", {"run_id": run_id, "seed": SEED, "purpose": "Disposable B1 acceptance; no personal saves"})
    env = dict(os.environ, **ENV)
    candidate = run / "source-candidate"
    candidate.mkdir()
    ignore = shutil.ignore_patterns("saves", "__pycache__", "*.pyc", "game_out.txt")
    shutil.copytree(ROOT / "roguelike", candidate / "roguelike", ignore=ignore)
    shutil.copytree(ROOT / "tools", candidate / "tools", ignore=ignore)
    baseline = run / "source-baseline"
    if args.baseline:
        shutil.copytree(args.baseline, baseline, ignore=shutil.ignore_patterns(".git", ".venv", ".baseline", "saves", "__pycache__", "*.pyc"))
    else:
        zpath = run / "baseline.zip"
        subprocess.run(["git", "archive", "--format=zip", "--output="+str(zpath), BASE_COMMIT], cwd=ROOT, check=True, timeout=30)
        with zipfile.ZipFile(zpath) as z:
            if z.testzip():
                raise RuntimeError("Baseline export CRC")
            z.extractall(baseline)
    expected_baseline = read(ROOT / "tools/b1_baseline_manifest.json")
    observed_baseline = hashes(baseline / "roguelike")
    baseline_ok = all(observed_baseline.get(p) == row for p, row in expected_baseline.items()) and len(observed_baseline) == len(expected_baseline)
    if not baseline_ok:
        raise RuntimeError("Baseline source hashes differ from captured reviewed bytes")
    matrix = read(ROOT / "tools/b1_acceptance_matrix.json")
    report = {"run_id": run_id, "command": [sys.executable, *sys.argv], "cwd": str(ROOT), "seed": SEED,
              "environment": ENV, "baseline_commit": BASE_COMMIT, "baseline_hashes_verified": baseline_ok,
              "candidate_source": hashes(candidate / "roguelike"), "test_source": hashes(candidate / "tools"),
              "workers": [], "checks": [], "coverage": {}, "defects": [], "partial_selection": args.only}
    def check(case, name, expected, observed):
        report["checks"].append(dict(case=case, property=name, expected=expected, observed=observed, passed=expected == observed))
    def launch(command, cwd, timeout=150):
        start = time.monotonic()
        try:
            p = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
            return {"command": command, "cwd": str(cwd), "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr,
                    "elapsed_seconds": time.monotonic()-start, "timeout": False}
        except subprocess.TimeoutExpired as error:
            # subprocess.run kills and waits for only the direct owned child.
            return {"command": command, "cwd": str(cwd), "exit_code": None, "stdout": str(error.stdout), "stderr": str(error.stderr),
                    "elapsed_seconds": time.monotonic()-start, "timeout": True}
    if args.only is None:
        for mode in ("zero", "missing", "stale", "phase", "crash", "timeout", "false"):
            job = {"run_id":run_id,"scenario":"runner-negative","phase":mode,"flavor":"selfcheck"}
            output = run / ("negative-" + mode + ".json")
            proc = launch([sys.executable, str(Path(__file__).resolve()), "--selfcheck-child", mode, str(output), json.dumps(job)], run, 0.2 if mode == "timeout" else 10)
            error = validate_worker(read(output) if output.exists() else None, job, proc["exit_code"], proc["timeout"])
            validation = launch([sys.executable,str(Path(__file__).resolve()),"--validate-evidence",str(output),json.dumps(job),str(proc["exit_code"]),str(proc["timeout"])],run,10)
            check("H03", mode+" produces failed acceptance process", 1, validation["exit_code"])
            check("H03", mode+" names the failure", True, bool(error) and error in validation["stdout"])
            report.setdefault("runner_negative_controls", []).append({"mode":mode,"acceptance_exit_code":validation["exit_code"],"validation_process":validation,"reason":error,**proc})
        # Reproduce the original unchanged tool, then enforce its corrected regressions.
        for flavor, source, expected_counts in (("baseline",baseline,[32,17,15]), ("candidate",candidate,[32,32,0])):
            prefix = "diagnostics-" + uuid.uuid4().hex[:8]
            proc = launch([sys.executable,str(candidate/"tools/b1_diagnostic_guard.py"),str(source/"tools/persistence_diagnostics.py"),"--prefix",prefix,"--assert-properties"],source,340)
            record_path=source/"evidence"/(prefix+"-results.json")
            record=read(record_path) if record_path.exists() else {}
            checks=[c for row in record.get("results",[]) for c in row.get("checks",[])]
            passed=sum(c["property_passed"] for c in checks)
            check("H01", flavor+" diagnostic assertions",expected_counts,[len(checks),passed,len(checks)-passed])
            check("H01", flavor+" ten complete workers",True,len(record.get("results",[]))==10 and record.get("harness_completed") is True)
            check("H01", flavor+" assertion exit policy",1 if flavor=="baseline" else 0,proc["exit_code"])
            dump(run/(flavor+"-original-diagnostics.json"),{"process":proc,"results":record})
            print(flavor,"original diagnostics",len(checks),passed,"passed",flush=True)
    writers = []
    planned = []
    def execute(scenario, variant, phase, flavor="candidate", writer=None):
        key = "-".join((flavor,scenario,variant,phase))
        planned.append(key)
        session = run / "workers" / key
        session.mkdir(parents=True, exist_ok=False)
        game = session / "roguelike"
        source = baseline if flavor == "baseline" else candidate
        shutil.copytree(source/"roguelike", game, ignore=ignore)
        job = dict(run_id=run_id, run_root=str(run), scenario=scenario, variant=variant, phase=phase, flavor=flavor,
                   game=str(game), result=str(session/"result.json"))
        if writer:
            wjob, wrecord = writer
            shutil.copytree(Path(wjob["game"])/"saves", game/"saves")
            check("H04", key+" reader starts exact writer bytes", wrecord.get("checkpoint"), hashes(game/"saves/slot_0"))
            job["expected"] = wjob["result"]
        else:
            slot = game/"saves/slot_0"
            slot.mkdir(parents=True)
            dump(slot/"world.json", {"seed":SEED})
        dump(session/"job.json",job)
        proc=launch([sys.executable,str(candidate/"tools/b1_worker.py"),str(session/"job.json")],game,180)
        record=read(job["result"]) if Path(job["result"]).exists() else None
        error=validate_worker(record,job,proc["exit_code"],proc["timeout"])
        check("H02",key+" completes with valid evidence",None,error)
        if record and record.get("imported_sources"):
            for name, binding in record["imported_sources"].items():
                expected_hash = hashlib.sha256((source/"roguelike"/binding["relative"]).read_bytes()).hexdigest()
                check("H02",key+" imported "+name,expected_hash,binding["sha256"])
        if writer and record:
            check("H04",key+" independent reader PID",True,record["pid"]!=writer[1]["pid"])
        dump(session/"process.json",proc)
        report["workers"].append({"key":key,"job":job,"process":proc,"result":record,"validation_error":error})
        if record:
            report["defects"].extend({"worker":key,**d} for d in record.get("defects",[]))
        print(key, "PASS" if error is None else "FAIL", (record or {}).get("error",error),flush=True)
        dump(run/"results.json",report)
        if phase == "write" and error is None:
            writers.append((job,record))
        return (job,record) if error is None else None
    def family(scenario, variants, flavor="candidate"):
        for variant in variants:
            writer=execute(scenario,variant,"write",flavor)
            if writer:
                execute(scenario,variant,"read",flavor,writer)
            execute(scenario,variant,"same",flavor)
    if args.only in (None,"scenes"):
        family("scenes",("surface","submap"))
    if args.only in (None,"gear"):
        family("gear",("empty","jerky","gear","first","second","reordered","inactive","burnout"))
    if args.only in (None,"lurker"):
        family("lurker",("dormant","awake","pending","owners"))
    if args.only in (None,"format"):
        for variant in ("versions","fields","scenes","bootstrap"):
            execute("format",variant,"same")
    if args.only in (None,"characterize"):
        for flavor in ("baseline","candidate"):
            family("characterize",("scope",),flavor)
    if args.only in (None,"journey"):
        for flavor in ("baseline","candidate"):
            for variant in ("movement","transfer","combat","text","processing","stairs","boundary","debug","needs_f9"):
                execute("journey",variant,"loop",flavor)
        writer=execute("journey","nondebug","write")
        if writer:
            execute("journey","nondebug","read",writer=writer)
    for job,record in writers:
        check("H04",job["scenario"]+" canonical writer remains immutable",record["checkpoint"],hashes(Path(job["game"])/"saves/slot_0"))
    report["planned_workers"]=planned
    report["known_defect_ids"]=sorted(set(d["id"] for d in report["defects"]))
    # Exact baseline/candidate characterization signatures must match.
    signatures={}
    for flavor in ("baseline","candidate"):
        signatures[flavor]=sorted((d["id"],json.dumps(d["symptom"],sort_keys=True)) for d in report["defects"] if d["worker"].startswith(flavor))
    check("H03","baseline/candidate exact deferred symptoms",signatures["baseline"],signatures["candidate"])
    required_keys = []
    for scenario, variants in (("scenes",("surface","submap")),
                               ("gear",("empty","jerky","gear","first","second","reordered","inactive","burnout")),
                               ("lurker",("dormant","awake","pending","owners")),
                               ("characterize",("scope",))):
        if args.only in (None, scenario):
            for flavor in (("baseline","candidate") if scenario == "characterize" else ("candidate",)):
                required_keys += ["-".join((flavor,scenario,v,p)) for v in variants for p in ("write","read","same")]
    if args.only in (None,"format"):
        required_keys += ["candidate-format-"+v+"-same" for v in ("versions","fields","scenes","bootstrap")]
    if args.only in (None,"journey"):
        required_keys += [f+"-journey-"+v+"-loop" for f in ("baseline","candidate") for v in ("movement","transfer","combat","text","processing","stairs","boundary","debug","needs_f9")]
        required_keys += ["candidate-journey-nondebug-write", "candidate-journey-nondebug-read"]
    check("H03","all mandatory parameter workers executed",sorted(required_keys),sorted(planned))
    all_checks=report["checks"]+[c for w in report["workers"] for c in (w["result"] or {}).get("checks",[])]
    for case in matrix["cases"]:
        rows=[c for c in all_checks if c["case"]==case["id"]]
        report["coverage"][case["id"]]={"title":case["title"],"classification":case["classification"],
              "assertions":len(rows),"passed":bool(rows) and all(c["passed"] for c in rows)}
    report["assertion_totals"]={"total":len(all_checks),"passed":sum(c["passed"] for c in all_checks),"failed":sum(not c["passed"] for c in all_checks)}
    selected_pass=all(c["passed"] for c in all_checks) and all(w["validation_error"] is None for w in report["workers"]) and signatures["baseline"]==signatures["candidate"]
    report["passed"]=selected_pass and args.only is None and all(v["passed"] for v in report["coverage"].values())
    report["selected_tests_passed"]=selected_pass
    dump(run/"results.json",report)
    dump(ROOT/"evidence/b1-latest.json",{"run_id":run_id,"result":str(run/"results.json"),"passed":report["passed"],"selected_tests_passed":selected_pass})
    print(json.dumps({"result":str(run/"results.json"),"passed":report["passed"],"selected_tests_passed":selected_pass,"assertions":report["assertion_totals"],"known_defect_ids":report["known_defect_ids"]}),flush=True)
    return 0 if selected_pass and (args.only is not None or report["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
