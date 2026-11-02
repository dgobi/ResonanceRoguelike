import sys,json
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'roguelike').is_dir())
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'roguelike')]
from verify_ai_8_play import *
def natural_response(out):
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
        # Known-geometry western approach: real senses/actions own the call.
        s.use('crude_blade');s.use('leather_jack')
        s.move(5+ox,10+oy);s.move(5+ox,7+oy)
        for _ in range(3):s.key(pygame.K_PERIOD)
        assert events(e,'emitted') and events(e,'accepted')
        assert any(t['reason']=='alarm_investigating' for a in actors(e) for t in a.ai.trace)
        capture(e,out/'natural-response.png')
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
        s.move(20+ox,4+oy);s.key(pygame.K_COMMA)
        assert e.player.inventory.get_by_id('faceted_ward')
        capture(e,out/'natural-response-aftermath.png')
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

pygame.init()
out=(ROOT/'.baseline/ai-8/natural-response');out.mkdir(parents=True,exist_ok=True)
r=natural_response(out)
(out/'responses.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps({'passed':r['passed'],'seed':r['seed'],'chunk':r['selected_chunk']}))
