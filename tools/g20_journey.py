"""Connected G20 expedition via original Engine.run and app-local key events.

Routes inspect full runtime state, as the established G16 driver does. No actor,
health, needs, fuel, inventory, geometry or assignment is staged by this driver.
"""
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
DESTINATION=(78,100,'submap_78_100_0')
ROUTE=None


def workshop(e):
    return next(p for p in e.world_map.plan['placements'] if p['asset']=='workshop_c'
                and p['id']=='settlement-0-cross-market-lot-1-44-S-0-building')


def walk(e,goals,key):
    """Existing threat-aware route, with legal combat for a dynamic choke."""
    import pygame
    from collections import deque
    from generation.access import enterable
    from g10_play import path,KEYS
    goals=set(goals)
    diagonal={(-1,-1):pygame.K_KP7,(1,-1):pygame.K_KP9,(-1,1):pygame.K_KP1,(1,1):pygame.K_KP3}
    with patch.dict(KEYS,diagonal):
        for _ in range(800):
            start=(e.player.x,e.player.y)
            if start in goals:return
            try:route=path(e,goals,prefer_firm=True)
            except AssertionError:
                # A blocking living actor may occupy the only static passage.
                # Plan toward it, then ordinary bump input resolves legal combat.
                parents={start:None};queue=deque([start]);end=None
                while queue:
                    here=queue.popleft()
                    if here in goals:end=here;break
                    for dx,dy in KEYS:
                        xy=here[0]+dx,here[1]+dy
                        if xy not in parents and enterable(e.local_map,xy,e.data):parents[xy]=here;queue.append(xy)
                assert end is not None,'No static route to goals'
                route=[end]
                while parents[route[-1]] is not None:route.append(parents[route[-1]])
                route.reverse()
            a,b=route[:2];yield key(KEYS[b[0]-a[0],b[1]-a[1]])
            assert e.player.fighter.hp>0 and not e.player_invincible
    raise AssertionError('G20 finite walk budget')


