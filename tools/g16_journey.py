"""Ordinary-start G16 expedition, using the established original Engine.run driver."""
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


def state(e):
    from g10_play import status
    from engine.save_components import serialize_item
    result=status(e)
    result['possessions']=[serialize_item(i) for i in e.player.inventory.items]
    return result


def walk(e,goals,key):
    import pygame
    from g10_play import path,KEYS
    goals=set(goals)
    diagonal={(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3}
    with patch.dict(KEYS,diagonal):
        for _ in range(400):
            if (e.player.x,e.player.y) in goals:return
            route=path(e,goals,prefer_firm=True);a,b=route[:2]
            yield key(KEYS[b[0]-a[0],b[1]-a[1]])
            assert e.player.fighter.hp>0 and not e.player_invincible
    raise AssertionError('G16 finite route budget')


def cross(e,dx,dy,key):
    import pygame
    from generation.access import enterable
    m=e.local_map
    edge=([(m.width-1 if dx>0 else 0,y) for y in range(m.height)] if dx else
          [(x,m.height-1 if dy>0 else 0) for x in range(m.width)])
    goals={xy for xy in edge if enterable(m,xy,e.data)}
    yield from walk(e,goals,key)
    old=e.world_x,e.world_y
    yield key({(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP}[dx,dy])
    assert (e.world_x,e.world_y)==(old[0]+dx,old[1]+dy)


def approach(e,xy,key):
    from engine.interaction_cursor import InteractionCursor
    goals={(xy[0]+dx,xy[1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))}
    yield from walk(e,goals,key)
    assert InteractionCursor.can_reach(e,*xy)


def close(e,key):
    from g15_journey import close_interaction
    yield from close_interaction(e,key)


def placement(e):
    return next(p for p in e.world_map.plan['placements'] if p['asset']=='workshop_b'
                and p['id']=='settlement-0-cross-market-lot-1-44-S-0-building')


def local(p,x,y,e):
    # G16 primary native selection is rotation zero; all transforms have focused coverage.
    assert p['rotation']==0 and not p['mirror']
    return (p['origin'][0]+x)%80,(p['origin'][1]+y)%43


def outbound(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,interact,select_prompt,recipe,snapshot,archive_checkpoint
    from generation.placement import digest
    from engine.save_components import serialize_item
    assert (e.world_x,e.world_y)==(73,99) and e.current_submap_id is not None
    inv=e.player.inventory
    assert sorted(i.item_id for i in inv.items)==sorted(['tallow_torch','crow_jerky','water_flask','crude_blade','leather_jack','moist_pebble'])
    assert e.player.fighter.hp==60 and e.world_time.turn==480
    p=placement(e)
    ev.record.update(controls='Real laboratory start, seed 20261023; original Engine.run and app-local Pygame events. Full-state threat-aware eight-way terrain-cost routing and UI row choices; established runtime RNG seed 20261020, PYTHONHASHSEED=20261020. Ordinary starter equipment/food/water only. Normal AI, FOV, survival, costs and resource depletion. No staging, teleportation, threat clearing, invincibility, injected supplies, synthetic injury/recovery or resets. A single F9 restores the named in-progress snapshot after one actual unsaved wait.',
        start=state(e),placement=copy.deepcopy(p),plan_identity=digest(e.world_map.plan),waypoints=[])
    yield None
    for iid in ('crude_blade','leather_jack'):
        yield from inventory(e,inv.get_by_id(iid),key,choose)
    stairs={(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
            if str(e.local_map.tiles[x,y]['terrain'])=='stairs_up'}
    yield from walk(e,stairs,key)
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    assert e.current_submap_id is None
    ev.record['laboratory_return']=dict(chunk=[e.world_x,e.world_y],position=[e.player.x,e.player.y],submap=e.world_map.get(e.world_x,e.world_y).submaps[0].submap_id)
    for dx,dy in ((1,0),(1,0),(0,1)):
        yield from cross(e,dx,dy,key)
        ev.record['waypoints'].append(state(e))
        if e.player.needs.thirst>.35 and inv.has('water_flask'):
            yield from inventory(e,inv.get_by_id('water_flask'),key,choose)
    assert (e.world_x,e.world_y)==(75,100)
    xy=local(p,2,2,e);note_xy=local(p,1,1,e)
    native=list(e.local_map.container_state[xy]['items'])
    assert sorted(i.item_id for i in native)==['stalker_musk_gland','wood_bundle']
    ev.record['native_crate']=[serialize_item(i) for i in native]
    yield from approach(e,xy,key)
    capture('g16-furnished-workshop-normal-fov')
    yield from approach(e,note_xy,key)
    yield from interact(e,note_xy,key)
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,'research_note',key)
    yield from close(e,key)
    note=next(i for i in inv.items if i.text_id=='workshop_musk_notes_b')
    yield from inventory(e,note,key,choose)
    assert e.text_reader.open and e.text_reader._text_id==note.text_id
    capture('g16-readable-musk-note')
    ev.record['note']=copy.deepcopy(e.text_reader._def)
    yield key(pygame.K_ESCAPE)
    if e.inventory_screen.open:yield key(pygame.K_i,'i')
    yield from approach(e,xy,key)
    for iid in ('stalker_musk_gland','wood_bundle'):
        yield from interact(e,xy,key)
        yield from select_prompt(e,iid,key)
        yield from close(e,key)
    assert all(inv.contains(i) for i in native) and not e.local_map.container_state[xy]['items']
    ev.record['acquisition']=state(e)
    yield from interact(e,xy,key)
    yield key(pygame.K_x,'x');assert e.interaction_cursor._dismantle_prompt
    yield key(pygame.K_RETURN,'\r')
    assert xy not in e.local_map.container_state and xy not in e.local_map.decor
    reclaimed,=e.local_map.floor_objects[xy];assert reclaimed.item_id=='wood_bundle'
    yield from close(e,key)
    yield from interact(e,xy,key)
    yield from close(e,key)
    assert inv.contains(reclaimed)
    # Open floor in the southern work area, away from the old scholar scene.
    work=local(p,8,7,e)
    yield from walk(e,[work],key)
    yield from recipe(e,'campfire',key)
    fire=(e._placement_cursor_x,e._placement_cursor_y)
    assert e._is_valid_placement(*fire)
    before=e.world_time.turn
    yield key(pygame.K_RETURN,'\r')
    assert e.world_time.turn==before+1 and e.local_map.decor[fire]=='campfire_unlit'
    assert not any(inv.contains(i) for i in native if i.item_id=='wood_bundle') and not inv.contains(reclaimed)
    yield from interact(e,fire,key)
    assert e.world_time.turn==before+2 and e.local_map.decor[fire]=='campfire_lit'
    yield from close(e,key)
    gland=next(i for i in native if i.item_id=='stalker_musk_gland')
    yield from recipe(e,'musk_pellet',key)
    spot=e._placement_cursor_x,e._placement_cursor_y
    phase_start=e.world_time.turn
    yield key(pygame.K_RETURN,'\r')
    assert not inv.contains(gland) and e.local_map.processing_layer[spot]['turns_remaining']==9
    assert inv.has('crude_blade') and inv.get_by_id('crude_blade').equipped
    ev.record['preparation']=dict(fire=fire,spot=spot,phase_start=phase_start,placement_turn=e.world_time.turn,
        exact_native_gland_spent=True,two_physical_wood_spent=True,tool_retained=True,source_dismantled=True,state=state(e))
    yield key(pygame.K_F5)
    saved=snapshot(e);archive=archive_checkpoint(e,out,'drying-in-progress')
    yield key(pygame.K_z,'z')
    unsaved=snapshot(e);assert unsaved!=saved
    yield key(pygame.K_F9)
    assert snapshot(e)==saved
    ev.record.update(checkpoint=str(archive),saved_snapshot=saved,unsaved_wait_snapshot=unsaved,
        f9_restored_named_drying_snapshot=True,finish=state(e),parent_pid=os.getpid())


def homeward(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import interact,snapshot,archive_checkpoint,inventory
    from g1_support import fingerprint
    p=placement(e);xy=local(p,2,2,e)
    spot,=e.local_map.processing_layer
    remaining=e.local_map.processing_layer[spot]['turns_remaining'];assert remaining==9
    ev.record.update(cold_pid=os.getpid(),start_snapshot=snapshot(e),start=state(e))
    yield None
    before=e.world_time.turn
    for _ in range(remaining):yield key(pygame.K_z,'z')
    assert spot not in e.local_map.processing_layer and e.world_time.turn==before+9
    pellet,=[i for i in e.local_map.floor_objects[spot] if i.item_id=='musk_pellet']
    yield from approach(e,spot,key)
    yield from interact(e,spot,key)
    yield from close(e,key)
    assert e.player.inventory.contains(pellet)
    capture('g16-owned-pellet-normal-fov')
    ev.record['prepared']=dict(state=state(e),processing_phases=10,placement_included=True,
        exactly_one_owned_pellet=True,source_dismantled=xy not in e.local_map.container_state)
    expected=fingerprint(e.local_map,[a for a in e.entities if a is not e.player])
    ev.record['workshop_before_departure']=expected
    for dx,dy in ((0,-1),(-1,0),(-1,0)):
        yield from cross(e,dx,dy,key)
        inv=e.player.inventory
        if e.player.needs.hunger>.35 and inv.has('crow_jerky'):
            yield from inventory(e,inv.get_by_id('crow_jerky'),key,choose)
        if e.player.needs.thirst>.35 and inv.has('water_flask'):
            yield from inventory(e,inv.get_by_id('water_flask'),key,choose)
    assert (e.world_x,e.world_y)==(73,99)
    laboratory=e.world_map.get(73,99).submaps[0].submap_id
    stairs={xy for xy,sid in e.local_map.submap_links.items() if sid==laboratory}
    yield from walk(e,stairs,key)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==laboratory and e.player.fighter.hp>0 and e.player.inventory.contains(pellet)
    capture('g16-returned-laboratory-with-pellet')
    yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'returned-pellet')
    command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--evidence',str(out/'cold-check'),'--check-returned',str(archive)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    cold=json.loads(archive.with_suffix('.returned-cold.json').read_text());assert cold['pid']!=os.getpid()
    # Focused disk revisit of the altered source, without a second itinerary.
    e.save_manager.cache.evict_distant(10,10)
    with patch('engine.scene_generation.create_surface',side_effect=AssertionError('must read persisted workshop')):
        m,actors=e._prepare_destination(75,100)
    assert xy not in m.decor and xy not in m.container_state
    assert not any(i.item_id in ('stalker_musk_gland','wood_bundle','musk_pellet') for rows in m.floor_objects.values() for i in rows)
    # AI/processing may run while hot; the durable reward/decor owners are the invariant.
    ev.record.update(finish=state(e),returned_alive_with_unspent_pellet=True,final_cold_pid=cold['pid'],
        persisted_source=dict(crate_absent=True,no_reward_on_floor=True,method='cache eviction and disk revisit; generation forbidden'),
        final_snapshot=snapshot(e),checkpoint=str(archive))


def check_returned(archive):
    import hashlib
    import tempfile
    from test_effect_persistence import load_data,make_engine
    from g12_journey import install_checkpoint,snapshot
    with tempfile.TemporaryDirectory(prefix='resonance-g16-returned-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        install_checkpoint(archive,root)
        e=make_engine(load_data());assert e.save_manager.load(e),e.save_manager.last_error
        assert snapshot(e)==json.loads(archive.with_suffix('.json').read_text())
        assert (e.world_x,e.world_y)==(73,99) and e.current_submap_id==e.world_map.get(73,99).submaps[0].submap_id and e.player.fighter.hp>0
        assert sum(i.item_id=='musk_pellet' for i in e.player.inventory.items)==1
        p=placement(e);xy=local(p,2,2,e)
        with patch('engine.scene_generation.create_surface',side_effect=AssertionError('must load saved workshop')):
            m,actors=e._prepare_destination(75,100)
        assert xy not in m.decor and xy not in m.container_state
        assert not any(i.item_id in ('stalker_musk_gland','wood_bundle','musk_pellet') for rows in m.floor_objects.values() for i in rows)
        archive.with_suffix('.returned-cold.json').write_text(json.dumps(dict(passed=True,pid=os.getpid(),
            checkpoint_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),snapshot=snapshot(e),
            owned_pellet=1,source_crate_absent=True,no_floor_rewards=True),indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--resume',type=Path);p.add_argument('--check-returned',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    if a.check_returned:
        check_returned(a.check_returned.resolve())
        return
    from g12_journey import run_stage
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        limits=dict(max_frames=2500,max_seconds=600,max_turns=1200)
        if a.resume:
            result=run_stage(out,'homeward',homeward,a.resume.resolve(),**limits)
            assert result['start_snapshot']==json.loads(a.resume.with_suffix('.json').read_text())
            (out/'homeward.json').write_text(json.dumps(result,indent=2)+'\n')
            return
        result=run_stage(out,'outbound',outbound,**limits)
        archive=Path(result['checkpoint'])
        command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--evidence',str(out/'cold-return'),'--resume',str(archive)]
        r=subprocess.run(command,capture_output=True,text=True,timeout=650)
        (out/'cold-return-output.txt').write_text(r.stdout+r.stderr)
        assert r.returncode==0,r.stdout+r.stderr
        returned=json.loads((out/'cold-return/homeward.json').read_text())
        assert returned['cold_pid']!=os.getpid()
        report=dict(passed=True,outbound=result,homeward=returned,cold_command=command)
        (out/'journey.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__=='__main__':main()
