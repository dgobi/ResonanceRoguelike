"""One declared G22 continuation, original loop and observation-limited navigation.

Decision helpers read only explored terrain and currently visible objects/actors.
The instrumentation ledger may measure full state, never select a route with it.
"""
import argparse
import heapq
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
STEPS={(-1,0):1073741904,(1,0):1073741903,(0,-1):1073741906,(0,1):1073741905,
       (-1,-1):1073741919,(1,-1):1073741921,(-1,1):1073741913,(1,1):1073741915}
EXHAUSTED={}
LEDGER=None


def observed(e):
    m=e.local_map
    return dict(position=[e.player.x,e.player.y], square=[e.world_x,e.world_y],
        terrain=[dict(x=x,y=y,terrain=str(m.tiles[x,y]['terrain']),decor=m.decor.get((x,y)))
                 for x in range(m.width) for y in range(m.height) if m.visible[x,y]],
        actors=[dict(name=a.name,x=a.x,y=a.y) for a in e.entities if a is not e.player and m.visible[a.x,a.y]],
        objects=[dict(x=x,y=y,names=[i.name for i in rows]) for (x,y),rows in m.floor_objects.items() if m.visible[x,y]])


def record(e,label):
    from g20_journey import state
    row=dict(label=label,state=state(e),observed=observed(e))
    LEDGER.append(row)
    print(json.dumps(dict(label=label,turn=e.world_time.turn,hp=e.player.fighter.hp,square=[e.world_x,e.world_y],position=[e.player.x,e.player.y])),flush=True)


def route(e,goals,aim,avoid=True,strict=False):
    """Eight-way Dijkstra only over remembered terrain, visible occupants."""
    from generation.access import enterable
    m=e.local_map;start=(e.player.x,e.player.y)
    occupied={(a.x,a.y) for a in e.entities if a is not e.player and a.blocks_movement and m.visible[a.x,a.y]}
    costs={start:0.};parents={start:None};todo=[(0.,start)]
    while todo:
        cost,p=heapq.heappop(todo)
        if cost!=costs[p]:continue
        for dx,dy in STEPS:
            q=p[0]+dx,p[1]+dy
            if strict and q in occupied:continue
            if not m.in_bounds(*q) or not m.explored[q] or not enterable(m,q,e.data):continue
            td=e.data.terrain.get(str(m.tiles[q]['terrain']),{})
            threat=sum(max(0,6-max(abs(q[0]-x),abs(q[1]-y)))*2 for x,y in occupied) if avoid else 0
            nxt=cost+td.get('move_cost',1)+threat+(30 if q in occupied else 0)
            if nxt<costs.get(q,float('inf')):costs[q]=nxt;parents[q]=p;heapq.heappush(todo,(nxt,q))
    available=goals & costs.keys()
    if available:end=min(available,key=lambda p:(costs[p],p))
    else:
        exhausted=EXHAUSTED.setdefault(id(m),set())
        frontier=[p for p in costs if p not in exhausted and p!=start and any(m.in_bounds(p[0]+dx,p[1]+dy) and not m.explored[p[0]+dx,p[1]+dy] for dx,dy in STEPS)]
        if not frontier:raise AssertionError('Observed reachable terrain has no remaining frontier toward '+str(aim))
        end=min(frontier,key=lambda p:(max(abs(p[0]-aim[0]),abs(p[1]-aim[1]))+costs[p]*.3,p))
    result=[end]
    while parents[result[-1]] is not None:result.append(parents[result[-1]])
    return result[::-1]


def walk(e,goals,key,*,aim=None,avoid=True,strict=False,stop_on_harm=False,limit=1000):
    goals=set(goals);aim=aim or min(goals)
    hp=e.player.fighter.hp
    for _ in range(limit):
        if (e.player.x,e.player.y) in goals:return True
        path=route(e,goals,aim,avoid,strict);a,b=path[:2]
        before=int(e.local_map.explored.sum());at=(e.player.x,e.player.y)
        yield key(STEPS[b[0]-a[0],b[1]-a[1]])
        if e.player.fighter.hp<=0:
            record(e,'fatal ordinary journey failure')
            LEDGER[-1]['last_messages']=[m.text for m in e.log.messages[-20:]]
        assert e.player.fighter.hp>0 and not e.player_invincible,'Ordinary journey died'
        if len(path)==2 and int(e.local_map.explored.sum())==before:EXHAUSTED.setdefault(id(e.local_map),set()).add(b)
        if stop_on_harm and e.player.fighter.hp<hp:return False
    raise AssertionError('Finite observed movement budget')


