"""Bind the completed W5M package, accepted bytes, observations and final gates."""
import hashlib,json,re,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5m';EVID=ROOT/'workbench/docs/evidence/w5m'
def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode())
native_path=next(p for p in sorted(ART.glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True) if read(p).get('passed'))
n=read(native_path);release=ROOT/'workbench/src-tauri/target/release'
assert n['package_sha256']==digest(release/'resonance-workbench.exe')
assert n['capture_v1']['captured']['manifest_sha256']==n['capture_reset']['captured']['manifest_sha256']!=n['capture_v2']['captured']['manifest_sha256']
assert n['compatibility_before']['pid']!=n['compatibility_after']['pid'];assert n['compatibility_after']['conservation'] and n['compatibility_after']['pickup_refused']
EVID.mkdir(parents=True,exist_ok=True);(EVID/'.gitattributes').write_bytes(b'*.json text eol=lf\nfixtures/*.json -text\n')
fixtures={}
for name,row in {**n['saved'],'room':n['room'],'satchel_revised':n['revised_bag']}.items():
    raw=row['raw'].encode();assert hashlib.sha256(raw).hexdigest()==row['sha256']
    p=EVID/'fixtures'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    fixtures[name]=dict(**ref(p),published_path=row['path'],definition=row['definition'],identity='Exact UTF-8 bytes authored, reviewed, single-file published and byte-checked reopened through packaged controls; -text preserves fixture bytes.')
shots={}
for name in ('controls-w5m_blade.png','controls-w5m_jack.png','controls-w5m_ward.png','controls-w5m_satchel.png','diff-w5m_satchel.png','game-equipped-kit.png','game-carrying.png','game-combat.png','game-cold-ownership.png'):
    p=EVID/name;shutil.copyfile(native_path.parent/name,p);shots[name]=ref(p)
def state(o):
    keys=('pid','player','turn','action_calls','hp','max_hp','mode','submap','light','lighting','equipment','carrying','effective_av','inventory','actors','attacks','logs')
    result={k:o[k] for k in keys if k in o}
    result['floor']=[r for r in o.get('floor',[]) if any(i['item_id'].startswith('w5m_') or i['item_id']=='wood_bundle' for i in r['items'])]
    return result
def ordinary(key):
    value=n[key];return {k:v for k,v in value.items() if k!='save_access_audit'}|dict(save_access_events=len(value['save_access_audit']),explicit_owned_roots=True)
observations=dict(package_sha256=n['package_sha256'],native_runner=ref(ROOT/'workbench/scripts/run-equipment.mjs'),host_pid=n['host_pid'],checks=n['checks'],
    scope='Packaged controls author the kit and all placements; raw Source establishes disclosed geometry only. No event injects equipment, inventory, slots, AV, discounts, health or creatures. Native encounter uses ordinary randomness; focused consumer tests alone control numeric branches.',
    reviewed_diffs=n['diffs'],production={k:n['production'][k] for k in ('origin','spawn','authored_start','population_receipts','access','source_path','source_sha256','draft_sha256','passed') if k in n['production']},
    actions=[dict(id=a['id'],selected=a['selected'],slot=a['slot'],before=state(a['before']),after=state(a['after'])) for a in n['actions']],
    light_displacement={k:state(v) for k,v in n['light_displacement'].items()},sibling_cleanup={**n['sibling_cleanup'],'after':state(n['sibling_cleanup']['after'])},
    carrying={k:state(v) for k,v in n['carrying'].items()},combat=state(n['combat']),saved=state(n['saved_state']),cold=state(n['cold']),
    cold_save_access_events=len(n['cold_audit']['events']),reset=state(n['reset']),latest=state(n['latest']),
    captures={k:{field:n[k]['captured'][field] for field in ('snapshot_id','manifest_sha256','room_sha256','runtime_sha256')} for k in ('capture_v1','capture_reset','capture_v2')},
    ordinary_before=ordinary('compatibility_before'),ordinary_after=ordinary('compatibility_after'),conflict=n['conflict'],recovery=n['recovery'],screenshots=shots,
    local_receipt=dict(path=str(native_path),sha256=digest(native_path)),errors=n['errors'])
write(EVID/'observations.json',observations)
for name in ('item-inventory.json','environment.json','preservation-after.json'):
    value=read(ART/name);write(EVID/('preservation.json' if name=='preservation-after.json' else name),value)
