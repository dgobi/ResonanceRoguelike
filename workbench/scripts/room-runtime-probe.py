"""Controlled normal handlers and genuine cold SaveManager persistence for W5G.

Invoked before and after the native app publishes the same-ID layout revision.
Only disposable artifact project/save roots are admitted. No natural assignment.
"""
import contextlib, hashlib, io, json, os, random, sys
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[2]
root,output=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()
assert '.artifacts' in root.parts and '.artifacts' in output.parts and root!=REPO
output.mkdir(parents=True,exist_ok=True)
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path[:0]=[str(root/'roguelike'),str(REPO/'tools/critical_fix_regressions/tests')]
import pygame
pygame.init();pygame.display.set_mode((1,1));os.chdir(root/'roguelike')
import config
config.DEBUG_MODE=False
from test_effect_persistence import make_engine,load_data
from test_generation_ownership import action_path
from engine.engine import MOVE_KEYS,GameMode
from engine.interaction_cursor import InteractionCursor
from engine.save_components import serialize_item
from engine.save_manager import _serialize_entity
from engine.effect_lifecycle import creature_id
from generation.structure_preview import preview
from generation.context import GenerationError
from world.world_map import SubMap
from components.ai import AIState

LAYOUT='w5g_native_room';OWNED='w5g-owned-instance';UNVISITED='w5g-unvisited-instance'
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None,(target,e.player.x,e.player.y)
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y;key=next(k for k,d in MOVE_KEYS.items() if d==delta)
        if str(e.local_map.tiles[xy]['terrain'])=='door_closed':e._handle_key_local(key)
        e._handle_key_local(key);assert (e.player.x,e.player.y)==xy,(xy,e.player.x,e.player.y)

def geometry(m): return hashlib.sha256(json.dumps([[str(m.tiles[x,y]['terrain']) for x in range(m.width)] for y in range(m.height)]).encode()).hexdigest()
def scene(m,actors,sm):
    return dict(terrain=geometry(m),floor=[dict(x=x,y=y,items=[serialize_item(i) for i in items]) for (x,y),items in sorted(m.floor_objects.items())],
        containers=[dict(x=x,y=y,state=v['state'],decor=v['decor_id'],items=[serialize_item(i) for i in v['items']]) for (x,y),v in sorted(m.container_state.items())],
        actors=[_serialize_entity(a) for a in actors],entry=[sm.entry_x,sm.entry_y],surface=[sm.surface_x,sm.surface_y],generated=sm.generated,
        stairs=[[x,y,str(m.tiles[x,y]['terrain'])] for x in range(m.width) for y in range(m.height) if str(m.tiles[x,y]['terrain']) in ('stairs_up','stairs_down')])

