"""G21 original-loop witnesses. Only documented initial fixture staging.

Each stage runs in a separate disposable save root; all input uses app-local
Pygame events. Native generation and prepared archive evidence remain separate.
"""
import argparse
import contextlib
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
PREPARED=ROOT/'evidence/gameplay-g20/final-a/expedition/preparation/prepared-return.zip'


def ledger(e):
    from engine.save_manager import _serialize_entity
    from g20_journey import state
    return dict(player=state(e),actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
                live=[dict(id=getattr(a,'_individual_id',None),definition=a._creature_id,scene=[wx,wy,sid],xy=[a.x,a.y]) for a,wx,wy,sid in e._live_pursuers],
                pending=[dict(id=getattr(r['entity'],'_individual_id',None),delay=r['delay']) for r in e._pending_pursuer_arrivals],
                zones=copy.deepcopy(e.local_map.disruption_zones),
                remains=[dict(xy=list(xy),id=i.item_id,source=i.source_creature,decay=i.decay_timer) for xy,rows in e.local_map.floor_objects.items() for i in rows])


def native(e,key,capture,choose,ev,out):
    import pygame
    from engine.scene_generation import create_surface
    from generation.placement import digest
    from g12_journey import archive_checkpoint
    assert e.world_map.seed==20261030
    # The only player placement: a valid native approach. No actor, terrain,
    # supply, health or needs edits. Preserve the prior starting laboratory.
    e.save_manager.cache.store_submap(e.current_submap_id,e.local_map,e.entities)
    c=e.world_map.get(63,121)
    result=create_surface(e.world_map,c,e.data,e.item_factory,e.creature_factory,80,43)
    e.world_x,e.world_y=63,121;e.current_submap_id=None
    e.local_map=result.local_map;e.entities=[e.player]+result.actors
    e.player.x,e.player.y=42,21;e.reality_bubble.update(63,121,e.world_map);e._update_fov()
    assert e.local_map.walkable[42,21]
    ev.record.update(controls='Fresh 20261030 ordinary start possessions. One disclosed player placement at (42,21) of production-generated (63,121). Native actors/terrain/supplies remain unchanged. Full-state cardinal routing and threat telemetry; normal survival/FOV/AI and real pursuit. Budget in native-budget.json.',start=ledger(e),plan=digest(e.world_map.plan))
    bandit=next(a for a in result.actors if a._creature_id=='highland_bandit')
    assert (bandit.x,bandit.y)==(35,21) and len(result.actors)==1
    # Production-generated neighbor is inspected once, retained unchanged.
    n=create_surface(e.world_map,e.world_map.get(64,121),e.data,e.item_factory,e.creature_factory,80,43)
    assert [(a._creature_id,a.x,a.y) for a in n.actors]==[('heath_stalker',7,33)]
    e.save_manager.cache.store(64,121,n.local_map,n.actors)
    ev.record['native_provenance']=dict(bandit=[63,121,35,21],stalker=[64,121,7,33],source='generate_world -> create_surface; unchanged production population',neighbor_actors=1)
    # East route disclosed in the brief. Pursuer must actually see and follow.
    while e.world_x==63:
        yield key(pygame.K_RIGHT)
        assert e.player.fighter.hp>0
    assert e.world_x==64
    ev.record['crossed']=ledger(e)
    # Move toward the stalker's approach, then retreat north while the Bandit
    # arrives via the normal player-pursuer queue. No inserted/teleported actor.
    for _ in range(7):yield key(pygame.K_RIGHT)
    for _ in range(7):yield key(pygame.K_DOWN)
    ev.record['formed_approach']=ledger(e)
    for _ in range(45):
        rivals=[a for a in e.entities if a is not e.player and getattr(a.ai,'local_target',None)]
        if len(rivals)==2 and any(a.fighter.hp<a.fighter.max_hp for a in rivals):break
        # Withdraw diagonally north-east; native grass/gravel route is checked.
        if e.player.y>15 and e.local_map.walkable[e.player.x+1,e.player.y-1]:
            yield key(pygame.K_KP9)
        else:yield key(pygame.K_z,'z')
        assert e.player.fighter.hp>0
    ev.record['encounter_result']=ledger(e)
    records=ev.record['ledger']
    assert any(len([a for a in row['actors'] if a.get('local_target')])==2 for row in records),'Native pair never selected each other'
    assert any(a.get('fighter',{}).get('hp',16)<16 for row in records for a in row['actors']),'Native pair never committed damage'
    assert {r['attacker_definition'] for r in ev.record.get('attacks',[])
            if r['committed'] and r['selected'] and r['selected']['id']==r['defender']} == {'highland_bandit','heath_stalker'},'Both native actors must commit a rival attack'
    capture('native-rivals');yield key(pygame.K_F5)
    ev.record.update(checkpoint=str(archive_checkpoint(e,out,'native-after')),completion=True)


