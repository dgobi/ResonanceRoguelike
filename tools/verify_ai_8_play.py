"""AI-8 ordinary handlers, disposable saves, disclosed controlled setup/routes.

Controlled comparison removes only the caller component before the first action.
Interrupt fixture stages the player at sight's edge before ordinary inputs.
Natural-world witness stages only at a genuinely selected native entrance.
No combat result, AI phase, signal, target evidence or perception is injected.
"""
import argparse,copy,json,os,random,subprocess,sys,tempfile,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];GAME=ROOT/'roguelike'
sys.path[:0]=[str(GAME),str(ROOT/'tools')]
from verify_ai_6_play import setup,snapshot,capture,display,Session
from engine.enemy_responses import CALL
import pygame


def actors(e):return [a for a in e.entities if getattr(a.ai if hasattr(a,'ai') else None,'response_config',None)]
def events(e,reason):return [(a._creature_id,t) for a in actors(e) for t in a.ai.response_trace if t['reason']==reason]


def controlled(out):
    reports=[]
    for enabled in (False,True):
        with tempfile.TemporaryDirectory(prefix='resonance-ai8-compare-') as temp:
            s=setup(temp,'ai8_alarm_crossing',out);e=s.e;a,b=actors(e)
            if not enabled:a.ai.response_config['modules']=[]
            positions=[]
            for n in range(3):
                s.key(pygame.K_PERIOD);positions.append([[x.x,x.y] for x in actors(e)])
                if enabled and n in (0,1,2):s.checkpoint(('prepared','cooldown','unresolved_report')[n])
            a,b=actors(e)
            if enabled:
                assert a.ai.responses['sequence']==1 and b.ai.responses['recent']
                assert b.ai.target is None and b.ai.responses['interest']
                assert positions[0][0]==positions[1][0] and positions[0][1]==positions[1][1]
                assert positions[2][1]!=positions[1][1]
            else:assert not events(e,'emitted') and not events(e,'accepted')
            # Continue through the physical alternate route to own sight/combat.
            s.use('crude_blade');s.use('leather_jack')
            for _ in range(10):s.key(pygame.K_PERIOD)
            capture(e,out/('enabled.png' if enabled else 'disabled.png'))
            r=s.report();r.update(enabled=enabled,first_three_positions=positions);reports.append(r)
    assert reports[0]['first_three_positions'][2][1]!=reports[1]['first_three_positions'][2][1]
    assert any(a['state']['target'] for row in reports[1]['rows'] for a in row['tactics']['actors'] if a['id']=='barrow_alarm_skirmisher'),'receiver must acquire own sight'
    return dict(passed=True,comparison=reports,setup=__doc__)


def interrupt(out):
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-interrupt-') as temp:
        s=setup(temp,'ai8_alarm_reverse',out);e=s.e;a,b=actors(e)
        e.player.x=a.x-7;e.player.y=a.y;e._update_fov()
        s.state('disclosed_sight_edge_player_setup');s.key(pygame.K_PERIOD)
        assert a.ai.responses['prepared'] is not None
        s.key(pygame.K_LEFT)
        assert a.ai.responses['prepared'] is None and not events(e,'emitted')
        assert b.ai.responses['interest'] is None
        return s.report()


def stale(out):
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-stale-') as temp:
        s=setup(temp,'ai8_alarm_crossing',out);e=s.e
        s.key(pygame.K_PERIOD);s.key(pygame.K_PERIOD)
        a,b=actors(e);origin=copy.deepcopy(b.ai.responses['interest']['incident'])
        ox,oy=a.ai.home_x-9,a.ai.home_y-5
        return_saved=False
        for x,y in ((4,4),(3,3),(2,2),(2,1)):
            s.move(x+ox,y+oy);a,b=actors(e)
            if not return_saved and a.ai.territory['phase'] in ('return','blocked'):
                s.checkpoint('committed_guard_return');return_saved=True
        assert return_saved,'save must witness committed physical return'
        for _ in range(20):s.key(pygame.K_PERIOD)
        a,b=actors(e)
        assert b.ai.responses['interest'] is None
        assert b.ai.target is None,'stale origin cannot reveal hidden player'
        assert any(t['reason'] in ('arrived','exhausted','unreachable','expired') for t in b.ai.response_trace)
        s.checkpoint('stale_site_aftermath')
        # Wait until guard retirement/physical return is observable and saved.
        for _ in range(20):
            if a.ai.territory['phase'] in ('return','blocked'):break
            s.key(pygame.K_PERIOD);a,b=actors(e)
        assert a.ai.territory['phase'] in ('return','blocked','guard')
        s.checkpoint('guard_return_or_completed_return')
        # Disclosed route to actual stair, then normal travel handlers.
        stair=next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
        s.move(*stair);e._try_ascend();assert e.current_submap_id is None
        e._try_descend();assert e.current_submap_id=='room-test-instance'
        assert all(x.ai.responses['interest'] is None for x in actors(e))
        s.checkpoint('scene_revisit_no_report_replay');r=s.report();r['origin']=origin;return r


