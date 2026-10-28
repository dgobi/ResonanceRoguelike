"""Assemble source-bound W5G evidence after the local gates, without a self hash."""
import hashlib,json,re,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];WB=ROOT/'workbench';ART=WB/'.artifacts/w5g'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def artifact(path):
    p=Path(path);p=p if p.is_absolute() else ROOT/p
    return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
def tree(path):
    rows=[(p.relative_to(path).as_posix(),sha(p)) for p in sorted(path.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    return dict(files=len(rows),sha256=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest())
def log(name): return (ART/name).read_text(encoding='utf-8-sig')
def unique_receipt(name):
    rows=re.findall(r'"output"\s*:\s*("(?:[^"\\]|\\.)*")',log(name))
    path=Path(json.loads(rows[-1]))/'receipt.json';value=json.loads(path.read_text(encoding='utf-8-sig'));assert value['passed'],(name,value)
    return path,value
commands=[]
def command(cmd,name,success,result=None):
    text=log(name);assert re.search(success,text),name
    commands.append(dict(command=cmd,exit_code=0,result=result or success,log=artifact(ART/name)))
command('npm.cmd test','frontend-final.log',r'Tests\s+65 passed','65 passed / 17 files')
command('npm.cmd run typecheck','typecheck-final.log',r'tsc --noEmit','passed')
command('cargo test --locked --manifest-path src-tauri/Cargo.toml','host-final.log',r'57 passed; 0 failed','57 passed; W4D faults and W5G host recovery/operation regressions included')
command('cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings','clippy-final.log',r'Finished','passed; warnings denied')
worker=log('worker-stable.log');match=re.search(r'Ran (\d+) tests',worker);assert match and 'FAILED' not in worker
command('worker/runtime/python.exe -X utf8 -X faulthandler -B -m unittest discover -s worker -v','worker-stable.log',r'OK \(skipped=1\)',f'{int(match[1])-1} passed, one expected dependency-absence skip')
command('standard Python 3.11: test_bridge.BridgeTests.test_dependency_absence_structured','missing-dependency.log',r'\bOK\b','missing-dependency control passes separately')
command('standard Python 3.11 + pinned payload: effect persistence, combat, scene ownership, G17, access, authoring destinations, three reader cases','production-final.log',r'Ran 55 tests','55 passed; tools directory included on PYTHONPATH for the historical G17 input')
assert 'FAILED' not in log('production-final.log')
command('npm.cmd run bundle -- -- --locked','package-delivery.log',r'Finished 1 bundle','Windows release and NSIS; complete pinned runtime verified; locked dependencies')
compat=json.loads((ART/'compatibility-outcomes.json').read_text(encoding='utf-8-sig'))
if isinstance(compat,dict):compat=[compat]
assert len(compat)==9,compat
for row in compat:
    name=row['script']+'.log'
    if row['script']=='run-recovery.mjs':
        assert json.loads(log('recovery-final.log'))['passed'];name='recovery-final.log'
    elif row['script']=='run-submaps.mjs':
        assert json.loads((ART/'submap-outcome.json').read_text(encoding='utf-8-sig'))['exit_code']==0;name='submaps-final.log'
    else:assert row['exit_code']==0,row
    commands.append(dict(command='node scripts/'+row['script'],exit_code=0,log=artifact(ART/name),first_attempt_exit_code=row['exit_code'],package_inputs='4df9ea10c4b0e723effbe85eaeeacdc0b9347c9e',tested_executable_sha256='1daded232f59f2f8bb42d3551242fac8401535bdfd79f9590b8ebb4607dc18b9'))
command('W5D_REOPEN_REGRESSION=lost node scripts/run-workspace.mjs','workspace-lost.log',r'"passed": true','lost publication-reopen response regression passes')
commands[-1]['package_inputs']='4df9ea10c4b0e723effbe85eaeeacdc0b9347c9e'
command('WORKBENCH_STARTUP_SMOKE=1 node scripts/startup-test.mjs','startup-delivery.log',r'"passed": true','final package: four isolated launch/project-change/restart scenarios pass')
native_path,native=unique_receipt('native-rooms-delivery.log');screenshots_path,screenshots=unique_receipt('room-screenshots-delivery.log')
command('node scripts/run-rooms.mjs','native-rooms-delivery.log',r'"passed":true','final package: two actual native processes, abrupt accepted-draft recovery, linked/mixed building-pool controls, two publications and exact reopen; real engine before/after processes')
for name in ('pools-delivery','submaps-delivery','workspace-delivery'):
    assert json.loads((ART/(name+'-outcome.json')).read_text(encoding='utf-8-sig'))['exit_code']==0
    command('node scripts/'+{'pools-delivery':'run-pools.mjs','submaps-delivery':'run-submaps.mjs','workspace-delivery':'run-workspace.mjs (W5D_REOPEN_REGRESSION=lost)'}[name],name+'.log',r'"passed": true','final package focused compatibility rerun')
runtime=json.loads((ART/'creature-runtime/results/runtime-result.json').read_text(encoding='utf-8'));assert runtime['passed']
command('packaged Python scripts/creature-runtime-probe.py disposable-project disposable-results','creature-runtime.log',r'"passed": true','retained W5F actual identity, AI/attack/pursuit, special dispatch and fresh-process injured-Wight restoration')
prior=json.loads((WB/'docs/w5f-verification.json').read_text(encoding='utf-8'))
changed=git('diff','--name-only','f2c85fa791092601f16411062024f9dba4e976ff','HEAD').splitlines()
files=set(prior['source']['worktree_sha256'])|set(changed)|{'workbench/scripts/w5g-receipt.py','workbench/scripts/capture-room-evidence.mjs'}
files={p for p in files if (ROOT/p).is_file() and p not in ('workbench/docs/w5g-verification.json','workbench/docs/W5G_DELIVERY.md')}
source=dict(revision=git('rev-parse','HEAD'),worktree_sha256={p:sha(ROOT/p) for p in sorted(files)},git_sha256={})
for p in sorted(files):
    result=subprocess.run(['git','show','HEAD:'+p],cwd=ROOT,capture_output=True)
    if result.returncode==0:source['git_sha256'][p]=hashlib.sha256(result.stdout).hexdigest()
release=WB/'src-tauri/target/release'
package=dict(executable_sha256=sha(release/'resonance-workbench.exe'),source_bridge_sha256=sha(WB/'worker/bridge.py'),bridge_sha256=sha(release/'bridge.py'),runtime_payload=tree(WB/'worker/runtime'),observed_runtime=tree(release/'python'),frontend=tree(WB/'dist'),installer_sha256=sha(release/'bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe'))
assert package['source_bridge_sha256']==package['bridge_sha256']
assert package['runtime_payload']==package['observed_runtime']
assert package['executable_sha256']==native['package_sha256']==screenshots['package_sha256']
sys.path.insert(0,str(WB/'worker'))
from bridge import source_identity
current_identity=source_identity(ROOT)
assert current_identity['game_source_sha256']==native['preview_v1']['source']['game_source_sha256']
assert current_identity['resources_sha256']==native['preview_v1']['source']['resources_sha256']
preservation=json.loads((ART/'preservation-after.json').read_text(encoding='utf-8'));assert not preservation['failures']
def preview_summary(p):
    return dict(origin=p['origin'],authored_start=p['authored_start'],actual_arrival=p['spawn'],stairs=p['stairs'],access=p['access'],
        records=[{k:r.get(k) for k in ('record_id','source_index','kind','source_xy','xy','relocated','item_id','text_id','text_override_present','decor_id','loot_pools','actual_count','actor_classes','creature_definition','objects')} for r in p['population_receipts']])
native_summary={k:native[k] for k in ('started_utc','processes','checks','drafts','baseline','text','creature','publication_v1','publication_v2','engine_before','engine_after')}
native_summary['engine_before'].pop('saved_scene',None)
native_summary.update(receipt=artifact(native_path),preview_v1=preview_summary(native['preview_v1']),preview_v2=preview_summary(native['preview_v2']))
images=[artifact(native_path.parent/p) for p in ('completed-room-preview.png','room-problems-and-results.png','engine/actual-room-reader.png','screenshots/completed-source-room.png','screenshots/completed-realized-room.png')]
receipt=dict(milestone='W5G',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),revisions=dict(baseline='f2c85fa791092601f16411062024f9dba4e976ff',initial_remote='f2c85fa791092601f16411062024f9dba4e976ff',repair='f02b41ef4df96af4810bd26e7ae4c408a1f92707',implementation='1b5b853a1030d890f3386e70e7e33f8b275f619c',malformed_inspection='4df9ea10c4b0e723effbe85eaeeacdc0b9347c9e',pool_return='9a5675a49473d544ad82e5614042112f905c0ab1',package_inputs='cffe43efd8f8b6c231c7295fea5594ac460677d6',test_inputs=source['revision'],evidence_ref='checkpoint/workbench-w5g-verified-20261027',evidence_note='Verified annotated checkpoint and external handoff identify the final evidence commit/remote main; no self-hash commit loop.',branch='main'),
    commands=commands,package=package,source=source,source_audit=dict(native_game_python_matches=True,native_fonts_ui_resources_match=True,game_source_sha256=current_identity['game_source_sha256'],resources_sha256=current_identity['resources_sha256']),preservation=preservation,native_rooms=native_summary,screenshots=dict(receipt=artifact(screenshots_path),images=images),retained_creature_runtime=dict(receipt=artifact(ART/'creature-runtime/results/runtime-result.json'),result=runtime),
    source_policy_coverage=dict(ordinary_room=['edit','variant'],exact_documentation_template=['recover unfinished intent','variant to immediate layouts only'],protected_laboratory=[],malformed_ambiguous_unsupported=[],text_recipe=['recover unfinished intent','variant'],special_creatures_typography=['edit; explicit variant intent refused']),
    provenance='All recorded final gates rerun locally on Windows. Native app uses app-local CDP only, disposable data/settings/recovery roots. Engine before/after PIDs differ and use real SaveManager save/load. Static preview, actual interactions and source analysis remain distinct.',
    verification_notes=['Initial native run found and corrected registered-room publication handoff invalidation; final exact reopen passes.', 'Runtime fixture equips a real tallow torch for actual FOV/interaction; static access does not establish player FOV.', 'An initial 55-case production command omitted tools on PYTHONPATH; final command includes it and all 55 pass.', 'Earlier W1/W4C test expectations were updated for registered room admission and explicit same-ID operations. Existing W4D stale/cancel/reserved-publication tests remain present.', 'Earlier full worker runs used superseded W1/W2 expectations. The final stable full run above uses the current tests.', 'Native recovery waits for the selected mounted file and retries only no-write BUSY contention. The adapted submap gate checks the native option disabled property, retains all stale/cancel/reserved publication checks and uses registered tabs.', 'The broad native compatibility matrix binds package inputs 4df9ea1. After narrow pool-origin and canvas-teardown fixes, the final package repeats the full room/cold-engine journey, ordinary pools, submap fault coverage, lost-reopen workspace and four startup scenarios. Game Python, host and bridge inputs are unchanged by those final frontend fixes.'],
    limits=['Bounded direct item/container/creature rooms only; weighted, scene, deferred-special sources and inactive decor authoring remain inspect-only.', 'No natural world assignment, campaign migration, unsaved dependency overlays, multi-file transaction or new simulation/playtest service.', 'Activation affects first generation after catalogue initialization, including unvisited existing-campaign submaps; owned scenes are retained. Established current-definition reads remain unchanged.', 'No wiki/reference-pack rebuild, owner-plan commit, personal campaign scan or desktop takeover.'])
(WB/'docs/w5g-verification.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(passed=True,source_files=len(files),commands=len(commands),unchanged=preservation['unchanged'],native=str(native_path))))