def common(e,key,capture,choose,ev,out):
    import pygame
    from engine.scene_generation import create_submap
    from world.world_map import SubMap
    from g12_journey import archive_checkpoint
    from engine.save_components import serialize_item
    before=ledger(e)
    e.save_manager.cache.store_submap(e.current_submap_id,e.local_map,e.entities)
    raw=json.loads((ROOT/'tools/critical_fix_regressions/fixtures/g21/rival_room.json').read_text())
    e.data.layouts[raw['id']]=raw
    sub=SubMap('g21-rival-room','cave','G21 controlled local arrangement',29417,layout_id=raw['id'])
    e.world_map.get(e.world_x,e.world_y).submaps.append(sub)
    result=create_submap(e.world_map,e.world_x,e.world_y,sub,e.data,e.item_factory,e.creature_factory,80,43)
    e.current_submap_id=sub.submap_id;e.local_map=result.local_map;e.entities=[e.player]+result.actors
    e.player.x,e.player.y=result.spawn;e._update_fov()
    ev.record.update(controls='Disposable copy of exact genuine G20 prepared-return archive. Initial authored-room/actor/player staging via native create_submap; no ownership, quantity, fuel, needs, equipment or health edits. Fresh G21 factory pair. This proves composition, not native selection in the archived campaign.',archive=str(PREPARED.relative_to(ROOT)),archive_sha256=hashlib.sha256(PREPARED.read_bytes()).hexdigest(),prepared_state=before,common_state=ledger(e))
    assert [serialize_item(i) for i in e.player.inventory.items]==before['player']['possessions']
    assert e.player.inventory.has('musk_pellet') and e.player.inventory.has('flint_shard')
    yield None;capture('prepared-common-state');yield key(pygame.K_F5)
    ev.record.update(checkpoint=str(archive_checkpoint(e,out,'common')),completion=True)


def continuation(e,key,capture,choose,ev,out,branch):
    import pygame
    from g12_journey import archive_checkpoint,inventory,snapshot
    from g20_journey import aim
    actors=[a for a in e.entities if a is not e.player]
    ev.record.update(controls=f'{branch}: independent cold continuation of common authored room, normal stats, owned resources, FOV/survival/AI, no winner or injury staging.',start=ledger(e))
    ox,oy=e.player.x-14,e.player.y-9
    if branch=='musk':
        pellet=e.player.inventory.get_by_id('musk_pellet');assert pellet
        yield from inventory(e,pellet,key,choose);yield from aim(e,(ox+14,oy+5),key)
        assert not e.player.inventory.contains(pellet)
        ev.record['after_throw']=ledger(e)
        assert e.local_map.disruption_zones[0]['turns_remaining']==5
        positions=[(a.x,a.y,a.ai.move_accumulator) for a in actors]
        for _ in range(5):yield key(pygame.K_UP)
        assert positions==[(a.x,a.y,a.ai.move_accumulator) for a in actors]
        assert not e.local_map.disruption_zones
        yield key(pygame.K_UP);yield key(pygame.K_UP)
        for _ in range(4):yield key(pygame.K_RIGHT)
    elif branch=='conflict':
        # Let reciprocal sight establish the fight, then exploit the far flank.
        yield key(pygame.K_z,'z')
        for _ in range(8):yield key(pygame.K_RIGHT)
        for _ in range(7):yield key(pygame.K_UP)
    else:
        # Useful unprepared direct-passage control, same initial state and goal.
        for _ in range(7):yield key(pygame.K_UP)
        for _ in range(4):yield key(pygame.K_RIGHT)
    ev.record['passage']=ledger(e)
    for _ in range(8):yield key(pygame.K_z,'z')
    assert e.player.fighter.hp>0
    capture(branch+'-withdrawal');yield key(pygame.K_F5)
    saved=snapshot(e);yield key(pygame.K_z,'z');yield key(pygame.K_F9)
    assert saved==snapshot(e)
    ev.record.update(finish=ledger(e),checkpoint=str(archive_checkpoint(e,out,'after')),completion=True)


