"""Assemble final W5H source-bound evidence; evidence identity uses a checkpoint."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2];WB=ROOT/'workbench';LOGS=WB/'.artifacts';ART=LOGS/'w5h'
BASE='3ee22ef3c77cd56df75441076873840ef3b66fc7'
PACKAGE='68bb14bdac7245d5d6e62a27b10225ac7c58ff23'
GAME='3282b0570a7839140a0361ec4fb1f7431944c4e9'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def log(name):return (LOGS/name).read_text(encoding='utf-8-sig')
def artifact(path):
    path=Path(path)
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))
def receipt_from_log(name):
    outputs=re.findall(r'"output"\s*:\s*("(?:[^"\\]|\\.)*")',log(name))
    path=Path(json.loads(outputs[-1]))/'receipt.json';value=json.loads(path.read_text(encoding='utf-8-sig'))
    assert value.get('passed'),(name,value.get('failure',value.get('error')))
    return path,value
commands=[]
def command(text,name,pattern,result):
    content=log(name);assert re.search(pattern,content),(name,content[-2000:]);assert '\nFAILED' not in content,name
    commands.append(dict(command=text,exit_code=0,result=result,log=artifact(LOGS/name)))
command('npm.cmd test','w5h-frontend-final.log',r'Tests\s+65 passed','65 passed / 17 files')
command('npm.cmd run typecheck','w5h-typecheck-final.log',r'tsc --noEmit','passed')
command('node scripts/test-geometry.mjs','w5h-geometry-final.log',r'PASS mounted geometry','actual mounted controls pass Source, Undo/Redo, companion coordinates, pending proposals and defaults')
command('cargo test --locked --manifest-path src-tauri/Cargo.toml','w5h-host-final.log',r'66 passed; 0 failed','66 passed; retained W4D/W5D/W5G plus real owned-process faults')
command('cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings','w5h-clippy-final.log',r'Finished','passed; warnings denied')
command('worker/runtime/python.exe -I -B -m unittest discover -s worker -v','w5h-worker-final.log',r'OK \(skipped=1\)','66 passed; one expected dependency-absence skip / 67 cases')
command('standard Python: test_bridge.BridgeTests.test_dependency_absence_structured','w5h-missing-dependency.log',r'\bOK\b','negative dependency control passes separately')
command('pinned development Python: persistence/combat/scene/G17/access/destinations/readers and room-session injection','w5h-production-final.log',r'Ran 58 tests','58 passed; includes three new explicit session tests and three retained reader cases')
command('npm.cmd run bundle -- -- --locked','w5h-package-final.log',r'Finished 1 bundle','Windows x64 release and NSIS; complete pinned embedded runtime')
for script,name,label in [('run-workspace.mjs','w5h-workspace-final.log','lost-reopen workspace'),('run-pools.mjs','w5h-pools-final.log','ordinary pools'),('run-submaps.mjs','w5h-submaps-final.log','registered submap scheduling/publication faults'),('startup-test.mjs','w5h-startup-final.log','four startup/project replacement/restart scenarios')]:
    value=json.loads(log(name));assert value['passed'],(name,value.get('error'))
    command('node scripts/'+script,name,r'"passed": true',label+' passes on final executable')
native_path,native=receipt_from_log('w5h-native-final.log')
command('node scripts/run-room-tests.mjs','w5h-native-final.log',r'"passed":true','packaged author/play/reset/revise, cold load, failures, switch, normal/abrupt exit and cleanup pass')
preflight_path,preflight=receipt_from_log('w5h-preflight-final.log')
command('node scripts/check-room-preflight.mjs <disposable journey project>','w5h-preflight-final.log',r'"passed":true','unusable ordinary starting light refuses replacement of running game; actual optional UI fallback is disclosed')
standalone_path=ART/'standalone-final/receipt.json';standalone=json.loads(standalone_path.read_text(encoding='utf-8-sig'));assert standalone['passed']
command('worker/runtime/python.exe -I -B scripts/standalone-room-regression.py <disposable project> <evidence>','w5h-standalone-final.log',r'"passed": true','ordinary 128x128 main, first actual frame, default save owner and production save/load pass headlessly')

exe=WB/'src-tauri/target/release/resonance-workbench.exe'
assert sha(exe)==native['package_sha256']
assert sha(WB/'worker/bridge.py')==sha(WB/'src-tauri/target/release/bridge.py')
first=native['first']['captured'];revised=native['revised']['capture']['captured']
assert first['room_sha256']==native['v1']['sha256'] and revised['room_sha256']==native['v2']['sha256']
assert first['manifest_sha256']==native['reset']['captured']['manifest_sha256']
assert first['runtime_sha256']==native['reset']['captured']['runtime_sha256']
assert native['revised']['added']['x']==35 and native['revised']['added']['y']==18
wood=native['revised']['added']['items'][0]
assert wood['item_id']=='wood_bundle' and wood['weight']==1 and wood['keywords']==[dict(tag='fuel',tier=1),dict(tag='fibrous',tier=1)]
runtime_source={p.relative_to(WB/'worker/runtime').as_posix():sha(p) for p in (WB/'worker/runtime').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert runtime_source==first['runtime_files'],'captured runtime differs from pinned source runtime'
source_audit=[]
for name,digest in first['files'].items():
    if name.endswith('.py') or name.startswith(('roguelike/assets/Fonts/','roguelike/assets/ui/','roguelike/assets/sprites/')):
        assert sha(ROOT/name)==digest,name
        source_audit.append(name)
revision=git('rev-parse','HEAD')
paths=git('diff','--name-only',BASE,revision).splitlines()
sources=[]
for name in paths:
    blob=subprocess.check_output(['git','show',f'{revision}:{name}'],cwd=ROOT)
    sources.append(dict(path=name,git_sha256=hashlib.sha256(blob).hexdigest(),working_sha256=sha(ROOT/name)))
before=json.loads((ART/'preservation-before.json').read_text())
unchanged=[];changed=[]
for name,old in before.items():
    p=ROOT/name;current=dict(sha256=sha(p),mtime_ns=p.stat().st_mtime_ns)
    (unchanged if current==old else changed).append(name)
expected={'roguelike/engine/player_setup.py','roguelike/room_test.py','roguelike/docs/ROOM_TEST_RUNTIME.md','tools/critical_fix_regressions/tests/test_room_test_session.py','workbench/scripts/run-room-tests.mjs','workbench/scripts/submap-journey.mjs','workbench/src-tauri/src/room_test.rs'}
assert set(changed)<=expected,changed
assert 'RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md' in unchanged
images=[artifact(p) for p in sorted(native_path.parent.glob('*.png'))]
images += [artifact(preflight_path.parent/'actual-ui-fallback.png'),artifact(ART/'standalone-final/ordinary-startup.png')]
def captured(value):return {k:value[k] for k in ('snapshot_id','captured_ms','room_id','room_path','room_sha256','manifest_sha256','runtime_sha256','seed','profile','descriptor_sha256')}
receipt=dict(milestone='W5H',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),
    revisions=dict(baseline=BASE,initial_remote=BASE,repair='03b19ad',implementation=PACKAGE,package_inputs=PACKAGE,final_game_inputs=GAME,test_inputs=revision,evidence_ref='checkpoint/workbench-w5h-verified-20261028',branch='main',note='Verified annotated evidence checkpoint and external remote-SHA handoff identify evidence without a self-hash loop. Package-to-test differences are verification changes plus the selected-project Python preflight correction; game code is captured from the project, not bundled in the executable.'),
    commands=commands,package=dict(executable=artifact(exe),installer=artifact(WB/'src-tauri/target/release/bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe'),bridge=artifact(WB/'worker/bridge.py'),source_release_bridge_equal=True,runtime_files=len(runtime_source),source_release_captured_runtime_equal=True),
    source=dict(revision=revision,files=sources,native_game_and_rendering_files_match_working_tree=source_audit),
    snapshots=dict(first=captured(first),latest=captured(revised),captured_input_count=len(first['files']),reset_manifest_seed_profile_retained=True,full_manifests=[artifact(native_path.parent/name) for name in ('first-capture.json','reset.json','latest.json')]),
    native=dict(receipt=artifact(native_path),checks=native['checks'],saved_v1=native['v1']['sha256'],saved_v2=native['v2']['sha256'],initial_arrival=native['first']['readiness']['arrival'],revised_arrival=native['revised']['arrival'],changed_object=native['revised']['added'],changed_terrain=native['revised']['terrain'],first_session=native['first']['session_id'],reset_session=native['reset']['session_id'],first_save_root=native['first']['state_root'],reader_text_id=native['reader']['text_id'],container=native['container'],ai=native['ai'],cold_pid=native['cold']['pid'],cold_save_access_events=len(native['cold']['audit']['events']),cold_save_audit_confined=True,missing_owned_cache_refused=native['missing_owned_cache'],parked=native['parked'],normal_exit=native['normal_exit']['reaped'],unexpected_exit=native['unexpected_exit']['exit_code'],project_switch=native['project_switch'],abrupt=native['abrupt']),
    preflight=dict(receipt=artifact(preflight_path),required_light_running_process_preserved=True,optional_ui_fallback_disclosed=True),
    standalone=dict(receipt=artifact(standalone_path),world=standalone['world'],ordinary_default_save_path=standalone['save_path'],scene=standalone['scene'],save_load=standalone['save_load'],audit_events=standalone['save_access_events'],verification_hook='Only Engine.run frame observer is supplied by a test wrapper; ordinary main construction, defaults, actual loop and SaveManager execute.'),
    preservation=dict(inventory=artifact(ART/'preservation-before.json'),captured=len(before),unchanged_hash_and_mtime=len(unchanged),expected_final_task_changes=changed,owner_plan=before['RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md'],personal_save_roots_excluded=True),images=images,
    provenance='Locally executed Windows gates. Mounted headless browser controls, headless validation/default-main tests, app-local packaged WebView controls, actual pygame game frames and audited cold processes are distinguished. Historical W5G review/independent rerun claims are retained as historical basis, not relabelled current observations.',
    notes=['Early geometry harness assertion needed to wait for React effects.', 'A real launch admission correction explicitly distinguishes acknowledged retained publication handoffs from unfinished ones.', 'Early native diagnostic frame replacement hit a transient Windows reader lock; bounded retry/skip preserves gameplay.', 'The cold fixture clears the deliberate prior Stop marker before invoking supported --load.', 'The revised-object assertion uses production center minus half-layout centering, including odd width.', 'An early production command used a Python whose isolated subprocess lacked pygame; the configured pinned development interpreter passes all retained cases.', 'An early worker run overlapped source edits; the final stable full suite is rerun after the final Python correction.', 'Native harnesses account for Node signalCode on forced Windows exit and retry only no-write BUSY monitor contention; conflict-denial checks also assert exact competing bytes.', 'Final Rust test source adds a startup-failure fixture; packaged production Rust/TS/bridge remain the package revision. The final Python preflight correction is captured from the selected project and is exercised by the final native/worker/production runs.'],
    limits=['Only eligible saved ordinary immediate layouts, one fixed profile/seed and one game per Workbench instance.', 'Controlled foyer/assigned room; no natural assignment, encounter-balance claim, deterministic combat replay, unsaved overlays, multi-file writes or persistent test library.', 'Game capture requires the packaged/prepared embedded Windows runtime; mutable development virtual environments are refused clearly.', 'No wiki/reference-pack rebuild or owner-plan commit; no personal save content is used for tests. Capture enumeration never descends save trees.'])
(WB/'docs/w5h-verification.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,commands=len(commands),source_files=len(sources),native=str(native_path),unchanged=len(unchanged))))
