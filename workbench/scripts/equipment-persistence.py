"""Separate ordinary-save/fresh-catalogue proof using exact UI-published equipment.

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
LAYOUT='w5m_equipment_room';OWNED='w5m-ordinary-owned'
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
    data=load_data();e=make_engine(data);e.debug=None;e.rng=random.Random(164)
    bag_path=root/'roguelike/data/items/equipment/satchel/w5m_satchel.json';source_hash=hashlib.sha256(bag_path.read_bytes()).hexdigest()
    if mode=='before':
        # Disclosed ordinary starting profile, before any authored-room acquisition.
        profile=create_player(data,e.item_factory,12,12)
        e.player.inventory=profile.inventory;e.player.equipment=profile.equipment;e.player.inventory.bind_carrying(e.player.equipment,data.items)
        chunk=e.world_map.get(0,0);chunk.submaps.append(SubMap(OWNED,'cave','W5M ordinary compatibility fixture',29417,layout_id=LAYOUT,surface_x=12,surface_y=12))
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=OWNED;e._try_descend();assert e.current_submap_id==OWNED
        kit={}
        for iid in ('w5m_blade','w5m_jack','w5m_satchel','w5m_ward'):
            item=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id==iid);acquire(e,item);equip(e,item);kit[iid]=item
        sibling=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='w5m_ward');acquire(e,sibling)
        for item in [i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='wood_bundle'][:13]:acquire(e,item)
        inv=e.player.inventory;assert sum(i.weight for i in inv.items)>inv.capacity;assert inv.current_weight<inv.capacity
        assert e.save_manager.save(e),e.save_manager.last_error
        expected=dict(scene=scene(e),inventory=[serialize_item(i) for i in inv.items],slots=slots(e),source_sha256=source_hash,effective_av=e.player.fighter.effective_av,
            weight=inv.current_weight,base_weight=sum(i.weight for i in inv.items),capacity=inv.capacity,kit_rows={k:next(n for n,i in enumerate(inv.items) if i is item) for k,item in kit.items()})
        (out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        return dict(**expected,scope='Exact UI-published definitions; ordinary shared starting profile, physical production descent, keyboard movement/pickup and inventory use. No equipment injection or encounter setup.')
    expected=json.loads((out/'expected.json').read_bytes());assert source_hash!=expected['source_sha256']
    assert e.save_manager.load(e),e.save_manager.last_error
    inv=e.player.inventory
    assert e.current_submap_id==OWNED;assert scene(e)==expected['scene'];assert [serialize_item(i) for i in inv.items]==expected['inventory'];assert slots(e)==expected['slots']
    for slot,index in slots(e).items():
        if index is not None:assert e.player.equipment.equipped_in(slot) is inv.items[index]
    assert e.player.fighter.effective_av==expected['effective_av']==5
    bag=inv.items[expected['kit_rows']['w5m_satchel']];assert bag.name=='W5M expedition satchel'
    assert inv.reductions_for()=={'all':.05,'Components':0};assert inv.current_weight>inv.capacity
    assert sum(i.weight for i in inv.items)==expected['base_weight'];assert inv.current_weight>expected['weight']
    remaining=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='wood_bundle')
    before=[serialize_item(i) for i in inv.items];floor=scene(e);walk(e,(remaining.x,remaining.y));e._handle_key_local(pygame.K_COMMA)
    assert not inv.contains(remaining);assert [serialize_item(i) for i in inv.items]==before;assert scene(e)==floor
    assert any('Too much to carry' in m.text for m in e.log.messages)
    fresh=e.item_factory.create('w5m_satchel');assert fresh.name=='W5M revised expedition satchel';assert fresh.weight==bag.weight
    assert e._get_equipped_weapon() is data.items['w5m_blade']
    assert e.save_manager.save(e),e.save_manager.last_error
    return dict(source_sha256=source_hash,scene=scene(e),inventory=[serialize_item(i) for i in inv.items],slots=slots(e),effective_av=e.player.fighter.effective_av,
        old_copied_name=bag.name,fresh_name=fresh.name,base_weight=sum(i.weight for i in inv.items),weight=inv.current_weight,capacity=inv.capacity,reductions=inv.reductions_for(),
        conservation=True,pickup_refused=True,current_weapon=data.items['w5m_blade'],
        scope='New process and catalogue, ordinary save independent of captures. Copied fields/slot row identities and depleted generated room retained; current bag reductions adopted even when over capacity. Fresh construction uses revised copied name.')
with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/'ordinary/saves'):result=run()
result.update(passed=True,pid=os.getpid(),mode=mode,save_access_audit=audit)
(out/(mode+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='save_access_audit'}))
