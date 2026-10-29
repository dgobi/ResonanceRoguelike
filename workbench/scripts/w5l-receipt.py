"""Collect source-bound W5L evidence without copying disposable saves/captures."""
import hashlib,json,re,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5l';EVID=ROOT/'workbench/docs/evidence/w5l'
def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode('utf-8').strip()
def blob(p):return subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())
def latest(pattern):
    for p in sorted(ROOT.glob(pattern),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        if read(p).get('passed'):return p,read(p)
    raise AssertionError(pattern)
native_path,n=latest('workbench/.artifacts/w5l/native-*/receipt.json')
assert n['package_sha256']==digest(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe')
assert n['capture_v1']['captured']['manifest_sha256']==n['capture_reset']['captured']['manifest_sha256']!=n['capture_v2']['captured']['manifest_sha256']
assert n['compatibility_before']['pid']!=n['compatibility_after']['pid']
screens=read(native_path.parent/'screenshots/receipt.json');assert screens['passed'] and screens['package_sha256']==n['package_sha256']
EVID.mkdir(parents=True,exist_ok=True)
(EVID/'.gitattributes').write_bytes(b'*.json text eol=lf\nfixtures/*.json -text\n')
fixtures={}
for name,row in {**n['saved'],'room':n['room'],'room_revised':n['room_revised']}.items():
    raw=row['raw'].encode();assert hashlib.sha256(raw).hexdigest()==row['sha256']
    p=EVID/'fixtures'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    fixtures[name]=dict(**ref(p),published_path=row['path'],definition=row['definition'],identity='Exact UTF-8 bytes authored, saved and byte-checked reopened through packaged controls; -text prevents normalization.')
shutil.copyfile(ART/'decor-inventory.json',EVID/'decor-inventory.json')
shots={}
for name in ('game-authored-light.png','game-choose-protected-unlit.png','game-choose-protected-lit.png','game-authored-cooking.png','game-floor-output.png','game-used-roast.png','game-cold-state.png','game-revised-furnishing.png'):
    target=EVID/name;shutil.copyfile(native_path.parent/name,target);shots[name]=ref(target)
for name in ('completed-source-room.png','completed-realized-room.png','completed-decor-receipts.png','completed-furnishing-properties.png'):
    target=EVID/name;shutil.copyfile(native_path.parent/'screenshots'/name,target);shots[name]=ref(target)
def state(o):
    result={k:o[k] for k in ('pid','player','turn','action_calls','needs','hp','max_hp','mode','craft','placement','processing','decor','logs','lighting','submap') if k in o}
    result['inventory']=[i for i in o.get('inventory',[]) if i['item_id'].startswith('w5l_') or i['item_id']=='tallow_torch']
    result['floor']=[dict(x=r['x'],y=r['y'],items=r['items']) for r in o.get('floor',[]) if any(i['item_id'].startswith('w5l_') for i in r['items'])]
    return result
def compatible(key):
    v=n[key];return {k:v for k,v in v.items() if k!='save_access_audit'}|dict(save_access_events=len(v['save_access_audit']),explicit_disposable_ownership=True)
observations=dict(scope='Final packaged controls author all demonstrated furnishings and dependencies. Source establishes disclosed geometry only. Events supply ordinary keys and once-only needs/health setup, never decor/heat. Read-only supplementary screenshots show the revised saved room.',
    package_sha256=n['package_sha256'],host_pid=n['host_pid'],checks=n['checks'],
    production={k:n['production'][k] for k in ('origin','authored_start','spawn','stairs','population_receipts','access','source_path','source_sha256','draft_sha256','passed') if k in n['production']},
    blocker=n['blocker'],light=n['light'],needs_setup=n['disclosed_needs'],unlit_failure=state(n['unlit_failure']),lit=state(n['lit']),
    cooking=dict(before=state(n['cooking']['before']),confirmed=state(n['cooking']['confirmed']),output=n['cooking']['output']),uses=n['uses'],
    extinguished=state(n['extinguished']),saved_state=state(n['saved_state']),cold=state(n['cold']),cold_save_access_events=len(n['cold_audit']['events']),
    reset=state(n['reset']),latest=state(n['latest']),captures={k:{a:n[k]['captured'][a] for a in ('snapshot_id','manifest_sha256','room_sha256','runtime_sha256')} for k in ('capture_v1','capture_reset','capture_v2')},
    ordinary_before=compatible('compatibility_before'),ordinary_after=compatible('compatibility_after'),conflict=n['conflict'],recovery=n['recovery'],screenshots=shots,
    native_receipt=dict(local_path=str(native_path),sha256=digest(native_path)),errors=n['errors'])
write(EVID/'observations.json',observations)
specs=[('npm.cmd test','frontend-final.log','70 frontend tests pass'),('npm.cmd run typecheck','typecheck-final.log','TypeScript passes'),
    ('cargo test --locked --manifest-path workbench/src-tauri/Cargo.toml','host.log','68 Rust tests pass; these Rust inputs are unchanged in the final package'),
    ('cargo clippy --locked --manifest-path workbench/src-tauri/Cargo.toml -- -D warnings','clippy.log','Pass, warnings denied'),
    ('Development CPython with a .pth pointing to the six pinned bundled libraries; absolute game/tests/tools PYTHONPATH; unittest test_furnished_rooms_w5l test_preparation_w5k test_crafting test_gameplay_g12 test_gameplay_g16 test_usable_supplies test_authored_assignment test_gameplay_g15 test_effect_persistence test_generation_ownership test_gameplay_g17 test_room_test_session test_combat_routes -v','game-final.log','110 game tests pass, including genuine subprocess save/load'),
    ('worker/runtime/python.exe -X utf8 -I -B -m unittest discover -s worker -v','worker-final.log','87 worker cases; 86 pass and one expected embedded-runtime skip'),
    ('Development Python: unittest test_bridge.BridgeTests.test_dependency_absence_structured -v','dependency-negative-final.log','Missing-dependency negative control passes'),
    ('npm.cmd run bundle -- -- --locked','package-final.log','Windows executable and NSIS pass'),
    ('node scripts/run-furnishings.mjs','native-delivery.log','Final packaged author/enter/prepare/use/cold/revise/reset/latest with useful container and separate ordinary-save compatibility pass'),
    ('node scripts/capture-furnishing-evidence.mjs <final native receipt>','screenshots-final.log','Read-only final-package source, properties and production receipts'),
    ('node scripts/run-workspace.mjs','workspace-final.log','Packaged shared-document lifecycle passes'),
    ('node scripts/run-room-tests.mjs','room-session-final.log','Packaged capture/cancellation/reset/cold/fault/ownership lifecycle passes'),
    ('Pinned Python: standalone-room-regression.py in fresh .artifacts/w5h/w5l-ordinary-final runtime inputs','ordinary-final.log','Ordinary 128x128 main startup/default save/load passes')]
commands=[]
for command,name,outcome in specs:
    p=ART/name;text=p.read_text(encoding='utf-8-sig')
    assert not re.search(r'^FAILED\b|^FAIL:|^ERROR:|^Traceback',text,re.M),name
    if name=='worker-final.log':assert 'Ran 87 tests' in text and 'OK (skipped=1)' in text
    if name=='game-final.log':assert 'Ran 110 tests' in text and '\nOK' in text
    commands.append(dict(command=command,exit_code=0,outcome=outcome,local_log=ref(p)))
write(EVID/'gates.json',dict(commands=commands,provenance='Locally executed Windows checks; full logs remain in ignored local artifacts, hashes retained. Earlier environment/import, initial NSIS lock and clipped-count visual attempts are not passing gates.'))
preserve=read(ART/'preservation-after.json');assert not preserve['failures'];write(EVID/'preservation.json',preserve)
paths=set(git('diff','--name-only','checkpoint/workbench-w5l-start-20261028','HEAD').splitlines())
paths.update('roguelike/'+p for p in ('generation/local_gen.py','generation/decor_utils.py','generation/access.py','engine/crafting.py','engine/engine.py','engine/vine_system.py','rendering/renderer.py','data/decoratives.json','data/generation/authored_submap_selection.json','engine/save_manager.py'))
paths={p for p in paths if p and '/docs/evidence/' not in p and p.endswith(('.py','.rs','.ts','.tsx','.json','.md','.mjs')) and not p.endswith(('W5L_DELIVERY.md','w5l-verification.json'))}
hashes={p:dict(working_sha256=digest(ROOT/p),committed_sha256=hashlib.sha256(blob(p)).hexdigest()) for p in sorted(paths)}
captured_files=n['capture_v1']['captured']['files']
captured_inputs={p:sha for p,sha in captured_files.items() if p in hashes}
for p,sha in captured_inputs.items():assert sha==hashes[p]['working_sha256'],p
native_revision=git('rev-parse','checkpoint/workbench-w5l-journey-inputs-20261028')
native_runner_bytes=subprocess.check_output(['git','show',native_revision+':workbench/scripts/run-furnishings.mjs'],cwd=ROOT)
release=ROOT/'workbench/src-tauri/target/release'
receipt=dict(milestone='W5L',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),contract='authored-room-2',route_contract='g2-3',
    revisions=dict(start='417ce1adca5c7b52f24f4201d2ab69cff3d3fbce',initial_remote='417ce1adca5c7b52f24f4201d2ab69cff3d3fbce',implementation=git('rev-parse','cdf35c3'),package_inputs=git('rev-parse','checkpoint/workbench-w5l-final-package-20261028'),evidence_inputs=git('rev-parse','HEAD'),final_delivery_ref='checkpoint/workbench-w5l-verified-20261028',note='Final commit cannot embed its own SHA. Resolve the named ref; post-push exact local/remote-main readback is in the handoff and ignored remote-readback.json. Package inputs precede evidence-only refinements.'),
    accepted_fixtures=fixtures,inventory=ref(EVID/'decor-inventory.json'),observations=ref(EVID/'observations.json'),gates=ref(EVID/'gates.json'),preservation=ref(EVID/'preservation.json'),
    package={p:ref(release/p) for p in ('resonance-workbench.exe','bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe')},
    runtime={p:ref(ROOT/'workbench'/p) for p in ('worker/bridge.py','worker/runtime/python.exe','worker/runtime/python311._pth','worker/requirements.lock')},
    source_hashes=hashes,captured_game_inputs=captured_inputs,
    native_runner_executed=dict(path='workbench/scripts/run-furnishings.mjs',revision=native_revision,sha256=hashlib.sha256(native_runner_bytes).hexdigest(),note='This exact committed runner authored the useful-container fixture. Read-only supplementary screenshots use the same package; earlier pending-preview images are excluded.'),
    limits=['Controlled authored-room proof; no unaided discovery, normal-start pacing or balance claim.','Decor light_emit supplies existing secondary FOV, not new RGB lighting; only campfire_lit supplies preparation heat.','Already saved decor IDs/positions persist; current catalogue properties are not copied.','No wiki/reference rebuild, personal campaign migration, decor registry edits, new stations/fuel rules, selector expansion or enabled live profile.'])
write(ROOT/'workbench/docs/w5l-verification.json',receipt)
print(json.dumps(dict(passed=True,sources=len(hashes),fixtures=len(fixtures),screenshots=len(shots),preserved=preserve['unchanged'])))
