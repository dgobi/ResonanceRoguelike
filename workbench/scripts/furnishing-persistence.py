"""Bounded natural assignment and separate ordinary-save/catalogue compatibility.

Uses exact UI-published definitions; no furnishing/heat injection. Temporary
assignment membership is confined to disposable fixture data and restored.
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
from engine.scene_generation import create_submap
from generation.world_gen import generate_world
from generation.authored_submap_selection import DEFAULT,RELATIVE
from world.world_map import SubMap,WorldMap
LAYOUT='w5l_furnished_room';OWNED='w5l-ordinary-owned'
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
    m=e.local_map
    return dict(decor=[dict(x=x,y=y,id=d) for (x,y),d in sorted(m.decor.items())],
        floor=[dict(x=x,y=y,items=[serialize_item(i) for i in rows]) for (x,y),rows in sorted(m.floor_objects.items()) if rows],
        containers=[{**r,'x':x,'y':y,'items':[serialize_item(i) for i in r['items']]} for (x,y),r in sorted(m.container_state.items())],
        terrain=hashlib.sha256(m.tiles['terrain'].tobytes()).hexdigest(),
        processing=[dict(x=x,y=y,**r) for (x,y),r in sorted(m.processing_layer.items())])
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y
        e._handle_key_local(next(k for k,d in MOVE_KEYS.items() if d==delta));assert (e.player.x,e.player.y)==xy
def run():
    data=load_data();e=make_engine(data);e.debug=None;e.rng=random.Random(164)
    source=root/f'roguelike/data/layouts/{LAYOUT}.json';source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    if mode=='before':
        profile=Path(data.root)/RELATIVE;original=profile.read_bytes()
        try:
            profile.write_text(json.dumps(dict(DEFAULT,enabled=True,authored_chance=1,candidates=[dict(layout_id=LAYOUT,weight=1)])),encoding='utf-8')
            world=WorldMap(32,32);world.seed=20261028
            generate_world(world,data,random.Random(99),plan_mode='legacy')
            assigned=[(xy,s) for xy,c in sorted(world.chunks.items()) for s in c.submaps if s.layout_id==LAYOUT]
            assert assigned
            (wx,wy),sm=assigned[0]
            result=create_submap(world,wx,wy,sm,data,e.item_factory,e.creature_factory,80,43)
            assert len(result.local_map.decor)==5 # four furnishings plus the real container's decor
            assignment=dict(world_size=[32,32],seed=world.seed,count=len(assigned),selected=dict(wx=wx,wy=wy,submap_id=sm.submap_id,layout_id=sm.layout_id),
                receipts=[r['realized_decor'] for r in result.receipts if r['kind']=='decor'],production_spawn=result.spawn,
                scope='Existing disposable profile → ordinary new-world selection → native create_submap. No ordinary-start expedition or frequency claim.')
        finally:profile.write_bytes(original)
        chunk=e.world_map.get(0,0);sm=SubMap(OWNED,'cave','W5L ordinary compatibility fixture',29417,layout_id=LAYOUT,surface_x=12,surface_y=12);chunk.submaps.append(sm)
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=OWNED
        e._try_descend();assert e.current_submap_id==OWNED
        item=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id=='letter')
        walk(e,(item.x,item.y));e._handle_key_local(pygame.K_COMMA);assert e.player.inventory.contains(item)
        walk(e,(39,22));e._update_fov();e._handle_key(pygame.K_e)
        cursor=e.interaction_cursor
        while (cursor.cursor_x,cursor.cursor_y)!=(39,21):
            e._handle_key(pygame.K_RIGHT if cursor.cursor_x<39 else pygame.K_LEFT if cursor.cursor_x>39 else pygame.K_UP if cursor.cursor_y>21 else pygame.K_DOWN)
        e._handle_key(pygame.K_RETURN);assert e.local_map.decor[39,21]=='campfire_lit'
        assert e.save_manager.save(e),e.save_manager.last_error
        expected=dict(scene=scene(e),inventory=[serialize_item(i) for i in e.player.inventory.items],source_sha256=source_hash,
                      needs=dict(hunger=e.player.needs.hunger,thirst=e.player.needs.thirst),hp=e.player.fighter.hp)
        (out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        return dict(assignment=assignment,**expected)
    expected=json.loads((out/'expected.json').read_bytes())
    assert source_hash!=expected['source_sha256']
    assert e.save_manager.load(e),e.save_manager.last_error
    assert e.current_submap_id==OWNED;assert scene(e)==expected['scene']
    assert [serialize_item(i) for i in e.player.inventory.items]==expected['inventory']
    assert dict(hunger=e.player.needs.hunger,thirst=e.player.needs.thirst)==expected['needs'];assert e.player.fighter.hp==expected['hp']
    assert e.local_map.decor[39,21]=='campfire_lit' and (41,21) not in e.local_map.decor
    assert not any(i.item_id=='letter' for rows in e.local_map.floor_objects.values() for i in rows)
    fresh=create_submap(e.world_map,0,0,SubMap('w5l-new','cave','Pending new fixture',29417,layout_id=LAYOUT),data,e.item_factory,e.creature_factory,80,43)
    assert fresh.local_map.decor[41,21]=='campfire_unlit' and (39,21) not in fresh.local_map.decor
    return dict(source_sha256=source_hash,scene=scene(e),inventory=[serialize_item(i) for i in e.player.inventory.items],
                old_realized_state_exact=True,new_constructed_fire=[41,21,'campfire_unlit'],removed_object_absent=True,
                scope='Fresh catalogue and process, ordinary owned save independent of immutable captures; old map positions, changed fire ID and removed physical object remain authoritative.')
with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/'ordinary/saves'):
    result=run()
result.update(passed=True,pid=os.getpid(),mode=mode,save_access_audit=audit)
(out/(mode+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='save_access_audit'}))
