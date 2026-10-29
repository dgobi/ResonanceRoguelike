"""Retain compact W5P source-bound evidence; bulky outputs stay ignored."""
import hashlib,json,re,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ART=ROOT/'workbench/.artifacts/w5p'
EVID=ROOT/'workbench/docs/evidence/w5p'
START='checkpoint/workbench-w5p-start-20261029'
IMPL='750c4db2f7ac3a8d0355026a7dbdb3160c1bc699'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
def blob(revision,p):return hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()
def compact(report):
    keys=('passed','rotation','mirror','origin','scene_seed','scene_address','candidate_sha256','terrain_sha256','source_path','source_sha256','draft_sha256','orientation_entry','access_verified','access','record_access','population_receipts','source','context','rendering')
    return {k:report[k] for k in keys if k in report}

passing=[p for p in sorted(ART.glob('native-*/receipt.json')) if read(p).get('passed')]
assert passing,'No passing native journey'
native=passing[-1];n=read(native);assert n['runner_sha256']==digest(ROOT/'workbench/scripts/run-buildings.mjs')
assert n['package_sha256']==digest(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe')
assert n['crop_refusal'] and n['stale_return'] and n['dependency_revoked'] and n['conflict']['preserved'] and not n['errors']
assert len(n['recovery'])==3 and len(n['processes'])==2
assert n['production_v2']['draft_sha256']==n['fixtures']['building_v2']['sha256']
replays=read(native.parent/'accepted-byte-replays.json')
EVID.mkdir(parents=True,exist_ok=True)
(EVID/'.gitattributes').write_bytes(b'*.json text eol=lf\nfixtures/*.json -text whitespace=cr-at-eol\n')
fixtures={}
for key,row in n['fixtures'].items():
    p=EVID/'fixtures'/(key+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(row['raw'].encode('utf-8'))
    assert digest(p)==row['sha256']==replays[key]['draft_sha256']
    report=replays[key]['preview'];assert replays[key]['valid'] and len(report['orientations'])==8
    assert all(r['passed'] and all(a['passed'] for a in r['access']) and all(a['receipt_owned'] for a in r['record_access']) for r in report['orientations'])
    fixtures[key]=dict(**ref(p),published_path=row['path'],note='Exact UI-authored reviewed/published bytes, verified by host reopen. -text preserves literal UTF-8/CRLF bytes.')
write(EVID/'orientation-access.json',dict(scope='Independent fresh worker revalidation of both exact accepted byte versions against unchanged saved dependencies, through the same registered adapter/all eight production orientations. Version one is replayed as a candidate over the reopened version-two original; no live fixture file is replaced.',
    local_full_receipt=ref(native.parent/'accepted-byte-replays.json'),versions={k:dict(draft_sha256=v['draft_sha256'],source_asset=v['source_asset'],original_source_sha256=v['source_sha256'],orientations=[compact(r) for r in v['preview']['orientations']]) for k,v in replays.items()},
    native_pre_navigation_preview=dict(draft_sha256=n['production_v1']['draft_sha256'],note='Native screenshot/revealed preview precedes the description revision before first publication. It is not mislabeled as the later accepted v1 exact bytes.'),
    native_revised_preview=dict(draft_sha256=n['production_v2']['draft_sha256'],orientations=[compact(r) for r in n['production_v2']['orientations']])))
screens={}
for name in ('recovered-drafts.png','authored-building.png','oriented-production.png','revised-saved-production.png'):
    p=EVID/name;shutil.copyfile(native.parent/name,p);screens[name]=ref(p)
plan=n['planned'];assert plan['passed'] and plan['source_sha256']==n['fixtures']['building_v2']['sha256'] and len(plan['selected'])==3 and len(plan['candidate_receipts'])==21
write(EVID/'planned-placement.json',{k:v for k,v in plan.items() if k!='scenes'}|dict(materialized_scene_count=len(plan['scenes']),scene_chunks=[s['chunk'] for s in plan['scenes']],local_full_receipt=ref(native.parent/'planned.json')))
write(EVID/'native-observations.json',dict(scope='Packaged native WebView events only, in positively owned disposable data/settings/recovery. Saved item/text/pool definitions were reused; the example is not installed canonically. No surface play session or acquisition/use expedition is claimed.',
    package_sha256=n['package_sha256'],runner_sha256=n['runner_sha256'],local_full_receipt=ref(native),checks=n['checks'],processes=n['processes'],screenshots=screens,
    recovered={p:dict(draft=row['record']['draft'],variant=row['record']['variant'],variant_id=row['record']['variant_id'],target=row['record']['target'],generation=row['record']['generation'],sha256=hashlib.sha256(row['record']['draft'].encode()).hexdigest()) for p,row in n['recovery'].items()},
    crop_refusal=n['crop_refusal'],grown_edge_failure=[d for d in n['grown_edge_failure'] if d['severity']=='error'],blocked_cell=n['blocked'],stale_return=n['stale_return'],dependency_revoked=n['dependency_revoked'],external_conflict=n['conflict'],byte_checked_fixtures=fixtures,errors=n['errors']))
inventory=ART/'building-inventory.json';assert read(inventory)['ordinary']==58
write(EVID/inventory.name,read(inventory))
package=read(ART/'package-source-inputs.json');assert package['revision']==IMPL
for p,h in package['files'].items():assert digest(ROOT/p)==h['working_sha256'] and blob(IMPL,p)==h['committed_sha256'],p
write(EVID/'package-source-inputs.json',package)
write(EVID/'environment.json',read(ART/'environment.json'))
changed=set(git('diff','--name-only',START,'HEAD').splitlines())|set(git('diff','--name-only').splitlines())|set(git('diff','--cached','--name-only').splitlines())
before=read(ART/'preservation-before.json')
failures=[p for p,h in before.items() if p not in changed and (not (ROOT/p).is_file() or digest(ROOT/p)!=h)]
assert not failures
write(EVID/'preservation.json',dict(preexisting_files=len(before),unchanged=len(before)-len(set(before)&changed),scoped_changes=sorted(changed),failures=failures,owner_plan_sha256=digest(ROOT/'RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md'),scope='Tracked pre-existing files plus the untracked owner plan; no campaign/save enumeration. This is not independent proof that every personal path was unread/untouched.'))
attempts=[]
for p in sorted(ART.glob('native-*/receipt.json')):
    r=read(p)
    if not r.get('passed'):attempts.append(dict(local_receipt=ref(p),failure=r.get('failure','interrupted'),counted_as_pass=False))
write(EVID/'attempts.json',dict(native=attempts,excluded=[
    'First worker full run: one expected dependency-control skip, one SOURCE_CHANGED during ongoing source edits, and one legacy building variant fixture without original source identity. The latter is adapted; the stable full run is authoritative.',
    'Early visual/authoring cases reflected legacy source-free variants and no production validation. Updated to enforce registered original authority, preserve BOM according to the structure loader, and retain invalid-value repair without promoting malformed originals.',
    'First Rust run exposed mock variant drafts that retained the original ID. Fixtures now use a registered building and real variant identity; final 70 tests pass without a legacy slot.',
    'Native recovery retries only explicit BUSY refusals. Early harness clicks outside an enlarged camera were corrected by using Fit layout; an obsolete runner launched after a wrong-cwd edit failure was stopped in its owned process tree.',
    'A harness assumed text IDs matched filenames; it now records the actual readable source path. The journey then exposed a real dropped origin location in the frontend wrapper; passthrough is corrected and return after selecting a different record plus stale return both pass.',
    'A package attempt overlapped an app process and failed NSIS with sharing error 32. The authoritative package completed before the passing native journey; executable hashes match.',
    'The first 334-test game run passed tests but crossed source edits and has source_stable=false; it is excluded. The final stable rerun is required.',
    'The shared-workspace journey is adapted from six plus a singleton to seven keyed owners. A confirmation lost during a freshness transition is retried with a new validation; no failed run is counted as passing.',
    'A focused weighted-coordinate assertion expected the code in the message; the actual compiler correctly returned CHOICE_COORDINATE in its code field. The assertion now checks that field.']))
source_paths=set(git('diff','--name-only',START,IMPL).splitlines())
source_paths-={'workbench/scripts/workspace-journey.mjs'}
sources={p:dict(working_sha256=digest(ROOT/p),committed_sha256=blob(IMPL,p)) for p in sorted(source_paths)}
game_paths=[p for p in source_paths if p.startswith('roguelike/') and p.endswith('.py')]
game_paths+=['roguelike/engine/scene_generation.py','roguelike/engine/item_factory.py','roguelike/engine/definition_sources.py','roguelike/generation/structure_contract.py','roguelike/generation/placement.py','roguelike/generation/plan_preview.py','roguelike/generation/planned_scene.py']
captured={}
for p in sorted(set(game_paths)):
    fixture_path=Path(n['root'])/p;assert digest(fixture_path)==digest(ROOT/p),p
    captured[p]=dict(working_sha256=digest(fixture_path),committed_sha256=blob(IMPL,p))
write(EVID/'captured-game-inputs.json',captured)
if '--collect' in sys.argv:
    print(json.dumps(dict(collected=True,fixtures=len(fixtures),orientations_per_version=8,selected=3)));raise SystemExit(0)
specs=[('npm test','frontend-verified.log','85 frontend tests'),('npm run typecheck','typecheck.log','TypeScript'),
    ('cargo test --locked --manifest-path src-tauri/Cargo.toml','host-verified.log','70 Rust tests'),('cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings','clippy-verified.log','Warnings denied'),
    ('Pinned CPython 3.11: unittest discover -s worker -v','worker-verified.log','108 worker tests; one expected missing-dependency control skip'),
    ('Development interpreter: BridgeTests.test_dependency_absence_structured','dependency-negative.log','Separate missing-dependency negative control'),
    ('Pinned verification venv: verify_fixes.py --evidence workbench/.artifacts/w5p/game-verified --timeout 1800','game-verified.log','334 broad game tests, stable source'),
    ('npm run bundle -- -- --locked','package-verified.log','Windows release executable and NSIS'),
    ('node scripts/run-buildings.mjs','native-attempt-6.log','Complete packaged surface-building journey and controlled planned placement'),
    ('node scripts/run-workspace.mjs','workspace-verified.log','Seven owners, stale/cancel/reopen/rollback lifecycle'),
    ('node scripts/run-room-tests.mjs','room-session.log','Retained room capture/cancellation/reset/latest/cold/fault lifecycle'),
    ('Pinned runtime: standalone-room-regression.py <fresh owned fixture> <owned output>','ordinary-main.log','Ordinary 128x128 startup and default-slot save/load; optional sprite fallback warnings, no sprite-render fidelity claim')]
commands=[]
for command,name,outcome in specs:
    p=ART/name;s=p.read_text(encoding='utf-8-sig');assert not re.search(r'^FAILED\b|^FAIL:|^ERROR:|^Traceback',s,re.M),name
    if name=='worker-verified.log':assert 'OK (skipped=1)' in s
    if name=='game-verified.log':assert '\nOK' in s
    if name=='package-verified.log':assert 'Finished 1 bundle' in s
    if name in ('workspace-verified.log','room-session.log'):assert '"passed": true' in s or '"passed":true' in s,name
    commands.append(dict(command=command,exit_code=0,outcome=outcome,log=ref(p)))
game=read(ART/'game-verified/run.json');assert game['passed'] and game['source_stable'] and all(digest(ROOT/p)==h for p,h in game['source'].items())
ordinary=read(ART/'ordinary-main/receipt.json');assert ordinary['passed'] and ordinary['save_load']
write(EVID/'ordinary-main.json',{k:v for k,v in ordinary.items() if k!='save_access_trace'}|dict(local_full_receipt=ref(ART/'ordinary-main/receipt.json'),scope='Fresh positively owned ordinary main/default-slot fixture. Audit installed before importing main/constructing Engine. Optional sprite resources are absent in this font/data fixture; no sprite-render fidelity claim.'))
write(EVID/'gates.json',dict(ordinary_main=ref(EVID/'ordinary-main.json'),commands=commands,game={k:v for k,v in game.items() if k!='source'},scope='Final source-stable gates. All failed/preliminary attempts remain excluded and locally retained.'))
verification_paths=['workbench/scripts/workspace-journey.mjs','workbench/scripts/w5p-receipt.py']
verification={p:dict(working_sha256=digest(ROOT/p),committed_sha256=blob('',p)) for p in verification_paths}
receipt=dict(milestone='W5P',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),contract='surface-building-1',
    revisions=dict(start=git('rev-parse',START),initial_remote='0df461cdea49209eb66140e15576ed604efd1502',application_and_package_inputs=IMPL,final_delivery_ref='checkpoint/workbench-w5p-verified-20261029',note='Final named ref resolves the evidence/harness delivery. Exact remote main readback is reported after push in the handoff and ignored remote-readback.json.'),
    commission=dict(path='C:/Users/dango/Downloads/CODEX_WORKBENCH_W5P_SURFACE_BUILDING_AUTHORING.md',sha256=digest(Path('C:/Users/dango/Downloads/CODEX_WORKBENCH_W5P_SURFACE_BUILDING_AUTHORING.md'))),
    accepted_fixtures=fixtures,inventory=ref(EVID/'building-inventory.json'),orientations=ref(EVID/'orientation-access.json'),planned=ref(EVID/'planned-placement.json'),native=ref(EVID/'native-observations.json'),gates=ref(EVID/'gates.json'),preservation=ref(EVID/'preservation.json'),attempts=ref(EVID/'attempts.json'),
    environment=ref(EVID/'environment.json'),package_source_inputs=ref(EVID/'package-source-inputs.json'),package={p:ref(ROOT/'workbench/src-tauri/target/release'/p) for p in ('resonance-workbench.exe','bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe')},
    runtime={p:ref(ROOT/'workbench'/p) for p in ('worker/bridge.py','worker/runtime/python.exe','worker/runtime/python311._pth','worker/requirements.lock')},
    source_hashes=sources,captured_game_inputs=ref(EVID/'captured-game-inputs.json'),verification_source_hashes=verification,
    limits=['Revealed initial production previews; no player FOV, ordinary use, safety, balance or natural-selection frequency claim.','Controlled grid/residential in-memory injection at one recorded seed is not saved registration. Legacy folder pools can discover added variants.','No canonical pack, current selection-membership change, world rewrite, surface Test-room launcher, save migration, wiki or reference-pack rebuild.','Installer built, not installed; Windows is the verified target. Exact-source operation history remains in memory; restart recovery restores text/intent, never old review authority.','Preservation inventory covers tracked bytes and the owner plan; it does not independently prove every personal path was unread. Existing owned-cache/missing-cache guarantees are exercised by retained game lifecycle coverage.'])
write(ROOT/'workbench/docs/w5p-verification.json',receipt)
print(json.dumps(dict(passed=True,source_files=len(sources),package_inputs=len(package['files']),fixtures=len(fixtures),selected=len(plan['selected']))))
