"""Compare W0's pre-edit local manifest without publishing personal save names."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
before = json.loads((ROOT / "workbench/.artifacts/source-before.json").read_text(encoding="utf-8"))
changed = []
for group in ("files", "saves"):
    for relative, expected in before[group].items():
        p = ROOT / relative
        if not p.is_file():
            changed.append((group, "removed", relative)); continue
        stat = p.stat()
        actual = {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "size": stat.st_size,
                  "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns}
        if any(actual[k] != v for k, v in expected.items()):
            changed.append((group, "changed", relative))
current_saves = {p.relative_to(ROOT).as_posix() for p in (ROOT / "roguelike/saves").rglob("*") if p.is_file()}
old_saves = {p.replace("\\", "/") for p in before["saves"]}
if current_saves != old_saves:
    changed.append(("saves", "file-set-difference", "details retained locally"))
receipt = {"passed": not changed, "baseline_head": before["head"], "source_files_checked": len(before["files"]),
           "save_files_checked": len(before["saves"]), "unchanged_bytes_and_measured_metadata": not changed,
           "metadata": ["size", "mtime_ns", "ctime_ns (source only)"], "save_file_set_unchanged": current_saves == old_saves,
           "owner_plan_sha256": before["files"]["RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md"]["sha256"],
           "preflight_manifest_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
           "changes_count": len(changed)}
(ROOT / "workbench/.artifacts/preservation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print(json.dumps(receipt, indent=2))
if changed:
    # Names remain in ignored local evidence, never in the committed summary.
    (ROOT / "workbench/.artifacts/preservation-changes.json").write_text(json.dumps(changed, indent=2), encoding="utf-8")
    raise SystemExit(1)
