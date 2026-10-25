"""Bounded G14 crate-to-fire trace on the existing original-loop event driver."""
import argparse
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT/'evidence/gameplay-g13/final-d/journey/shed/shed-checkpoint.zip'


def historical(out):
    from test_effect_persistence import load_data, make_engine
    from g12_journey import install_checkpoint, snapshot
    from generation.placement import check_dependencies, digest
    with tempfile.TemporaryDirectory(prefix='resonance-g14-historical-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
        install_checkpoint(HISTORICAL, root)
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
        expected = json.loads(HISTORICAL.with_suffix('.json').read_text())
        assert snapshot(e) == expected
        plan = digest(e.world_map.plan)
        for p in e.world_map.plan['placements']:
            check_dependencies(p, e.world_map.plan, e.data)
        p = next(p for p in e.world_map.plan['placements'] if p['asset']=='tool_shed_b'
                 and p['origin'][0]//80==75 and p['origin'][1]//43==99)
        crates = [(t['x']%80,t['y']%43) for t in p['targets'] if t['kind']=='container'
                  and e.local_map.container_state[(t['x']%80,t['y']%43)]['decor_id']=='crate']
        empty = next(xy for xy in crates if not e.local_map.container_state[xy]['items'])
        assert e.local_map.decor[empty] == 'crate'
        assert e.local_map.container_state[empty]['state'] == 'looted'
        assert not e.local_map.floor_objects.get(empty)
        assert digest(e.world_map.plan) == plan and snapshot(e) == expected
        out.write_text(json.dumps(dict(passed=True,pid=os.getpid(),
            checkpoint=str(HISTORICAL.relative_to(ROOT)),sha256=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),
            restored_exactly=True,state=expected,empty_crate=list(empty),crate_still_present=True,
            dependency_checks=len(e.world_map.plan['placements']),plan_identity=plan,
            controls='Genuine committed pre-edit G13 visited shed loaded in a separate process/disposable save root. No actions or reinterpretation; original empty crate, floor contents, plan and dependencies preserved.'),indent=2)+'\n')


def shed(e, key, capture, choose, ev, out):
    import pygame
    from engine.save_manager import SceneAddress
    from engine.interaction_cursor import InteractionCursor
    from generation.placement import digest, transform
    from g12_journey import walk_to, interact, select_prompt, inventory, recipe, snapshot, archive_checkpoint, verify_cold
    from g10_play import status, KEYS
    from engine.save_components import serialize_item
    from g13_journey import contents

    p = next(p for p in e.world_map.plan['placements'] if p['asset']=='tool_shed_b'
             and p['origin'][0]//80==75 and p['origin'][1]//43==99)
    prepared = e._ensure_surface_scene(75,99)
    SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
    e.local_map,natives = prepared
    e.world_x,e.world_y,e.current_submap_id = 75,99,None
    e.entities = [e.player]+natives
    e.player.x,e.player.y = p['join'][0]-75*80,p['join'][1]-99*43
    e.world_map.get(75,99).visited = True
    e._update_fov()
    assert not e.player_invincible
    assert (e.player.x,e.player.y) not in {(a.x,a.y) for a in natives}
    positions = [(t['x']%80,t['y']%43) for t in p['targets'] if t['kind']=='container']
    bag_crate = next(xy for xy in positions if any(i.item_id=='leather_satchel'
                     for i in e.local_map.container_state[xy]['items']))
    raw = transform(e.data.structures[p['asset']],p['rotation'],p['mirror'])
    native_wood_xy, = [((p['origin'][0]+t['x'])%80,(p['origin'][1]+t['y'])%43)
                       for t in raw['special_tiles'] if t.get('item_id')=='wood_bundle']
    native_wood, = [i for i in e.local_map.floor_objects[native_wood_xy] if i.item_id=='wood_bundle']
    inv = e.player.inventory
    blade = inv.get_by_id('crude_blade'); torch = inv.get_by_id('tallow_torch')
    assert blade and torch and not inv.has('wood_bundle')
    bag, = [i for i in e.local_map.container_state[bag_crate]['items'] if i.item_id=='leather_satchel']
    initial = contents(e,positions)
    ev.record.update(controls='Local interaction/process demonstration, not a normal-start expedition. Seed 20261023; sole initial staging at the normally selected G13 shed public approach. Starting possessions/HP/needs retained; full-state cardinal route and UI-row selection. Existing driver fixes gameplay RNGs to 20261020. Normal FOV, native AI, survival and action costs; no fuel/reward insertion, cleared threats, invincibility or later resets. F9 at end deliberately restores the earlier dismantling checkpoint, before unsaved pickup/fire creation.',
        seed=e.world_map.seed,content_source='roguelike/data/buildings/storage/tool_shed_b.json',
        placement=copy.deepcopy(p),plan_identity=digest(e.world_map.plan),start=status(e),
        initial_contents=initial,native_floor_wood=dict(position=list(native_wood_xy),item=serialize_item(native_wood)))
    yield None

    def approach(xy):
        yield from walk_to(e,{(xy[0]+dx,xy[1]+dy) for dx,dy in KEYS},key)
        assert InteractionCursor.can_reach(e,*xy)

    yield from approach(bag_crate)
    yield from interact(e,bag_crate,key)
    assert e.interaction_cursor._selection_prompt['source']=='container'
    yield from select_prompt(e,'leather_satchel',key)
    assert inv.contains(bag) and not e.local_map.container_state[bag_crate]['items']
    assert e.local_map.decor[bag_crate]=='crate'
    if not blade.equipped:
        yield from inventory(e,blade,key,choose)
    assert inv.contains(blade) and e.player.equipment.equipped_in('weapon') is blade
    yield from interact(e,bag_crate,key)
    assert e.interaction_cursor._selection_prompt is None
    capture('g14-empty-crate-offer')
    before = e.world_time.turn
    assert e._move_debt < 1
    yield key(pygame.K_x,'x')
    assert e.interaction_cursor._dismantle_prompt
    assert e.world_time.turn==before
    capture('g14-dismantle-confirmation')
    # The production prompt at a constrained display, without changing game state.
    small = pygame.Surface((480,320))
    e.interaction_cursor._render_dismantle_prompt(small,e,small.get_rect())
    pygame.image.save(small,str(out/'g14-confirmation-480x320.png'))
    yield key(pygame.K_RETURN,'\r')
    assert e.world_time.turn==before+1
    assert bag_crate not in e.local_map.decor and bag_crate not in e.local_map.container_state
    wood, = e.local_map.floor_objects[bag_crate]
    assert wood.item_id=='wood_bundle' and wood.count==1
    assert not inv.contains(wood) and inv.contains(blade) and inv.contains(torch) and inv.contains(bag)
    assert digest(e.world_map.plan)==ev.record['plan_identity']
    ev.record['conversion'] = dict(position=list(bag_crate),turn_before=before,turn_after=e.world_time.turn,
        output=serialize_item(wood),source_removed=True,output_on_floor=True,tool_retained=True)
    capture('g14-one-floor-wood-crate-removed')
    yield key(pygame.K_F5)
    saved = snapshot(e)
    archive = archive_checkpoint(e,out,'dismantled-checkpoint')
    verify_cold(archive)
    cold = json.loads(archive.with_suffix('.cold.json').read_text())
    assert cold['pid']!=os.getpid()

    yield from interact(e,bag_crate,key)
    assert inv.contains(wood) and bag_crate not in e.local_map.floor_objects
    yield from approach(native_wood_xy)
    yield from interact(e,native_wood_xy,key)
    assert inv.contains(native_wood) and native_wood_xy not in e.local_map.floor_objects
    assert sum(i.item_id=='wood_bundle' for i in inv.items)==2
    yield from recipe(e,'campfire',key)
    assert e.mode.value=='placement_cursor'
    fire = (e._placement_cursor_x,e._placement_cursor_y)
    before_place = e.world_time.turn
    yield key(pygame.K_RETURN,'\r')
    assert e.mode.value=='local' and e.local_map.decor[fire]=='campfire_unlit'
    assert e.world_time.turn==before_place+1
    assert not inv.contains(wood) and not inv.contains(native_wood)
    assert inv.contains(blade) and inv.contains(torch) and inv.contains(bag)
    assert e.player.equipment.equipped_in('weapon') is blade
    before_ignite = e.world_time.turn
    yield from interact(e,fire,key)
    assert e.local_map.decor[fire]=='campfire_lit'
    assert e.world_time.turn==before_ignite+1
    assert not e.player_invincible and e.player.fighter.hp>0
    capture('g14-paid-working-fire-normal-fov')
    unsaved = snapshot(e)
    ev.record['campfire'] = dict(position=list(fire),two_exact_wood_instances_spent=True,
        tool_and_torch_retained=True,bag_retained=True,placement_turns=1,ignition_turns=1,
        lit=True,status=status(e),unsaved_state=unsaved)
    assert unsaved!=saved
    yield key(pygame.K_F9)
    assert snapshot(e)==saved
    assert bag_crate not in e.local_map.decor and bag_crate not in e.local_map.container_state
    assert [i.item_id for i in e.local_map.floor_objects[bag_crate]]==['wood_bundle']
    assert e.local_map.decor.get(fire)!='campfire_lit'
    ev.record.update(persistence=dict(f5=True,cold_process_pid=cold['pid'],parent_pid=os.getpid(),
        f9=True,checkpoint_state=saved,later_unsaved_fire=unsaved,restored_checkpoint_exact=True),finish=status(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--historical-output',type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE = False
    if args.historical_output:
        historical(args.historical_output.resolve())
        return
    from g12_journey import run_stage
    out = args.evidence.resolve(); out.mkdir(parents=True,exist_ok=True)
    assert not (out/'journey.json').exists(), 'Use a fresh evidence directory'
    result = subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),
        '--historical-output',str(out/'historical.json')],capture_output=True,text=True,timeout=90)
    (out/'historical-output.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        record = run_stage(out,'shed',shed)
    record['completed'] = True
    (out/'shed/result.json').write_text(json.dumps(record,indent=2)+'\n')
    report = dict(passed=True,historical=json.loads((out/'historical.json').read_text()),shed=record)
    (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__': main()