def reverse(out):
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-reverse-') as temp:
        s=setup(temp,'ai8_alarm_reverse',out);e=s.e
        for _ in range(4):s.key(pygame.K_PERIOD)
        a,b=actors(e);assert events(e,'accepted')
        assert a.ai.profile['recipe']=='strike_and_withdraw' and b.ai.profile['recipe']=='territorial_guard'
        assert b.ai.responses['sequence']==0,'receipt cannot echo on both-module host'
        assert any(t['reason']=='alarm_investigating' for t in b.ai.trace)
        s.checkpoint('portable_guard_response');return s.report()


def natural(out):
    from engine.data_loader import DataLoader
    from engine.display_config import DisplayConfig
    from engine.creature_factory import CreatureFactory
    from engine.item_factory import ItemFactory
    from engine.player_setup import create_player
    from engine.scene_generation import create_surface,publish_metadata
    from engine.engine import Engine
    from engine.save_manager import SaveManager
    from rendering.tile_registry import TileRegistry
    from generation.world_gen import generate_world
    from world.world_map import WorldMap
    from engine import location_reports
    from config import MAP_WIDTH,MAP_HEIGHT
    os.chdir(GAME);data=DataLoader('data');world=WorldMap(128,128);world.seed=20261027
    world=generate_world(world,data,random.Random(world.seed))
    selected=[(wx,wy,c,s) for (wx,wy),c in world.chunks.items() for s in c.submaps if s.layout_id=='barrow_ward_store_c']
    assert selected
    assert all(any(s.layout_id=='barrow_ward_store_'+suffix for c in world.chunks.values() for s in c.submaps) for suffix in ('a','b'))
    wx,wy,chunk,sub=min(selected,key=lambda r:(abs(r[0]-world.start_wx)+abs(r[1]-world.start_wy),r[0],r[1]))
    assert any(r[2]==sub.submap_id and r[3]=='barrow_ward_store_c' for r in location_reports.candidates(world,'ward_store'))
    items=ItemFactory(data);factory=CreatureFactory(data)
    result=create_surface(world,chunk,data,items,factory,MAP_WIDTH,MAP_HEIGHT);publish_metadata(chunk,result.metadata);chunk.generation_revision=result.local_map.generation_revision;chunk.visited=True
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-natural-') as temp:
        p=create_player(data,items,sub.surface_x,sub.surface_y)
        e=Engine(p,result.local_map,[p]+result.actors,TileRegistry('data/tiles.json',mode='sprite'),world,wx,wy,data,DisplayConfig.from_config(),save_manager=SaveManager(save_root=Path(temp)/'saves'),debug_mode=False)
        e.item_system.use(p.inventory.get_by_id('tallow_torch'),e);e._try_descend();assert e.current_submap_id==sub.submap_id
        e.rng=random.Random(17);e.ai_system._rng=random.Random(19);display(e)
        config=dict(state_root=temp,seed=world.seed,room_path='roguelike/data/layouts/barrow_ward_store_c.json',session_id='ai8-natural')
        s=Session(e,config,out);s.state('selected_native_entrance_arrival');a,b=actors(e);ox,oy=a.ai.home_x-9,a.ai.home_y-5
        assert {x._creature_id for x in actors(e)}=={'barrow_alarm_sentinel','barrow_alarm_skirmisher'}
        # Deliberate quiet southern/eastern route to the resource, then approach
        # the western lane to witness a real encounter; no signal is forced.
        s.use('crude_blade');s.use('leather_jack')
        s.move(20+ox,12+oy);s.move(20+ox,4+oy);s.key(pygame.K_COMMA)
        assert e.player.inventory.get_by_id('faceted_ward')
        s.move(20+ox,10+oy);s.move(5+ox,10+oy);s.move(5+ox,6+oy)
        for _ in range(3):s.key(pygame.K_PERIOD)
        assert events(e,'emitted'),'native ordinary encounter must call'
        capture(e,out/'natural-encounter.png')
        from engine.spatial import melee_attack_legal
        keys={(0,-1):pygame.K_UP,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(0,1):pygame.K_DOWN,(-1,-1):pygame.K_y,(1,-1):pygame.K_u,(-1,1):pygame.K_b,(1,1):pygame.K_n}
        for _ in range(60):
            living=actors(e)
            if not living:break
            seen=[a for a in living if e.normal_player_vision()['visible'][a.x,a.y]]
            contact=next((a for a in seen if melee_attack_legal(e.local_map,e.player,a)),None)
            if contact:
                dx=(contact.x>e.player.x)-(contact.x<e.player.x);dy=(contact.y>e.player.y)-(contact.y<e.player.y);s.key(keys[dx,dy])
            elif seen:s.key(pygame.K_PERIOD)
            else:s.move(11+ox,9+oy)
        assert not actors(e),'bounded real confrontation must finish'
        remains=[i for rows in e.local_map.floor_objects.values() for i in rows if getattr(i,'source_creature',None) in ('barrow_alarm_sentinel','barrow_alarm_skirmisher')]
        assert len(remains)==2,'each authored hostile leaves one real remain'
        capture(e,out/'natural-aftermath.png')
        before=snapshot(e);s.key(pygame.K_F5);s.key(pygame.K_F9);assert before==snapshot(e)
        coldpath=Path(temp)/'natural-config.json';coldpath.write_text(json.dumps(config),encoding='utf8')
        child=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'tools/verify_ai_6_play.py'),'--natural-cold',str(coldpath)],capture_output=True,text=True)
        assert child.returncode==0,child.stderr
        assert before==json.loads(child.stdout.splitlines()[-1])
        s.move(3+ox,12+oy);e._try_ascend();assert e.current_submap_id is None
        e._try_descend();assert e.current_submap_id==sub.submap_id
        assert e.player.inventory.get_by_id('faceted_ward')
        assert not any(i.item_id=='faceted_ward' for rows in e.local_map.floor_objects.values() for i in rows)
        assert not actors(e),'dead authored actors must not respawn'
        r=s.report();r.update(seed=world.seed,world_size=[128,128],selected_chunk=[wx,wy],submap_id=sub.submap_id,selected_c_count=len(selected),cold_equal=True,staging='Player staged at the genuine selected surface entrance. Known-geometry route script, fixed RNG 17/19 after entrance. No unaided laboratory journey or balance claim.')
        return r