def cross(e,dx,dy,key):
    import pygame
    from generation.access import enterable
    m=e.local_map
    edge=([(m.width-1 if dx>0 else 0,y) for y in range(m.height)] if dx else [(x,m.height-1 if dy>0 else 0) for x in range(m.width)])
    yield from walk(e,{xy for xy in edge if enterable(m,xy,e.data)},key)
    old=e.world_x,e.world_y
    yield key({(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP}[dx,dy])
    assert (e.world_x,e.world_y)==(old[0]+dx,old[1]+dy)


def planned_cross(e,leg,key,*,reverse=False):
    import pygame
    source,destination=leg['source'],leg['destination'];dx,dy=leg['direction']
    pairs=leg['pairs']
    if reverse:
        source,destination=destination,source;dx,dy=-dx,-dy;pairs=[[b,a] for a,b in pairs]
    assert [e.world_x,e.world_y]==source
    yield from walk(e,{tuple(a) for a,b in pairs},key)
    before=(e.player.x,e.player.y);expected=next(tuple(b) for a,b in pairs if tuple(a)==before)
    yield key({(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP}[dx,dy])
    assert [e.world_x,e.world_y]==destination
    assert (e.player.x,e.player.y)==expected,((e.player.x,e.player.y),expected)


def state(e):
    from g16_journey import state as ordinary_state
    r=ordinary_state(e)
    r['torch']=[dict(id=i.item_id,used=i.turns_lit,total=i.burn_turns,
                     lit=bool(e.player.light_source and e.player.light_source.active and getattr(e.player.light_source,'_item_ref',None) is i))
                for i in e.player.inventory.items if i.light_data]
    r['offhand']=getattr(e.player.equipment.slots.get('offhand'),'item_id',None)
    return r


def torch(e,lit,key,choose):
    from g12_journey import inventory
    item=e.player.inventory.get_by_id('tallow_torch');assert item,'Real torch exhausted'
    active=bool(e.player.light_source and e.player.light_source.active)
    if active != lit:yield from inventory(e,item,key,choose)
    assert bool(e.player.light_source and e.player.light_source.active)==lit


def provisions(e,key,choose):
    from g12_journey import inventory
    for need,iid in (('hunger','crow_jerky'),('thirst','water_flask')):
        if getattr(e.player.needs,need)>.5 and e.player.inventory.has(iid):
            yield from inventory(e,e.player.inventory.get_by_id(iid),key,choose)


def gather(e,key,choose,ev):
    from g16_journey import approach,close
    from g12_journey import interact
    if e.player.inventory.has('flint_shard'):return
    rocks=[(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
           if str(e.local_map.tiles['terrain'][x,y])=='flint_rock']
    if not rocks:return
    xy=min(rocks,key=lambda p:abs(p[0]-e.player.x)+abs(p[1]-e.player.y))
    yield from approach(e,xy,key)
    start=e.world_time.turn
    for _ in range(12):
        yield from interact(e,xy,key);yield from close(e,key)
        if e.player.inventory.has('flint_shard'):break
    assert e.player.inventory.has('flint_shard'),'finite real gather budget'
    assert str(e.local_map.tiles['terrain'][xy])=='flint_rock_depleted'
    ev.record['gather']=dict(chunk=[e.world_x,e.world_y],source=list(xy),turns=e.world_time.turn-start,finish=state(e))


def preparation(e,key,capture,choose,ev,out):
    import pygame
    from g16_journey import approach,local,close
    from g12_journey import inventory,interact,select_prompt,recipe,archive_checkpoint
    assert (e.world_x,e.world_y)==(73,99) and e.world_time.turn==480 and e.current_submap_id
    assert sorted(i.item_id for i in e.player.inventory.items)==sorted(['tallow_torch','crow_jerky','water_flask','crude_blade','leather_jack','moist_pebble'])
    ev.record.update(controls='Ordinary seed 20261023 laboratory start. Full-state threat-aware eight-way routing and UI choices; existing driver RNG seed 20261020. Normal AI, FOV, survival, costs, gathering rolls and finite supplies. No teleportation, inserted supplies, actor edits, artificial health, restored fuel or forced kills. Torch extinguished ordinarily outdoors and relit for fire/underground. This is route-assisted play, not unaided discovery.',start=state(e))
    for iid in ('crude_blade','leather_jack'):yield from inventory(e,e.player.inventory.get_by_id(iid),key,choose)
    stairs={(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles['terrain'][x,y])=='stairs_up'}
    yield from walk(e,stairs,key);yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    ev.record['laboratory_return']=dict(chunk=[e.world_x,e.world_y],position=[e.player.x,e.player.y],submap=e.world_map.get(e.world_x,e.world_y).submaps[0].submap_id)
    yield from torch(e,False,key,choose);yield from gather(e,key,choose,ev)
    for dx,dy in ((1,0),(1,0),(0,1)):
        yield from cross(e,dx,dy,key);yield from provisions(e,key,choose);yield from gather(e,key,choose,ev)
    assert (e.world_x,e.world_y)==(75,100)
    p=workshop(e);xy=local(p,2,2,e);note_xy=local(p,1,1,e)
    native=list(e.local_map.container_state[xy]['items'])
    assert sorted(i.item_id for i in native)==['stalker_musk_gland','wood_bundle']
    ev.record['workshop']=dict(placement=copy.deepcopy(p),native=[i.item_id for i in native])
    supply=local(p,9,6,e)
    contents=list(e.local_map.container_state[supply]['items'])
    assert sorted(i.item_id for i in contents)==['crow_jerky','tallow_torch','water_flask']
    yield from approach(e,supply,key)
    for iid in ('tallow_torch','crow_jerky','water_flask'):
        yield from interact(e,supply,key);yield from select_prompt(e,iid,key);yield from close(e,key)
    assert not e.local_map.container_state[supply]['items'] and all(e.player.inventory.contains(i) for i in contents)
    ev.record['finite_travel_supplies']=dict(chunk=[e.world_x,e.world_y],source=list(supply),items=[i.item_id for i in contents])
    yield from approach(e,note_xy,key);yield from interact(e,note_xy,key)
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,'research_note',key)
    yield from close(e,key)
    note=next(i for i in e.player.inventory.items if i.text_id=='workshop_musk_notes_b')
    yield from inventory(e,note,key,choose);assert e.text_reader.open;capture('preparation-clue')
    yield key(pygame.K_ESCAPE)
    if e.inventory_screen.open:yield key(pygame.K_i)
    yield from approach(e,xy,key)
    for iid in ('stalker_musk_gland','wood_bundle'):
        yield from interact(e,xy,key);yield from select_prompt(e,iid,key);yield from close(e,key)
    yield from interact(e,xy,key);yield key(pygame.K_x,'x');assert e.interaction_cursor._dismantle_prompt
    yield key(pygame.K_RETURN);yield from close(e,key);yield from interact(e,xy,key);yield from close(e,key)
    assert len([i for i in e.player.inventory.items if i.item_id=='wood_bundle'])==2
    yield from torch(e,True,key,choose)
    yield from walk(e,[local(p,8,7,e)],key);yield from recipe(e,'campfire',key)
    fire=e._placement_cursor_x,e._placement_cursor_y;assert e._is_valid_placement(*fire)
    yield key(pygame.K_RETURN);yield from interact(e,fire,key);yield from close(e,key)
    assert e.local_map.decor[fire]=='campfire_lit'
    yield from recipe(e,'musk_pellet',key);spot=e._placement_cursor_x,e._placement_cursor_y
    yield key(pygame.K_RETURN)
    assert e.local_map.processing_layer[spot]['turns_remaining']==9
    for _ in range(9):yield key(pygame.K_z,'z')
    yield from approach(e,spot,key);yield from interact(e,spot,key);yield from close(e,key)
    assert e.player.inventory.has('musk_pellet') and e.player.inventory.has('flint_shard')
    capture('gathered-flint-prepared-pellet');ev.record['prepared']=state(e)
    yield from torch(e,False,key,choose)
    for dx,dy in ((0,-1),(-1,0),(-1,0)):
        yield from cross(e,dx,dy,key);yield from provisions(e,key,choose)
    lab=e.world_map.get(73,99).submaps[0].submap_id
    yield from walk(e,{xy for xy,sid in e.local_map.submap_links.items() if sid==lab},key)
    yield from torch(e,True,key,choose);yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==lab and e.player.fighter.hp>0
    capture('returned-preparation');yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'prepared-return')
    ev.record.update(finish=state(e),checkpoint=str(archive),completion=True)


def destination_entry(e,key,capture,choose,ev,out):
    import pygame
    from g16_journey import approach,close
    from g12_journey import inventory,interact,archive_checkpoint,snapshot
    ev.record.update(controls='Cold continuation of genuine G20 preparation return. Same ordinary runtime and full-state route assistance. Existing saved-policy assignment, surface approach and normal stairs. No supplied resources, actor edits, visibility override or reset.',start=state(e))
    assert (e.world_x,e.world_y)==(73,99) and e.current_submap_id
    assert e.player.inventory.has('musk_pellet') and e.player.inventory.has('flint_shard')
    yield from provisions(e,key,choose)
    stairs={(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height) if str(e.local_map.tiles['terrain'][x,y])=='stairs_up'}
    yield from walk(e,stairs,key);yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    yield from torch(e,False,key,choose)
    assert ROUTE is not None
    ev.record['route_assistance']=copy.deepcopy(ROUTE)
    for leg in ROUTE['chosen']['legs']:
        yield from planned_cross(e,leg,key);yield from provisions(e,key,choose)
        ev.record.setdefault('waypoints',[]).append(state(e))
    assert (e.world_x,e.world_y)==DESTINATION[:2]
    sub=next(s for s in e.world_map.get(*DESTINATION[:2]).submaps if s.submap_id==DESTINATION[2])
    assert sub.layout_id=='barrow_ward_store_a'
    entrance=next(xy for xy,sid in e.local_map.submap_links.items() if sid==sub.submap_id)
    yield from walk(e,[entrance],key);yield from torch(e,True,key,choose)
    capture('ordinary-selected-entrance');yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==sub.submap_id
    ox,oy=sub.entry_x-3,sub.entry_y-12
    clue=ox+4,oy+12
    yield from approach(e,clue,key);yield from interact(e,clue,key);yield from close(e,key)
    note=next(i for i in e.player.inventory.items if i.text_id=='barrow_ward_store_note_a')
    yield from inventory(e,note,key,choose);assert e.text_reader.open and not e.text_reader._def.get('deep_tongue',False)
    capture('ordinary-readable-ward-clue');yield key(pygame.K_ESCAPE)
    if e.inventory_screen.open:yield key(pygame.K_i)
    capture('ordinary-ward-store-entry');yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'common-entry')
    ev.record.update(finish=state(e),checkpoint=str(archive),destination=dict(chunk=list(DESTINATION[:2]),submap=sub.submap_id,layout=sub.layout_id,entrance=list(entrance),origin=[ox,oy]),completion=True)


