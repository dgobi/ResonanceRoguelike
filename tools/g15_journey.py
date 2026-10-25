"""One native treatment, acquired then used in a genuinely cold game process."""
import argparse
import contextlib
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def walk_to(e,goals,key):
    import pygame
    from g12_journey import walk_to as established_walk
    # The inherited layout's entrance needs ordinary diagonal movement. Extend
    # the existing driver's path/key table to the game's shipped keypad controls.
    diagonal={(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3}
    with patch.dict('g10_play.KEYS',diagonal):
        yield from established_walk(e,goals,key)


def source(e):
    p=next(p for p in e.world_map.plan['placements'] if p['asset']=='apothecary_b'
           and (p['origin'][0]//80,p['origin'][1]//43)==(75,100))
    xy=next((t['x']%80,t['y']%43) for t in p['targets'] if t['kind']=='container'
            and e.local_map.container_state[t['x']%80,t['y']%43]['decor_id']=='medicine_chest')
    return p,xy


def approach(e,xy,key):
    from g10_play import KEYS
    from engine.interaction_cursor import InteractionCursor
    yield from walk_to(e,{(xy[0]+dx,xy[1]+dy) for dx,dy in KEYS},key)
    assert InteractionCursor.can_reach(e,*xy)


def close_interaction(e,key):
    import pygame
    if e.interaction_cursor._selection_prompt:yield key(pygame.K_ESCAPE)
    if e.mode.value!='local':yield key(pygame.K_ESCAPE)


def unsaved_step(e,key):
    from g10_play import KEYS
    from generation.access import enterable
    occupied={(a.x,a.y) for a in e.entities if a is not e.player and a.blocks_movement}
    before=(e.player.x,e.player.y)
    for dx,dy in KEYS:
        xy=before[0]+dx,before[1]+dy
        if e.local_map.in_bounds(*xy) and e.local_map.walkable[xy] and xy not in occupied and enterable(e.local_map,xy,e.data):
            yield key(KEYS[dx,dy])
            assert (e.player.x,e.player.y)!=before
            return
    raise AssertionError('No legal ordinary unsaved step')


def acquisition(e,key,capture,choose,ev,out):
    import pygame
    from engine.save_manager import SceneAddress
    from engine.save_components import serialize_item
    from generation.placement import digest
    from g12_journey import interact,select_prompt,snapshot,archive_checkpoint
    from g10_play import status
    # Sole staging: native complete scene at the normally selected public join.
    p=next(p for p in e.world_map.plan['placements'] if p['asset']=='apothecary_b'
           and (p['origin'][0]//80,p['origin'][1]//43)==(75,100))
    prepared=e._ensure_surface_scene(75,100)
    SceneAddress(e.world_x,e.world_y,e.current_submap_id).store(e.save_manager.cache,e.local_map,e.entities)
    e.local_map,natives=prepared;e.world_x,e.world_y,e.current_submap_id=75,100,None;e.entities=[e.player]+natives
    public=(p['join'][0]%80,p['join'][1]%43)
    e.player.x,e.player.y=public;e.world_map.get(75,100).visited=True
    # One disclosed injury before any ordinary acquisition actions.
    initial_hp=e.player.fighter.hp
    injury=e.player.fighter.take_damage(24)
    e._update_fov()
    assert not e.player_invincible and public not in {(a.x,a.y) for a in natives}
    p,xy=source(e);chest=e.local_map.container_state[xy]
    dose,=[i for i in chest['items'] if i.item_id=='herbal_dressing']
    ev.record.update(controls='Local acquisition/use/persistence demonstration; not normal-start discovery, recovery balance, two expeditions or H1 completion. Seed 20261023; one initial staging at the genuine selected public approach, one setup injury of 24 HP before inputs. Full-state eight-way routing/UI selection; established driver RNG seed 20261020. Normal FOV, native AI, effects, survival and action costs. No treatment insertion, threat removal, invincibility, supply reset, or later repositioning.',
        seed=e.world_map.seed,placement=copy.deepcopy(p),plan_identity=digest(e.world_map.plan),
        source_position=xy,native_chest_before=[serialize_item(i) for i in chest['items']],
        setup_injury=dict(before=initial_hp,damage=injury,after=e.player.fighter.hp),start=status(e))
    yield None
    yield from approach(e,xy,key)
    before=e.world_time.turn
    yield from interact(e,xy,key)
    assert e.interaction_cursor._selection_prompt['source']=='container' and e.world_time.turn==before
    capture('g15-native-medicine-chest')
    yield from select_prompt(e,'herbal_dressing',key)
    assert e.player.inventory.contains(dose) and all(i is not dose for i in chest['items'])
    yield from close_interaction(e,key)
    capture('g15-acquired-normal-fov')
    yield key(pygame.K_i,'i');yield from choose(e,dose)
    assert 'up to 12 HP' in dose.description and 'one use' in dose.description
    capture('g15-readable-treatment-detail')
    yield key(pygame.K_i,'i')
    # A second real search has no replacement dose; other native reagents remain.
    yield from interact(e,xy,key)
    assert not any(i.item_id=='herbal_dressing' for i in chest['items'])
    yield from close_interaction(e,key)
    yield key(pygame.K_F5)
    saved=snapshot(e);archive=archive_checkpoint(e,out,'acquired-unused')
    yield from unsaved_step(e,key)
    unsaved=snapshot(e);assert unsaved!=saved
    yield key(pygame.K_F9)
    assert snapshot(e)==saved
    ev.record.update(checkpoint=str(archive),saved_snapshot=saved,unsaved_movement_snapshot=unsaved,
        f9_restored_identified_acquired_snapshot=True,finish=status(e),parent_pid=os.getpid())


def consume(e,key,capture,choose,ev,out):
    import pygame
    from engine.save_components import serialize_item
    from g12_journey import inventory,interact,snapshot,archive_checkpoint,verify_cold
    from g10_play import status
    p,xy=source(e);dose=e.player.inventory.get_by_id('herbal_dressing')
    assert dose and not any(i.item_id=='herbal_dressing' for i in e.local_map.container_state[xy]['items'])
    ev.record.update(cold_pid=os.getpid(),start_snapshot=snapshot(e),start=status(e),selected_dose=serialize_item(dose))
    possessions=[i for i in e.player.inventory.items if i is not dose]
    equipped=dict(e.player.equipment.slots)
    yield None
    before=e.world_time.turn
    boundary={};heal=e.player.fighter.heal
    def observed(amount):
        boundary['before_hp']=e.player.fighter.hp
        actual=heal(amount)
        boundary.update(requested=amount,actual=actual,after_hp=e.player.fighter.hp,turn=e.world_time.turn)
        return actual
    with patch.object(e.player.fighter,'heal',side_effect=observed):
        yield from inventory(e,dose,key,choose)
    assert boundary['actual']==min(12,e.player.fighter.max_hp-boundary['before_hp']) and boundary['actual']>0
    assert boundary['after_hp']==boundary['before_hp']+boundary['actual']
    assert not e.player.inventory.contains(dose) and not e.player.inventory.has('herbal_dressing')
    assert e.player.inventory.items==possessions and e.player.equipment.slots==equipped
    assert e.world_time.turn==before+1
    assert any(f"recover {boundary['actual']} HP" in m.text for m in e.log.messages)
    ev.record.update(effect_boundary=boundary,after_normal_turn=status(e),use_turns=e.world_time.turn-before)
    capture('g15-use-result-normal-fov')
    public=(p['join'][0]%80,p['join'][1]%43)
    yield from walk_to(e,[public],key)
    yield from approach(e,xy,key)
    yield from interact(e,xy,key)
    assert not any(i.item_id=='herbal_dressing' for i in e.local_map.container_state[xy]['items'])
    yield from close_interaction(e,key)
    yield from walk_to(e,[public],key)
    assert e.player.fighter.hp>0 and not e.player_invincible
    yield key(pygame.K_F5)
    saved=snapshot(e);archive=archive_checkpoint(e,out,'consumed-healed')
    verify_cold(archive)
    cold=json.loads(archive.with_suffix('.cold.json').read_text());assert cold['pid']!=os.getpid()
    yield from unsaved_step(e,key)
    unsaved=snapshot(e);assert unsaved!=saved
    yield key(pygame.K_F9)
    assert snapshot(e)==saved and not e.player.inventory.has('herbal_dressing')
    capture('g15-returned-depleted-source')
    ev.record.update(saved_snapshot=saved,unsaved_movement_snapshot=unsaved,f9_restored_identified_consumed_snapshot=True,
        cold_consumed_pid=cold['pid'],left_and_returned_by_ordinary_movement=True,
        finish=status(e))


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--consume',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    from g12_journey import run_stage
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        if a.consume:
            record=run_stage(out,'consume',consume,a.consume.resolve())
            expected=json.loads(a.consume.with_suffix('.json').read_text())
            assert record['start_snapshot']==expected
            record['completed']=True
            (out/'consumption.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            return
        record=run_stage(out,'acquisition',acquisition)
        record['completed']=True
        archive=Path(record['checkpoint'])
        r=subprocess.run([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--evidence',str(out/'cold-use'),
            '--consume',str(archive)],capture_output=True,text=True,timeout=180)
        (out/'cold-use-output.txt').write_text(r.stdout+r.stderr,encoding='utf-8')
        assert r.returncode==0,r.stdout+r.stderr
        consumed=json.loads((out/'cold-use/consumption.json').read_text())
        assert consumed['cold_pid']!=os.getpid()
        report=dict(passed=True,acquisition=record,consumption=consumed)
        (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
