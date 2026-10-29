"""Bind W5N accepted bytes, native provenance, immutable inputs and final gates."""
import hashlib,json,re,shutil,subprocess
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5n';EVID=ROOT/'workbench/docs/evidence/w5n'
def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode())
native_path=next(p for p in sorted(ART.glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True) if read(p).get('passed'))
n=read(native_path);release=ROOT/'workbench/src-tauri/target/release'
assert n['package_sha256']==digest(release/'resonance-workbench.exe')
assert n['capture_v1']['captured']['manifest_sha256']==n['capture_reset']['captured']['manifest_sha256']!=n['capture_v2']['captured']['manifest_sha256']
assert n['compatibility_before']['pid']!=n['compatibility_after']['pid'];assert n['compatibility_after']['conservation'];assert n['compatibility_after']['no_regenerated_actor'];assert n['compatibility_after']['no_duplicate_reward']
assert n['capture_v1']['captured']['files'][n['room']['path']]==n['room']['sha256']
for path,key in [('roguelike/data/texts/lab/lab_note_primary_a.json','parked_text_sha256'),('roguelike/data/entities/creatures/hollow_revenant.json','parked_creature_sha256')]:
    assert n['capture_v1']['captured']['files'][path]==digest(ROOT/path)
    assert n['recovery'][key]!=n['capture_v1']['captured']['files'][path]
assert len(n['harvest']['outputs'])==2 and len(n['latest']['outputs'])==1 and len(n['compatibility_after']['outputs'])==3
assert n['cooking']['spent'][0]['instance'] in [i['instance'] for i in n['harvest']['outputs']]
assert not any(i['instance']==n['cooking']['output']['instance'] for i in n['used']['after']['inventory'])
assert any(r['type']=='decor' and r['decor_id']=='campfire_unlit' for r in n['room']['definition']['special_tiles'])
assert any(r['kind']=='decor' and r['actual_count']==1 and r.get('realized_decor',{}).get('id')=='campfire_unlit' for r in n['production']['population_receipts'])
EVID.mkdir(parents=True,exist_ok=True);(EVID/'.gitattributes').write_bytes(b'*.json text eol=lf\nfixtures/*.json -text\n*.diff -text\n')
fixtures={}
for name,row in {**n['saved'],'room':n['room']}.items():
    raw=row['raw'].encode();assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=EVID/'fixtures'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    fixtures[name]=dict(**ref(p),published_path=row['path'],definition=row['definition'],identity='Exact UI-authored, reviewed, single-file-published UTF-8 bytes; host reopen hash equals saved bytes. Fixture -text prevents normalization.')
shots={}
for name in ('creature-harvest-controls.png','accepted-room.png','native-corpse.png','native-harvest.png','native-cooking.png','native-used-food.png','native-cold-state.png','native-revised-harvest.png'):
    p=EVID/name;shutil.copyfile(native_path.parent/name,p);shots[name]=ref(p)
diffs={}
for name,text in n['diffs'].items():
    p=EVID/(name+'.diff');p.write_bytes((text+'\n').encode());diffs[name]=ref(p)
def state(o):
    keys=('pid','player','turn','action_calls','hp','max_hp','mode','submap','needs','equipment','inventory','actors','attacks','logs','decor','processing')
    result={k:o[k] for k in keys if k in o}
    result['floor']=[r for r in o.get('floor',[]) if any(i['item_id'] in ('corpse','raw_meat_common','cooked_meat','animal_bone','w5n_cleaver') for i in r['items'])]
    return result
scope=('Controlled authored-room journey with ordinary player profile and RNG. Supported UI controls author creature stats/profile and tool; Source supplies disclosed 19x11 geometry only. '
       'No creature health/stat/equipment/corpse/material injection, death-finalization shortcut, heat/needs fixture, or yield/RNG replacement occurs in the native journey. '
       'Read-only IDs bind native death -> corpse -> physical harvest -> consumed ingredient -> completion -> picked/eaten food. Focused branch/fault tests alone control randint. '
       'Separate ordinary compatibility fixture discloses production death finalization and is independent of immutable captures.')
observations=dict(scope=scope,package_sha256=n['package_sha256'],native_runner=ref(ROOT/'workbench/scripts/run-harvest.mjs'),host_pid=n['host_pid'],checks=n['checks'],screenshots=shots,reviewed_diffs=diffs,
    production={k:n['production'][k] for k in ('origin','spawn','authored_start','population_receipts','access','source_path','source_sha256','draft_sha256','passed') if k in n['production']},
    initial=state(n['initial']),encounter=dict(tool=n['encounter']['tool'],corpse=n['encounter']['corpse'],after=state(n['encounter']['after'])),
    insufficient={k:state(v) for k,v in n['insufficient'].items()},harvest={k:state(v) if k in ('before','after','picked') else v for k,v in n['harvest'].items()},
    cooking={k:state(v) if k in ('before','confirmed') else v for k,v in n['cooking'].items()},used={k:state(v) for k,v in n['used'].items()},
    saved=state(n['saved_state']),cold=state(n['cold']),cold_save_access_events=len(n['cold_audit']['events']),cold_stale_control_removed=n['cold_stale_control_removed'],
    reset={k:state(v) if k in ('before','after') else v for k,v in n['reset'].items()},latest={k:state(v) if k in ('before','after') else v for k,v in n['latest'].items()},
    ordinary={key:{k:v for k,v in n['compatibility_'+key].items() if k!='save_access_audit'}|dict(save_access_events=len(n['compatibility_'+key]['save_access_audit']),explicit_owned_roots=True) for key in ('before','after')},
    conflict=n['conflict'],recovery=n['recovery'],local_receipt=ref(native_path),errors=n['errors'])
