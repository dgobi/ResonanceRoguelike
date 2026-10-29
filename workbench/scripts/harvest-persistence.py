"""Separate ordinary old-corpse/current-table proof from exact UI-published sources.

Fixture scene entry and acquisition/use run production routes. The initial ordinary
loadout is the shared player profile. No test-owned equipment or stats are injected.
"""
import contextlib, hashlib, io, json, os, random, sys
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[2]
root,out=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve();mode=sys.argv[3][2:]
assert '.artifacts' in root.parts and '.artifacts' in out.parts and root!=REPO
out.mkdir(parents=True,exist_ok=True)
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1')
sys.path[:0]=[str(root/'roguelike'),str(REPO/'tools/critical_fix_regressions/tests'),str(REPO/'tools')]
import pygame
pygame.init();pygame.display.set_mode((1,1));os.chdir(root/'roguelike')
from test_effect_persistence import make_engine,load_data
from test_generation_ownership import action_path
from engine.engine import MOVE_KEYS
from engine.save_components import serialize_item
from engine.player_setup import create_player
from world.world_map import SubMap
LAYOUT='w5n_harvest_room';OWNED='w5n-ordinary-owned'
audit=[]
def audit_save(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.remove','os.rename','os.rmdir'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        path=Path(os.fsdecode(value)).absolute()
        if 'saves' in path.parts or '.sessions' in path.parts:
            assert path.is_relative_to(out),(event,str(path));audit.append(dict(event=event,path=str(path)))
sys.addaudithook(audit_save)
def scene(e):
    return dict(decor=[dict(x=x,y=y,id=d) for (x,y),d in sorted(e.local_map.decor.items())],
        floor=[dict(x=x,y=y,items=[serialize_item(i) for i in rows]) for (x,y),rows in sorted(e.local_map.floor_objects.items()) if rows],
        terrain=hashlib.sha256(e.local_map.tiles['terrain'].tobytes()).hexdigest())
def slots(e):
    return {slot:next((i for i,owned in enumerate(e.player.inventory.items) if owned is item),None) for slot,item in e.player.equipment.slots.items()}
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y;e._handle_key_local(next(k for k,d in MOVE_KEYS.items() if d==delta));assert (e.player.x,e.player.y)==xy
def equip(e,item):
    # Render the actual carried panel to obtain its normal selected instance.
    screen=e.inventory_screen
    for field in ('_font_title','_font_small','_font_normal'):setattr(screen,field,pygame.font.Font(None,18))
    screen._row_height=24;screen.open=True;screen._flat=[]
    screen._draw_carried_panel(pygame.Surface((600,900)),e,0,0,600,900,20)
    screen.selected=next(i for i,r in enumerate(screen._flat) if r[0] is item)
    before=e.world_time.turn;e._handle_key(pygame.K_RETURN);assert e.world_time.turn==before+1
    e._handle_key(pygame.K_ESCAPE);assert e.player.equipment.is_equipped(item)
def acquire(e,item):
    walk(e,(item.x,item.y));e._handle_key_local(pygame.K_COMMA);assert e.player.inventory.contains(item)
def run():
    data=load_data();e=make_engine(data);e.debug=None
    creature_path=root/'roguelike/data/entities/creatures/w5n_carrier.json'
    tool_path=root/'roguelike/data/items/weapons/w5n_cleaver.json'
    hashes=dict(creature=hashlib.sha256(creature_path.read_bytes()).hexdigest(),tool=hashlib.sha256(tool_path.read_bytes()).hexdigest())
    if mode=='before':
        profile=create_player(data,e.item_factory,12,12)
        e.player.inventory=profile.inventory;e.player.equipment=profile.equipment;e.player.inventory.bind_carrying(e.player.equipment,data.items)
        chunk=e.world_map.get(0,0);chunk.submaps.append(SubMap(OWNED,'cave','W5N ordinary compatibility fixture',29417,layout_id=LAYOUT,surface_x=12,surface_y=12))
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=OWNED;e._try_descend();assert e.current_submap_id==OWNED
        tool=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='w5n_cleaver');acquire(e,tool);equip(e,tool)
        actor=next(a for a in e.entities if getattr(a,'_creature_id',None)=='w5n_carrier')
        # Disclosed headless production death fixture, separate from native
        # ordinary-attack defeat. No corpse/item/equipment is injected.
        e._on_entity_death(actor);e._advance_turn()
        corpse=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.source_creature=='w5n_carrier')
        walk(e,(corpse.x,corpse.y));assert e.save_manager.save(e),e.save_manager.last_error
        expected=dict(scene=scene(e),inventory=[serialize_item(i) for i in e.player.inventory.items],slots=slots(e),hashes=hashes,
            tool_row=next(i for i,it in enumerate(e.player.inventory.items) if it is tool),corpse=serialize_item(corpse),xy=[corpse.x,corpse.y],turn=e.world_time.turn,
            actors=[getattr(a,'_creature_id',None) for a in e.entities if a is not e.player],scene_id=e.current_submap_id)
        assert tool.keywords==[dict(tag='cutting',tier=2)];assert 450<corpse.decay_timer<500
        (out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        return dict(**expected,scope='Ordinary disposable scene entered via production descent; exact UI-published tool acquired/equipped through ordinary input. Production death finalization supplies the unbutchered corpse (disclosed headless fixture). No yield table/item/slot/timer injection; independent of frozen captures.')
    expected=json.loads((out/'expected.json').read_bytes());assert hashes!=expected['hashes']
    assert e.save_manager.load(e),e.save_manager.last_error
    inv=e.player.inventory;assert e.current_submap_id==expected['scene_id'];assert scene(e)==expected['scene'];assert [serialize_item(i) for i in inv.items]==expected['inventory'];assert slots(e)==expected['slots']
    assert [getattr(a,'_creature_id',None) for a in e.entities if a is not e.player]==expected['actors']==[]
    corpse=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.source_creature=='w5n_carrier');assert serialize_item(corpse)==expected['corpse']
    tool=inv.items[expected['tool_row']];assert e.player.equipment.slots['weapon'] is tool;assert tool.keywords==[dict(tag='cutting',tier=2)]
    assert data.items['w5n_cleaver']['keywords']==[dict(tag='cutting',tier=1)];assert e.item_factory.create('w5n_cleaver').keywords==data.items['w5n_cleaver']['keywords']
    before=scene(e);before_turn=e.world_time.turn
    # Ordinary keyboard pickup is the harvest caller. Old copied tier 2 must
    # select revised threshold 2, producing three bones, rather than one.
    e._handle_key_local(pygame.K_COMMA)
    outputs=[i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='animal_bone'];assert len(outputs)==3
    assert not any(i.source_creature=='w5n_carrier' for rows in e.local_map.floor_objects.values() for i in rows)
    assert e.world_time.turn-before_turn==5;assert e._move_debt==0
    assert [serialize_item(i) for i in inv.items]==expected['inventory'];assert slots(e)==expected['slots']
    after=scene(e);assert after['terrain']==before['terrain'];assert after['decor']==before['decor']
    assert not e._interactable_butcher(*expected['xy'],corpse);assert len([i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='animal_bone'])==3
    # A new production finalization uses revised initial decay. It is a fresh
    # Actor fixture, never regeneration of the depleted saved placement.
    fresh=e.creature_factory.spawn('w5n_carrier',e.player.x,e.player.y);e.entities.append(fresh);e._on_entity_death(fresh)
    new_corpse=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.source_creature=='w5n_carrier');assert new_corpse.decay_timer==900
    e._advance_turn();assert new_corpse.decay_timer==899
    return dict(hashes=hashes,loaded_corpse=expected['corpse'],old_tool=serialize_item(tool),current_tool_keywords=data.items['w5n_cleaver']['keywords'],
        elapsed_harvest_turns=e.world_time.turn-before_turn-1,outputs=[serialize_item(i) for i in outputs],scene_before=before,scene_after_harvest=after,
        fresh_corpse=serialize_item(new_corpse),fresh_initial_decay=900,slots=slots(e),conservation=True,no_regenerated_actor=True,no_duplicate_reward=True,
        scope='Separate process/catalogue ordinary save restore. Exact old corpse name/source/timer and old copied tool tier remain; revised table yields three real bones using the owned copied tier. No elapsed turn precedes the old-timer comparison. Harvest costs five turns; fresh death initializes 900 then one ordinary tick gives 899. Unrelated scene/depletion and ownership retained.')
with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/'ordinary/saves'):result=run()
result.update(passed=True,pid=os.getpid(),mode=mode,save_access_audit=audit)
(out/(mode+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='save_access_audit'}))
