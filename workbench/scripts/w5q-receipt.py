"""Retain compact source-bound W5Q evidence; bulky logs and binaries stay local."""
import gzip,hashlib,json,platform,re,shutil,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3] if '.artifacts' in Path(__file__).parts else Path(__file__).resolve().parents[2]
ART=ROOT/'workbench/.artifacts/w5q';EVID=ROOT/'workbench/docs/evidence/w5q'
START='f34ab95d7ee82735afb61fac41ddb873bab149a3';IMPL='43506c5b89d1a4ef98c931c1b33718d3203536e7'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p),bytes=p.stat().st_size)
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
def latest_pass(pattern):return next(p for p in sorted(ART.glob(pattern),key=lambda p:p.stat().st_mtime_ns,reverse=True) if read(p).get('passed'))
def compact(frame):
    return {k:v for k,v in frame.items() if k not in ('scene','input_files','source','runtime','descriptor_sha256','observed_at_utc','draft_sha256','path','contract','inputs')}

native=latest_pass('native-*/receipt.json');n=read(native)
assert n['package_sha256']==digest(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe')
fixtures={}
for name,f in n['fixtures'].items():
    p=EVID/'fixtures'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(f['raw'].encode('utf-8'));assert digest(p)==f['sha256'];fixtures[name]=dict(ref(p),source_path=f['path'])
enrolled,removed,landmark=n['enrolled'],n['removed'],n['landmark']
assert enrolled['profile_sha256']==fixtures['policy_enrolled']['sha256'];assert removed['profile_sha256']==fixtures['policy_removed']['sha256']
assert enrolled['input_files'][n['fixtures']['building']['path']]==fixtures['building']['sha256']==removed['input_files'][n['fixtures']['building']['path']]
assert enrolled['selection_matches_saved_resolve'] and removed['selection_matches_saved_resolve']
assert enrolled['seed']==removed['seed'];assert enrolled['plan_identity']!=removed['plan_identity']
assert any(r['asset']=='w5p_lodge' and r['selected'] for r in enrolled['summary'])
assert not any(r['asset']=='w5p_lodge' and r['profile']=='grid' for r in removed['summary'])
assert landmark['scene']['placement']['id'].startswith('landmark-') and all(r['receipt_owned'] for r in landmark['scene']['records'])
for name,frame in [('enrolled',enrolled),('removed',removed),('landmark',landmark)]:
    if name=='landmark':
        write(EVID/'landmark-plan.json',dict(same_verified_plan='enrolled-plan.json',plan_identity=frame['plan_identity'],input_identity=frame['input_identity'],seed=frame['seed'],inspected_placement=frame['scene']['placement']['id']))
    else:
        small=compact(frame)
        keys=('id','asset','owner','profile','role','path','chunk','origin','rotation','mirror','frontage','entrance_cells')
        small['rows']=[{k:r[k] for k in keys} for r in frame['rows']]
        write(EVID/(name+'-plan.json'),dict(small,input_manifest='saved-inputs-'+name+'.json',full_plan='ordinary-plan-'+name+'.json.gz'))
    if frame['scene']:
        scene=frame['scene'];payload=dict(scene=scene,policy_sha256=frame['profile_sha256'],seed=frame['seed'],input_identity=frame['input_identity'],plan_identity=frame['plan_identity'])
        full=EVID/(name+'-scene.json.gz');full.write_bytes(gzip.compress(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode(),mtime=0))
        assert json.loads(gzip.decompress(full.read_bytes()))==payload
        write(EVID/(name+'-construction.json'),dict(policy_sha256=frame['profile_sha256'],seed=frame['seed'],input_identity=frame['input_identity'],plan_identity=frame['plan_identity'],placement=scene['placement'],chunk=scene['chunk'],scene_address=scene['scene_address'],scene_seed=scene['scene_seed'],width=80,height=43,terrain_sha256=hashlib.sha256(json.dumps(scene['terrain'],separators=(',',':')).encode()).hexdigest(),scene_counts={k:len(scene[k]) for k in ('decor','items','containers','actors')},records=scene['records'],access=scene['access'],full_scene=ref(full),scope=scene['note']))
for name,frame in [('enrolled',enrolled),('removed',removed)]:write(EVID/('saved-inputs-'+name+'.json'),dict(input_identity=frame['input_identity'],files=frame['input_files'],seed=frame['seed'],policy_sha256=frame['profile_sha256']))
screens={}
for name in ('recovered-drafts.png','selected-building.png','removed-same-seed.png'):
    p=EVID/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(native.parent/name,p);screens[name]=ref(p)
write(EVID/'native-observations.json',dict(package_sha256=n['package_sha256'],runner_sha256=n['runner_sha256'],local_full_receipt=ref(native),
    checks=n['checks'],samples=n['samples'],stopping_rule=n['stopping_rule'],fixtures=fixtures,screenshots=screens,
    recovered={p:dict(draft=r['record']['draft'],variant=r['record']['variant'],variant_id=r['record']['variant_id'],target=r['record']['target'],sha256=hashlib.sha256(r['record']['draft'].encode()).hexdigest()) for p,r in n['recovery'].items()},
    protected_recovery_rejected=n['protected_recovery_rejected'],invalid_weight=n['invalid_weight'],stale_membership_return=n['stale_membership_return'],historical_after_reopen=n['historical_after_reopen'],parked_building=n['parked_building'],errors=n['errors'],
    scope='Actual packaged WebView, new controls, shared publication/reopen and host restart; positively owned disposable data/settings/recovery. No canonical content or campaign reads. Construction observations do not establish player interaction, frequency, balance or fun.'))
write(EVID/'entrance-diagnostic.json',read(ART/'diagnostic.json'))
for name in ('ordinary-plan-enrolled.json.gz','ordinary-plan-removed.json.gz'):shutil.copyfile(ART/name,EVID/name)
replay=read(ART/'ordinary-replay.json')
for name in ('enrolled','removed'):replay[name]['plan_gzip']=ref(EVID/('ordinary-plan-'+name+'.json.gz'))
write(EVID/'ordinary-replay.json',replay)
package=read(ART/'package-source-inputs.json');assert package['revision']==IMPL
for p,h in package['files'].items():assert digest(ROOT/p)==h['working_sha256'] and hashlib.sha256(subprocess.check_output(['git','show',IMPL+':'+p],cwd=ROOT)).hexdigest()==h['committed_sha256'],p
write(EVID/'package-source-inputs.json',package)
previous_package=read(ART/'package-pre-links-inputs.json')
room_changes=[p for p,h in previous_package['files'].items() if h['working_sha256']!=package['files'][p]['working_sha256']]
assert room_changes==['workbench/src/SelectionEditor.tsx'],room_changes
write(EVID/'room-retained-package-boundary.json',dict(previous_revision=previous_package['revision'],final_revision=IMPL,changed_package_inputs=room_changes,previous_inputs=previous_package['files'],scope='Room lifecycle was executed in this task on the preceding package. Only selection-row read-only navigation changed afterward; all room host/runtime/game inputs are unchanged.'))
sources={}
for p in git('diff','--name-only',START,IMPL).splitlines():
    sources[p]=dict(working_sha256=digest(ROOT/p),committed_sha256=hashlib.sha256(subprocess.check_output(['git','show',IMPL+':'+p],cwd=ROOT)).hexdigest())
write(EVID/'implementation-inputs.json',dict(revision=IMPL,files=sources,newline_note='Working-byte and Git-normalized byte identities are intentionally recorded separately; accepted fixtures remain exact UTF-8 bytes.'))
captured={p:dict(native_sha256=enrolled['input_files'][p],working_sha256=digest(ROOT/p)) for p in sources if p.startswith('roguelike/') and p.endswith('.py')}
assert all(h['native_sha256']==h['working_sha256'] for h in captured.values())
write(EVID/'captured-game-inputs.json',captured)
before=read(ART/'preservation-before-gates.json');later_scoped={'workbench/scripts/workspace-journey.mjs'}
failures=[p for p,h in before['files'].items() if p not in later_scoped and (not (ROOT/p).is_file() or digest(ROOT/p)!=h['sha256'])]
assert not failures
write(EVID/'preservation.json',dict(scope=before['scope'],captured_files=len(before['files']),later_scoped_harness_changes=sorted(later_scoped),unchanged_files=len(before['files'])-len(later_scoped),excluded_implementation_paths=before['excluded'],failures=failures,owner_plan_sha256=digest(ROOT/'RESONANCE_WORKBENCH_PLAN_PROPOSED_2026-10-25.md'),initial_status='Only the owner plan was untracked; production main matched remote f34ab95.',unchanged_canonical_data=git('diff','--name-only',START,'--','roguelike/data')=='',limitations='The pre-gate inventory was captured after implementation edits and explicitly excludes those paths; it is not mislabeled as a full pre-edit byte inventory or proof that every personal path was unread.'))
commands=[]
for name in ('frontend-links','typecheck-links','host','clippy','worker','dependency-negative','package-links'):
    r=read(ART/(name+'.json'));assert r['exit_code']==0,name
    changed=[p for p,h in r['inputs'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    relevant=[p for p in changed if p.startswith(('roguelike/','workbench/worker/'))] if name in ('worker','dependency-negative') else [p for p in changed if p.startswith('workbench/src-tauri/src/')] if name in ('host','clippy') else [p for p in changed if not p.startswith('workbench/scripts/')]
    assert not relevant,(name,relevant)
    commands.append({k:v for k,v in r.items() if k!='inputs'}|dict(input_manifest=ref(ART/(name+'.json')),non_consumed_source_changes=changed,consumed_sources_unchanged=True,scoped_passed=True))
game=read(ART/'game/run.json');assert game['passed'] and game['source_stable']
workspace=read(ROOT/'workbench/.artifacts/desktop-workspace/receipt.json');assert workspace['passed'];assert workspace['package_sha256']==n['package_sha256'] if 'package_sha256' in workspace else True
room_root=ROOT/'workbench/.artifacts/w5h';room=next(p for p in sorted(room_root.glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True) if read(p).get('passed'));room_receipt=read(room)
ordinary=read(ART/'ordinary-main/receipt.json') if (ART/'ordinary-main/receipt.json').is_file() else read(ART/'ordinary-main/result.json')
assert ordinary['passed']
write(EVID/'gates.json',dict(commands=commands,game={k:v for k,v in game.items() if k!='source'},game_source_manifest_sha256=hashlib.sha256(json.dumps(game['source'],sort_keys=True).encode()).hexdigest(),
    native=ref(native),workspace=dict(local_receipt=ref(ROOT/'workbench/.artifacts/desktop-workspace/receipt.json'),checks=workspace['checks'],passed=True,scope='Actual final release package, app-local seven-owner freshness/cancellation/conflict/rollback/reopen lifecycle. Tab activation avoids automation autoscroll changing the state under test.'),
    room_session=dict(local_receipt=ref(room),checks=room_receipt['checks'],passed=True,package_sha256=room_receipt['package_sha256'],scope='Passed on the immediately preceding package; the later change only enables read-only selection row navigation. Room host/runtime/game source inputs are unchanged.'),ordinary_main=ordinary))
attempts=[dict(local_receipt=ref(p),failure=read(p).get('failure'),counted_as_pass=False) for p in sorted(ART.glob('native-*/receipt.json')) if not read(p).get('passed')]
write(EVID/'attempts.json',dict(native=attempts,excluded=[
    'Preliminary selector checks exposed incorrect case checking against the shared scratch/data staging path. Corrected before final worker/game gates.',
    'A focused source-span test exposed add/remove whitespace loss. Selection insertion now preserves the native array trailing span; frontend tests pass.',
    'The native journey exposed selector Source history clearing. Fixed to use the shared history and allow undo from malformed JSON; final package/native journey verifies it.',
    'Initial native event readiness and assumed undo button placement were corrected in the app-local harness. A later journey exposed row navigation disabled by the edit fieldset; read-only source navigation is enabled in the final renderer. All failed receipts remain excluded.',
    'Workspace harness failures included a stale Begin-edit target, Playwright autoscrolling the old pane while clicking its offscreen tab, and one fixture process exiting with Windows status -1073740791 without output. The harness now waits for the intended owner and editing state, and activates tabs through the same app-local click handler without changing the old pane scroll first. Final lifecycle checks pass; no failed attempt is counted.',
    'An intermediate successful build crossed a frontend/harness edit and was source_stable=false. Only package-links and its matching primary native receipts are used.',
    'The full worker run crossed frontend/harness-only edits. Exact worker/game Python input hashes are unchanged; its original broad source_stable flag and precise non-consumed changes remain disclosed. No expensive gate was repeated solely to relabel evidence.']))
brief=Path('C:/Users/dango/Downloads/CODEX_WORKBENCH_W5Q_SETTLEMENT_SELECTION_AUTHORING.md');shutil.copyfile(brief,EVID/'issued-brief.md')
write(ROOT/'workbench/docs/w5q-verification.json',dict(recorded_utc=datetime.now(timezone.utc).isoformat(),start_revision=START,entrance_repair_revision='aaa7f0d1890b6ea7ad1f93ae34026800c59da638',implementation_package_revision=IMPL,
    final_delivery_ref='checkpoint/workbench-w5q-verified-20261029',issued_brief=ref(EVID/'issued-brief.md'),
    evidence={p.name:ref(p) for p in sorted(EVID.glob('*.json'))},fixtures=fixtures,package=dict(executable=ref(ROOT/'workbench/src-tauri/target/release/resonance-workbench.exe'),installer=ref(ROOT/'workbench/src-tauri/target/release/bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe')),
    runtime=dict(node=subprocess.check_output(['node','--version']).decode().strip(),rust=subprocess.check_output(['rustc','--version']).decode().strip(),python=game['python'],dependencies=game['dependencies']),
    activation='New world plans only; existing captured plans/caches and consumed-dependency gates retain their contracts.',
    limits='Windows verified. Revealed initial production construction and static full-span access; no player interaction, natural discovery frequency, balance, installer UX, other platform, save migration, canonical pack or wiki rebuild.'))
print(json.dumps(dict(fixtures=fixtures,selected=sum(r['selected'] for r in enrolled['summary'] if r['asset']=='w5p_lodge'),seed=enrolled['seed'],evidence=str(EVID))))