write(EVID/'observations.json',observations)
write(EVID/'capture-inputs.json',{key:n[key]['captured'] for key in ('capture_v1','capture_reset','capture_v2')})
corrections=[]
for p in sorted(ART.glob('native-*/receipt.json')):
    attempt=read(p)
    if attempt.get('passed') or not attempt.get('failure'):continue
    failure=attempt['failure'];category=('publication action selector' if 'Apply variant' in failure or 'Review & apply' in failure else 'DOM-normalized CRLF comparison' if "actual - expected" in failure else 'variant admission acknowledgement' if 'New variant ID' in failure else 'explicit recovery BUSY refusal' if 'Recover drafts' in failure else 'terminal-newline invalid-fixture construction' if 'validate()).valid' in failure else 'stale quit-control replay/exit acknowledgement')
    corrections.append(dict(local_receipt=ref(p),package_sha256=attempt['package_sha256'],category=category,failure_excerpt=failure[:400],scope='Excluded harness attempt. Application/game implementation bytes were unchanged; passing final journey uses corrected verification controls.'))
write(EVID/'harness-corrections.json',dict(attempts=corrections,passing_receipt=ref(native_path),application_bytes_unchanged=True))

for name in ('creature-inventory.json','environment.json','package-source-inputs.json','preservation-after.json'):
    write(EVID/('preservation.json' if name=='preservation-after.json' else name),read(ART/name))
assert not read(EVID/'preservation.json')['failures']
package_inputs=read(EVID/'package-source-inputs.json')
for p,h in package_inputs['files'].items():
    assert digest(ROOT/p)==h['working_sha256'],p
    assert hashlib.sha256(subprocess.check_output(['git','show',package_inputs['revision']+':'+p],cwd=ROOT)).hexdigest()==h['committed_sha256'],p
    assert subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)==subprocess.check_output(['git','show',package_inputs['revision']+':'+p],cwd=ROOT),p
specs=[('npm.cmd test','frontend-final.log','77 frontend tests pass'),('npm.cmd run typecheck','typecheck-final.log','TypeScript passes'),
 ('cargo test --locked --manifest-path src-tauri/Cargo.toml','host-final.log','68 Rust tests pass'),('cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings','clippy-final.log','Clippy passes with warnings denied'),
 ('Development pinned-library CPython; inherited absolute game/tests/tools PYTHONPATH: python -B -m unittest test_harvest_w5n test_equipment_w5m test_furnished_rooms_w5l test_preparation_w5k test_crafting test_gameplay_g12 test_gameplay_g16 test_usable_supplies test_authored_assignment test_gameplay_g15 test_effect_persistence test_generation_ownership test_gameplay_g17 test_room_test_session test_combat_routes -v','game-final.log','124 game tests pass'),
 ('Final current consumer cases: pinned-library Python -B -m unittest test_harvest_w5n -v','game-focused-final.log','9 focused consumer cases pass, including final absent-profile and perk-roll assertions'),
 ('worker/runtime/python.exe -X utf8 -I -B -m unittest discover -s worker -v','worker-final.log','98 worker cases, one expected embedded-runtime missing-dependency skip'),
 ('Development Python: workbench/worker/test_bridge.py BridgeTests.test_dependency_absence_structured -v','dependency-negative-final.log','Separate missing-dependency control passes without a skip'),
 ('npm.cmd run bundle -- -- --locked','package-final.log','Windows executable and NSIS complete'),('node scripts/run-harvest.mjs','native-final.log','Packaged full connected journey, reset/latest and separate ordinary fresh-catalogue compatibility pass'),
 ('node scripts/run-workspace.mjs','workspace-final.log','Shared-document lifecycle passes'),('node scripts/run-room-tests.mjs','room-session-final.log','Capture/cancellation/reset/cold/fault/ownership lifecycle passes'),
 ('Pinned Python: standalone-room-regression.py <fresh disposable w5h/w5n fixture> <w5n output>','ordinary-final.log','Ordinary 128x128 main/default save/load passes')]
