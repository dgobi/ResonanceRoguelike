"""Controlled authored encounter: original loop, ordinary combat and two cold processes."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT/'roguelike/docs/examples/g17_authored_creature_room.json'
SID = 'g17-controlled-room'
CONTROLS = ('Controlled disposable linked-submap fixture, not native world selection or H1 completion. '
    'Only setup: bind the unchanged example in memory, use the generated surface with its existing provenance, '
    'omit its native occupants and clear a 3x3 surface/stair link at the starting chunk; '
    'retain ordinary starter equipment. Destination terrain, actor and mixed objects come exclusively from production '
    'authored construction. Original Engine.run, real app-local events, normal AI/FOV/combat/time and survival. '
    'Existing driver seeds gameplay RNGs and PYTHONHASHSEED to 20261020 in each process; full-state movement/UI choices. '
    'After setup there is no health restoration, invincibility, actor insertion/deletion, or direct death. No encounter-balance claim.')


def bind(e):
    raw = json.loads(EXAMPLE.read_text())
    e.data.layouts = dict(e.data.layouts, **{raw['id']: raw})


def actors(e):
    return [a for a in e.entities if a is not e.player]


def owned_content(e):
    from engine.save_components import serialize_item
    m = e.local_map
    return dict(wood=[serialize_item(i) for rows in m.floor_objects.values() for i in rows if i.item_id == 'wood_bundle'],
        containers=[dict(xy=list(xy), state=c['state'], decor_id=c['decor_id'], items=[serialize_item(i) for i in c['items']])
                    for xy,c in sorted(m.container_state.items())])


def assert_ownership(e, *, living=True):
    # The active scene supersedes its cached serialized snapshot. Other scenes
    # and live pursuer lists must not also own this actor.
    rows = actors(e)
    if living:
        assert len(rows) == 1
        assert rows[0]._creature_id == 'hollow_revenant' and rows[0].is_alive
    else:
        assert not rows  # Ordinary turn cleanup removes the defeated actor; its physical remains live on the floor.
    assert len({id(a) for a in e.entities}) == len(e.entities)
    assert not e._live_pursuers and not e._pending_transfer
    surface = e.save_manager.cache.load(e.world_x, e.world_y)
    assert surface is not None and not surface.entities
    items = list(e.player.inventory.items) + [i for v in e.local_map.floor_objects.values() for i in v]
    items += [i for c in e.local_map.container_state.values() for i in c['items']]
    assert len(items) == len({id(i) for i in items})
    assert len([i for i in items if i.item_id == 'wood_bundle']) >= 1
    return rows[0] if living else None


def step_toward(e, actor, key):
    import pygame
    directions = {(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP,
        (1,1):pygame.K_KP3,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(-1,-1):pygame.K_KP7}
    dx = (actor.x > e.player.x) - (actor.x < e.player.x)
    dy = (actor.y > e.player.y) - (actor.y < e.player.y)
    return key(directions[dx,dy])


def living(e,key,capture,choose,ev,out):
    import pygame
    from world.world_map import SubMap
    from engine.save_manager import _serialize_entity
    from g12_journey import inventory, archive_checkpoint, snapshot
    bind(e)
    m = e.save_manager.cache.load(e.world_x,e.world_y).local_map
    for x in range(39,42):
        for y in range(20,23):
            m.set_tile(x,y,'grass',True,True)
            m.decor.pop((x,y),None); m.container_state.pop((x,y),None)
    m.set_tile(40,21,'stairs_down',True,True); m.submap_links[(40,21)] = SID
    e.local_map = m; e.entities = [e.player]; e.current_submap_id = None
    e.player.x,e.player.y = 40,21
    sub = SubMap(SID,'cave','G17 controlled authoring example',17017,
                 layout_id='g17_authored_creature_room',surface_x=40,surface_y=21)
    e.world_map.get(e.world_x,e.world_y).submaps.append(sub); e._update_fov()
    ev.record.update(controls=CONTROLS, fixture=dict(example=EXAMPLE.relative_to(ROOT).as_posix(),
        sha256=hashlib.sha256(EXAMPLE.read_bytes()).hexdigest(), scene_seed=sub.seed, surface=[e.world_x,e.world_y,40,21]))
    for iid in ('crude_blade','leather_jack'):
        yield from inventory(e,e.player.inventory.get_by_id(iid),key,choose)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id == SID and sub.generated
    actor = assert_ownership(e)
    assert (actor.x,actor.y,actor.fighter.hp) == (42,20,14)
    assert e.player.fighter.hp > 0 and not e.player_invincible
    ev.record['constructed_actor'] = _serialize_entity(actor)
    ev.record['authored_content'] = owned_content(e)
    capture('g17-authored-arrival-normal-fov')
    # Engage through ordinary bump movement until an actual wound exists.
    for _ in range(30):
        if 0 < actor.fighter.hp < actor.fighter.max_hp: break
        assert actor.is_alive and e.player.fighter.hp > 0
        yield step_toward(e,actor,key)
    assert actor.is_alive and 0 < actor.fighter.hp < 14
    ev.record['living_actor'] = _serialize_entity(assert_ownership(e))
    ev.record['live_player_hp'] = e.player.fighter.hp
    capture('g17-wounded-live-actor-normal-fov')
    yield key(pygame.K_F5)
    ev.record['checkpoint'] = str(archive_checkpoint(e,out,'living-actor'))
    ev.record['live_snapshot'] = snapshot(e)


def defeated(e,key,capture,choose,ev,out):
    import pygame
    from engine.save_manager import _serialize_entity
    from g12_journey import archive_checkpoint,snapshot
    from g16_journey import walk
    bind(e)
    expected = json.loads(Path(ev.job['checkpoint']).with_suffix('.json').read_text())
    assert snapshot(e) == expected
    actor = assert_ownership(e)
    assert actor.is_alive and 0 < actor.fighter.hp < 14
    ev.record.update(controls=CONTROLS, cold_pid=os.getpid(), start_snapshot=snapshot(e),
                     restored_actor=_serialize_entity(actor))
    content = owned_content(e); start_hp = e.player.fighter.hp; start_turn = e.world_time.turn
    for _ in range(40):
        if not actor.is_alive: break
        yield step_toward(e,actor,key)
        assert e.player.fighter.hp > 0 and not e.player_invincible
    assert not actor.is_alive and actor.fighter.hp <= 0
    remains = [(xy,i) for xy,rows in e.local_map.floor_objects.items() for i in rows if i.source_creature == 'hollow_revenant']
    assert len(remains) == 1 and remains[0][1].item_id == 'corpse'
    assert owned_content(e) == content
    ev.record['defeated_actor'] = _serialize_entity(actor)
    ev.record['combat'] = dict(turns=e.world_time.turn-start_turn, player_hp_before=start_hp, player_hp_after=e.player.fighter.hp,
                              normal_remains=True, remains_xy=list(remains[0][0]))
    capture('g17-defeated-with-normal-remains')
    stair = next(xy for xy in ((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height))
                 if str(e.local_map.tiles[xy]['terrain']) == 'stairs_up')
    yield from walk(e,{stair},key)
    with patch('engine.scene_generation.create_submap',side_effect=AssertionError('cache revisit must not regenerate')):
        yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
        assert e.current_submap_id is None and (e.player.x,e.player.y) == (40,21)
        yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id == SID
    assert_ownership(e, living=False)
    assert owned_content(e) == content
    ev.record['cache_revisit'] = dict(passed=True,generation_forbidden=True)
    yield key(pygame.K_F5)
    ev.record['checkpoint'] = str(archive_checkpoint(e,out,'defeated-actor'))
    ev.record['final_snapshot'] = snapshot(e)
    ev.record['unrelated_authored_ownership'] = content


def revisit(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import snapshot
    from g16_journey import walk
    bind(e)
    expected = json.loads(Path(ev.job['checkpoint']).with_suffix('.json').read_text())
    assert snapshot(e) == expected
    assert_ownership(e, living=False)
    content = owned_content(e)
    ev.record.update(controls=CONTROLS,cold_pid=os.getpid(),start_snapshot=snapshot(e))
    with patch('engine.scene_generation.create_submap',side_effect=AssertionError('disk revisit must not regenerate')):
        yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
        assert e.current_submap_id is None
        e.save_manager.cache.evict_distant(10,10)
        yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id == SID
    assert_ownership(e, living=False)
    assert owned_content(e) == content
    assert len([i for rows in e.local_map.floor_objects.values() for i in rows if i.source_creature == 'hollow_revenant']) == 1
    capture('g17-cold-disk-revisit-no-respawn')
    ev.record.update(disk_revisit=dict(passed=True,generation_forbidden=True,actor_respawned=False,normal_remains=True),
                     final_snapshot=snapshot(e),unrelated_authored_ownership=content)


def stage(out,name,actions,checkpoint=None):
    from g12_journey import run_stage
    # Keep the established helper unchanged; new G17 metadata follows its actual
    # exhaustion assertion rather than inheriting the stale historical default.
    def wrapped(e,key,capture,choose,ev,directory):
        if checkpoint: ev.job['checkpoint'] = str(checkpoint)
        yield from actions(e,key,capture,choose,ev,directory)
    result = run_stage(out,name,wrapped,checkpoint,max_frames=250,max_seconds=120,max_turns=100)
    result['completed'] = any(c['property'] == 'original loop completed bounded driver' and c['passed'] and c['observed']
                              for c in result['checks'])
    assert result['completed'] and result['passed']
    (out/name/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--resume',type=Path); p.add_argument('--revisit',type=Path); a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/'output.txt').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        if a.revisit:
            stage(out,'revisit',revisit,a.revisit.resolve()); return
        if a.resume:
            result=stage(out,'combat',defeated,a.resume.resolve())
            option, archive = '--revisit', result['checkpoint']
        else:
            result=stage(out,'living',living)
            option, archive = '--resume', result['checkpoint']
        child=out/'cold'
        command=[sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--evidence',str(child),option,archive]
        r=subprocess.run(command,capture_output=True,text=True,timeout=180)
        (out/'cold-output.txt').write_text(r.stdout+r.stderr)
        assert r.returncode == 0,r.stdout+r.stderr
        child_result=json.loads((child/('revisit' if a.resume else 'combat')/'result.json').read_text())
        assert child_result['cold_pid'] != os.getpid()
        (out/'journey.json').write_text(json.dumps(dict(passed=True,completed=True,controls=CONTROLS,
            stage=result,cold_command=command,cold_stage=child_result),indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,evidence=str(out))))


if __name__ == '__main__': main()
