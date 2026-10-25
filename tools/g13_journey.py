"""One generated shed, using the existing bounded original-loop event driver."""
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
HISTORICAL = ROOT/'evidence/gameplay-g12/final-b/journey/lab/lab-checkpoint.zip'


def historical(out):
    import main
    from test_effect_persistence import load_data, make_engine
    from g12_journey import install_checkpoint, snapshot
    from generation.placement import check_dependencies, digest
    from engine.scene_generation import create_surface
    from g1_support import fingerprint
    from b1_support import Evidence
    with tempfile.TemporaryDirectory(prefix='resonance-g13-historical-') as root, patch('engine.save_manager.SAVE_DIR', Path(root)):
        install_checkpoint(HISTORICAL, root)
        e = make_engine(load_data())
        assert e.save_manager.load(e), e.save_manager.last_error
        expected = json.loads(HISTORICAL.with_suffix('.json').read_text())
        assert snapshot(e) == expected
        plan = digest(e.world_map.plan)
        for p in e.world_map.plan['placements']:
            check_dependencies(p, e.world_map.plan, e.data)
        scene = create_surface(e.world_map, e.world_map.get(75,99), e.data, e.item_factory, e.creature_factory, 80,43)
        pending = fingerprint(scene.local_map, scene.actors)
        assert pending == 'c16c2366f60e69af3ea7040b2b4d30ae19770aa0a1ad03f3d89ce8f332c599fb'
        assert digest(e.world_map.plan) == plan
        assert snapshot(e) == expected
        old = [p for p in e.world_map.plan['placements'] if p['asset']=='tool_shed_a' and p['origin'][0]//80==75 and p['origin'][1]//43==99]
        assert len(old)==1
        ev = Evidence(dict(run_id='g13-historical',scenario='historical',phase='cold',flavor='candidate'))
        ev.bind_sources(ROOT/'roguelike')
        ev.record.update(passed=True,completed=True,archive=str(HISTORICAL.relative_to(ROOT)),
            checkpoint_sha256=hashlib.sha256(HISTORICAL.read_bytes()).hexdigest(),
            state=expected,plan_identity=plan,pending_fingerprint=pending,
            dependency_checks=len(e.world_map.plan['placements']),old_pending_placement=old[0],
            controls='Genuine retained G12 real-event checkpoint in a disposable save root. No historical receipt or scene rewritten. Visited lab restores exactly; pending old shed materializes with its original complete fingerprint.')
        out.write_text(json.dumps(ev.record,indent=2)+'\n')


def contents(e, coordinates):
    from engine.save_components import serialize_item
    return [dict(position=list(xy),decor_id=e.local_map.container_state[xy]['decor_id'],
                 state=e.local_map.container_state[xy]['state'],
                 items=[serialize_item(i) for i in e.local_map.container_state[xy]['items']]) for xy in coordinates]


def shed(e, key, capture, choose, ev, out):
    import pygame
    from engine.save_manager import SceneAddress
    from generation.placement import digest
    from engine.interaction_cursor import InteractionCursor
    from g12_journey import walk_to, interact, select_prompt, inventory, snapshot, archive_checkpoint, verify_cold
    from g10_play import status, KEYS

    # The sole staging operation: actual normally selected production scene and
    # its public road join. Native terrain, contents, actors and player retained.
    p = next(p for p in e.world_map.plan['placements'] if p['asset']=='tool_shed_b'
             and p['origin'][0]//80==75 and p['origin'][1]//43==99)
    prepared = e._ensure_surface_scene(75,99)
    SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
    e.local_map,natives = prepared
    e.world_x,e.world_y,e.current_submap_id = 75,99,None
    e.entities = [e.player]+natives
    e.player.x,e.player.y = p['join'][0]-75*80,p['join'][1]-99*43
    e.world_map.get(75,99).visited=True
    e._update_fov()
    assert not e.player_invincible
    assert (e.player.x,e.player.y) not in {(a.x,a.y) for a in natives}
    positions=[(t['x']-75*80,t['y']-99*43) for t in p['targets'] if t['kind']=='container']
    rack,chest,sack=positions
    bag=next(i for i in e.local_map.container_state[chest]['items'] if i.item_id=='leather_satchel')
    assert sum(i.item_id=='leather_satchel' for xy in positions for i in e.local_map.container_state[xy]['items'])==1
    initial=contents(e,positions)
    ev.record.update(controls='Seed 20261023, ordinary production-selected/materialized tool_shed_b at (75,99). Sole initial staging at its actual public road join; this is a local demonstration, not a normal-start expedition. Starting possessions/HP/needs retained; full-state cardinal route and UI row selection disclosed. Driver fixes gameplay RNG seed 20261020. Native AI, survival, action costs and normal FOV remain active. No reward insertion, threat removal, invincibility or later resets.',
        content_source='roguelike/data/buildings/storage/tool_shed_b.json',placement=copy.deepcopy(p),
        seed=e.world_map.seed,plan_identity=digest(e.world_map.plan),initial_contents=initial,start=status(e))
    yield None
    capture('g13-public-approach-normal-fov')

    def approach(xy):
        yield from walk_to(e,{(xy[0]+dx,xy[1]+dy) for dx,dy in KEYS},key)
        assert InteractionCursor.can_reach(e,*xy)

    # Browse every real storage source through the normal interaction prompt.
    acquired=[]
    for name,xy in (('tool-crate',rack),('provision-barrel',sack),('satchel-crate',chest)):
        yield from approach(xy)
        before=e.world_time.turn
        yield from interact(e,xy,key)
        prompt=e.interaction_cursor._selection_prompt
        assert prompt and prompt['source']=='container'
        assert e.world_time.turn==before
        capture('g13-search-'+name)
        item=bag if xy==chest else prompt['items'][0]
        yield from select_prompt(e,item.item_id,key)
        assert e.player.inventory.contains(item)
        assert all(i is not item for i in e.local_map.container_state[xy]['items'])
        assert e.world_time.turn==before+1
        acquired.append(item)
        if e.mode.value!='local':yield key(pygame.K_ESCAPE)

    inv=e.player.inventory
    before_ids=[id(i) for i in inv.items]
    before_raw=sum(i.weight for i in inv.items)
    before_load=inv.current_weight
    assert bag.weight==0.8
    yield from inventory(e,bag,key,choose)
    assert e.player.equipment.equipped_in('satchel') is bag and bag.equipped
    assert [id(i) for i in inv.items]==before_ids
    assert sum(i.weight for i in inv.items)==before_raw
    assert abs(inv.current_weight-before_load*.9)<1e-9
    ev.record['carrying']=dict(same_inventory=True,raw_kg=before_raw,before_effective_kg=before_load,
        equipped_effective_kg=inv.current_weight,bag_physical_kg=bag.weight,reduction=.10,
        acquired=[i.item_id for i in acquired])
    yield key(pygame.K_i,'i')
    yield from choose(e,bag)
    capture('g13-acquired-satchel-inventory')
    yield key(pygame.K_i,'i')

    public=(p['join'][0]-75*80,p['join'][1]-99*43)
    yield from walk_to(e,[public],key)
    depleted=contents(e,positions)
    assert e.local_map.container_state[chest]['items']==[]
    # Re-enter and search the now empty chest; no second reward can be taken.
    yield from approach(chest)
    yield from interact(e,chest,key)
    assert e.interaction_cursor._selection_prompt is None
    assert contents(e,positions)==depleted
    assert sum(i.item_id=='leather_satchel' for i in e.player.inventory.items)==1
    yield key(pygame.K_ESCAPE)
    capture('g13-revisited-empty-chest')
    yield from walk_to(e,[public],key)
    assert e.player.fighter.hp>0
    capture('g13-exit-normal-fov')
    yield key(pygame.K_F5)
    saved=snapshot(e)
    archive=archive_checkpoint(e,out,'shed-checkpoint')
    verify_cold(archive)
    cold=json.loads(archive.with_suffix('.cold.json').read_text())
    assert cold['pid']!=os.getpid()
    # A real later unsaved ownership/equipment mutation distinguishes F9's
    # restored checkpoint from the subsequent trace.
    yield key(pygame.K_i,'i')
    yield from choose(e,bag)
    yield key(pygame.K_d,'d')
    yield key(pygame.K_i,'i')
    assert not e.player.inventory.contains(bag)
    unsaved=snapshot(e)
    assert unsaved!=saved
    yield key(pygame.K_F9)
    assert snapshot(e)==saved
    assert contents(e,positions)==depleted
    restored=e.player.inventory.get_by_id('leather_satchel')
    assert e.player.equipment.equipped_in('satchel') is restored
    assert restored.equipped
    ev.record.update(depleted_contents=depleted,finish=status(e),
        persistence=dict(f5=True,cold_process_pid=cold['pid'],parent_pid=os.getpid(),f9=True,
                         checkpoint_state=saved,later_unsaved_drop=unsaved,restored_checkpoint_exact=True),
        acquired_once=True,exited_and_revisited=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--historical-output',type=Path)
    args=parser.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    if args.historical_output:
        historical(args.historical_output.resolve())
        return
    from g12_journey import run_stage
    out=args.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    assert not (out/'journey.json').exists(),'Use a fresh evidence directory'
    result=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),
        '--historical-output',str(out/'historical.json')],capture_output=True,text=True,timeout=90)
    (out/'historical-output.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        record=run_stage(out,'shed',shed)
    record['completed']=True
    (out/'shed/result.json').write_text(json.dumps(record,indent=2)+'\n')
    report=dict(passed=True,historical=json.loads((out/'historical.json').read_text()),shed=record)
    (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
