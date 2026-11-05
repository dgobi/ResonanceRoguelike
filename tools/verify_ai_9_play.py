"""AI-9 ordinary controls, genuine selected entrances and cold legacy saves.

Player placement at a real newly selected entrance and scripted knowledge of room
geometry are disclosed. No damage, AI decisions, perception or outcomes are set.
"""
import argparse, copy, hashlib, json, os, random, subprocess, sys, tempfile, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools')]
from verify_ai_6_play import setup as base_setup,snapshot,capture,display,Session as BaseSession
import pygame


class Session(BaseSession):
    def key(self,k):
        from engine.venom import fully_paralysed
        physical={pygame.K_UP,pygame.K_DOWN,pygame.K_LEFT,pygame.K_RIGHT,pygame.K_y,pygame.K_u,pygame.K_b,pygame.K_n,pygame.K_e,pygame.K_COMMA}
        if k in physical:
            for _ in range(16):
                if not fully_paralysed(self.e.player):break
                super().key(pygame.K_PERIOD)
            assert not fully_paralysed(self.e.player),'bounded Wait must restore physical agency'
        super().key(k)

    def checkpoint(self,label):
        if self.config['session_id']!='ai9-natural':return super().checkpoint(label)
        before=snapshot(self.e);self.key(pygame.K_F5);self.key(pygame.K_F9)
        assert before==snapshot(self.e),(label,'F5/F9 changed state')
        config=Path(self.config['state_root'])/'cold-config.json';config.write_text(json.dumps(self.config),encoding='utf8')
        child=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/verify_ai_6_play.py'),'--natural-cold',str(config)],capture_output=True,text=True)
        assert child.returncode==0,child.stderr
        assert before==json.loads(child.stdout.splitlines()[-1]),(label,'cold state differed')
        self.persistence.append(dict(label=label,f5_f9_equal=True,cold_equal=True,state=before))

    def move(self,x,y,limit=100):
        from collections import deque
        from engine.spatial import melee_contact
        keys={(0,-1):pygame.K_UP,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(0,1):pygame.K_DOWN,
              (-1,-1):pygame.K_y,(1,-1):pygame.K_u,(-1,1):pygame.K_b,(1,1):pygame.K_n}
        for _ in range(limit):
            e=self.e;start=(e.player.x,e.player.y)
            if start==(x,y):return
            visible=e.normal_player_vision()['visible']
            blocked={(a.x,a.y) for a in e.entities if a is not e.player and getattr(a,'blocks_movement',False) and visible[a.x,a.y]}-{(x,y)}
            q=deque([start]);parents={start:None}
            while q:
                a=q.popleft()
                if a==(x,y):break
                for dx,dy in keys:
                    b=a[0]+dx,a[1]+dy
                    if b not in parents and b not in blocked and melee_contact(e.local_map,*a,*b) and not e._decor_blocks_movement(*b):
                        parents[b]=a;q.append(b)
            assert (x,y) in parents,('no ordinary route',start,(x,y))
            step=(x,y)
            while parents[step]!=start:step=parents[step]
            self.key(keys[step[0]-start[0],step[1]-start[1]])
        raise AssertionError('bounded ordinary route did not finish')


def setup(temp,room,out):
    original=base_setup(temp,room,out)
    s=Session(original.e,original.config,out);s.rows=original.rows
    return s