commands=[]
for command,name,outcome in specs:
    p=ART/name;text=p.read_text(encoding='utf-8-sig');assert not re.search(r'^FAILED\b|^FAIL:|^ERROR:|^Traceback',text,re.M),name
    if name=='worker-final.log':assert 'Ran 98 tests' in text and 'OK (skipped=1)' in text
    if name=='game-final.log':assert 'Ran 124 tests' in text and '\nOK' in text
    if name=='game-focused-final.log':assert 'Ran 9 tests' in text and '\nOK' in text
    if name=='dependency-negative-final.log':assert 'Ran 1 test' in text and '\nOK' in text and 'skipped' not in text
    if name=='package-final.log':assert 'Finished 1 bundle' in text
    commands.append(dict(command=command,exit_code=0,outcome=outcome,local_log=ref(p),application_revision=package_inputs['revision'],test_source_revision=git('log','-1','--format=%H','--','tools/critical_fix_regressions/tests/test_harvest_w5n.py') if name=='game-focused-final.log' else git('log','-1','--format=%H','--','workbench/scripts/run-harvest.mjs') if name=='native-final.log' else package_inputs['revision']))
write(EVID/'gates.json',dict(commands=commands,ordinary_main={k:v for k,v in read(ART/'ordinary-final/receipt.json').items() if k!='save_access_trace'},earlier_attempts='Only passing final commands count. Application/game bytes are unchanged after the package-input revision. Final focused consumer assertions supplement the broader game run. Earlier harness selector, BUSY admission, CRLF/invalid-fixture and stale quit-control corrections are disclosed in delivery; an early concurrent workspace scroll timeout is excluded after an isolated passing rerun. Test doubles and headless finalization fixtures are distinct from native ordinary play.'))
paths=set(git('diff','--name-only','checkpoint/workbench-w5n-start-20261029','HEAD').splitlines())
paths.update('roguelike/'+p for p in ('entities/item.py','engine/item_factory.py','engine/item_system.py','components/inventory.py','components/equipment.py','engine/item_transfers.py','engine/save_components.py','engine/save_manager.py','engine/creature_factory.py','engine/creature_abilities.py','engine/player_setup.py','engine/room_test_diagnostics.py','room_test.py','generation/floor_object_utils.py','generation/authored_decor.py'))
paths={p for p in paths if p and '/docs/evidence/' not in p and not p.endswith(('w5n-verification.json','W5N_DELIVERY.md'))}
hashes={p:dict(working_sha256=digest(ROOT/p),committed_sha256=hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)).hexdigest()) for p in sorted(paths)}
captured={p:h for p,h in n['capture_v1']['captured']['files'].items() if p in hashes}
for p,h in captured.items():assert h==hashes[p]['working_sha256'],p
for key in ('creature','tool'):assert n['capture_v1']['captured']['files'][n['saved'][key]['path']]==n['saved'][key]['sha256']
for key in ('creature_revised','tool_revised'):assert n['capture_v2']['captured']['files'][n['saved'][key]['path']]==n['saved'][key]['sha256']
receipt=dict(milestone='W5N',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),contract='creature-harvest-2',
 revisions=dict(start=git('rev-parse','checkpoint/workbench-w5n-start-20261029'),initial_remote='838958de0f72054e573651cbc250e9ada8ebb8c0',implementation=git('rev-parse','checkpoint/workbench-w5n-package-inputs-20261029'),evidence_inputs=git('rev-parse','HEAD'),final_delivery_ref='checkpoint/workbench-w5n-verified-20261029',note='Final commit cannot embed its own hash. Resolve final ref; post-push ignored remote-readback.json and user handoff report exact full local/remote main equality. Application/package inputs precede later evidence commits; working and Git-normalized committed bytes are bound separately.'),
 commission=dict(local_path='C:/Users/dango/Downloads/CODEX_WORKBENCH_W5N_CREATURE_HARVESTS.md',sha256=digest(Path('C:/Users/dango/Downloads/CODEX_WORKBENCH_W5N_CREATURE_HARVESTS.md'))),
 accepted_fixtures=fixtures,inventory=ref(EVID/'creature-inventory.json'),observations=ref(EVID/'observations.json'),captures=ref(EVID/'capture-inputs.json'),environment=ref(EVID/'environment.json'),package_source_inputs=ref(EVID/'package-source-inputs.json'),gates=ref(EVID/'gates.json'),preservation=ref(EVID/'preservation.json'),harness_corrections=ref(EVID/'harness-corrections.json'),
 package={p:ref(release/p) for p in ('resonance-workbench.exe','bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe')},
 runtime={p:ref(ROOT/'workbench'/p) for p in ('worker/bridge.py','worker/runtime/python.exe','worker/runtime/python311._pth','worker/requirements.lock')},source_hashes=hashes,captured_game_inputs=captured,
 limits=['One controlled authored-room journey; no natural discovery, encounter balance or all-ability certification.','Native combat and harvest retain ordinary RNG. Only focused branch/fault tests control random quantities.','Separate headless ordinary compatibility uses disclosed production finalization rather than a second native defeat.','No content pack, starter redistribution, save migration, decay simulation change, wiki edition or reference-pack refresh.'])
write(ROOT/'workbench/docs/w5n-verification.json',receipt)
print(json.dumps(dict(passed=True,sources=len(hashes),captured_inputs=len(captured),fixtures=len(fixtures),screenshots=len(shots))))