def lethal(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,interact,archive_checkpoint,verify_cold
    from engine.harvesting import owned_cutters
    a,b=[next(a for a in e.entities if getattr(a,'_creature_id',None)==iid)
         for iid in ('highland_bandit','heath_stalker')]
    ox,oy=e.player.x-14,e.player.y-9
    a.x,a.y=ox+12,oy+6;b.x,b.y=ox+13,oy+6;e.player.x,e.player.y=ox+12,oy+8
    b.fighter.hp=1;e.rng=random.Random(4);e._update_fov()
    ev.record.update(controls='Separate controlled lethal continuation: initial player/pair positions and Stalker HP=1, combat RNG seed 4. Ordinary factory stats otherwise unchanged. Real AI fatal resolution, then ordinary player combat for safe access, owned equipped cutter, cursor butchery and paid debt. This establishes credit/lifecycle, not encounter balance or a natural winner.',start=ledger(e),xp_start=e.player.level.exp)
    for _ in range(8):
        if not b.is_alive:break
        yield key(pygame.K_z,'z')
    assert not b.is_alive and a.is_alive
    assert e.player.level.exp==ev.record['xp_start']
    corpse=next(i for rows in e.local_map.floor_objects.values() for i in rows if i.source_creature=='heath_stalker')
    ev.record['creature_death']=dict(state=ledger(e),xp=e.player.level.exp)
    capture('creature-caused-remains')
    # Existing owned blade; no granted tool, forged equipment flag or free time.
    if not owned_cutters(e.player):
        blade=e.player.inventory.get_by_id('crude_blade');assert blade
        yield from inventory(e,blade,key,choose)
    assert owned_cutters(e.player)
    for _ in range(30):
        if not a.is_alive:break
        dx=(a.x>e.player.x)-(a.x<e.player.x);dy=(a.y>e.player.y)-(a.y<e.player.y)
        keys={(0,-1):pygame.K_UP,(0,1):pygame.K_DOWN,(-1,0):pygame.K_LEFT,(1,0):pygame.K_RIGHT,(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3}
        yield key(keys[dx,dy]);assert e.player.fighter.hp>0
    assert not a.is_alive
    ev.record['direct_player_kill']=dict(xp=e.player.level.exp,state=ledger(e))
    assert e.player.level.exp>ev.record['xp_start']
    while max(abs(e.player.x-corpse.x),abs(e.player.y-corpse.y))>1:
        yield key(pygame.K_RIGHT if e.player.x<corpse.x else pygame.K_LEFT)
    from engine.harvesting import select_tier
    actual=max(t for _,t in owned_cutters(e.player))
    tier=select_tier(e.data.entities['heath_stalker']['butcher_yield'],actual)
    expected_cost=max(1,5-(actual-tier['min_cutting_tier']))
    start=e.world_time.turn;xp=e.player.level.exp;debt=e._move_debt
    yield from interact(e,(corpse.x,corpse.y),key)
    assert not any(i is corpse for rows in e.local_map.floor_objects.values() for i in rows)
    # The interaction handler settles ordinary butchery debt through charged phases.
    assert e.world_time.turn-start==expected_cost and abs(e._move_debt-debt)<1e-9
    assert e.player.level.exp==xp
    outputs=[i.item_id for i in e.local_map.floor_objects.get((corpse.x,corpse.y),[])]
    assert 'stalker_meat' in outputs and 'animal_bone' in outputs
    ev.record['harvest']=dict(turns=e.world_time.turn-start,debt_before=debt,debt_after=e._move_debt,xp=xp,outputs=outputs,cutters=[dict(id=i.item_id,tier=t) for i,t in owned_cutters(e.player)],state=ledger(e))
    capture('harvested-creature-remains');yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'depleted');verify_cold(archive)
    ev.record.update(checkpoint=str(archive),completion=True)


def revisit(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import archive_checkpoint
    from g20_journey import walk
    sid=e.current_submap_id;ev.record['cold_start']=ledger(e)
    assert not any(i.source_creature=='heath_stalker' for rows in e.local_map.floor_objects.values() for i in rows)
    yield from walk(e,{xy for xy in ((x,y) for x in range(80) for y in range(43)) if str(e.local_map.tiles['terrain'][xy])=='stairs_up'},key)
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    assert e.current_submap_id is None
    # The fixture is intentionally outside canonical selection. The engine's
    # native transition method revisits its already-owned cached scene directly.
    # This is a disclosed transition diagnostic, not a new canonical entrance.
    e._descend_to_submap(sid)
    assert e.current_submap_id==sid
    assert not any(i.source_creature=='heath_stalker' for rows in e.local_map.floor_objects.values() for i in rows)
    assert any(i.item_id=='stalker_meat' for rows in e.local_map.floor_objects.values() for i in rows)
    ev.record['cold_revisited']=ledger(e);capture('cold-revisited-depletion')
    yield key(pygame.K_F5);ev.record.update(checkpoint=str(archive_checkpoint(e,out,'revisited')),completion=True)


def run(out,stage,checkpoint=None):
    from b1_support import Evidence
    from b1_journey import run_journey
    from g12_journey import install_checkpoint
    folder=out/stage;folder.mkdir(parents=True)
    ev=Evidence(dict(run_id='g21-'+stage,scenario='journey',phase='loop',flavor='candidate',variant=stage,result=str(folder/'result.json')))
    with tempfile.TemporaryDirectory(prefix='resonance-g21-'+stage+'-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        if checkpoint:install_checkpoint(checkpoint,root)
        else:
            slot=Path(root)/'slot_0';slot.mkdir();(slot/'world.json').write_text('{"seed":20261030}')
        def actions(e,key,capture,choose):
            from components.ai import _monster_attack_entity
            original=e._advance_turn
            def advance():
                original();ev.record.setdefault('ledger',[]).append(ledger(e))
            def attack(attacker,defender,engine):
                before=defender.fighter.hp
                selected=copy.deepcopy(getattr(attacker.ai,'local_target',None))
                committed=_monster_attack_entity(attacker,defender,engine)
                ev.record.setdefault('attacks',[]).append(dict(turn=e.world_time.turn,
                    attacker=getattr(attacker,'_individual_id',None),attacker_definition=attacker._creature_id,
                    defender=getattr(defender,'_individual_id',None),
                    defender_definition='player' if defender is e.player else defender._creature_id,
                    selected=selected,committed=committed,hp_before=before,hp_after=defender.fighter.hp))
                return committed
            with patch.object(e,'_advance_turn',new=advance),patch('components.ai._monster_attack_entity',new=attack):
                if stage=='native':yield from native(e,key,capture,choose,ev,folder)
                elif stage=='common':yield from common(e,key,capture,choose,ev,folder)
                elif stage=='lethal':yield from lethal(e,key,capture,choose,ev,folder)
                elif stage=='revisit':yield from revisit(e,key,capture,choose,ev,folder)
                else:yield from continuation(e,key,capture,choose,ev,folder,stage)
        old=Path.cwd()
        try:
            os.chdir(ROOT/'roguelike');run_journey(ev,actions,max_frames=900,max_seconds=300,max_turns=360)
            ev.bind_sources(ROOT/'roguelike');ev.record['passed']=True
        finally:
            os.chdir(old);(folder/'result.json').write_text(json.dumps(ev.record,indent=2)+'\n')
    return ev.record


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--stage',choices=['native','common','conflict','musk','passive','lethal','revisit'],required=True);p.add_argument('--resume',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    result=run(a.evidence.resolve(),a.stage,a.resume.resolve() if a.resume else PREPARED if a.stage=='common' else None)
    print(json.dumps(dict(passed=result['passed'],stage=a.stage,checkpoint=result.get('checkpoint'))))


if __name__=='__main__':main()
