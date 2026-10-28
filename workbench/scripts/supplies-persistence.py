"""Ordinary saved acquired UI-authored supplies, fresh process after UI revision.

Separate from immutable W5H captures. Explicit disposable save ownership before
engine initialization; no definition writes and no campaign access.
"""
import contextlib, hashlib, io, json, os, random, sys
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[2]
root,out=Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()
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
from engine.crafting import _item_has_tag,material_candidate
from world.world_map import SubMap

audit=[]
def audit_save(event,args):
    if event not in ('open','os.listdir','os.scandir','os.mkdir','os.remove','os.rename','os.rmdir'):return
    for value in args[:2] if event=='os.rename' else args[:1]:
        if not isinstance(value,(str,bytes,os.PathLike)):continue
        path=Path(os.fsdecode(value)).absolute()
        if 'saves' in path.parts or '.sessions' in path.parts:
            assert path.is_relative_to(out),(event,str(path))
            audit.append(dict(event=event,path=str(path)))
sys.addaudithook(audit_save)

def scene(e):
    return dict(terrain=hashlib.sha256(json.dumps([[str(e.local_map.tiles[x,y]['terrain']) for x in range(e.local_map.width)] for y in range(e.local_map.height)]).encode()).hexdigest(),
        floor=[dict(x=x,y=y,items=[serialize_item(i) for i in rows]) for (x,y),rows in sorted(e.local_map.floor_objects.items())])
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y
        e._handle_key_local(next(k for k,d in MOVE_KEYS.items() if d==delta));assert (e.player.x,e.player.y)==xy

def run():
    data=load_data();e=make_engine(data);e.debug=None;e.rng=random.Random(164)
    files={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'roguelike/data/items').rglob('w5j_*.json')}
    if '--before' in sys.argv:
        chunk=e.world_map.get(0,0);sm=SubMap('w5j-owned-supplies','cave','Compatibility fixture',29417,layout_id='w5j_supplies_room',surface_x=12,surface_y=12);chunk.submaps.append(sm)
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=sm.submap_id
        torch=e.item_factory.create('tallow_torch');assert e.player.inventory.add(torch);e.item_system.use(torch,e)
        e._try_descend();assert e.current_submap_id==sm.submap_id
        for xy,rows in list(e.local_map.floor_objects.items()):
            if not any(i.item_id.startswith('w5j_') for i in rows):continue
            assert len(rows)==1;item=rows[0];walk(e,xy);e._handle_key_local(pygame.K_COMMA);assert e.player.inventory.contains(item)
        owned=[serialize_item(i) for i in e.player.inventory.items]
        material=next(i for i in e.player.inventory.items if i.item_id=='w5j_material')
        assert _item_has_tag(material,'fuel',2);assert not material_candidate(material);assert material_candidate(material,'w5j_material')
        assert len([i for i in owned if i['item_id'].startswith('w5j_')])==8
        expected=dict(inventory=owned,scene=scene(e),source_hashes=files)
        assert e.save_manager.save(e),e.save_manager.last_error
        (out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        return dict(passed=True,pid=os.getpid(),source_hashes=files,save_root=str(e.save_manager.save_path),
            inventory=owned,material=dict(owned=True,fuel_tier=2,automatic=False,explicit=True),scene=expected['scene'],
            scope='Controlled compatibility room entrance; ordinary walk/pickup; production material predicates; ordinary SaveManager.save. UI-authored definitions unchanged.')
    expected=json.loads((out/'expected.json').read_text(encoding='utf-8'));assert files!=expected['source_hashes']
    assert e.save_manager.load(e),e.save_manager.last_error
    assert e.current_submap_id=='w5j-owned-supplies'
    assert [serialize_item(i) for i in e.player.inventory.items]==expected['inventory']
    assert scene(e)==expected['scene']
    assert not any(i.item_id.startswith('w5j_') for rows in e.local_map.floor_objects.values() for i in rows)
    old=next(i for i in e.player.inventory.items if i.item_id=='w5j_drink');sibling=next(i for i in e.player.inventory.items if i.item_id=='w5j_drink' and i is not old)
    assert old.hydration==.25 and old.drink_message=='W5J trail drink restores you.'
    new=e.item_factory.create('w5j_drink');assert new.hydration==.5 and new.drink_message=='W5J revised drink message.'
    old_material=next(i for i in e.player.inventory.items if i.item_id=='w5j_material');assert old_material.weight==.25 and old_material.name=='W5J cordwood'
    e.player.needs.thirst=.8
    screen=e.inventory_screen;screen.open=True;screen._flat=[(old,False,'')];screen.selected=0
    before=e.world_time.turn;needs=e.player.needs.thirst
    with patch.object(e,'_advance_turn',wraps=e._advance_turn) as advance:e._handle_key(pygame.K_RETURN)
    assert advance.call_count==1 and e.world_time.turn==before+1
    assert not e.player.inventory.contains(old) and e.player.inventory.contains(sibling)
    returned=next(i for i in e.player.inventory.items if i.item_id=='w5j_material' and i is not old_material)
    assert returned.name=='W5J revised cordwood' and returned.weight==.4
    assert abs(needs-e.player.needs.thirst-.25)<.005
    assert any('W5J trail drink restores you.' in m.text for m in e.log.messages)
    return dict(passed=True,pid=os.getpid(),source_hashes=files,save_root=str(e.save_manager.save_path),
        stored_inventory_exact=True,removed_objects_stay_removed=True,old_drink=serialize_item(old),new_drink=serialize_item(new),
        return_item=serialize_item(returned),old_material=serialize_item(old_material),sibling_retained=True,
        before_thirst=needs,after_thirst=e.player.needs.thirst,turn_delta=e.world_time.turn-before,action_calls=advance.call_count,
        scope='Fresh process/catalogue; SaveManager.load; exact persisted copied values/ownership; old hydration/message, current empty_form and current newly constructed return.')

with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/'saves'):result=run()
result['save_access_audit']=audit
(out/('before.json' if '--before' in sys.argv else 'after.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='save_access_audit'}))