def approach(e,xy,key):
    goals={(xy[0]+dx,xy[1]+dy) for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))}
    yield from walk(e,goals,key,aim=xy)


def visible_tiles(e,predicate):
    m=e.local_map
    return [(x,y) for x in range(m.width) for y in range(m.height) if m.visible[x,y] and predicate(x,y)]


def discover(e,predicate,key,*,aim=(40,21),limit=350):
    for _ in range(limit):
        found=visible_tiles(e,predicate)
        if found:return min(found,key=lambda p:(max(abs(p[0]-e.player.x),abs(p[1]-e.player.y)),p))
        path=route(e,set(),aim);a,b=path[:2];before=int(e.local_map.explored.sum())
        yield key(STEPS[b[0]-a[0],b[1]-a[1]])
        assert e.player.fighter.hp>0,'Ordinary journey died during scouting'
        if len(path)==2 and int(e.local_map.explored.sum())==before:EXHAUSTED.setdefault(id(e.local_map),set()).add(b)
    raise AssertionError('Finite observed landmark search budget')


def cross(e,dx,dy,key,*,strict=False):
    m=e.local_map
    edge=({(m.width-1 if dx>0 else 0,y) for y in range(m.height)} if dx else {(x,m.height-1 if dy>0 else 0) for x in range(m.width)})
    aim=(m.width-1 if dx>0 else 0,e.player.y) if dx else (e.player.x,m.height-1 if dy>0 else 0)
    yield from walk(e,edge,key,aim=aim,strict=strict)
    before=(e.world_x,e.world_y)
    yield key(STEPS[dx,dy])
    assert (e.world_x,e.world_y)==(before[0]+dx,before[1]+dy),'Observed edge did not permit crossing'
    record(e,'ordinary crossing')


def travel(e,target,key,choose):
    from g20_journey import provisions
    # Predeclared coarse policy: resolve east/west displacement, then north/south.
    while (e.world_x,e.world_y)!=tuple(target):
        dx=(target[0]>e.world_x)-(target[0]<e.world_x)
        dy=0 if dx else (target[1]>e.world_y)-(target[1]<e.world_y)
        yield from cross(e,dx,dy,key);yield from provisions(e,key,choose)


def read_owned(e,item,key,choose,capture,label):
    import pygame
    from g12_journey import inventory
    yield from inventory(e,item,key,choose)
    assert e.text_reader.open
    pages=[p['text'] for p in e.text_reader._def['pages']]
    for n in range(len(pages)):
        capture(label+'-'+str(n))
        if n+1<len(pages):yield key(pygame.K_RIGHT)
    yield key(pygame.K_ESCAPE)
    if e.inventory_screen.open:yield key(pygame.K_i)
    return pages


def placement_choice(e,key,*,drying=False):
    """Choose an adjacent visibly clear tile through the placement cursor."""
    valid=e._is_valid_drying if drying else e._is_valid_placement
    choices=visible_tiles(e,lambda x,y:(x,y)!=(e.player.x,e.player.y)
        and max(abs(x-e.player.x),abs(y-e.player.y))<=1 and not e.local_map.decor.get((x,y)) and valid(x,y))
    assert choices,'No visibly valid adjacent preparation spot'
    target=min(choices)
    while e._placement_cursor_x!=target[0]:yield key(STEPS[(target[0]>e._placement_cursor_x)-(target[0]<e._placement_cursor_x),0])
    while e._placement_cursor_y!=target[1]:yield key(STEPS[0,(target[1]>e._placement_cursor_y)-(target[1]<e._placement_cursor_y)])
    return target


