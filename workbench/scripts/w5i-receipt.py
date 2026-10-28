"""Assemble concise source-bound evidence; never read personal campaigns."""
import hashlib, json, re, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5i'
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def ref(p):
    p=Path(p);return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def read(p):return json.loads(Path(p).read_bytes())
native_path=sorted(ART.glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns)[-1]
native=read(native_path);assert native.get('passed') and native.get('saved_dependency_staled_fresh_preview')
assert native['natural']['staging']['outside_protected_entrance_footprint']
session_path=sorted((ROOT/'workbench/.artifacts/w5h').glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns)[-1]
session=read(session_path);assert session['passed']
assert native['package_sha256']==session['package_sha256']==digest(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe')
commands=[]
for name,command,pattern in [
 ('frontend-verified.log','npm.cmd test',r'67 passed'),('typecheck-verified.log','npm.cmd run typecheck',r'tsc --noEmit'),
 ('host-verified.log','cargo test --locked --manifest-path src-tauri/Cargo.toml',r'67 passed; 0 failed'),
 ('clippy-verified.log','cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings',r'Finished'),
 ('assignment-verified.log','configured development Python: unittest test_authored_assignment -v',r'Ran 6 tests[\s\S]*OK'),
 ('production-verified.log','configured development Python: session/persistence/combat/scene/G17/access/destinations (PYTHONPATH game, tests, tools)',r'Ran 60 tests[\s\S]*OK'),
 ('worker-stable.log','pinned runtime: python -I -B -m unittest discover -s worker -v',r'Ran 70 tests[\s\S]*OK'),
 ('assignment-worker-verified.log','pinned runtime: unittest test_assignment.py',r'Ran 3 tests[\s\S]*OK'),
 ('missing-dependency.log','standard development Python: test_dependency_absence_structured',r'Ran 1 test[\s\S]*OK'),
 ('package-verified.log','npm.cmd run bundle -- -- --locked',r'Finished 1 bundle'),
 ('native-final-evidence.log','node scripts/run-assignments.mjs',r'"passed":true'),
 ('workspace.log','node scripts/run-workspace.mjs',r'"passed": true'),
 ('room-session.log','node scripts/run-room-tests.mjs',r'"passed":true'),
 ('ordinary.log','pinned runtime: scripts/standalone-room-regression.py (fresh disposable inputs)',r'"passed": true')]:
    p=ART/name;s=p.read_text(encoding='utf-8-sig');assert re.search(pattern,s),(name,s[-1000:])
    commands.append(dict(command=command,exit_code=0,log=ref(p)))
preservation=read(ART/'preservation-after.json');assert not preservation['failures']
files=git('diff','--name-only','checkpoint/workbench-w5i-start-20261028','HEAD').splitlines()
source_hashes={p:dict(working_sha256=digest(ROOT/p),git_sha256=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)).hexdigest()) for p in files if (ROOT/p).is_file()}
fixture=Path(native['root']);code={};differences=[]
for p in (ROOT/'roguelike').rglob('*.py'):
    if any(part in ('saves','__pycache__') for part in p.parts):continue
    relative=p.relative_to(ROOT);copied=fixture/relative
    if not copied.is_file() or digest(p)!=digest(copied):differences.append(relative.as_posix())
    code[relative.as_posix()]=digest(p)
assert not differences,differences
release=ROOT/'workbench/src-tauri/target/release';bundled=release/'python';runtime=ROOT/'workbench/worker/runtime'
runtime_rows={p.relative_to(runtime).as_posix():digest(p) for p in runtime.rglob('*') if p.is_file()}
packaged_rows={p.relative_to(bundled).as_posix():digest(p) for p in bundled.rglob('*') if p.is_file()}
assert runtime_rows==packaged_rows
assert digest(release/'bridge.py')==digest(ROOT/'workbench/worker/bridge.py')
evidence=ROOT/'workbench/docs/evidence/w5i';evidence.mkdir(parents=True,exist_ok=True)
import shutil
for name in ('natural-exterior.png','natural-room.png','natural-reader.png','natural-return.png','assignment-sample.png'):
    shutil.copy2(native_path.parent/name,evidence/name)
