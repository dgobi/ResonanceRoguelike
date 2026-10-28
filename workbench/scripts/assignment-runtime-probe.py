"""Natural production world/entrance in an owned app-local game, no foyer.

Only the ordinary player's initial position is staged outside the real entrance.
The Node driver posts ordinary pygame keys through DiagnosticEvents. Cold checks
separately disclose metadata restoration and lazy pending-scene construction.
"""
import contextlib, hashlib, io, json, os, random, sys
from pathlib import Path
root,output=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve();mode=sys.argv[3]
assert '.artifacts' in root.parts and '.artifacts' in output.parts
output.mkdir(parents=True,exist_ok=True)
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path[:0]=[str(root/'roguelike'),str(Path(__file__).resolve().parents[2]/'tools/critical_fix_regressions/tests')]
os.chdir(root/'roguelike')
import pygame
from config import MAP_WIDTH,MAP_HEIGHT
from main import WORLD_WIDTH,WORLD_HEIGHT
from engine.data_loader import DataLoader
from engine.engine import Engine
from engine.display_config import DisplayConfig
from engine.item_factory import ItemFactory
from engine.creature_factory import CreatureFactory
from engine.player_setup import create_player
from engine.save_manager import SaveManager,_serialize_world
from engine.scene_generation import create_surface,publish_metadata
from generation.world_gen import generate_world
from rendering.tile_registry import TileRegistry
from world.world_map import WorldMap
from world.local_map import LocalMap
from engine.room_test_diagnostics import DiagnosticEvents
from test_generation_ownership import action_path
from room_test import write_json
from engine.save_components import serialize_item