def read_start(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import interact,inventory,archive_checkpoint
    from g16_journey import close
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[])
    ev.record['policy']='Fresh seed 20261023; real start/resources/time, original input loop. Dijkstra uses explored tiles, visible actors/objects only. Destinations parsed from rendered report pages. Coarse travel resolves horizontal then vertical displacement; scout nearest frontier toward the next edge or visible landmark. No hidden-scene route ranking or tactical inputs. Existing deterministic driver gameplay RNG 20261020, not reseeded for outcomes.'
    record(e,'real fresh start')
    assert e.world_time.turn==480 and e.player.fighter.hp==60
    yield None
    for iid in ('crude_blade','leather_jack'):yield from inventory(e,e.player.inventory.get_by_id(iid),key,choose)
    xy=next((xy for xy,rows in e.local_map.floor_objects.items() if e.local_map.visible[xy] and any(i.text_id=='lab_route_sheet_a' for i in rows)))
    yield from approach(e,xy,key);yield from interact(e,xy,key);yield from close(e,key)
    sheet=next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    assert not e.world_map.learned_reports
    yield key(pygame.K_F5)
    unread=e.world_time.turn
    pages=yield from read_owned(e,sheet,key,choose,capture,'route-sheet')
    assert e.world_time.turn==unread+1
    ev.record['rendered_report']=pages
    targets=[list(map(int,re.search(r'square \((\d+), (\d+)\)',p).groups())) for p in pages[1:]]
    ev.record['destinations_from_reader']=dict(workshop=targets[0],ward_store=targets[1])
    yield key(pygame.K_i);yield from choose(e,sheet);yield key(pygame.K_d,'d');yield key(pygame.K_i)
    assert len(e.world_map.learned_reports)==2
    yield key(pygame.K_COMMA,',')
    assert e.player.inventory.contains(sheet)
    yield key(pygame.K_F9)
    assert not e.world_map.learned_reports and e.world_time.turn==unread
    sheet=next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    yield from read_owned(e,sheet,key,choose,capture,'reread-after-f9')
    record(e,'read recovered original report after divergent F9')
    yield key(pygame.K_F5)
    archive=archive_checkpoint(e,out,'read-lab')
    ev.record.update(checkpoint=str(archive),completion=True)


