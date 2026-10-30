"""Independent ordinary replay of exact native accepted inputs; no injected policy."""
import contextlib,gzip,hashlib,io,json,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3] if '.artifacts' in Path(__file__).parts else Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'workbench/worker'),str(ROOT/'roguelike')]
from test_authoring import data_fixture
from engine.data_loader import DataLoader
from generation.world_gen import generate_world
from generation.placement import digest
from generation.settlement_selection import resolve,validate
from world.world_map import WorldMap
import config
config.DEBUG_MODE=False
ART=ROOT/'workbench/.artifacts/w5q'
native=next(p for p in sorted(ART.glob('native-*/receipt.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True) if json.loads(p.read_text(encoding='utf-8')).get('passed'))
n=json.loads(native.read_text(encoding='utf-8'));fixture=ART/('replay-'+str(time.time_ns()))/'project';data_fixture(fixture)
building=n['fixtures']['building'];(fixture/building['path']).write_bytes(building['raw'].encode('utf-8'))
results={};plans={}
for name,key in [('enrolled','policy_enrolled'),('removed','policy_removed')]:
    policy=n['fixtures'][key];(fixture/policy['path']).write_bytes(policy['raw'].encode('utf-8'))
    with contextlib.redirect_stdout(io.StringIO()):
        data=DataLoader(str(fixture/'roguelike/data'));world=WorldMap(128,128);world.seed=n['enrolled']['seed'];generate_world(world,data,random.Random(world.seed))
    assert digest(world.plan)==n[name]['plan_identity'] and world.plan['selection']==resolve(data)
    rows=[p for p in world.plan['placements'] if p['asset']=='w5p_lodge'];assert bool(rows)==(name=='enrolled')
    saved=json.dumps(world.plan,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8');out=ART/('ordinary-plan-'+name+'.json.gz');out.write_bytes(gzip.compress(saved,mtime=0));plans[name]=world.plan
    results[name]=dict(seed=world.seed,plan_identity=digest(world.plan),policy_sha256=hashlib.sha256(policy['raw'].encode()).hexdigest(),selected_lodge=len(rows),plan_gzip=dict(path=out.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),bytes=out.stat().st_size),saved_resolve_equal=True)
# This is the self-contained policy contract, separate from G5's actual pending
# scene/cache save-load regression. Current removal cannot invalidate old policy.
validate(plans['enrolled']['selection'])
results['old_captured_policy_still_valid_after_removal']=True
results['scope']='Supporting replay in a disposable saved-data fixture. Exact accepted policy/building bytes, ordinary generate_world defaults and one already recorded seed; no candidate injection or additional seed search. Full old-plan pending construction is covered separately by the existing G5 save regression.'
(ART/'ordinary-replay.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8');print(json.dumps(results))