def legacy(out):
    from room_test import build_engine
    from engine.save_manager import _serialize_entity
    record=json.loads((ROOT/'evidence/ai-8/legacy-v6-snapshot.json').read_text())
    archive=ROOT/'evidence/ai-8/legacy-v6-save.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
    with tempfile.TemporaryDirectory(prefix='resonance-ai8-prechange-v6-') as temp:
        with zipfile.ZipFile(archive) as z:z.extractall(temp)
        config=dict(record['config'],state_root=temp);os.chdir(GAME);e=build_engine(config,load=True);display(e)
        actor=next(a for a in e.entities if getattr(a,'_creature_id','')=='ash_escort')
        assert record['actor']==_serialize_entity(actor)
        assert 'responses' not in actor.ai.snapshot()
        s=Session(e,config,out);s.checkpoint('historical_runtime_v6_escort')
        return dict(passed=True,source_revision=record['source_revision'],capture_kind=record['capture_kind'],archive_sha256=record['archive_sha256'],exact=True,persistence=s.persistence)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--only',choices=['controlled','interrupt','stale','reverse','natural','legacy']);args=ap.parse_args()
    pygame.init();out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,setup=__doc__,scenarios={})
    for name,fn in [('controlled',controlled),('interrupt',interrupt),('stale',stale),('reverse',reverse),('natural',natural),('legacy',legacy)]:
        if args.only and args.only!=name:continue
        report['scenarios'][name]=fn(out)
        (out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(name+' passed',flush=True)
    report['passed']=True;(out/'responses.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':main()
