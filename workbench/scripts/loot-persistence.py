"""Ordinary saved container versus fresh catalogue, separate from frozen Test room.

Only scene identities/foyer are staged. Contents are production population from
the exact UI-published definitions, with ordinary movement, transfer and use.
"""
import contextlib, hashlib, io, json, os, sys
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
from engine.engine import MOVE_KEYS,GameMode
from engine.save_components import serialize_item
from engine.player_setup import create_player
from world.world_map import SubMap
LAYOUT='w5o_loot_room';OWNED='w5o-ordinary-owned';PENDING='w5o-ordinary-pending'
audit=[]
def audit_save(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.remove','os.rename','os.rmdir'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        path=Path(os.fsdecode(value)).absolute()
        if 'saves' in path.parts or '.sessions' in path.parts:
            assert path.is_relative_to(out),(event,str(path));audit.append(dict(event=event,path=str(path)))
sys.addaudithook(audit_save)
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y;e._handle_key_local(next(k for k,d in MOVE_KEYS.items() if d==delta));assert (e.player.x,e.player.y)==xy
def state(e):
    return dict(containers=[dict(x=x,y=y,state=c['state'],decor=c['decor_id'],items=[serialize_item(i) for i in c['items']]) for (x,y),c in sorted(e.local_map.container_state.items())],
        inventory=[serialize_item(i) for i in e.player.inventory.items],terrain=hashlib.sha256(e.local_map.tiles['terrain'].tobytes()).hexdigest(),scene=e.current_submap_id,
        ownership=dict(inventory_unique=len({id(i) for i in e.player.inventory.items})==len(e.player.inventory.items),disjoint=not {id(i) for i in e.player.inventory.items}&{id(i) for c in e.local_map.container_state.values() for i in c['items']}))
def browse(e):
    target=next(iter(e.local_map.container_state));walk(e,(target[0],target[1]+1));e._update_fov();e._handle_key(pygame.K_e);assert e.mode==GameMode.INTERACTION_CURSOR
    for _ in range(20):
        x,y=e.interaction_cursor.cursor_x,e.interaction_cursor.cursor_y
        if (x,y)==target:break
        e._handle_key(pygame.K_RIGHT if x<target[0] else pygame.K_LEFT if x>target[0] else pygame.K_DOWN if y<target[1] else pygame.K_UP)
    assert (e.interaction_cursor.cursor_x,e.interaction_cursor.cursor_y)==target
    e._handle_key(pygame.K_RETURN);assert e.interaction_cursor._selection_prompt['source']=='container'
def take(e,identifier):
    browse(e);prompt=e.interaction_cursor._selection_prompt;index=next(i for i,r in enumerate(prompt['items']) if r.item_id==identifier);item=prompt['items'][index]
    for _ in range(index):e._handle_key(pygame.K_DOWN)
    e._handle_key(pygame.K_RETURN);assert e.player.inventory.contains(item);assert not any(i is item for c in e.local_map.container_state.values() for i in c['items']);return item
def use(e,item):
    screen=e.inventory_screen
    for field in ('_font_title','_font_small','_font_normal'):setattr(screen,field,pygame.font.Font(None,18))
    screen._row_height=24;e._handle_key(pygame.K_i);screen._flat=[]
    screen._draw_carried_panel(pygame.Surface((600,900)),e,0,0,600,900,20)
    index=next(i for i,r in enumerate(screen._flat) if r[0] is item)
    while screen.selected!=index:e._handle_key(pygame.K_DOWN if screen.selected<index else pygame.K_UP)
    before=e.world_time.turn;e._handle_key(pygame.K_RETURN);assert e.world_time.turn==before+1;assert not e.player.inventory.contains(item);e._handle_key(pygame.K_ESCAPE)
def stairs(e):
    return next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
def revisit(e):
    walk(e,stairs(e));e._try_ascend();assert e.current_submap_id is None;e._try_descend();assert e.current_submap_id==OWNED
def run():
    data=load_data();e=make_engine(data);e.debug=None
    hashes={name:hashlib.sha256((root/path).read_bytes()).hexdigest() for name,path in dict(pool='roguelike/data/loot_pools/w5o_provisions.json',food='roguelike/data/items/consumables/w5o_biscuit.json',room='roguelike/data/layouts/w5o_loot_room.json').items()}
    if mode=='before':
        profile=create_player(data,e.item_factory,12,12);e.player.inventory=profile.inventory;e.player.equipment=profile.equipment;e.player.inventory.bind_carrying(e.player.equipment,data.items)
        chunk=e.world_map.get(0,0)
        for identifier,x in ((OWNED,12),(PENDING,14)):
            chunk.submaps.append(SubMap(identifier,'cave','W5O ordinary disposable scene',29417,layout_id=LAYOUT,surface_x=x,surface_y=12));e.local_map.set_tile(x,12,'stairs_down',True,True);e.local_map.submap_links[x,12]=identifier
        e._try_descend();assert e.current_submap_id==OWNED
        initial=state(e);assert sorted(i['item_id'] for i in initial['containers'][0]['items'])==sorted(['w5o_biscuit','w5o_biscuit','wood_bundle','tallow_torch'])
        consumed=take(e,'w5o_biscuit');use(e,consumed);acquired=take(e,'w5o_biscuit');copied=serialize_item(acquired)
        expected=state(e);revisit(e);assert state(e)==expected
        pending=next(s for s in e.world_map.get(0,0).submaps if s.submap_id==PENDING);assert not pending.generated;assert e.save_manager.cache.load_submap(PENDING) is None
        assert e.save_manager.save(e),e.save_manager.last_error
        result=dict(hashes=hashes,state=state(e),initial=initial,acquired=copied,consumed=serialize_item(consumed),pending=dict(id=PENDING,layout=pending.layout_id,generated=pending.generated),turn=e.world_time.turn)
        (out/'expected.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
    expected=json.loads((out/'expected.json').read_bytes());assert expected['hashes']['pool']!=hashes['pool'];assert expected['hashes']['food']==hashes['food'];assert expected['hashes']['room']==hashes['room']
    assert e.save_manager.load(e),e.save_manager.last_error
    loaded=state(e);assert loaded==expected['state'];assert len([i for i in e.player.inventory.items if i.item_id=='w5o_biscuit'])==1
    assert next(serialize_item(i) for i in e.player.inventory.items if i.item_id=='w5o_biscuit')==expected['acquired']
    browse(e);e._handle_key(pygame.K_ESCAPE);e._handle_key(pygame.K_ESCAPE);assert state(e)==loaded;revisit(e);assert state(e)==loaded
    pending=next(s for s in e.world_map.get(0,0).submaps if s.submap_id==PENDING);assert not pending.generated;assert e.save_manager.cache.load_submap(PENDING) is None
    walk(e,stairs(e));e._try_ascend();assert e.current_submap_id is None;walk(e,(14,12));e._try_descend();assert e.current_submap_id==PENDING
    fresh=state(e);assert sorted(i['item_id'] for c in fresh['containers'] for i in c['items'])==['animal_bone','tallow_torch'];assert fresh['ownership']['inventory_unique'] and fresh['ownership']['disjoint']
    objects=[i for c in e.local_map.container_state.values() for i in c['items']];assert len({id(i) for i in objects})==2
    return dict(hashes=hashes,loaded=loaded,fresh=fresh,pending_became_generated=pending.generated,conservation=True,no_reroll=True,consumed_absent=True,acquired_copied_fields_retained=True,fresh_objects_distinct=True)
with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/'ordinary/saves'):result=run()
result.update(passed=True,pid=os.getpid(),mode=mode,save_access_audit=audit,scope='Separate process/current catalogue ordinary save. Only known scene identities and foyer staged; exact UI-published source bytes supply production content. Ordinary movement, container input, exact transfer and inventory use. No RNG/object or inventory injection. Process memory IDs are not serialized identities.')
(out/(mode+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='save_access_audit'}))
