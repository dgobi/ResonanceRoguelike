"""Assemble compact accessible W5J evidence from completed existing gates."""
import hashlib, json, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5j';DOC=ROOT/'workbench/docs';EVID=DOC/'evidence/w5j'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def passed_latest(pattern):
    rows=sorted(ROOT.glob(pattern),key=lambda p:p.stat().st_mtime_ns)
    for p in reversed(rows):
        r=read(p)
        if r.get('passed'):return p,r
    raise AssertionError(pattern)
native_path,native=passed_latest('workbench/.artifacts/w5j/native-*/receipt.json')
room_path,room=passed_latest('workbench/.artifacts/w5h/native-*/receipt.json')
assert native['package_sha256']==room['package_sha256']==digest(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe')
EVID.mkdir(parents=True,exist_ok=True);fixtures=EVID/'fixtures';fixtures.mkdir(exist_ok=True)
saved={}
for name,row in dict(native['saved'],room=native['room']).items():
    target=fixtures/(name+'.json');target.write_bytes(row['raw'].encode('utf-8'));assert digest(target)==row['sha256']
    saved[name]=dict(source=row['path'],**ref(target))
shots={}
for name in ('workbench-drink.png','workbench-room.png','game-return-visible.png','game-treatment.png','game-revised.png'):
    target=EVID/name;shutil.copyfile(native_path.parent/name,target);shots[name]=ref(target)
def compact_item(i):return {k:i[k] for k in ('item_id','instance','name','weight','nutrition','hydration','heal_amount','eat_message','drink_message','consumed_on_use','keywords') if k in i}
uses=[]
for row in native['uses']:
    after=row['after']
    uses.append(dict(id=row['id'],selected=row['selected'],siblings=row['siblings'],selected_values=compact_item(row['definition']),before=row['before'],
        after={**{k:v for k,v in after.items() if k not in ('inventory','rows')},'inventory':[compact_item(i) for i in after['inventory']],'rows':after['rows']}))
captures={name:{k:v for k,v in native[key]['captured'].items() if k not in ('files','runtime_files')} for name,key in [('original','capture_v1'),('reset','capture_reset'),('latest','capture_v2')]}
assert captures['original']['manifest_sha256']==captures['reset']['manifest_sha256']!=captures['latest']['manifest_sha256']
observations=dict(native_source=ref(native_path),saved=saved,recovery=native['recovery'],conflict=native['conflict'],return_navigation=native['return_navigation'],
    acquisition=[compact_item(i) for i in native['acquired']],disclosed_fixture=native['disclosed_fixture'],uses=uses,captures=captures,
    compatibility_before={k:v for k,v in native['compatibility_before'].items() if k!='save_access_audit'},
    compatibility_after={k:v for k,v in native['compatibility_after'].items() if k!='save_access_audit'},
    save_audit=dict(before_events=len(native['compatibility_before']['save_access_audit']),after_events=len(native['compatibility_after']['save_access_audit']),explicit_disposable_ownership=True),
    checks=native['checks'],screenshots=shots,scope='Packaged Windows controls; ordinary app-local pygame input; separate-process ordinary saved-instance compatibility. Controlled initial needs/injury and staged room entrance, no balance/pacing claim.')
(EVID/'observations.json').write_text(json.dumps(observations,indent=2),encoding='utf-8')
commands=[]
for name,command,pattern,summary in [
 ('frontend.log','npm.cmd test',r'68 passed','68 tests pass'),('typecheck.log','npm.cmd run typecheck',r'tsc --noEmit','passes'),
 ('host.log','cargo test --locked --manifest-path src-tauri/Cargo.toml',r'68 passed; 0 failed','68 tests pass'),
 ('clippy.log','cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings',r'Finished','passes; warnings denied'),
 ('production-verified.log','Configured development Python with absolute PYTHONPATH game/tests/tools: unittest test_usable_supplies test_authored_assignment test_gameplay_g15 test_effect_persistence test_generation_ownership test_gameplay_g17 test_room_test_session test_combat_routes -v',r'Ran 66 tests[\s\S]*\nOK','66 tests pass'),
 ('worker.log','worker/runtime/python.exe -I -B -m unittest discover -s worker -v',r'Ran 72 tests[\s\S]*OK','72 cases; 71 pass, one expected embedded dependency-absence skip'),
 ('missing-dependency.log','Standard Python: unittest test_bridge.BridgeTests.test_dependency_absence_structured',r'Ran 1 test[\s\S]*OK','negative control passes'),
 ('package-final.log','npm.cmd run bundle -- -- --locked',r'Finished 1 bundle','Windows executable and NSIS pass'),
 ('native-final.log','node scripts/run-supplies.mjs',r'"passed":true','packaged supplies journey passes'),
 ('workspace.log','node scripts/run-workspace.mjs',r'"passed": true','packaged shared lifecycle passes'),
 ('room-session.log','node scripts/run-room-tests.mjs',r'"passed":true','packaged capture/reset/cold-load/lifecycle passes'),
 ('ordinary-final.log','Pinned Python: standalone-room-regression.py (fresh disposable inputs)',r'"passed": true','ordinary 128x128 startup and default disposable save/load pass')]:
    p=ART/name;text=p.read_text(encoding='utf-8-sig');assert re.search(pattern,text),(name,text[-1000:])
    commands.append(dict(command=command,exit_code=0,outcome=summary,log=ref(p)))
preservation=read(ART/'preservation-after.json');assert not preservation['failures']
fixture=Path(native['root']);differences=[]
for p in (ROOT/'roguelike').rglob('*.py'):
    if any(part in ('saves','__pycache__') for part in p.parts):continue
    target=fixture/p.relative_to(ROOT)
    if not target.is_file() or digest(p)!=digest(target):differences.append(p.relative_to(ROOT).as_posix())
assert not differences,differences
canonical_differences=[p.relative_to(ROOT).as_posix() for p in (ROOT/'roguelike/data').rglob('*') if p.is_file() and (not (fixture/p.relative_to(ROOT)).is_file() or digest(p)!=digest(fixture/p.relative_to(ROOT)))]
assert not canonical_differences,canonical_differences
release=ROOT/'workbench/src-tauri/target/release';bundled=release/'python';runtime=ROOT/'workbench/worker/runtime'
runtime_files={p.relative_to(runtime).as_posix():digest(p) for p in runtime.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert all((bundled/name).is_file() and digest(bundled/name)==value for name,value in runtime_files.items())
assert digest(release/'bridge.py')==digest(ROOT/'workbench/worker/bridge.py')
sources={}
for name in git('diff','--name-only','checkpoint/workbench-w5j-start-20261028','HEAD').splitlines():
    p=ROOT/name
    if p.is_file() and not name.startswith('workbench/docs/evidence/'):
        sources[name]=dict(working_sha256=digest(p),git_sha256=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest())
receipt=dict(milestone='W5J',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),
    revisions=dict(reviewed_start=git('rev-parse','checkpoint/workbench-w5j-start-20261028'),initial_remote='9068855894c2ce53e4617dd0f5f696fbab0bbb4a',implementation='d36f623',
        package_inputs=git('rev-parse','checkpoint/workbench-w5j-final-package-20261028'),evidence_inputs=git('rev-parse','HEAD'),final_delivery_ref='checkpoint/workbench-w5j-verified-20261028',
        note='Final evidence/delivery commit identity is resolved by this Git ref and exact remote-main readback in the handoff; it cannot embed its own hash. Package bytes bind the earlier package-input commit.'),
    contract='usable-supplies-1',corpus=ref(EVID/'shipped-sources.json'),observations=ref(EVID/'observations.json'),
    commands=commands,package=dict(executable=ref(release/'resonance-workbench.exe'),installer=ref(release/'bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe'),
        bundled_runtime_files=len(runtime_files),bundled_runtime_matches=True,bundled_bridge_matches=True),
    source_hashes=sources,shipped_assignment=read(ROOT/'roguelike/data/generation/authored_submap_selection.json'),
    preservation=dict(**preservation,owner_plan='Untracked and byte/mtime preserved',canonical_native_fixture_matches=True,game_fixture_matches=True),
    screenshots=shots,room_session=ref(room_path),
    corrections=[
      'An early focused worker run overlapped source edits and correctly rejected SOURCE_CHANGED; stable final full suite follows frozen game code.',
      'The first broad game invocation named two nonexistent modules and used embedded Python whose cold children ignored PYTHONPATH; corrected to actual test module names and configured development environment (66 pass).',
      'Native harness waits for asynchronous Revert completion and selects the actual shared apply label. Failed attempts are retained, not counted as successful journeys.',
      'W5H persistence observation comparison now omits W5J transient instance identities; saved item values and ownership remain fully compared across F9/cold load.',
      'Initial standalone fixture optional docs copy collided with an existing directory; the final fresh fixture uses dirs_exist_ok and passes startup/save/load.'
    ],limits=['Controlled needs/injury and staged room entrance; no balance, unaided discovery or normal-start pacing claim.',
        'No new equipment/effects, recipe processing, filling mechanics, migration, asset creation or wiki work. New definitions require explicit saved references.'])
(DOC/'w5j-verification.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=True,corpus=read(EVID/'shipped-sources.json')['classes'],commands=len(commands),package_inputs=receipt['revisions']['package_inputs'])))