def run():
    data=load_data();e=make_engine(data);e.debug=None;e.rng=random.Random(164)
    layout_path=root/f'roguelike/data/layouts/{LAYOUT}.json';raw=json.loads(layout_path.read_bytes())
    report,_,_=preview(raw,'authored_submap',data,path=str(layout_path),derive_access=True)
    assert report['passed'],report['access']
    if '--before' in sys.argv:
        torch=e.item_factory.create('tallow_torch',12,12);assert e.player.inventory.add(torch)
        e.item_system.use(torch,e);assert e.player.light_source.active and e.player.equipment.equipped_in('offhand') is torch
        chunk=e.world_map.get(0,0)
        for sid,x in [(OWNED,12),(UNVISITED,14)]:
            sm=SubMap(sid,'cave','Controlled W5G instance',29417,layout_id=LAYOUT,surface_x=x,surface_y=12);chunk.submaps.append(sm)
            e.local_map.set_tile(x,12,'stairs_down',True,True);e.local_map.submap_links[x,12]=sid
        e.player.x,e.player.y=12,12;e._try_descend();assert e.current_submap_id==OWNED
        sm=next(s for s in chunk.submaps if s.submap_id==OWNED);assert [e.player.x,e.player.y]==report['spawn']
        letter=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='letter' and i.text_id=='w5g_native_text')
        walk(e,(letter.x,letter.y));e._handle_key_local(pygame.K_COMMA)
        assert any(i is letter for i in e.player.inventory.items);assert not any(i is letter for rows in e.local_map.floor_objects.values() for i in rows)
        e.item_system.use(letter,e);assert e.text_reader.open and e.text_reader._text_id=='w5g_native_text'
        assert e.text_reader._def['pages'][0]['text'].startswith('W5G: the north chest')
        e.display.init();e.text_reader.init(e.display);frame=pygame.Surface((1280,720));e.text_reader.render(frame,e);pygame.image.save(frame,str(output/'actual-room-reader.png'));e.text_reader.open=False
        target=next(r for r in report['access'] if r.get('kind')=='container' and r['source_xy']==[5,4])
        approach=min(target['approaches'],key=lambda xy:abs(xy[0]-e.player.x)+abs(xy[1]-e.player.y));walk(e,approach);e._update_fov();assert InteractionCursor.can_reach(e,*target['xy'])
        container=e.local_map.container_state[tuple(target['xy'])];assert container['items'];loot=container['items'][0]
        e.mode=GameMode.INTERACTION_CURSOR;e.interaction_cursor._cursor_x,e.interaction_cursor._cursor_y=target['xy'];e.interaction_cursor.candidates=[tuple(target['xy'])]
        e._handle_key(pygame.K_RETURN);assert e.interaction_cursor._selection_prompt is not None;e._handle_key(pygame.K_RETURN)
        assert any(i is loot for i in e.player.inventory.items) and not any(i is loot for i in container['items'])
        actor=next(a for a in e.entities if a is not e.player and creature_id(a)=='w5g_native_actor')
        # Controlled adjacency triggers the actual constructed AI through the normal turn.
        neighbours=[(actor.x+dx,actor.y+dy) for dx,dy in MOVE_KEYS.values() if e.local_map.in_bounds(actor.x+dx,actor.y+dy) and e.local_map.walkable[actor.x+dx,actor.y+dy] and not e._decor_blocks_movement(actor.x+dx,actor.y+dy)]
        e.player.x,e.player.y=neighbours[0];e._update_fov();actor.ai.state=AIState.ATTACKING
        from engine.combat import resolve_attack
        with patch('engine.combat.resolve_attack',wraps=resolve_attack) as attack:e._advance_turn()
        assert attack.called;actor.fighter.hp=7;actor.ai.state=AIState.WANDERING
        ox,oy=report['origin'];e.local_map.set_tile(ox+1,oy+1,'ash',True,True)
        stairs=next(s for s in report['stairs'] if s['terrain']=='stairs_up');walk(e,(stairs['x'],stairs['y']))
        actor.ai.state=AIState.WANDERING;e._try_ascend();assert e.current_submap_id is None;assert (e.player.x,e.player.y)==(12,12)
        cached=e.save_manager.cache.load_submap(OWNED)
        from engine.engine import _deserialize_entities_inline
        owned=scene(cached.local_map,_deserialize_entities_inline(cached.entities,e),sm)
        assert e.save_manager.save(e),e.save_manager.last_error
        inventory=[serialize_item(i) for i in e.player.inventory.items]
        expected=dict(scene=owned,inventory=inventory,layout_sha256=hashlib.sha256(layout_path.read_bytes()).hexdigest(),old_origin=report['origin'],old_spawn=report['spawn'])
        (output/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        return dict(passed=True,pid=os.getpid(),layout_sha256=expected['layout_sha256'],saved_generation=e.save_manager.generation,
            authored_start=report['authored_start'],actual_arrival=report['spawn'],carrier_id=letter.item_id,text_id=e.text_reader._text_id,physical_inventory_owner=True,
            container_source=[5,4],container_pools=['storage_tools'],transferred_item_id=loot.item_id,equipped_fixture_light='tallow_torch',ai_class=type(actor.ai).__name__,actor_id=creature_id(actor),actual_ai_attack=True,
            saved_scene=owned,route='normal descent → walk → pickup → inventory/use → actual reader; container interaction/transfer; actual AI turn; normal ascent → SaveManager.save')
    expected=json.loads((output/'expected.json').read_text(encoding='utf-8'));assert hashlib.sha256(layout_path.read_bytes()).hexdigest()!=expected['layout_sha256']
    assert e.save_manager.load(e),e.save_manager.last_error
    assert e.current_submap_id is None
    chunk=e.world_map.get(0,0);sm=next(s for s in chunk.submaps if s.submap_id==OWNED)
    assert sm.generated
    with patch('engine.scene_generation.create_submap',side_effect=AssertionError('owned scene regenerated')):
        e._try_descend();assert e.current_submap_id==OWNED
    restored=scene(e.local_map,[a for a in e.entities if a is not e.player],sm)
    assert restored==expected['scene'],(restored,expected['scene'])
    assert [serialize_item(i) for i in e.player.inventory.items]==expected['inventory']
    assert sum(i.item_id=='letter' and i.text_id=='w5g_native_text' for i in e.player.inventory.items)==1
    assert not any(i.item_id=='letter' and i.text_id=='w5g_native_text' for rows in e.local_map.floor_objects.values() for i in rows)
    # Revisit uses stored entry metadata; walk to the retained physical return.
    old_stair=next(r for r in restored['stairs'] if r[2]=='stairs_up');walk(e,old_stair[:2]);e._try_ascend();assert e.current_submap_id is None
    e.player.x,e.player.y=14,12;e._try_descend();assert e.current_submap_id==UNVISITED
    assert [e.player.x,e.player.y]==report['spawn'] and report['spawn']!=expected['old_spawn']
    assert str(e.local_map.tiles[report['origin'][0]+1,report['origin'][1]+1]['terrain'])=='flagstone'
    assert geometry(e.local_map)!=expected['scene']['terrain']
    assert any(i.item_id=='letter' and i.text_id=='w5g_native_text' for rows in e.local_map.floor_objects.values() for i in rows)
    missing=SubMap('w5g-missing-owned','cave','Missing cache',7,layout_id=LAYOUT,generated=True);chunk.submaps.append(missing)
    with patch('engine.scene_generation.create_submap',side_effect=AssertionError('missing owned scene regenerated')):
        try:e._ensure_submap_scene(0,0,missing.submap_id)
        except GenerationError as error:assert 'generation refused' in str(error)
        else:raise AssertionError('missing-cache refusal lost')
    return dict(passed=True,pid=os.getpid(),layout_sha256=hashlib.sha256(layout_path.read_bytes()).hexdigest(),old_scene_exact=True,inventory_owned_once=True,old_actor_hp=next(a['fighter']['hp'] for a in restored['actors'] if a['id']=='w5g_native_actor'),
        owned_instance=OWNED,new_instance=UNVISITED,new_authored_start=report['authored_start'],new_arrival=report['spawn'],new_geometry_observed=True,new_contents_observed=True,missing_cache_refused=True,
        route='fresh process → DataLoader revised layout only → SaveManager.load → normal revisit without generation → distinct untouched SubMap using same layout ID → missing-cache refusal')

with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',output/'saves'): result=run()
(output/('after.json' if '--after' in sys.argv else 'before.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