def legacy(out):
    record=json.loads((ROOT/'evidence/ai-9/legacy-baseline.json').read_bytes())
    rows=[]
    for saved in record['records']:
        archive=ROOT/'evidence/ai-9'/saved['archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest()==saved['sha256']
        with tempfile.TemporaryDirectory(prefix='resonance-ai9-legacy-') as temp:
            with zipfile.ZipFile(archive) as z:z.extractall(temp)
            config=dict(saved['config'],state_root=temp)
            path=Path(temp)/'cold-config.json';path.write_text(json.dumps(config),encoding='utf8')
            child=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/verify_ai_6_play.py'),'--cold',str(path)],capture_output=True,text=True)
            assert child.returncode==0,child.stderr
            actual=json.loads(child.stdout.splitlines()[-1]);assert actual==saved['state'],saved['label']
            rows.append(dict(label=saved['label'],source_revision=saved['source_revision'],sha256=saved['sha256'],cold_equal=True))
    return dict(passed=True,archives=rows)


def encounter_actors(e):
    return [a for a in e.entities if getattr(getattr(a,'ai',None),'maneuver_config',None)]


def residents(e):
    return sorted((a._individual_id,a._creature_id,a.fighter.hp,a.ai.home_x,a.ai.home_y)
                  for a in encounter_actors(e))


def remains(e):
    return sorted((xy,i.source_creature,i.count) for xy,rows in e.local_map.floor_objects.items()
                  for i in rows if i.item_id=='corpse')


def fight(s,limit=70):
    from engine.spatial import melee_attack_legal
    keys={(0,-1):pygame.K_UP,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(0,1):pygame.K_DOWN,
          (-1,-1):pygame.K_y,(1,-1):pygame.K_u,(-1,1):pygame.K_b,(1,1):pygame.K_n}
    for _ in range(limit):
        e=s.e;actors=encounter_actors(e)
        if not actors:return
        visible=[a for a in actors if e.normal_player_vision()['visible'][a.x,a.y]]
        contact=next((a for a in visible if melee_attack_legal(e.local_map,e.player,a)),None)
        if contact:
            dx=(contact.x>e.player.x)-(contact.x<e.player.x);dy=(contact.y>e.player.y)-(contact.y<e.player.y)
            s.key(keys[dx,dy])
        else:s.key(pygame.K_PERIOD)
        for a in encounter_actors(e):
            if a.ai.maneuvers['current']:
                label=a.ai.maneuvers['current']['kind']
                if not any(r['label']==label for r in s.persistence):s.checkpoint(label)


def room_play(out):
    reports=[]
    for room in ('ai9_lateral_lane','ai9_venom_lane','ai9_shadow_lane'):
        with tempfile.TemporaryDirectory(prefix='resonance-ai9-room-') as temp:
            s=setup(temp,room,out)
            s.use('crude_blade');s.use('leather_jack')
            for _ in range(5):
                s.key(pygame.K_PERIOD)
                for a in encounter_actors(s.e):
                    c=a.ai.maneuvers['current']
                    if c and not any(r['label']==c['kind'] for r in s.persistence):s.checkpoint(c['kind'])
            fight(s,25)
            s.checkpoint(room+'_resolved_or_finite_continuation')
            capture(s.e,out/(room+'.png'))
            reports.append(dict(room=room,**s.report()))
    return dict(passed=True,rooms=reports)


def selected_world():
    from engine.data_loader import DataLoader
    from generation.world_gen import generate_world
    from world.world_map import WorldMap
    os.chdir(GAME);data=DataLoader('data');world=WorldMap(128,128);world.seed=20261027
    return data,generate_world(world,data,random.Random(world.seed))


def natural(out):
    from engine.display_config import DisplayConfig
    from engine.creature_factory import CreatureFactory
    from engine.item_factory import ItemFactory
    from engine.player_setup import create_player
    from engine.scene_generation import create_surface,publish_metadata
    from engine.engine import Engine
    from engine.save_manager import SaveManager
    from rendering.tile_registry import TileRegistry
    from config import MAP_WIDTH,MAP_HEIGHT
    data,world=selected_world();reports=[]
    choices={suffix:[(wx,wy,c,s) for (wx,wy),c in world.chunks.items() for s in c.submaps if s.layout_id=='barrow_ward_store_'+suffix] for suffix in 'abcde'}
    assert all(choices.values()),'all five real selection memberships remain available'
    for suffix in 'de':
        chosen=min(choices[suffix],key=lambda r:(abs(r[0]-world.start_wx)+abs(r[1]-world.start_wy),r[0],r[1]))
        for response in ('direct','alternate'):
            # Independent new native world scene per response, from unchanged
            # selector output. This copy is in-memory scenario state, not source.
            scenario_world=copy.deepcopy(world);wx,wy=chosen[:2];chunk=scenario_world.get(wx,wy)
            sub=next(s for s in chunk.submaps if s.submap_id==chosen[3].submap_id)
            items=ItemFactory(data);factory=CreatureFactory(data)
            result=create_surface(scenario_world,chunk,data,items,factory,MAP_WIDTH,MAP_HEIGHT)
            publish_metadata(chunk,result.metadata);chunk.generation_revision=result.local_map.generation_revision;chunk.visited=True
            with tempfile.TemporaryDirectory(prefix='resonance-ai9-natural-') as temp:
                p=create_player(data,items,sub.surface_x,sub.surface_y)
                e=Engine(p,result.local_map,[p]+result.actors,TileRegistry('data/tiles.json',mode='sprite'),scenario_world,wx,wy,data,DisplayConfig.from_config(),save_manager=SaveManager(save_root=Path(temp)/'saves'),debug_mode=False)
                e.rng=random.Random(17);e.ai_system._rng=random.Random(19);display(e)
                config=dict(state_root=temp,seed=world.seed,room_path=f'roguelike/data/layouts/barrow_ward_store_{suffix}.json',session_id='ai9-natural')
                s=Session(e,config,out);s.state('staged_at_real_selected_surface_entrance')
                s.use('tallow_torch');e._try_descend();assert e.current_submap_id==sub.submap_id
                s.state('normal_descent');s.use('crude_blade');s.use('leather_jack')
                actor=encounter_actors(e)[0]
                source=json.loads((GAME/config['room_path'].removeprefix('roguelike/')).read_bytes())
                spawn=next(r for r in source['special_tiles'] if r.get('creature_id')==actor._creature_id)
                ox,oy=actor.ai.home_x-spawn['x'],actor.ai.home_y-spawn['y']
                if response=='direct':
                    if suffix=='e':s.use('tallow_torch')
                    s.move(5+ox,6+oy)
                    fight(s,12 if suffix=='e' else 70)
                    if suffix=='e':s.use('tallow_torch')
                # Both choices can reach the resource through the south/east lane.
                s.move(20+ox,12+oy);s.move(20+ox,4+oy);s.key(pygame.K_COMMA)
                assert e.player.inventory.get_by_id('faceted_ward')
                if suffix=='e' and response=='direct':
                    s.move(18+ox,6+oy);fight(s)
                capture(e,out/(suffix+'-'+response+'.png'))
                before=snapshot(e);s.key(pygame.K_F5);s.key(pygame.K_F9);assert snapshot(e)==before
                cp=Path(temp)/'natural-config.json';cp.write_text(json.dumps(config),encoding='utf8')
                child=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/verify_ai_6_play.py'),'--natural-cold',str(cp)],capture_output=True,text=True)
                assert child.returncode==0,child.stderr
                assert before==json.loads(child.stdout.splitlines()[-1])
                s.move(3+ox,12+oy);living_before=residents(e);remains_before=remains(e)
                e._try_ascend();assert e.current_submap_id is None
                e._try_descend();assert e.current_submap_id==sub.submap_id
                assert residents(e)==living_before,'revisit changed resident identity, injury or original home'
                assert remains(e)==remains_before,'revisit repopulated deaths or lost remains'
                assert e.player.inventory.get_by_id('faceted_ward')
                assert not any(i.item_id=='faceted_ward' for rows in e.local_map.floor_objects.values() for i in rows)
                reports.append(dict(layout=sub.layout_id,response=response,seed=world.seed,chunk=[wx,wy],submap_id=sub.submap_id,
                    selected_counts={k:len(v) for k,v in choices.items()},cold_equal=True,revisit_residents_equal=True,
                    revisit_remains_equal=True,**s.report()))
                (out/'natural-progress.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
    comparisons=[]
    for suffix in 'de':
        direct,alternate=[r for r in reports if r['layout']=='barrow_ward_store_'+suffix]
        reasons=lambda r:sorted({t['reason'] for row in r['rows'] for a in row['tactics']['actors'] for t in a['recent']})
        assert direct['final']['hp']!=alternate['final']['hp'] and reasons(direct)!=reasons(alternate)
        comparisons.append(dict(layout=direct['layout'],direct_hp=direct['final']['hp'],alternate_hp=alternate['final']['hp'],
            direct_actions=reasons(direct),alternate_actions=reasons(alternate)))
    return dict(passed=True,staging=__doc__,encounters=reports,comparisons=comparisons)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--only',choices=['legacy','rooms','natural'])
    args=ap.parse_args();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True);pygame.init()
    report=dict(passed=False,scenarios={})
    for name,fn in [('legacy',legacy),('rooms',room_play),('natural',natural)]:
        if args.only and args.only!=name:continue
        report['scenarios'][name]=fn(out)
        (out/'play.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(name+' passed',flush=True)
    report['passed']=True;(out/'play.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':main()
