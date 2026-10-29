"""Assemble W5K's accessible evidence, with explicit package/source boundaries."""
import hashlib, json, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'workbench/.artifacts/w5k';DOC=ROOT/'workbench/docs';EVID=DOC/'evidence/w5k'
def read(p):return json.loads(p.read_bytes())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8').strip()
def blob(revision,path):return subprocess.check_output(['git','show',revision+':'+path],cwd=ROOT)
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=digest(p))
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
def latest(pattern):
    for p in sorted(ROOT.glob(pattern),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        r=read(p)
        if r.get('passed'):return p,r
    raise AssertionError(pattern)
native_path,native=latest('workbench/.artifacts/w5k/native-*/receipt.json')
parent_path=Path(native['accepted_authoring_continuation']['path']) if native.get('accepted_authoring_continuation') else native_path
parent=read(parent_path)
if parent_path!=native_path:
    assert digest(parent_path)==native['accepted_authoring_continuation']['sha256']
    assert parent['package_sha256']==native['accepted_authoring_continuation']['authoring_package_sha256']
room_path,room=latest('workbench/.artifacts/w5h/native-*/receipt.json')
release=ROOT/'workbench/src-tauri/target/release'
assert native['package_sha256']==room['package_sha256']==digest(release/'resonance-workbench.exe')
assert native['compatibility_before']['pid']!=native['compatibility_after']['pid']!=native['compatibility_final']['pid']
assert native['capture_v1']['captured']['manifest_sha256']==native['capture_reset']['captured']['manifest_sha256']!=native['capture_v2']['captured']['manifest_sha256']
EVID.mkdir(parents=True,exist_ok=True)
(EVID/'.gitattributes').write_bytes(b'# Reports have portable LF identities; accepted fixture bytes remain exact.\n*.json text eol=lf\nfixtures/*.json -text\n')
saved={}
for name,row in {**native['saved'],'room':native['room'],'immediate_same_id':native['immediate']}.items():
    raw=row['raw'].encode('utf-8');assert hashlib.sha256(raw).hexdigest()==row['sha256']
    p=EVID/'fixtures'/(name+'.json');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    saved[name]=dict(**ref(p),published_path=row['path'],definition=row['definition'],identity='Exact accepted UI-authored UTF-8 bytes; Git -text prevents normalization')
shutil.copyfile(ART/'shipped-sources.json',EVID/'shipped-sources.json')
shots={}
for name in ('workbench-w5k_cook-preparation.png','workbench-w5k_dry.png','workbench-room.png','game-cooking.png','game-roast-floor.png','game-drying.png','game-treatment.png','game-revised-job.png'):
    source=native_path.parent/name
    if not source.exists():source=parent_path.parent/name
    target=EVID/name;shutil.copyfile(source,target);shots[name]=dict(**ref(target),observed_process='authoring parent' if source.parent==parent_path.parent and parent_path!=native_path else 'completed journey')
def state(o):
    return {k:o[k] for k in ('pid','turn','action_calls','player','mode','needs','hp','max_hp','craft','placement','processing','decor','logs') if k in o}|dict(
        inventory=[i for i in o['inventory'] if i['item_id'].startswith('w5k_')],
        floor=[dict(x=r['x'],y=r['y'],items=[i for i in r['items'] if i['item_id'].startswith('w5k_')]) for r in o['floor'] if any(i['item_id'].startswith('w5k_') for i in r['items'])])
def compatibility(key):
    r=native[key];return {k:v for k,v in r.items() if k!='save_access_audit'}|dict(save_access_events=len(r['save_access_audit']),explicit_disposable_ownership=True)
observations=dict(
    scope='Accepted baseline definitions authored/reopened in packaged Windows controls; continued from their exact bytes after a harness event-file lock. Final process repeats both real preparations, pickup/use, revisions/reset/latest, and separate-process ordinary saves. No external JSON writes are counted as accepted authoring.',
    authoring_parent=dict(**ref(parent_path),host_pid=parent.get('host_pid'),checks=parent['checks'],interrupted_gameplay_counted_as_completed=False),
    completed_journey=ref(native_path),saved=saved,recovery=native['recovery'],conflict=native['conflict'],acquired=native['acquired'],
    initial_setup=native['disclosed_fixture'],cooking={**{k:v for k,v in native['cooking'].items() if k!='confirmed'},'confirmed':state(native['cooking']['confirmed'])},
    drying={**{k:v for k,v in native['drying'].items() if k not in ('before','confirmed')},'before':state(native['drying']['before']),'confirmed':state(native['drying']['confirmed'])},
    uses=native['uses'],captures={name:{k:v for k,v in native[key]['captured'].items() if k not in ('files','runtime_files')} for name,key in [('original','capture_v1'),('reset','capture_reset'),('latest','capture_v2')]},
    reset_job=state(native['reset_job']),latest_job=state(native['latest_job']),
    compatibility={key:compatibility(key) for key in ('compatibility_before','compatibility_after','missing','resumed','compatibility_final')},checks=native['checks'],screenshots=shots)
write(EVID/'observations.json',observations)
commands=[]
for name,command,pattern,outcome in [
 ('frontend.log','npm.cmd test',r'69 passed','69 frontend tests pass'),
 ('web.log','npm.cmd run build:web',r'built in','TypeScript and production frontend build pass'),
 ('host-final.log','cargo test --locked --manifest-path src-tauri/Cargo.toml',r'68 passed; 0 failed','68 Rust tests pass'),
 ('clippy-final.log','cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings',r'Finished','clippy passes with warnings denied'),
 ('production-final.log','Configured development Python, absolute PYTHONPATH game/tests/tools: unittest test_preparation_w5k test_crafting test_gameplay_g12 test_gameplay_g16 test_usable_supplies test_authored_assignment test_gameplay_g15 test_effect_persistence test_generation_ownership test_gameplay_g17 test_room_test_session test_combat_routes -v',r'Ran 101 tests[\s\S]*\nOK','101 broad game cases pass'),
 ('repairs-final.log','Pinned Python: unittest test_preparation_w5k -v',r'Ran 6 tests[\s\S]*\nOK','6 focused repairs pass, including one additional hot/cold owner case added after broad run (102 distinct game cases overall)'),
 ('worker-serial-final.log','worker/runtime/python.exe -X utf8 -I -B -m unittest discover -s worker -v',r'Ran 79 tests[\s\S]*OK','79 worker cases: 78 pass, expected embedded dependency-absence skip'),
 ('missing-dependency.log','Development Python: test_bridge dependency_absence with -S child',r'Ran 1 test[\s\S]*\nOK','Separate missing-dependency negative control passes'),
 ('package.log','npm.cmd run bundle -- -- --locked',r'Finished 1 bundle','Windows executable and NSIS pass'),
 ('native-final.log','RESONANCE_W5K_ACCEPTED_JOURNEY=<exact prior authoring receipt>, RESTORE_BASELINE=1, REFRESH_RUNTIME=1; node scripts/run-preparation.mjs',r'"passed":true','Packaged preparations/use/revision and cold compatibility pass from accepted authored bytes'),
 ('workspace.log','node scripts/run-workspace.mjs',r'"passed": true','Packaged shared document lifecycle passes'),
 ('room-session.log','node scripts/run-room-tests.mjs',r'"passed":true','Packaged capture/reset/cold-load/lifetime/fault boundaries pass'),
 ('ordinary.log','Pinned Python: standalone-room-regression.py in fresh disposable runtime inputs',r'"passed": true','Ordinary 128x128 startup/default save/load passes')]:
    p=ART/name;text=p.read_text(encoding='utf-8-sig');assert re.search(pattern,text),(name,text[-1200:])
    commands.append(dict(command=command,exit_code=0,outcome=outcome,local_log=ref(p)))
write(EVID/'gates.json',dict(commands=commands,provenance='Locally executed Windows checks. Full logs remain in ignored local artifacts; exact hashes retained. Accessible observations/screenshots/accepted bytes are alongside this summary. No independent native rerun is claimed.'))
preservation=read(ART/'preservation-after.json');assert not preservation['failures']
fixture=Path(native['root']);source_audit=[]
for p in (ROOT/'roguelike').rglob('*.py'):
    if any(part in ('saves','__pycache__') for part in p.parts):continue
    target=fixture/p.relative_to(ROOT)
    if not target.is_file() or digest(p)!=digest(target):source_audit.append(p.relative_to(ROOT).as_posix())
assert not source_audit,source_audit
runtime=ROOT/'workbench/worker/runtime';runtime_rows={p.relative_to(runtime).as_posix():digest(p) for p in runtime.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
assert all((release/'python'/name).is_file() and digest(release/'python'/name)==value for name,value in runtime_rows.items())
assert digest(release/'bridge.py')==digest(ROOT/'workbench/worker/bridge.py')
sources={}
for name in git('diff','--name-only','checkpoint/workbench-w5k-start-20261028','HEAD').splitlines():
    p=ROOT/name
    if p.is_file() and not name.startswith('workbench/docs/evidence/'):
        sources[name]=dict(working_sha256=digest(p),committed_sha256=hashlib.sha256(blob('HEAD',name)).hexdigest())
w5j=read(DOC/'w5j-verification.json');portable={}
for key in ('corpus','observations'):
    row=w5j[key];committed=blob('HEAD',row['path'])
    assert hashlib.sha256(committed).hexdigest()==row['sha256']
    assert hashlib.sha256(committed.replace(b'\n',b'\r\n')).hexdigest()==row['original_working_crlf_sha256']
    portable[key]=row
def environment(executable):
    code="import sys,platform,json,importlib.metadata as m;print(json.dumps(dict(executable=sys.executable,python=sys.version,platform=platform.platform(),dependencies={k:m.version(k) for k in ['pygame','tcod','numpy','cffi','pycparser','typing_extensions']})))"
    return json.loads(subprocess.check_output([str(executable),'-X','utf8','-I','-B','-c',code],text=True))
receipt=dict(milestone='W5K',passed=True,observed_utc=datetime.now(timezone.utc).isoformat(),contract='item-preparation-1',
    revisions=dict(reviewed_start=git('rev-parse','checkpoint/workbench-w5k-start-20261028'),initial_remote='ce3c7ab6d1b845c2dd41d07a9c91f6ed6d1b1d33',
        implementation=git('rev-parse','2dbd277'),package_inputs=git('rev-parse','checkpoint/workbench-w5k-final-package-20261028'),earlier_package_inputs=git('rev-parse','checkpoint/workbench-w5k-package-inputs-20261028'),evidence_inputs=git('rev-parse','HEAD'),
        final_delivery_ref='checkpoint/workbench-w5k-verified-20261028',note='Final commit cannot embed its own hash. Resolve this named local ref; exact final local/remote-main SHA readback is recorded in the handoff and local remote-readback.json. Package inputs precede later harness/evidence/documentation commits.'),
    corpus=ref(EVID/'shipped-sources.json'),observations=ref(EVID/'observations.json'),gates=ref(EVID/'gates.json'),accepted_fixtures=saved,screenshots=shots,
    environments=dict(pinned=environment(runtime/'python.exe'),development=environment(Path('G:/GameDev/RoguelikeBaseline-20261020/project/.venv/Scripts/python.exe'))),
    package=dict(executable=ref(release/'resonance-workbench.exe'),installer=ref(release/'bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe'),bridge=ref(release/'bridge.py'),source_release_bridge_equal=True,runtime_files=len(runtime_rows),runtime_equal=True,runtime_manifest_sha256=hashlib.sha256(json.dumps(runtime_rows,sort_keys=True).encode()).hexdigest()),
    source_hashes=sources,native_game_python_matches_working_tree=True,w5j_portable_readback=portable,preservation=preservation,
    shipped_assignment=read(ROOT/'roguelike/data/generation/authored_submap_selection.json'),
    corrections=['Updated historical variant-only/passive-readonly test expectations to the commissioned source policy; recovery/inspection still grants no review.',
        'Unsupported item-array worker regression uses an eligible unreferenced source so an empty candidate does not first invalidate unrelated room references.',
        'Native navigation retries only read-only monitor contention; recipe controls reside in the portalled shared panel, not the inspector.',
        'An interrupted event-file rename hit a transient Windows reader lock. The event publisher retries the same id, so accepted inputs never replay. Accepted exact UI-authored bytes from that process are retained; final gameplay repeats in a new process.',
        'An incomplete concurrent worker attempt is not counted; final full worker suite runs serially.',
        'A temporary Windows locale decoding mistake in edited documentation/test strings was repaired against committed UTF-8; final source diffs and screenshots are checked.'],
    limits=['Controlled initial needs/injury and production-created heat; no balance, pacing, unaided discovery or room-decor authoring claim.',
        'Conjunctions remain automatic-only. Campfire/world placement, legacy/deprecated sources, new stations/effects/equipment/learning, broad migration/offscreen expansion and wiki work remain excluded.',
        'Only disposable fixture definitions/save roots were used; live content and shipped assignment profile remain unchanged.'])
write(DOC/'w5k-verification.json',receipt)
print(json.dumps(dict(passed=True,corpus=read(EVID/'shipped-sources.json')['classes'],commands=len(commands),native=str(native_path),package_inputs=receipt['revisions']['package_inputs'])))