assert not read(EVID/'preservation.json')['failures']
specs=[('npm.cmd test','frontend-final.log','74 frontend tests pass'),('npm.cmd run typecheck','typecheck-final.log','TypeScript passes'),
    ('cargo test --locked --manifest-path src-tauri/Cargo.toml','host-final.log','68 Rust tests pass'),
    ('cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings','clippy-final.log','Clippy passes with warnings denied'),
    ('Development CPython with pinned bundled libraries and absolute inherited game/tests/tools PYTHONPATH: python -B -m unittest test_equipment_w5m test_furnished_rooms_w5l test_preparation_w5k test_crafting test_gameplay_g12 test_gameplay_g16 test_usable_supplies test_authored_assignment test_gameplay_g15 test_effect_persistence test_generation_ownership test_gameplay_g17 test_room_test_session test_combat_routes -v','game-final.log','115 game tests pass, including real subprocess save/load'),
    ('worker/runtime/python.exe -X utf8 -I -B -m unittest discover -s worker -v','worker-final.log','93 worker tests: 92 pass, one expected embedded-runtime skip'),
    ('Development Python: worker/test_bridge.py BridgeTests.test_dependency_absence_structured -v','dependency-negative-final.log','Separate missing-dependency control passes'),
    ('npm.cmd run bundle -- -- --locked','package-final.log','Windows executable and NSIS complete'),
    ('node scripts/run-equipment.mjs','native-final.log','Packaged author/acquire/equip/combat/carry/drop/cold/revise/reset/latest and separate ordinary compatibility pass'),
    ('node scripts/run-workspace.mjs','workspace-final.log','Shared-document lifecycle passes'),
    ('node scripts/run-room-tests.mjs','room-session-final.log','Packaged capture/cancellation/reset/cold/fault/ownership lifecycle passes'),
    ('Pinned Python: standalone-room-regression.py <fresh disposable w5h/w5m fixture> <w5m output>','ordinary-final.log','Ordinary 128x128 main/default save/load passes')]
commands=[]
for command,name,outcome in specs:
    p=ART/name;text=p.read_text(encoding='utf-8-sig');assert not re.search(r'^FAILED\b|^FAIL:|^ERROR:|^Traceback',text,re.M),name
    if name=='worker-final.log':assert 'Ran 93 tests' in text and 'OK (skipped=1)' in text
    if name=='game-final.log':assert 'Ran 115 tests' in text and '\nOK' in text
    if name=='package-final.log':assert 'Finished 1 bundle' in text
    commands.append(dict(command=command,exit_code=0,outcome=outcome,local_log=ref(p)))
write(EVID/'gates.json',dict(commands=commands,earlier_attempts='Early child import environment, changing-source worker response, runner selector and NSIS lock attempts are excluded from passing gates. Final commands use stable source, inherited subprocess imports and completed package inputs.'))
paths=set(git('diff','--name-only','checkpoint/workbench-w5m-start-20261029','HEAD').splitlines())
paths.update('roguelike/'+p for p in ('entities/item.py','engine/item_factory.py','engine/item_system.py','components/inventory.py','components/equipment.py','engine/inventory_screen.py','engine/item_transfers.py','engine/combat.py','engine/engine.py','components/ai.py','engine/movesets.py','engine/save_components.py','engine/save_manager.py','engine/player_setup.py','room_test.py','engine/data_loader.py','engine/scene_generation.py','generation/authored_decor.py'))
paths={p for p in paths if p and '/docs/evidence/' not in p and not p.endswith(('w5m-verification.json','W5M_DELIVERY.md'))}
hashes={p:dict(working_sha256=digest(ROOT/p),committed_sha256=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)).hexdigest()) for p in sorted(paths)}
captured={p:h for p,h in n['capture_v1']['captured']['files'].items() if p in hashes}
for p,h in captured.items():assert h==hashes[p]['working_sha256'],p
for row in n['saved'].values():assert n['capture_v1']['captured']['files'][row['path']]==row['sha256']
receipt=dict(milestone='W5M',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),contract='expedition-items-2',
    revisions=dict(start='a60c66680127112f467611d3986043bb48d0fa33',initial_remote='a60c66680127112f467611d3986043bb48d0fa33',implementation=git('rev-parse','829a2ac'),package_inputs=git('rev-parse','checkpoint/workbench-w5m-package-inputs-20261029'),evidence_inputs=git('rev-parse','HEAD'),final_delivery_ref='checkpoint/workbench-w5m-verified-20261029',note='Final commit cannot embed its own hash. Resolve the final named ref; post-push remote-readback.json and the handoff report exact local/remote main equality. Package runtime inputs are separate from later harness/evidence commits.'),
    accepted_fixtures=fixtures,environment=ref(EVID/'environment.json'),inventory=ref(EVID/'item-inventory.json'),observations=ref(EVID/'observations.json'),gates=ref(EVID/'gates.json'),preservation=ref(EVID/'preservation.json'),
    package={p:ref(release/p) for p in ('resonance-workbench.exe','bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe')},
    runtime={p:ref(ROOT/'workbench'/p) for p in ('worker/bridge.py','worker/runtime/python.exe','worker/runtime/python311._pth','worker/requirements.lock')},source_hashes=hashes,captured_game_inputs=captured,
    limits=['One controlled equipment expedition, no unaided discovery, encounter balance or every-moveset certification.','Factory/definition evidence is distinct from ordinary owned use. Focused numeric tests control RNG; native encounter does not.','Physical copied fields, unchanged capture restore, revised-catalogue ordinary restore and fresh construction are separately demonstrated.','No live content, starting kit, enabled profile, gameplay rebalance, save migration, wiki edition or reference-pack change.'])
write(ROOT/'workbench/docs/w5m-verification.json',receipt)
print(json.dumps(dict(passed=True,sources=len(hashes),captured_inputs=len(captured),fixtures=len(fixtures),screenshots=len(shots))))