def aim(e,xy,key):
    import pygame
    while e._placement_cursor_x!=xy[0]:yield key(pygame.K_RIGHT if e._placement_cursor_x<xy[0] else pygame.K_LEFT)
    while e._placement_cursor_y!=xy[1]:yield key(pygame.K_DOWN if e._placement_cursor_y<xy[1] else pygame.K_UP)
    yield key(pygame.K_RETURN)


def room_coordinates(e):
    sub=next(s for s in e.world_map.get(e.world_x,e.world_y).submaps if s.submap_id==e.current_submap_id)
    return sub.entry_x-3,sub.entry_y-12


def finish_encounter(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,interact,archive_checkpoint
    from g16_journey import close
    ox,oy=room_coordinates(e);reward=ox+20,oy+4
    yield from walk(e,[reward],key);yield from interact(e,reward,key);yield from close(e,key)
    ward=e.player.inventory.get_by_id('faceted_ward');assert ward
    ev.record['reward_acquired']=state(e);capture('ordinary-acquired-ward')
    # Move to the far side of the lower wall before stationary equipment choices.
    yield from walk(e,[(ox+20,oy+9)],key)
    yield from walk(e,[(ox+14,oy+12)],key)
    guard=next((a for a in e.entities if a is not e.player and getattr(a,'_creature_id','')=='hollow_revenant'),None)
    before=e.world_time.turn
    yield from inventory(e,ward,key,choose)
    assert e.player.equipment.slots['offhand'] is ward and not e.player.light_source.active
    assert e.world_time.turn==before+1
    ev.record['ward_extinguishes_torch']=dict(turn=e.world_time.turn,torch=[i.turns_lit for i in e.player.inventory.items if i.light_data],hp=e.player.fighter.hp)
    capture('ward-displaces-light');yield from torch(e,True,key,choose)
    assert e.player.equipment.slots['offhand'].item_id=='tallow_torch'
    # Real withdrawal and reposition in the existing arrival room, under active AI.
    yield from walk(e,[(ox+3,oy+12)],key)
    from components.ai import _creature_can_see_player
    for _ in range(12):
        if (guard is None or getattr(guard,'_last_known_px',None) is None
                or _creature_can_see_player(guard,e.player,e.local_map,1,engine=e)):break
        yield key(pygame.K_z,'z')
    ev.record['withdrawal']=dict(start=ev.record['start'],finish=state(e),guard_trail=None if guard is None else [getattr(guard,'_last_known_px',None),getattr(guard,'_last_known_py',None)])
    assert e.player.fighter.hp>0 and ward in e.player.inventory.items
    capture('withdrawn-to-return-stair');yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    assert e.current_submap_id is None
    yield from torch(e,False,key,choose)
    # This acquired reward now supplies an actual outdoor protection choice.
    yield from inventory(e,ward,key,choose);assert e.player.equipment.slots['offhand'] is ward
    yield key(pygame.K_F5);archive=archive_checkpoint(e,out,'altered-exit')
    ev.record.update(finish=state(e),checkpoint=str(archive),completion=True)


def lure(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory
    from engine.effect_lifecycle import valid_throw
    from engine.sound import propagation,STRENGTH,REFERENCE_HEARING
    ox,oy=room_coordinates(e);guard=next(a for a in e.entities if a is not e.player and getattr(a,'_creature_id','')=='hollow_revenant')
    ev.record.update(controls='Disposable continuation from the common genuinely prepared entry. Ordinary flint consumption, source-correct investigation and far opening; normal AI/FOV/survival. Full-state route/target assistance, no actor or resource staging.',start=state(e))
    yield from walk(e,[(ox+10,oy+11)],key)
    assert getattr(guard,'_last_known_px',None) is None,'The lure is intentionally used before genuine player contact'
    shard=e.player.inventory.get_by_id('flint_shard');assert shard
    yield from inventory(e,shard,key,choose)
    candidates=[]
    for x in range(e.local_map.width):
        for y in range(e.local_map.height):
            if y>oy+7 or x>=guard.x or not valid_throw(e,x,y):continue
            cost=propagation(e.local_map,x,y,12).get((guard.x,guard.y))
            if cost is not None and cost<=STRENGTH['flint']+guard.perception.hearing_radius-REFERENCE_HEARING:
                candidates.append(((x-(ox+20))**2+(y-(oy+4))**2,-cost,(x,y),cost))
    assert candidates,'No honest pre-contact clatter target'
    _,_,impact,cost=max(candidates)
    before=(guard.x,guard.y);turn=e.world_time.turn
    yield from aim(e,impact,key)
    assert not e.player.inventory.contains(shard)
    ev.record['lure']=dict(impact=list(impact),received_cost=cost,guard_before=list(before),throw_phase=e.world_time.turn-turn)
    if (guard.x,guard.y)==before:yield key(pygame.K_z,'z')
    assert (guard.x,guard.y)!=before
    assert getattr(guard,'_last_known_px',None) is None
    assert any(r['actors'] and r['actors'][0]['state']=='investigating' and r['actors'][0]['trail']==[None,None] for r in ev.record['encounter'])
    ev.record['lure'].update(route_trace_guard=[guard.x,guard.y],guard_visible=bool(e.local_map.visible[guard.x,guard.y]),turn=e.world_time.turn,interest=copy.deepcopy(guard.ai.sound_interest),feedback='Player clatter is visible/logged. Hidden guard movement is full-state verification telemetry; no hidden identity or outcome is shown in UI.')
    capture('clatter-before-far-passage')
    yield key(pygame.K_RIGHT)
    yield from walk(e,[(ox+20,oy+8)],key)
    assert getattr(guard,'_last_known_px',None) is None
    yield from finish_encounter(e,key,capture,choose,ev,out)


def musk(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory
    from engine.effect_lifecycle import valid_throw,zone_covers
    ox,oy=room_coordinates(e);guard=next(a for a in e.entities if a is not e.player and getattr(a,'_creature_id','')=='hollow_revenant')
    ev.record.update(controls='Independent disposable continuation of the same entry checkpoint. Direct opening, genuine contact, one actually prepared musk pellet, finite passage and withdrawal under recovered ordinary AI. Full-state route/target assistance; no health, actor, timer, fuel or supply edits.',start=state(e))
    yield from walk(e,[(ox+10,oy+7)],key)
    for _ in range(3):
        if getattr(guard,'_last_known_px',None) is not None:break
        yield key(pygame.K_z,'z')
    assert getattr(guard,'_last_known_px',None) is not None,'Genuine contact precedes prepared disruption'
    ev.record['genuine_contact']=dict(turn=e.world_time.turn,guard=[guard.x,guard.y],player=[e.player.x,e.player.y],hp=e.player.fighter.hp)
    pellet=e.player.inventory.get_by_id('musk_pellet');assert pellet
    yield from inventory(e,pellet,key,choose)
    candidates=[]
    for x in range(e.local_map.width):
        for y in range(e.local_map.height):
            if valid_throw(e,x,y) and zone_covers(e.local_map,dict(x=x,y=y,radius=3,turns_remaining=6),guard.x,guard.y):
                candidates.append(((x-guard.x)**2+(y-guard.y)**2,(x,y)))
    assert candidates,'No valid prepared impact';impact=min(candidates)[1]
    before=(guard.x,guard.y);turn=e.world_time.turn;yield from aim(e,impact,key)
    assert not e.player.inventory.contains(pellet) and (guard.x,guard.y)==before
    assert e.local_map.disruption_zones[-1]['turns_remaining']==5
    ev.record['musk']=dict(impact=list(impact),guard=list(before),throw_phase=e.world_time.turn-turn,remaining=5)
    capture('visible-finite-musk-passage')
    yield from walk(e,[(ox+15,oy+4)],key)
    yield from finish_encounter(e,key,capture,choose,ev,out)


def homeward(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,archive_checkpoint
    from engine.save_components import serialize_item
    from engine.save_manager import _serialize_entity
    from g1_support import fingerprint
    assert e.current_submap_id is None and tuple([e.world_x,e.world_y])==DESTINATION[:2]
    ev.record.update(controls='Separate-process cold continuation of the altered exit. Ordinary re-entry/return, then every planned reciprocal crossing replayed in reverse with normal AI, survival and actual acquired Ward. No scene regeneration or supply reset.',start=state(e))
    ward=e.player.inventory.get_by_id('faceted_ward');assert ward and e.player.equipment.slots['offhand'] is ward
    # Cold ordinary revisit of the saved room, with generation explicitly forbidden.
    with patch('engine.scene_generation.create_submap',side_effect=AssertionError('owned room must not regenerate')):
        yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==DESTINATION[2]
    assert not any(i.item_id in ('faceted_ward','letter') for rows in e.local_map.floor_objects.values() for i in rows)
    ev.record['cold_revisited_room']=dict(actors=[_serialize_entity(a) for a in e.entities if a is not e.player],floor=[[list(xy),[i.item_id for i in rows]] for xy,rows in e.local_map.floor_objects.items()],zones=copy.deepcopy(e.local_map.disruption_zones),fingerprint=fingerprint(e.local_map,[a for a in e.entities if a is not e.player]))
    capture('cold-ordinary-room-revisit');yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    for leg in reversed(ROUTE['chosen']['legs']):
        yield from planned_cross(e,leg,key,reverse=True);yield from provisions(e,key,choose)
    assert (e.world_x,e.world_y)==(73,99)
    lab=e.world_map.get(73,99).submaps[0].submap_id
    stairs={xy for xy,sid in e.local_map.submap_links.items() if sid==lab}
    yield from walk(e,stairs,key)
    # The new shield was carried outdoors; underground travel calls for held light.
    before=e.world_time.turn;yield from torch(e,True,key,choose)
    assert e.world_time.turn==before+1 and e.player.equipment.slots['offhand'].item_id=='tallow_torch'
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==lab and e.player.fighter.hp>0
    assert e.player.inventory.contains(ward)
    ev.record['later_light_choice']=dict(ward_owned=True,offhand='tallow_torch',paid=True,torch_used=[i.turns_lit for i in e.player.inventory.items if i.light_data])
    capture('returned-ward-light-choice');yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'returned-ward')
    ev.record.update(finish=state(e),checkpoint=str(archive),completion=True)


def tracked(actions):
    def run(e,key,capture,choose,ev,out):
        original=e._advance_turn
        def advance():
            original();ev.record.setdefault('ledger',[]).append(dict(turn=e.world_time.turn,chunk=[e.world_x,e.world_y],submap=e.current_submap_id,hp=e.player.fighter.hp,hunger=e.player.needs.hunger,thirst=e.player.needs.thirst,torch_used=[i.turns_lit for i in e.player.inventory.items if i.light_data],food=sum(i.item_id=='crow_jerky' for i in e.player.inventory.items),water=sum(i.item_id=='water_flask' for i in e.player.inventory.items)))
            if e.current_submap_id==DESTINATION[2]:
                ev.record.setdefault('encounter',[]).append(dict(turn=e.world_time.turn,player=[e.player.x,e.player.y],hp=e.player.fighter.hp,zones=copy.deepcopy(e.local_map.disruption_zones),actors=[dict(position=[a.x,a.y],state=a.ai.state.value,interest=copy.deepcopy(a.ai.sound_interest),trail=[getattr(a,'_last_known_px',None),getattr(a,'_last_known_py',None)],visible=bool(e.local_map.visible[a.x,a.y])) for a in e.entities if a is not e.player and getattr(a,'ai',None)]))
        with patch.object(e,'_advance_turn',new=advance):yield from actions(e,key,capture,choose,ev,out)
    return run


def main():
    p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--stage',choices=['preparation','destination_entry','lure','musk','homeward'],default='preparation');p.add_argument('--resume',type=Path);p.add_argument('--route',type=Path);a=p.parse_args()
    global ROUTE,DESTINATION
    if a.route:
        ROUTE=json.loads(a.route.read_text());DESTINATION=tuple(ROUTE['chosen']['target'])
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    from g12_journey import run_stage
    out=a.evidence.resolve();out.mkdir(parents=True,exist_ok=True)
    with (out/(a.stage+'-output.txt')).open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
        result=run_stage(out,a.stage,tracked(globals()[a.stage]),a.resume.resolve() if a.resume else None,max_frames=5000,max_seconds=900,max_turns=2500)
    finish=result.get('finish',{})
    print(json.dumps(dict(passed=True,stage=a.stage,checkpoint=result.get('checkpoint'),finish={k:finish.get(k) for k in ('turn','hp','hunger','thirst','inventory','torch')})))


if __name__=='__main__':main()