preview=native['preview'];sample={k:preview[k] for k in ('profile_path','profile_sha256','contract','descriptor_sha256','runtime','source','seed','width','height','plan_mode','generation_revision','target_type','authored_chance','matching_count','authored_count','procedural_count','truncated')}
result=dict(milestone='W5I',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),
 revisions=dict(reviewed_start='ba66670604ddde091918a6009d92ed4ab1c56612',initial_remote='ba66670604ddde091918a6009d92ed4ab1c56612',
                implementation=git('rev-parse','6484a59'),package_inputs=git('rev-parse','2df8413'),test_inputs=git('rev-parse','HEAD'),
                evidence_ref='checkpoint/workbench-w5i-verified-20261028',branch='main',
                note='Package Rust/TS/bridge inputs remain the implementation package boundary. The later game numeric-bound diagnostic correction is imported from the selected project; final natural fixture Python hashes all match. Evidence commit/tag and external remote readback avoid a self-hash loop.'),
 commands=commands,profile_contract='authored-submap-selection-1',shipped_profile=read(ROOT/'roguelike/data/generation/authored_submap_selection.json'),
 saved_reopened=dict(room_a=native['room_a']['sha256'],room_b=native['room_b']['sha256'],text=native['text']['sha256'],profile=native['profile']['sha256'],same_id_room_revision=native['room_a_revision']['sha256'],changed_profile=native['changed_profile_sha256'],
                     note='Supported packaged controls validate/review/apply, host expected-hash reopen and reopened token/disk hashes; no accepted room/profile file hand-edited. Fault injections are separately labelled.'),
 sample=sample,natural=native['natural'],arrival=native['arrival'],readable=dict(carrier='letter',text_id=native['reader']['text_id'],title=native['reader']['definition']['title'],first_page=native['reader']['definition']['pages'][0]['text']),
 persistence=dict(f5_f9=native['f5_f9'],cold=native['cold'],absent_profile=native['absent_profile_load'],invalid_profile=native['invalid_profile_load'],
                  distinction='Recorded layout IDs persist after profile edits. Current same-ID definitions apply on pending first construction; generated scenes retain saved geometry, contents and mutation.'),
 ownership=dict(cancelled_preview_stale=True,saved_dependency_staled_fresh_preview=True,confirmed_conflict=native['conflict'],invalid_recovery_fresh_validation=native['recovered_fresh_validation'],parked_item_draft_unchanged=True),
 packaged_room_session=dict(passed=True,receipt=ref(session_path),scope='Actual packaged W5H capture/reset/latest-saved, cold load, missing-cache refusal, gameplay, stop/quit/owner-death/project lifecycle.'),
 artifacts=[ref(native_path),ref(ART/'ordinary/evidence/receipt.json'),ref(ART/'preservation-after.json'),*[ref(p) for p in sorted(evidence.glob('*.png'))]],
 package=dict(executable=ref(release/'resonance-workbench.exe'),installer=ref(release/'bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe'),bridge=ref(release/'bridge.py'),runtime_files=len(runtime_rows),runtime_manifest_sha256=hashlib.sha256(json.dumps(runtime_rows,sort_keys=True).encode()).hexdigest(),runtime_all_files_equal=True),
 source_hashes=source_hashes,final_natural_python_inputs=dict(files=len(code),manifest_sha256=hashlib.sha256(json.dumps(code,sort_keys=True).encode()).hexdigest(),differences=differences),
 preservation=preservation,fault_injections=native['fault_injections'],
 prior_attempts=['Early shared payload validation incorrectly hardened protected starting-lab inspection; scoped to eligible originals and rerun.',
 'Early restoration fixture used 1x1 dimensions; corrected. Wrong regression module names/PYTHONPATH and embedded child-import setup were corrected with the configured pinned development environment.',
 'First natural fixture enabled debug bindings, so F5 teleported/F9 dumped state; corrected per-engine debug=False and rerun.',
 'Windows diagnostic command-file rename briefly hit a reader lock; fixture retries only transient sharing errors. Normal quit does not wait for another frame.',
 'Packaging overlapped a test launch, causing an NSIS file-sharing failure; final package completes before all final native observations.',
 'Initial freshness harness reused a cancelled/stale preview and omitted confirmed on conflict IPC; final evidence obtains a fresh preview before the dependency edit and requires semantic refusal from confirmed apply.',
 'Initial natural staging was within the exterior shell; final staging excludes the complete production protected entrance footprint.',
 'Worker run interleaved a numeric source correction and had one missing-result test error; final stable full worker suite runs after production code is frozen.'],
 limits=['Local Windows observations and headless/app-local production rendering; no independent rerun is claimed.',
 'Natural entry stages the normal player outside the real entrance to avoid a world walk. It proves local access/use/return, not unaided discovery, pacing, balance or whole-game fun.',
 'One fixed profile and one ordinary type at a time. No whole-world play launcher, batch generation, unsaved overlays, campaign migration or new population layer.',
 'Detailed disposable manifests/saves/logs remain ignored locally; five concise rendered evidence frames are committed. Wiki/reference pack and owner plan are unchanged.'])
out=ROOT/'workbench/docs/w5i-verification.json';out.write_text(json.dumps(result,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,receipt=str(out),native=str(native_path),sample={k:sample[k] for k in ('seed','matching_count','authored_count','procedural_count')},runtime_files=len(runtime_rows))))