def preparation(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,interact,select_prompt,recipe,archive_checkpoint
    from g16_journey import close
    from g20_journey import torch,provisions
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[]);record(e,'cold read laboratory')
    # The target is reobtained from the same frozen rendered document.
    sheet=next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    pages=yield from read_owned(e,sheet,key,choose,capture,'original-report-cold')
    target=list(map(int,re.search(r'square \((\d+), (\d+)\)',pages[1]).groups()))
    home=(e.world_x,e.world_y)
    stairs=visible_tiles(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
    yield from walk(e,stairs,key);yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    home_entry=e.player.x,e.player.y
    yield key(pygame.K_m,'m');assert e.mode.value=='overmap'
    turn=e.world_time.turn
    targets=[list(map(int,re.search(r'square \((\d+), (\d+)\)',p).groups())) for p in pages[1:]]
    for destination in targets:
        for _ in range(20):
            if e.overmap_cursor_x==destination[0]:break
            yield key(STEPS[(destination[0]>e.overmap_cursor_x)-(destination[0]<e.overmap_cursor_x),0])
        for _ in range(20):
            if e.overmap_cursor_y==destination[1]:break
            yield key(STEPS[0,(destination[1]>e.overmap_cursor_y)-(destination[1]<e.overmap_cursor_y)])
        assert [e.overmap_cursor_x,e.overmap_cursor_y]==destination
        capture('reported-square-'+str(destination[0])+'-'+str(destination[1]))
    yield key(pygame.K_RETURN);assert e.world_time.turn==turn and e.current_submap_id is None
    yield from torch(e,False,key,choose)
    # Gather from an actually observed rock before leaving the waking forest.
    rock=yield from discover(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='flint_rock',key,aim=home_entry,limit=180)
    yield from approach(e,rock,key)
    for _ in range(12):
        yield from interact(e,rock,key);yield from close(e,key)
        if e.player.inventory.has('flint_shard'):break
    assert e.player.inventory.has('flint_shard')
    record(e,'observed flint gathered')
    yield from travel(e,target,key,choose)
    # Search by visible preparation note, never by building IDs/placement data.
    note_xy=yield from discover(e,lambda x,y:any(i.text_id=='workshop_musk_notes_c' for i in e.local_map.floor_objects.get((x,y),[])),key)
    record(e,'observed workshop note');capture('workshop-observed')
    yield from approach(e,note_xy,key);yield from interact(e,note_xy,key)
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,'research_note',key)
    yield from close(e,key)
    note=next(i for i in e.player.inventory.items if i.text_id=='workshop_musk_notes_c')
    ev.record['preparation_note']=yield from read_owned(e,note,key,choose,capture,'musk-procedure')
    # Two crates adjacent to visible tables. Inspect each before choosing items.
    crates=visible_tiles(e,lambda x,y:e.local_map.decor.get((x,y))=='crate')
    assert len(crates)>=2,'Workshop crates must be visible before selecting them'
    for xy in sorted(crates,key=lambda p:(max(abs(p[0]-note_xy[0]),abs(p[1]-note_xy[1])),p))[:2]:
        yield from approach(e,xy,key);yield from interact(e,xy,key)
        # Contents are consulted only after the real chest UI has opened.
        prompt=e.interaction_cursor._selection_prompt;assert prompt
        offered=[i.item_id for i in prompt['items']]
        ev.record.setdefault('opened_crates',[]).append(dict(square=target,position=xy,offered=offered))
        for iid in offered:
            if e.interaction_cursor._selection_prompt:yield from select_prompt(e,iid,key)
            else:yield from interact(e,xy,key);yield from select_prompt(e,iid,key)
        yield from close(e,key)
        if 'wood_bundle' in offered:
            yield from interact(e,xy,key);yield key(pygame.K_x,'x');assert e.interaction_cursor._dismantle_prompt
            yield key(pygame.K_RETURN);yield from close(e,key);yield from interact(e,xy,key);yield from close(e,key)
    assert e.player.inventory.has('herbal_dressing') and e.player.inventory.has('stalker_musk_gland')
    record(e,'finite supplies acquired');capture('finite-dressing-owned')
    yield from torch(e,True,key,choose)
    yield from recipe(e,'campfire',key)
    fire=yield from placement_choice(e,key)
    yield key(pygame.K_RETURN);yield from interact(e,fire,key);yield from close(e,key)
    yield from recipe(e,'musk_pellet',key);spot=yield from placement_choice(e,key,drying=True)
    yield key(pygame.K_RETURN)
    for _ in range(9):yield key(pygame.K_z,'z')
    yield from approach(e,spot,key);yield from interact(e,spot,key);yield from close(e,key)
    assert e.player.inventory.has('musk_pellet')
    record(e,'prepared musk from actual gland and fire');capture('prepared-musk')
    yield from torch(e,False,key,choose);yield from provisions(e,key,choose)
    yield from travel(e,home,key,choose)
    yield from walk(e,{home_entry},key)
    stairs=yield from discover(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_down',key,aim=home_entry)
    yield from walk(e,{stairs},key);yield from torch(e,True,key,choose)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id and e.player.inventory.has('herbal_dressing') and e.player.inventory.has('musk_pellet')
    record(e,'returned alive to laboratory with preparation and treatment');capture('prepared-return')
    yield key(pygame.K_F5);ev.record.update(checkpoint=str(archive_checkpoint(e,out,'prepared-return')),completion=True)


def ward(e,key,capture,choose,ev,out):
    import pygame
    from g12_journey import inventory,interact,select_prompt,archive_checkpoint
    from g16_journey import close
    from g20_journey import torch,provisions,aim
    from engine.effect_lifecycle import valid_throw,zone_covers
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[]);record(e,'cold prepared laboratory; second outing')
    home=(e.world_x,e.world_y)
    sheet=next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    pages=yield from read_owned(e,sheet,key,choose,capture,'report-second-outing')
    target=list(map(int,re.search(r'square \((\d+), (\d+)\)',pages[2]).groups()))
    ev.record['destination_from_rendered_report']=target
    stairs=visible_tiles(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
    yield from walk(e,stairs,key);yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    home_entry=e.player.x,e.player.y
    yield from torch(e,False,key,choose);yield from provisions(e,key,choose)
    yield from travel(e,target,key,choose)
    record(e,'arrived reported Ward square')
    entry=yield from discover(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_down',key)
    yield from walk(e,{entry},key);yield from torch(e,True,key,choose)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id
    inside_entry=e.player.x,e.player.y
    record(e,'ordinary store entry');capture('store-entry')
    note_xy=next(xy for xy,rows in e.local_map.floor_objects.items() if e.local_map.visible[xy] and any(i.text_id=='barrow_ward_store_note_a' for i in rows))
    yield from approach(e,note_xy,key);yield from interact(e,note_xy,key)
    if e.interaction_cursor._selection_prompt:yield from select_prompt(e,'letter',key)
    yield from close(e,key)
    note=next(i for i in e.player.inventory.items if i.text_id=='barrow_ward_store_note_a')
    ev.record['ward_note']=yield from read_owned(e,note,key,choose,capture,'ward-note')
    record(e,'direct approach before spending musk; declared mistake begins')
    hp=e.player.fighter.hp
    # Scout north/east of the known entry, following the displayed dividing-wall
    # clue. No authored-room coordinates or hidden guard feed this choice.
    reward=None
    for _ in range(60):
        found=visible_tiles(e,lambda x,y:any(i.item_id=='faceted_ward' for i in e.local_map.floor_objects.get((x,y),[])))
        if found:reward=found[0]
        if reward:
            reached=yield from walk(e,{reward},key,avoid=False,stop_on_harm=True,limit=80)
            if not reached or e.player.fighter.hp<hp:break
            # One ordinary pickup attempt completes a direct commitment; there
            # is no waiting under attacks for an injury number.
            yield from interact(e,reward,key);yield from close(e,key)
            break
        path=route(e,set(),(inside_entry[0]+18,inside_entry[1]-8),avoid=False);a,b=path[:2]
        yield key(STEPS[b[0]-a[0],b[1]-a[1]])
        assert e.player.fighter.hp>0
        if e.player.fighter.hp<hp:break
    record(e,'setback measurement before withdrawal');capture('actual-setback')
    if e.player.fighter.hp==hp:
        ev.record['local_revision']='Original direct pickup caused no injury. One predeclared local revision: equip the actual Ward while adjacent to the observed keeper, then withdraw. No waits or HP/RNG changes.'
        assert (e.world_time.turn,e.player.fighter.hp,e.player.x,e.player.y)==(1793,57,48,18),'Original no-injury path must reproduce before its single local revision'
        yield key(pygame.K_F5)
        ev.record['no_injury_checkpoint']=str(archive_checkpoint(e,out,'direct-pickup-no-injury'))
        yield from inventory(e,e.player.inventory.get_by_id('faceted_ward'),key,choose)
        record(e,'one declared equipment delay beside keeper')
        yield from walk(e,{inside_entry},key,stop_on_harm=True)
    assert e.player.fighter.hp<hp,'Single permitted revision also produced no injury; no further attempts'
    record(e,'first real injury after declared mistake')
    yield key(pygame.K_F5);ev.record['injury_checkpoint']=str(archive_checkpoint(e,out,'first-injury'))
    (out/'continuation-context.json').write_text(json.dumps(dict(inside_entry=inside_entry,home=home,home_entry=home_entry,reward=reward)))
    yield from recover_actions(e,key,capture,choose,ev,out,inside_entry,home,home_entry,reward)


def recover_actions(e,key,capture,choose,ev,out,inside_entry,home,home_entry,reward):
    import pygame
    from g12_journey import inventory,archive_checkpoint
    from g20_journey import torch
    yield from torch(e,True,key,choose)
    yield from walk(e,{tuple(inside_entry)},key,strict=True)
    record(e,'withdrawn to known entry; before dressing');capture('withdrawn')
    dressing=e.player.inventory.get_by_id('herbal_dressing');assert dressing
    before=e.player.fighter.hp;turn=e.world_time.turn
    yield from inventory(e,dressing,key,choose)
    ev.record['treatment']=dict(before_hp=before,after_hp=e.player.fighter.hp,turns=e.world_time.turn-turn,
        owned_after=e.player.inventory.contains(dressing),remaining=e.player.inventory.has('herbal_dressing'))
    assert not e.player.inventory.contains(dressing) and e.player.fighter.hp>before
    record(e,'finite owned dressing spent after actual injury');capture('treated')
    yield key(pygame.K_F5);ev.record['treated_checkpoint']=str(archive_checkpoint(e,out,'treated'))
    (out/'continuation-context.json').write_text(json.dumps(dict(inside_entry=inside_entry,home=home,home_entry=home_entry,reward=reward)))
    yield from finish_ward(e,key,capture,choose,ev,out,inside_entry,home,home_entry,reward)


def finish_ward(e,key,capture,choose,ev,out,inside_entry,home,home_entry,reward):
    import pygame
    from g12_journey import inventory,interact,archive_checkpoint
    from g16_journey import close
    from g20_journey import torch,provisions,aim
    from engine.effect_lifecycle import valid_throw,zone_covers
    inside_entry,home,home_entry=tuple(inside_entry),tuple(home),tuple(home_entry)
    reward=tuple(reward) if reward else None
    # The store note warned that the Ward occupies the torch hand. Restore the
    # retained light through its ordinary item action before revising the plan.
    yield from torch(e,True,key,choose)
    # Revised plan: use the finite preparation when the observed keeper is in
    # throw range, then take the visible opening and retrieve the real Ward.
    used=False
    for _ in range(100):
        guards=[a for a in e.entities if a is not e.player and e.local_map.visible[a.x,a.y] and a.is_alive]
        if guards and not used:
            guard=min(guards,key=lambda a:max(abs(a.x-e.player.x),abs(a.y-e.player.y)))
            pellet=e.player.inventory.get_by_id('musk_pellet');assert pellet
            yield from inventory(e,pellet,key,choose)
            impacts=visible_tiles(e,lambda x,y:valid_throw(e,x,y) and zone_covers(e.local_map,dict(x=x,y=y,radius=3,turns_remaining=6),guard.x,guard.y))
            if impacts:
                impact=min(impacts,key=lambda p:((p[0]-guard.x)**2+(p[1]-guard.y)**2,p))
                yield from aim(e,impact,key)
                if e.inventory_screen.open:yield key(pygame.K_i)
                used=True;record(e,'owned musk spent for revised approach');capture('musk-revised-approach')
            else:
                yield key(pygame.K_ESCAPE)
                if e.inventory_screen.open:yield key(pygame.K_i)
        found=visible_tiles(e,lambda x,y:any(i.item_id=='faceted_ward' for i in e.local_map.floor_objects.get((x,y),[])))
        if found:reward=found[0]
        if e.player.inventory.has('faceted_ward') and used:break
        if reward and not e.player.inventory.has('faceted_ward') and (e.player.x,e.player.y)==reward:
            yield from interact(e,reward,key);yield from close(e,key);continue
        owned=e.player.inventory.has('faceted_ward')
        goal=(guards[0].x,guards[0].y) if owned and guards else reward
        if goal and (e.player.x,e.player.y)==tuple(goal):goal=tuple(inside_entry)
        path=route(e,{goal} if goal else set(),goal or (inside_entry[0]+18,inside_entry[1]-8),avoid=False);a,b=path[:2]
        yield key(STEPS[b[0]-a[0],b[1]-a[1]])
        assert e.player.fighter.hp>0
    assert e.player.inventory.has('faceted_ward') and used
    record(e,'actual bronze Ward retained after treatment and revised plan');capture('ward-retained')
    yield from walk(e,{inside_entry},key)
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    assert e.current_submap_id is None
    record(e,'withdrew from store alive')
    yield from torch(e,False,key,choose);yield from provisions(e,key,choose)
    ward=e.player.inventory.get_by_id('faceted_ward');assert ward
    if e.player.equipment.slots.get('offhand') is not ward:
        yield from inventory(e,ward,key,choose)
    record(e,'actual Ward equipped in freed hand for exposed return')
    # Return along the travelled outbound row, using its observed shallows.
    # The first new-row geometric return died of thirst; no source is added.
    yield from cross(e,0,1,key,strict=True)
    while e.world_x!=home[0]:
        yield from cross(e,1 if home[0]>e.world_x else -1,0,key,strict=True)
        water=[(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
               if e.local_map.explored[x,y] and e.data.terrain.get(str(e.local_map.tiles[x,y]['terrain']),{}).get('drinkable')]
        if water and e.player.needs.thirst>.5:
            xy=min(water,key=lambda p:(max(abs(p[0]-e.player.x),abs(p[1]-e.player.y)),p))
            yield from approach(e,xy,key)
            for _ in range(2):
                if not e.player.inventory.has('empty_water_skin'):break
                yield from interact(e,xy,key);yield from close(e,key)
            skin=e.player.inventory.get_by_id('water_skin');assert skin,'Observed shallows did not refill the owned vessel'
            yield from inventory(e,skin,key,choose);record(e,'ordinary refill and drink at previously observed shallows')
        yield from provisions(e,key,choose)
    yield from walk(e,{home_entry},key)
    yield from torch(e,True,key,choose);yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id and e.player.inventory.has('faceted_ward')
    record(e,'second outing returned alive with actual Ward');capture('returned-ward')
    yield key(pygame.K_F5);ev.record.update(checkpoint=str(archive_checkpoint(e,out,'returned-ward')),completion=True)


def cold_return(e,key,capture,choose,ev,out):
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[]);record(e,'cold used-treatment continuation; no refunded dressing')
    assert not e.player.inventory.has('herbal_dressing')
    context=json.loads(CONTEXT.read_text())
    yield from finish_ward(e,key,capture,choose,ev,out,**context)


def cold_recover(e,key,capture,choose,ev,out):
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[]);record(e,'cold genuine first injury; finite response continuation')
    yield from recover_actions(e,key,capture,choose,ev,out,**json.loads(CONTEXT.read_text()))


def store_revisit(e,key,capture,choose,ev,out):
    import copy
    import pygame
    from g12_journey import archive_checkpoint
    global LEDGER
    LEDGER=ev.record.setdefault('ledger',[])
    before=copy.deepcopy(e.world_map.location_reports)
    assert not e.player.inventory.has('herbal_dressing') and e.player.inventory.has('faceted_ward')
    entry=next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
               if e.local_map.explored[x,y] and str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
    yield from walk(e,{entry},key,strict=True)
    sub=e.current_submap_id
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id==sub
    assert not any(i.item_id=='faceted_ward' for rows in e.local_map.floor_objects.values() for i in rows)
    sheet=next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    ev.record['original_report_after_revisit']=yield from read_owned(e,sheet,key,choose,capture,'original-sheet-revisit')
    assert e.world_map.location_reports==before and not e.player.inventory.has('herbal_dressing')
    record(e,'cold treatment depletion and ordinary store revisit retain report and taken Ward')
    yield key(pygame.K_F5);ev.record.update(checkpoint=str(archive_checkpoint(e,out,'revisited-store')),completion=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['read','preparation','ward','return','recover','revisit'],required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--resume',type=Path);p.add_argument('--context',type=Path);a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    from g12_journey import run_stage
    a.evidence=a.evidence.resolve();a.evidence.mkdir(parents=True,exist_ok=True)
    global CONTEXT
    CONTEXT=a.context.resolve() if a.context else None
    run_stage(a.evidence,a.stage,{'read':read_start,'preparation':preparation,'ward':ward,'return':cold_return,'recover':cold_recover,'revisit':store_revisit}[a.stage],a.resume,max_frames=6500,max_seconds=900,max_turns=4000)


if __name__=='__main__':main()