save_root=output/'saves';audit=[]
def audited(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.rename','os.remove','os.rmdir'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        p=Path(os.fsdecode(value)).absolute()
        if 'saves' in p.parts or '.sessions' in p.parts:
            assert p.is_relative_to(save_root),(event,p)
            audit.append(dict(event=event,path=str(p)))
sys.addaudithook(audited)

def scene(m):
    return dict(terrain=hashlib.sha256(json.dumps([[str(m.tiles[x,y]['terrain']) for x in range(m.width)] for y in range(m.height)]).encode()).hexdigest(),
                floor=[dict(x=x,y=y,items=[serialize_item(i) for i in rows]) for (x,y),rows in sorted(m.floor_objects.items())])

def build():
    pygame.init();pygame.display.set_mode((1,1))
    saves=SaveManager(save_root=save_root)
    data=DataLoader(str(root/'roguelike/data'));world=WorldMap(WORLD_WIDTH,WORLD_HEIGHT);world.seed=20261028
    item_factory=ItemFactory(data)
    if mode=='--new':
        assert saves.startup_state()[0]!='load'
        generate_world(world,data,random.Random(world.seed))
        assignments=[(xy,s) for xy,c in sorted(world.chunks.items()) for s in c.submaps]
        authored=[(xy,s) for xy,s in assignments if s.layout_id=='w5i_room_a'];assert len(authored)>1
        (wx,wy),sm=authored[0];pending=authored[1]
        procedural=next((xy,s) for xy,s in assignments if s.submap_type=='barrow' and not s.layout_id)
        chunk=world.get(wx,wy)
        result=create_surface(world,chunk,data,item_factory,CreatureFactory(data),MAP_WIDTH,MAP_HEIGHT);publish_metadata(chunk,result.metadata)
        local=result.local_map;actors=result.actors
        # Choose a reachable point at least six local tiles from the stair. This
        # retains the actual entrance shell, approach, doors, terrain and links.
        candidates=sorted(((x,y) for x in range(1,local.width-1) for y in range(1,local.height-1)
                           if 6<=abs(x-sm.surface_x)+abs(y-sm.surface_y)<=9 and local.walkable[x,y]
                           and (x,y) not in local.decor and not any((a.x,a.y)==(x,y) for a in actors)),key=lambda xy:(abs(xy[0]-sm.surface_x)+abs(xy[1]-sm.surface_y),xy))
        player=create_player(data,item_factory,0,0)
        e=Engine(player,local,[player]+actors,TileRegistry(str(data.root/'tiles.json')),world,wx,wy,data,DisplayConfig.from_config(),save_manager=saves,debug_mode=False,session_label='W5I natural entrance verification')
        start=next(xy for xy in candidates if action_path(e,xy,(sm.surface_x,sm.surface_y)))
        player.x,player.y=start;chunk.visited=True;chunk.generation_revision=local.generation_revision
        state=dict(seed=world.seed,dimensions=[world.width,world.height],plan_mode=world.plan_mode,generation_revision=world.generation_revision,
                   selected=dict(chunk=[wx,wy],submap_id=sm.submap_id,type=sm.submap_type,seed=sm.seed,layout_id=sm.layout_id),
                   pending=dict(chunk=list(pending[0]),submap_id=pending[1].submap_id,layout_id=pending[1].layout_id),
                   procedural=dict(chunk=list(procedural[0]),submap_id=procedural[1].submap_id,layout_id=procedural[1].layout_id),
                   staging=dict(player=list(start),surface_stairs=[sm.surface_x,sm.surface_y],description='Ordinary player staged 6–9 local steps from the genuine production exterior stair. No entrance, destination, SubMap or room replaced.'),
                   source_sha256=hashlib.sha256((data.root/'layouts/w5i_room_a.json').read_bytes()).hexdigest(),
                   profile_sha256=hashlib.sha256((data.root/'generation/authored_submap_selection.json').read_bytes()).hexdigest(),
                   world_sha256=hashlib.sha256(json.dumps(_serialize_world(world),sort_keys=True).encode()).hexdigest(),surface_provenance=getattr(local,'surface_provenance',{}))
        write_json(output/'natural.json',state)
        torch=next(i for i in player.inventory.items if i.item_id=='tallow_torch');e.item_system.use(torch,e)
        return e,state
    state=json.loads((output/'natural.json').read_bytes());player=create_player(data,item_factory,0,0)
    e=Engine(player,LocalMap(MAP_WIDTH,MAP_HEIGHT),[player],TileRegistry(str(data.root/'tiles.json')),world,0,0,data,DisplayConfig.from_config(),save_manager=saves,debug_mode=False)
    assert saves.load(e),saves.last_error
    for key in ('selected','pending','procedural'):
        r=state[key];s=next(s for s in e.world_map.get(*r['chunk']).submaps if s.submap_id==r['submap_id']);assert s.layout_id==r['layout_id']
    if mode=='--unused':
        write_json(output/'unused.json',dict(passed=True,pid=os.getpid(),assignments_retained=True,policy_not_read=True));return None,state
    expected=json.loads((output/'checkpoint.json').read_bytes());owned=state['selected'];pending=state['pending']
    cached=e.save_manager.cache.load_submap(owned['submap_id']);assert cached is not None
    assert scene(cached.local_map)==expected['scene']
    assert [serialize_item(i) for i in e.player.inventory.items]==expected['inventory']
    assert any(i.item_id=='letter' and i.text_id=='w5i_assignment_text' for i in e.player.inventory.items)
    s=next(s for s in e.world_map.get(*pending['chunk']).submaps if s.submap_id==pending['submap_id']);assert not s.generated
    definition=data.layouts.pop(s.layout_id)
    from generation.context import GenerationError
    try:e._ensure_submap_scene(*pending['chunk'],s.submap_id)
    except GenerationError as error:assert 'missing authored layout' in str(error)
    else:raise AssertionError('Missing selected layout substituted procedural content')
    data.layouts[s.layout_id]=definition
    m,_=e._ensure_submap_scene(*pending['chunk'],s.submap_id)
    assert any(i.item_id=='wood_bundle' for rows in m.floor_objects.values() for i in rows)
    assert [s.entry_x,s.entry_y]!=expected['arrival']
    assert not any(i.item_id=='wood_bundle' for rows in cached.local_map.floor_objects.values() for i in rows)
    # Existing owned scene metadata deliberately refuses a lost cache.
    from unittest.mock import patch
    with patch.object(e.save_manager.cache,'load_submap',return_value=None):
        try:e._ensure_submap_scene(*owned['chunk'],owned['submap_id'])
        except GenerationError as error:assert 'generation refused' in str(error)
        else:raise AssertionError('Missing owned cache regenerated')
    write_json(output/'cold.json',dict(passed=True,pid=os.getpid(),assignments_retained=True,procedural_pending_retained=True,
        owned_scene_exact=True,picked_item_owned_once=True,pending_current_definition=True,pending_arrival=[s.entry_x,s.entry_y],
        needed_missing_layout_refused=True,missing_owned_cache_refused=True,definition_sha256=hashlib.sha256((data.root/'layouts/w5i_room_a.json').read_bytes()).hexdigest()))
    return None,state

try:
    with contextlib.redirect_stdout(io.StringIO()): engine,state=build()
    if engine:
        diagnostic=DiagnosticEvents(output)
        def frame(e,screen):
            diagnostic.frame(e,screen)
            write_json(output/'ready.json',dict(pid=os.getpid(),natural=True))
            if e.save_manager.save_path.exists() and not e.current_submap_id:
                cached=e.save_manager.cache.load_submap(state['selected']['submap_id'])
                if cached is not None:
                    sm=next(s for s in e.world_map.get(*state['selected']['chunk']).submaps if s.submap_id==state['selected']['submap_id'])
                    write_json(output/'checkpoint.json',dict(scene=scene(cached.local_map),inventory=[serialize_item(i) for i in e.player.inventory.items],arrival=[sm.entry_x,sm.entry_y]))
        engine.run(on_frame=frame)
finally:
    write_json(output/('audit-'+mode[2:]+'.json'),dict(passed=True,pid=os.getpid(),events=audit))
