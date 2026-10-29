"""Separate-process ordinary saves using accepted UI-authored W5K inputs.

No definition writes. Missing-output fault injection is owned/restored by the
native journey and operates only inside its disposable fixture.
"""
import contextlib, copy, hashlib, io, json, os, random, shutil, sys
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
from world.world_map import SubMap
from generation.decor_utils import place_decor

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
        floor=[dict(x=x,y=y,items=[serialize_item(i) for i in rows]) for (x,y),rows in sorted(e.local_map.floor_objects.items()) if rows],
        processing=[dict(x=x,y=y,**r) for (x,y),r in sorted(e.local_map.processing_layer.items())])
def walk(e,target):
    path=action_path(e,(e.player.x,e.player.y),tuple(target));assert path is not None
    for xy in path[1:]:
        delta=xy[0]-e.player.x,xy[1]-e.player.y
        e._handle_key_local(next(k for k,d in MOVE_KEYS.items() if d==delta));assert (e.player.x,e.player.y)==xy
def craft(e,identifier):
    e._handle_key(pygame.K_c);s=e.craft_screen
    rows=s._build_flat_items(s._get_recipes(e));index=next(n for n,r in enumerate(rows) if r.get('recipe',{}).get('id')==identifier)
    for _ in range(index):e._handle_key(pygame.K_DOWN)
    e._handle_key(pygame.K_RETURN);assert s._choosing
    e._handle_key(pygame.K_RETURN);assert e.mode.name=='PLACEMENT_CURSOR'
    e._handle_key(pygame.K_RETURN);assert not s.open
def floor_outputs(e,identifier):
    return [i for rows in e.local_map.floor_objects.values() for i in rows if i.item_id==identifier]
def load(e):
    assert e.save_manager.load(e),e.save_manager.last_error
    assert e.current_submap_id=='w5k-owned-preparation'
def save(e):assert e.save_manager.save(e),e.save_manager.last_error
def result(e,**values):
    return dict(passed=True,pid=os.getpid(),mode=mode,save_root=str(e.save_manager.save_path),turn=e.world_time.turn,
        inventory=[serialize_item(i) for i in e.player.inventory.items],scene=scene(e),**values)
