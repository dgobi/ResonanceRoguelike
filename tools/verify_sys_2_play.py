"""SYS-2 selected-world acquisitions and two ordinary light approaches.

Each route starts once at a real selected shed public join with ordinary starting
possessions. Full map/stock knowledge and fixed RNGs choose the bounded route;
movement, pickup, equipment, AI, survival, F5/F9 and stairs use normal handlers.
The separate native bandit witness starts at disclosed midnight and lawful range.
These are local usefulness/persistence witnesses, not unaided discovery or balance.
"""
import argparse,copy,hashlib,json,os,random,subprocess,sys,tempfile,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
import pygame
from verify_sys_1_play import Journey as BaseJourney,snapshot as base_snapshot
from verify_ai_6_play import display,capture
from g10_play import boot,status
from engine.save_manager import SceneAddress,_serialize_entity,SaveManager
from engine.illumination import scene_light
from components.ai import _creature_can_see_player


def snapshot(e):
    r=base_snapshot(e);f=scene_light(e)
    r.update(actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
        ambient=f.ambient,emitted_sha256=hashlib.sha256(f.emitted.tobytes()).hexdigest(),
        observed_sha256=hashlib.sha256(e.normal_player_vision()['visible'].tobytes()).hexdigest())
    return r


class Journey(BaseJourney):
    def key(self,k,text=''):
        e=self.e;before=e.world_time.turn;e._handle_key(k,text);self.receipt['events']+=1
        assert not e._player_is_dead,('player died',status(e))
        if e.world_time.turn!=before:
            f=scene_light(e);view=e.normal_player_vision()['visible']
            self.receipt.setdefault('paid',[]).append(dict(key=text or pygame.key.name(k),turn=e.world_time.turn,
                scene=[e.world_x,e.world_y,e.current_submap_id],player=[e.player.x,e.player.y],hp=e.player.fighter.hp,
                offhand=getattr(e.player.equipment.slots['offhand'],'item_id',None),
                fuel={i.item_id:i.turns_lit for i in e.player.inventory.items if i.on_use=='equip_light'},
                light_sources=[dict(kind=t[0],id=t[1],position=[t[2],t[3]],radius=t[4]) for t in f.sources],
                watchers=[dict(id=a._creature_id,position=[a.x,a.y],lit=bool(f.lit[a.x,a.y]),observed=bool(view[a.x,a.y]),
                    state=a.ai.snapshot(),trace=copy.deepcopy(a.ai.trace[-2:])) for a in e.entities
                    if getattr(a,'_creature_id','')=='barrow_shy_stalker']))

    def checkpoint(self,label):
        e=self.e;before=snapshot(e);self.key(pygame.K_F5);self.key(pygame.K_F9)
        after=snapshot(e)
        if before!=after:(self.out/(label+'-difference.json')).write_text(json.dumps(dict(before=before,after=after),indent=2))
        assert before==after,(label,e.save_manager.last_error)
        archive=self.out/(label+'.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for p in e.save_manager.checkpoint_path().rglob('*'):
                if p.is_file():z.write(p,p.relative_to(e.save_manager.checkpoint_path()))
        archive.with_suffix('.json').write_text(json.dumps(before),encoding='utf8')
        child=subprocess.run([sys.executable,'-X','utf8','-B',str(Path(__file__).resolve()),'--cold',str(archive)],capture_output=True,text=True,timeout=120)
        assert child.returncode==0,child.stdout+child.stderr
        result=json.loads(child.stdout.splitlines()[-1]);assert result['pid']!=os.getpid()
        self.receipt['checkpoints'].append(dict(label=label,f5_f9_equal=True,cold=result,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))

    def use(self,iid): self.item(iid);self.close()

    def travel(self,wx,wy):
        from generation.access import enterable
        e=self.e
        for _ in range(8):
            if (e.world_x,e.world_y)==(wx,wy):return
            dx=(wx>e.world_x)-(wx<e.world_x);dy=(wy>e.world_y)-(wy<e.world_y)
            if dx and not dy:
                x=79 if dx>0 else 0;goals=[(x,y) for y in range(43) if enterable(e.local_map,(x,y),e.data)]
                self.move(goals);self.key(pygame.K_RIGHT if dx>0 else pygame.K_LEFT)
            else:
                y=42 if dy>0 else 0;goals=[(x,y) for x in range(80) if enterable(e.local_map,(x,y),e.data)]
                self.move(goals);self.key(pygame.K_DOWN if dy>0 else pygame.K_UP)
        raise AssertionError('bounded interscene route exhausted')


def select(e):
    subs=[(wx,wy,s) for (wx,wy),c in e.world_map.chunks.items() for s in c.submaps if s.layout_id=='barrow_lamplit_store']
    sheds=[p for p in e.world_map.plan['placements'] if p['asset']=='tool_shed_c']
    ranked=[]
    for p in sheds:
        wx,wy=p['origin'][0]//80,p['origin'][1]//43
        for sx,sy,sub in subs:
            distance=abs(wx-sx)+abs(wy-sy)
            if distance<=3:ranked.append((distance,abs(wx-e.world_map.start_wx)+abs(wy-e.world_map.start_wy),p['id'],wx,wy,sx,sy,sub.submap_id,p))
    for row in sorted(ranked)[:30]:
        _,_,_,wx,wy,sx,sy,sid,p=row
        m,_=e._ensure_surface_scene(wx,wy)
        targets={(r['x']-wx*80,r['y']-wy*43) for r in p['targets'] if r['kind']=='container'}
        stock=next((xy for xy in targets if any(i.item_id=='watch_lantern' for i in m.container_state[xy]['items'])),None)
        if stock is not None:return dict(shed=p,chunk=[wx,wy],stock=list(stock),destination=[sx,sy],submap_id=sid,candidates=len(ranked))
    raise AssertionError('No bounded selected light-stock route in this seed')


def stage(e,wx,wy,xy):
    prepared=e._ensure_surface_scene(wx,wy)
    SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
    e.local_map,natives=prepared;e.world_x,e.world_y,e.current_submap_id=wx,wy,None
    e.entities=[e.player]+natives;e.player.x,e.player.y=xy
    e.world_map.get(wx,wy).visited=True;e._update_fov();display(e)


def journey(response,out,seed):
    with tempfile.TemporaryDirectory(prefix='sys2-ordinary-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
        e=boot(Path(tmp)/'saves',seed=seed);e.rng=random.Random(20261020);e.ai_system._rng=random.Random(20261020)
        choice=select(e);wx,wy=choice['chunk'];p=choice['shed']
        stage(e,wx,wy,(p['join'][0]%80,p['join'][1]%43))
        s=Journey(e,out);s.receipt.update(seed=seed,setup=__doc__,response=response,selection=choice,initial=status(e))
        try:
            s.stage('selected tool-shed approach');s.use('crude_blade');s.use('leather_jack')
            s.take(tuple(choice['stock']),'watch_lantern');s.stage('acquired native lantern');s.checkpoint('acquired')
            sx,sy=choice['destination'];s.travel(sx,sy)
            sub=next(s for s in e.world_map.get(sx,sy).submaps if s.submap_id==choice['submap_id'])
            s.move([(sub.surface_x,sub.surface_y)])
            s.use('watch_lantern')
            s.key(pygame.K_PERIOD,'>');assert e.current_submap_id==sub.submap_id
            ox,oy=e.player.x-3,e.player.y-12;s.stage('normal selected descent')
            s.move([(ox+4,oy+11)]);s.key(pygame.K_COMMA);assert e.player.inventory.has('faceted_ward')
            if response=='fixed':s.use('faceted_ward')
            else:assert e.player.equipment.slots['offhand'].item_id=='watch_lantern'
            s.stage('held light' if response=='held' else 'fixed pool with ward')
            s.move([(ox+11,oy+12)]);capture(e,out/'approach.png');s.checkpoint('approach')
            # Existing useful grave material, while keeping a viable south exit.
            s.move([(ox+18,oy+12)]);s.move([(ox+18,oy+9)]);s.key(pygame.K_COMMA)
            assert e.player.inventory.has('resonant_bone_fragment');s.stage('recovered grave material')
            s.move([(ox+11,oy+12)])
            if response=='fixed':
                s.approach((ox+12,oy+10));s.interact((ox+12,oy+10));s.close()
                assert e.local_map.decor.get((ox+12,oy+10))=='campfire_unlit'
            else:
                s.use('watch_lantern');assert not e.player.light_source.active
            s.stage('extinguished before retreat');s.checkpoint('changed_place')
            s.move([(ox+3,oy+12)]);s.key(pygame.K_COMMA,'<');assert e.current_submap_id is None
            s.key(pygame.K_PERIOD,'>');assert e.current_submap_id==sub.submap_id
            assert not any(i.item_id in ('faceted_ward','resonant_bone_fragment') for rows in e.local_map.floor_objects.values() for i in rows)
            if response=='fixed':assert e.local_map.decor[(ox+12,oy+10)]=='campfire_unlit'
            s.checkpoint('revisited');s.stage('same selected changed place revisited')
            observed=[r for r in s.receipt['paid'] if any(w['observed'] for w in r['watchers'])]
            assert observed,'No actual direct observation occurred'
            if response=='fixed':assert any(r['offhand']=='faceted_ward' and not any(t['kind']=='held' for t in r['light_sources']) for r in observed)
            s.receipt.update(passed=True,observed_paid_phases=len(observed),final=status(e))
        finally:(out/'journey.json').write_text(json.dumps(s.receipt,indent=2),encoding='utf8')
        return s.receipt


def bandit(out,seed):
    with tempfile.TemporaryDirectory(prefix='sys2-night-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
        e=boot(Path(tmp)/'saves',seed=seed);e.world_time.turn=0
        e.rng=random.Random(20261020);e.ai_system._rng=random.Random(20261020)
        display(e);s=Journey(e,out);s.use('tallow_torch')
        found=None
        candidates=sorted(e.world_map.chunks.items(),key=lambda r:abs(r[0][0]-e.world_map.start_wx)+abs(r[0][1]-e.world_map.start_wy))
        for (wx,wy),chunk in candidates:
            if not any(z=='highstone' for z,_ in chunk.zones):continue
            m,actors=e._ensure_surface_scene(wx,wy)
            for a in actors:
                if getattr(a,'_creature_id','')!='highland_bandit':continue
                for dx,dy in [(6,0),(-6,0),(0,6),(0,-6)]:
                    xy=a.x+dx,a.y+dy
                    if not m.in_bounds(*xy) or not m.walkable[xy] or any((b.x,b.y)==xy for b in actors):continue
                    if scene_light(e,m,fallback_ambient=.02).lit[xy]:continue
                    probe=copy.copy(e.player);probe.x,probe.y=xy
                    if _creature_can_see_player(a,probe,m,1.0):found=(wx,wy,xy,(a.x,a.y));break
                if found:break
            if found:break
        assert found,'No legal ordinary native bandit comparison'
        wx,wy,xy,axy=found;stage(e,wx,wy,xy);a=next(a for a in e.entities if (a.x,a.y)==axy)
        s.receipt.update(seed=seed,setup='Starting torch extinguished by paid inventory action in the lab, then one separately disclosed nighttime placement six tiles from a naturally generated Highland Bandit. Normal paid on/off, native AI and survival.',initial=status(e))
        see=lambda:_creature_can_see_player(a,e.player,e.local_map,engine=e)
        s.receipt['dark_before']=see()
        assert not see()
        s.use('tallow_torch')
        s.receipt['lit_after']=see();assert see();assert a._last_known_px is not None
        s.receipt['remembered_before']=[a._last_known_px,a._last_known_py];s.use('tallow_torch')
        s.receipt['dark_after']=see();assert not see();assert a._last_known_px is not None
        s.receipt['remembered_after']=[a._last_known_px,a._last_known_py];s.checkpoint('night_exposure')
        s.receipt.update(passed=True,final=status(e));(out/'journey.json').write_text(json.dumps(s.receipt,indent=2),encoding='utf8')
        return s.receipt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path);ap.add_argument('--cold',type=Path)
    ap.add_argument('--seed',type=int,default=20261117);ap.add_argument('--only',choices=['held','fixed','bandit','discover']);args=ap.parse_args()
    out=args.evidence.resolve() if args.evidence else None;cold=args.cold.resolve() if args.cold else None
    pygame.init();os.chdir(GAME)
    if cold:
        from g12_journey import install_checkpoint
        from test_effect_persistence import make_engine,load_data
        with tempfile.TemporaryDirectory(prefix='sys2-cold-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)):
            install_checkpoint(cold,tmp);e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
            assert snapshot(e)==json.loads(cold.with_suffix('.json').read_text(encoding='utf8'))
            print(json.dumps(dict(passed=True,pid=os.getpid(),state_equal=True)))
        return
    out.mkdir(parents=True,exist_ok=True)
    if args.only=='discover':
        with tempfile.TemporaryDirectory(prefix='sys2-discover-') as tmp,patch('engine.save_manager.SAVE_DIR',Path(tmp)/'saves'):
            e=boot(Path(tmp)/'saves',seed=args.seed);print(json.dumps(select(e),indent=2))
        return
    rows=[]
    for label in ('held','fixed','bandit'):
        if args.only and args.only!=label:continue
        folder=out/label;folder.mkdir(exist_ok=True)
        rows.append(bandit(folder,args.seed) if label=='bandit' else journey(label,folder,args.seed))
    (out/'play.json').write_text(json.dumps(dict(passed=True,setup=__doc__,journeys=rows),indent=2),encoding='utf8')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