def run():
    data=load_data();e=make_engine(data);e.debug=None;e.rng=random.Random(164)
    if mode=='before':
        chunk=e.world_map.get(0,0);sm=SubMap('w5k-owned-preparation','cave','Compatibility fixture',29417,layout_id='w5k_preparation_room',surface_x=12,surface_y=12);chunk.submaps.append(sm)
        e.local_map.set_tile(12,12,'stairs_down',True,True);e.local_map.submap_links[12,12]=sm.submap_id
        torch=e.item_factory.create('tallow_torch');assert e.player.inventory.add(torch);e.item_system.use(torch,e)
        e._try_descend();assert e.current_submap_id==sm.submap_id
        for xy,rows in list(e.local_map.floor_objects.items()):
            if not any(i.item_id.startswith('w5k_') for i in rows):continue
            assert len(rows)==1;item=rows[0];walk(e,xy);e._handle_key_local(pygame.K_COMMA);assert e.player.inventory.contains(item)
        walk(e,(39,22));place_decor(e.local_map,39,21,'campfire_lit')
        e.player.needs.hunger=e.player.needs.thirst=.8;e.player.fighter.hp=40
        before=e.world_time.turn;craft(e,'w5k_cook')
        assert e.world_time.turn==before+1;record=e.local_map.processing_layer[(39,21)]
        assert record['turns_remaining']==2 and record['item_id']=='w5k_roast'
        assert record['on_fire'] and record['decor_id']=='' and record['source']=='cooking'
        assert len([i for i in e.player.inventory.items if i.item_id=='w5k_meat'])==1
        assert any(i.item_id=='w5k_pot' for i in e.player.inventory.items)
        expected=dict(job=copy.deepcopy(record),scene=scene(e),inventory=[serialize_item(i) for i in e.player.inventory.items])
        save(e);(out/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')
        # A separate owned save root for missing-definition retention/resumption.
        shutil.copytree(out/'ordinary/saves',out/'fault/saves')
        return result(e,job=record,scope='Ordinary movement/pickup and CraftScreen keys; disclosed production heat/needs fixture; exact commitment; first tick; ordinary save. No immutable capture edited.')
    expected=json.loads((out/'expected.json').read_text(encoding='utf-8'));load(e)
    if mode in ('after','missing'):
        assert scene(e)==expected['scene'];assert [serialize_item(i) for i in e.player.inventory.items]==expected['inventory']
        assert e.local_map.processing_layer[(39,21)]==expected['job']
        assert not any('recipe_id' in r for r in e.local_map.processing_layer.values())
    if mode=='missing':
        assert 'w5k_roast' not in data.items
        for _ in range(4):e._handle_key(pygame.K_z)
        record=e.local_map.processing_layer[(39,21)]
        assert record['turns_remaining']==0 and record['item_id']=='w5k_roast';assert not floor_outputs(e,'w5k_roast')
        assert e.local_map.decor[(39,21)]=='campfire_lit'
        errors=[dict(text=m.text,count=m.count) for m in e.log.messages if 'unfinished work remains' in m.text]
        assert sum(m['count'] for m in errors)==1
        save(e);return result(e,job=record,diagnostics=errors,fault_injection='Output definition temporarily unavailable only in disposable project; queued work retained, not restarted/refunded.')
    if mode=='resume':
        assert e.local_map.processing_layer[(39,21)]['turns_remaining']==0
        e._handle_key(pygame.K_z);assert not e.local_map.processing_layer
        output,=floor_outputs(e,'w5k_roast');assert output.nutrition==.6
        e._handle_key(pygame.K_z);assert len(floor_outputs(e,'w5k_roast'))==1
        return result(e,output=serialize_item(output),scope='Fresh catalogue after restored definition; due zero job completes once through ordinary turn input.')
    if mode=='after':
        revised=data.recipes['w5k_cook'];assert revised['processing_turns']==5 and revised['result_item']=='w5k_dressing'
        old=copy.deepcopy(e.local_map.processing_layer[(39,21)])
        for _ in range(old['turns_remaining']):e._handle_key(pygame.K_z)
        assert not e.local_map.processing_layer;roast,=floor_outputs(e,'w5k_roast');assert roast.nutrition==.6
        assert roast.name=='W5K revised nourishing roast'
        assert any('W5K roast ready:' in m.text for m in e.log.messages)
        e._handle_key(pygame.K_COMMA);e._handle_key(pygame.K_UP);assert e.player.inventory.contains(roast)
        # Save the acquired output before revising its definition again. New
        # work uses revised recipe parameters in this fresh catalogue.
        craft(e,'w5k_cook');new=e.local_map.processing_layer[(39,21)]
        assert new['turns_remaining']==4 and new['item_id']=='w5k_dressing'
        assert new['completion_message']=='W5K revised work ready: {item_name}.'
        assert not any(i.item_id=='w5k_meat' for i in e.player.inventory.items)
        save(e);return result(e,old_job=old,old_output=serialize_item(roast),new_job=new,scope='Different PID, fresh catalogue; old job retains captured parameters, output uses revised stored target definition; later work uses revised recipe.')
    assert mode=='final'
    roast=next(i for i in e.player.inventory.items if i.item_id=='w5k_roast');assert roast.nutrition==.6
    assert e.item_factory.create('w5k_roast').nutrition==.8
    assert not any(i.item_id=='w5k_meat' for i in e.player.inventory.items)
    for _ in range(4):e._handle_key(pygame.K_z)
    dressing,=floor_outputs(e,'w5k_dressing');assert dressing.heal_amount==9
    e._handle_key(pygame.K_COMMA);e._handle_key(pygame.K_UP);assert e.player.inventory.contains(dressing)
    screen=e.inventory_screen;screen.open=True;screen._flat=[(dressing,False,'')];screen.selected=0
    hp=e.player.fighter.hp;turn=e.world_time.turn;e._handle_key(pygame.K_RETURN)
    assert e.player.fighter.hp==hp+9 and e.world_time.turn==turn+1
    assert not e.player.inventory.contains(dressing);screen.open=False
    save(e);saved_scene=scene(e);saved_inventory=[serialize_item(i) for i in e.player.inventory.items]
    load(e);e._handle_key(pygame.K_z)
    assert not e.local_map.processing_layer and not floor_outputs(e,'w5k_dressing') and not floor_outputs(e,'w5k_roast')
    assert scene(e)==saved_scene;assert [serialize_item(i) for i in e.player.inventory.items]==saved_inventory
    return result(e,stored_output=serialize_item(roast),current_factory=serialize_item(e.item_factory.create('w5k_roast')),
        treatment_hp_delta=9,treatment_turn_delta=1,no_duplicate_after_load=True,removed_material_stays_removed=True,
        scope='Fresh process preserves acquired copied values after same-ID definition revision; finishes revised job, ordinary inventory treatment handler, save/load has no duplicate output or respawned material.')

save_group='fault' if mode in ('missing','resume') else 'ordinary'
with contextlib.redirect_stdout(io.StringIO()),patch('engine.save_manager.SAVE_DIR',out/save_group/'saves'):observed=run()
observed['save_access_audit']=audit
(out/(mode+'.json')).write_text(json.dumps(observed,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in observed.items() if k!='save_access_audit'}))
