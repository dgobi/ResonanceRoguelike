"""Bounded connected G22A witness. Decisions use ordinary observations/items.

This is a test player, not runtime automation. Full-state persistence inspection
is confined to the cold audit, after play; it never chooses a route or a target.
"""
import argparse
from collections import Counter
import copy
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def visible_hostiles(e):
    return [a for a in e.entities if a is not e.player and a.is_alive
            and e.local_map.visible[a.x, a.y]
            and 'player' in getattr(getattr(a, 'perception', None), 'hostile_to', [])]


def distance(e, a):
    return max(abs(a.x-e.player.x), abs(a.y-e.player.y))


def validate_situation(e, context, *, keeper_delay=False):
    """Reject a replay coincidence, foreign world, stale ownership or unseen keeper."""
    from engine import location_reports
    from engine.spatial import melee_contact
    location_reports.validate(e.world_map)
    assert e.world_map.seed == 20261023 and e.world_map.report_owner == context['owner'], 'Wrong campaign'
    assert e.player.fighter.hp > 0 and not e.player_invincible, 'Living ordinary character required'
    report = next(r for r in e.world_map.location_reports if r['role'] == 'ward_store')
    assert 'ward_store' in e.world_map.learned_reports
    assert [report['target']['x'], report['target']['y']] == list(context['target']), 'Wrong reported destination'
    assert any(i.text_id == 'lab_route_sheet_a' for i in e.player.inventory.items), 'Physical route sheet required'
    assert all(e.player.inventory.has(i) for i in ('herbal_dressing', 'musk_pellet')), 'Owned finite preparation required'
    if keeper_delay:
        assert [e.world_x, e.world_y] == list(context['target'])
        assert e.current_submap_id == context['submap'] == report['target']['id']
        assert e.player.inventory.has('faceted_ward'), 'Genuine owned Ward required'
        assert any(i.text_id == 'barrow_ward_store_note_a' for i in e.player.inventory.items)
        assert any(getattr(a, '_creature_id', '') == 'hollow_revenant'
                   and melee_contact(e.local_map, e.player.x, e.player.y, a.x, a.y)
                   for a in visible_hostiles(e)), 'No observed adjacent keeper; equipment-delay premise absent'
    return True


class Policy:
    def __init__(self, choose, ev):
        self.choose, self.ev = choose, ev
        self.busy = False
        self.second = False
        self.context = None
        self.setback = None
        self.armed_keeper = False
        self.treated = False
        self.pellet_used = False
        self.actions = 0
        self.next_budget = 0
        self.cooked = False

    def record(self, e, reason, **extra):
        if reason == 'cold read laboratory':
            reason = 'same-process laboratory; first outing begins'
        n = e.player.needs
        row = dict(reason=reason, turn=e.world_time.turn, time=e.world_time.time_string,
            hp=e.player.fighter.hp, square=[e.world_x,e.world_y], submap=e.current_submap_id,
            position=[e.player.x,e.player.y], hunger=n.hunger, thirst=n.thirst,
            needs_feedback=[n.hunger_state,n.thirst_state],
            movement_penalty=[n.hunger_move_penalty,n.thirst_move_penalty],
            direct_needs_hp_drain=[n.hunger_hp_drain,n.thirst_hp_drain],
            inventory=dict(Counter(i.item_id for i in e.player.inventory.items)),
            load=e.player.inventory.current_weight, capacity=e.player.inventory.capacity,
            torch=[dict(used=i.turns_lit,remaining=i.burn_turns-i.turns_lit,
                burning=bool(e.player.light_source and e.player.light_source.active
                             and getattr(e.player.light_source,'_item_ref',None) is i))
                for i in e.player.inventory.items if i.light_data],
            offhand=getattr(e.player.equipment.slots.get('offhand'),'item_id',None),
            observed_threats=[dict(name=a.name,position=[a.x,a.y]) for a in visible_hostiles(e)], **extra)
        self.ev.record.setdefault('ledger',[]).append(row)
        print(json.dumps(dict(turn=row['turn'],hp=row['hp'],reason=reason)),flush=True)

    def after_action(self, e, before, event):
        self.actions += 1
        if e.player.fighter.hp > before['hp']:
            self.record(e,'actual HP gain during ordinary action',before_hp=before['hp'],event=event,
                        messages=[m.text for m in e.log.messages[-6:]])
        if e.player.fighter.hp < before['hp']:
            injury = dict(before_hp=before['hp'],after_hp=e.player.fighter.hp,
                          event=event, observed_before=before['threats'],
                          messages=[m.text for m in e.log.messages[-10:]])
            self.record(e,'actual damage during ordinary action',damage=injury)
            if self.second and self.setback is None:
                if self.armed_keeper:
                    case = 'premature Ward equipment beside observed keeper'
                elif e.current_submap_id is None and (before['threats'] or visible_hostiles(e)):
                    case = 'surface pursuit caught continued travel commitment'
                else:
                    case = None
                if case:
                    validate_situation(e,self.context)
                    self.setback = dict(case=case,turn=e.world_time.turn,injury=injury,
                                       ward_already_owned=e.player.inventory.has('faceted_ward'))
                    self.ev.record['setback'] = self.setback
        assert e.player.fighter.hp > 0 and not e.player_invincible, 'Ordinary connected journey died'

    def light(self, e, lit, key, choose=None):
        from g12_journey import inventory
        current = e.player.light_source
        active = bool(current and current.active)
        if active == lit:
            return
        if not lit:
            item = current._item_ref
        else:
            usable = [i for i in e.player.inventory.items if i.light_data and i.turns_lit < i.burn_turns]
            assert usable, 'No carried usable torch'
            item = usable[0]  # finish the older torch before using the finite spare
        turn = e.world_time.turn
        yield from inventory(e,item,key,self.choose)
        assert bool(e.player.light_source and e.player.light_source.active) == lit
        self.record(e,'ordinary light choice',requested_lit=lit,paid_phases=e.world_time.turn-turn)

    def eat_drink(self, e, key):
        from g12_journey import inventory
        for need, forms in (('hunger',('crow_jerky','cooked_meat')),('thirst',('water_flask','water_skin'))):
            if getattr(e.player.needs,need) >= .5:
                item = next((i for i in e.player.inventory.items if i.item_id in forms),None)
                if item:
                    turn = e.world_time.turn
                    form = item.item_id
                    yield from inventory(e,item,key,self.choose)
                    assert not e.player.inventory.contains(item)
                    self.record(e,'ordinary carried provision',form=form,paid_phases=e.world_time.turn-turn)

    def water(self, e, key):
        import g22_journey as j
        from g12_journey import interact
        from g16_journey import close
        from engine.interaction_cursor import InteractionCursor
        if e.current_submap_id is not None or visible_hostiles(e):
            return
        inv = e.player.inventory
        if not inv.has('empty_water_skin') and e.player.needs.thirst < .4:
            return
        # A small local detour to observed/remembered terrain, never unseen water.
        candidates = [(x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
            if e.local_map.explored[x,y]
            and e.data.terrain.get(str(e.local_map.tiles[x,y]['terrain']),{}).get('drinkable')
            and max(abs(x-e.player.x),abs(y-e.player.y)) <= 12]
        if not candidates:
            return
        xy = min(candidates,key=lambda p:(max(abs(p[0]-e.player.x),abs(p[1]-e.player.y)),p))
        self.record(e,'prudent water detour from remembered shallows',water=list(xy))
        yield from j.approach(e,xy,key)
        if visible_hostiles(e) or not InteractionCursor.can_reach(e,*xy):
            return
        for _ in range(sum(i.item_id=='empty_water_skin' for i in inv.items)):
            empty = inv.get_by_id('empty_water_skin')
            turn, weight = e.world_time.turn, inv.current_weight
            yield from interact(e,xy,key)
            yield from close(e,key)
            assert not inv.contains(empty) and inv.has('water_skin'), 'Ordinary refill failed'
            assert e.world_time.turn > turn
            self.record(e,'owned empty vessel refilled before long exposure',paid_phases=e.world_time.turn-turn,
                        weight_before=weight,water=list(xy))
        # E with no empties is the supported adjacent direct-drinking handler.
        if e.player.needs.thirst >= .25 and not inv.has('empty_water_skin'):
            thirst, turn = e.player.needs.thirst, e.world_time.turn
            yield from interact(e,xy,key)
            yield from close(e,key)
            assert e.player.needs.thirst < thirst and e.world_time.turn > turn
            self.record(e,'ordinary direct surface drink; filled vessels retained',paid_phases=e.world_time.turn-turn)

    def musk(self, e, key):
        import g22_journey as j
        import pygame
        from g12_journey import inventory
        from g20_journey import aim
        from engine.effect_lifecycle import valid_throw,zone_covers
        guards = visible_hostiles(e)
        pellet = e.player.inventory.get_by_id('musk_pellet')
        if not guards or not pellet:
            return False
        guard = min(guards,key=lambda a:(distance(e,a),a.x,a.y))
        # valid_throw deliberately requires the real pending cursor/owned item.
        yield from inventory(e,pellet,key,self.choose)
        impacts = j.visible_tiles(e,lambda x,y:valid_throw(e,x,y)
            and zone_covers(e.local_map,dict(x=x,y=y,radius=3,turns_remaining=6),guard.x,guard.y))
        if not impacts:
            yield key(pygame.K_ESCAPE)
            if e.inventory_screen.open:yield key(pygame.K_i)
            return False
        impact = min(impacts,key=lambda p:((p[0]-guard.x)**2+(p[1]-guard.y)**2,p))
        yield from aim(e,impact,key)
        if e.inventory_screen.open:
            yield key(pygame.K_i)
        assert not e.player.inventory.contains(pellet)
        self.pellet_used = True
        self.record(e,'finite workshop musk covers response to observed threat',impact=list(impact))
        return True

    def food_opportunity(self, e, key):
        """One ordinary roadside cooking stop from observed fallen fuel/remains."""
        import pygame
        import g22_journey as j
        from g12_journey import interact,select_prompt,recipe
        from g16_journey import close
        from g20_journey import aim
        if not self.second or self.cooked or e.current_submap_id or visible_hostiles(e):
            return
        inv=e.player.inventory
        # Carry two real fuel bundles when a nearby observed source permits it.
        wood=sum(i.count for i in inv.items if i.item_id=='wood_bundle')
        if wood<2:
            fuel=j.visible_tiles(e,lambda x,y:e.data.terrain.get(str(e.local_map.tiles[x,y]['terrain']),{}).get('gather_item')=='wood_bundle'
                and max(abs(x-e.player.x),abs(y-e.player.y))<=8)
            if fuel:
                xy=min(fuel,key=lambda p:(max(abs(p[0]-e.player.x),abs(p[1]-e.player.y)),p))
                self.record(e,'observed fallen fuel for finite roadside cooking budget',source=list(xy))
                yield from j.approach(e,xy,key)
                yield from interact(e,xy,key)
                yield from close(e,key)
            return
        if e.player.needs.hunger<.6 or inv.has('crow_jerky') or inv.has('cooked_meat'):
            return
        remains=j.visible_tiles(e,lambda x,y:max(abs(x-e.player.x),abs(y-e.player.y))<=4
            and any(getattr(i,'source_creature',None) in ('heath_stalker','plague_crow')
                    for i in e.local_map.floor_objects.get((x,y),[])))
        if not remains:
            return
        xy=min(remains,key=lambda p:(max(abs(p[0]-e.player.x),abs(p[1]-e.player.y)),p))
        self.record(e,'observed defeated animal supplies an ordinary food opportunity',remains=list(xy))
        yield from j.approach(e,xy,key)
        yield from interact(e,xy,key)
        if e.interaction_cursor._selection_prompt:
            corpse=next(i for i in e.interaction_cursor._selection_prompt['items'] if getattr(i,'source_creature',None))
            yield from select_prompt(e,corpse.item_id,key)
        yield from close(e,key)
        # Butchery publishes outputs on the floor. Inspect only this visible pile.
        for _ in range(3):
            meat=next((i for i in e.local_map.floor_objects.get(xy,[]) if i.item_id in ('crow_meat','stalker_meat')),None)
            if not meat:break
            yield from interact(e,xy,key)
            if e.interaction_cursor._selection_prompt:yield from select_prompt(e,meat.item_id,key)
            yield from close(e,key)
        if not any(i.item_id in ('crow_meat','stalker_meat') for i in inv.items):
            return
        yield from self.light(e,True,key)
        yield from recipe(e,'campfire',key)
        fire=yield from j.placement_choice(e,key)
        yield key(pygame.K_RETURN)
        yield from interact(e,fire,key)
        yield from close(e,key)
        for _ in range(3):
            if not any(i.item_id in ('crow_meat','stalker_meat') for i in inv.items):break
            yield key(pygame.K_c,'c')
            screen=e.craft_screen
            flat=screen._build_flat_items(screen._get_recipes(e))
            target=next(n for n,row in enumerate(flat) if row.get('recipe',{}).get('id')=='cook_meat')
            while screen.selected!=target:
                yield key(pygame.K_DOWN if screen.selected<target else pygame.K_UP)
            yield key(pygame.K_RETURN)
            while screen._choosing:
                prompt=screen._choice_prompts[screen._choice_index]
                target=next(n for n,opt in enumerate(prompt['options']) if opt['item_id'] in ('crow_meat','stalker_meat'))
                while screen._choice_selected!=target:
                    yield key(pygame.K_DOWN if screen._choice_selected<target else pygame.K_UP)
                yield key(pygame.K_RETURN)
            yield from aim(e,fire,key)
            for _ in range(7):yield key(pygame.K_z,'z')
            yield from interact(e,fire,key)
            if e.interaction_cursor._selection_prompt:yield from select_prompt(e,'cooked_meat',key)
            yield from close(e,key)
            yield from self.eat_drink(e,key)
        self.cooked=True
        self.record(e,'finite observed meat cooked over actual gathered-fuel fire')

    def respond(self, e, key):
        import g22_journey as j
        from engine.spatial import melee_contact
        from generation.access import enterable
        from g12_journey import inventory
        # A first actual setback gets one finite response, never an injury quota.
        if self.setback and not self.treated:
            spent = yield from self.musk(e,key)
            if spent:
                for _ in range(3):
                    actors = visible_hostiles(e)
                    occupied = {(a.x,a.y) for a in actors}
                    steps = [(e.player.x+dx,e.player.y+dy) for dx,dy in j.STEPS]
                    steps = [p for p in steps if e.local_map.in_bounds(*p) and e.local_map.explored[p]
                             and p not in occupied and enterable(e.local_map,p,e.data)]
                    if not actors or not steps:
                        break
                    at = e.player.x,e.player.y
                    dest = max(steps,key=lambda p:(min(max(abs(p[0]-a.x),abs(p[1]-a.y)) for a in actors),p))
                    yield key(j.STEPS[dest[0]-at[0],dest[1]-at[1]])
                self.record(e,'repositioned during finite disruption before treatment')
            dressing = e.player.inventory.get_by_id('herbal_dressing')
            assert dressing and e.player.fighter.hp < e.player.fighter.max_hp
            before, turn = e.player.fighter.hp,e.world_time.turn
            yield from inventory(e,dressing,key,self.choose)
            assert not e.player.inventory.contains(dressing) and not e.player.inventory.has('herbal_dressing')
            assert e.world_time.turn > turn
            self.treated = True
            self.ev.record['treatment'] = dict(before_hp=before,after_hp=e.player.fighter.hp,
                paid_phases=e.world_time.turn-turn,maximum_effect=12,ward_already_owned=e.player.inventory.has('faceted_ward'))
            self.record(e,'one real paid dressing after actual injury')
        # Defensive bump only against an observed hostile in legal contact.
        # Reassess after each strike; never walk through occupied tiles blindly.
        close = [a for a in visible_hostiles(e)
                 if melee_contact(e.local_map,e.player.x,e.player.y,a.x,a.y)]
        if close:
            a = min(close,key=lambda a:(distance(e,a),a.x,a.y))
            self.record(e,'defensive blade strike against observed contacting pursuer',target=a.name)
            yield key(j.STEPS[a.x-e.player.x,a.y-e.player.y])
            return True
        # A diving crow at two tiles can punish every slow escape step. Close
        # once through observed clear terrain, then reconsider legal contact.
        crows=[a for a in visible_hostiles(e) if getattr(a,'_creature_id','')=='plague_crow' and distance(e,a)<=3]
        if crows:
            a=min(crows,key=lambda a:(distance(e,a),a.x,a.y))
            goals={(a.x+dx,a.y+dy) for dx,dy in j.STEPS}
            path=j.route(e,goals,(a.x,a.y),avoid=False,strict=True)
            if len(path)>1:
                at,dest=path[:2]
                self.record(e,'close observed diving crow instead of repeated exposed escape steps')
                yield key(j.STEPS[dest[0]-at[0],dest[1]-at[1]])
                return True
        return False

    def check(self, e, key):
        if self.busy:
            return
        self.busy = True
        try:
            for _ in range(20):
                if not (yield from self.respond(e,key)):
                    break
            else:
                raise AssertionError('Bounded defensive response exhausted; diagnose engagement')
            # Protection when a threat is close after acquisition; scouting light
            # otherwise follows actual night/underground conditions.
            ward = e.player.inventory.get_by_id('faceted_ward')
            close = any(distance(e,a)<=3 for a in visible_hostiles(e))
            if ward and close:
                if e.player.equipment.slots.get('offhand') is not ward:
                    from g12_journey import inventory
                    yield from inventory(e,ward,key,self.choose)
                    self.record(e,'Ward protection chosen for observed close threat')
            else:
                yield from self.light(e,bool(e.current_submap_id or e.world_time.is_night),key)
            yield from self.eat_drink(e,key)
            yield from self.water(e,key)
            yield from self.food_opportunity(e,key)
            if e.world_time.turn >= self.next_budget:
                self.record(e,'travel/search budget reconsidered from public conditions')
                self.next_budget = e.world_time.turn + 80
        finally:
            self.busy = False


def ward(e,key,capture,choose,ev,out,policy):
    import pygame
    import g22_journey as j
    from g12_journey import inventory,interact,select_prompt
    from g16_journey import close
    home = e.world_x,e.world_y
    lab = e.current_submap_id
    sheet = next(i for i in e.player.inventory.items if i.text_id=='lab_route_sheet_a')
    pages = yield from j.read_owned(e,sheet,key,choose,capture,'second-report')
    target = list(map(int,re.search(r'square \((\d+), (\d+)\)',pages[2]).groups()))
    policy.context = dict(owner=e.world_map.report_owner,home=home,target=target)
    validate_situation(e,policy.context)
    policy.second = True
    policy.record(e,'second outing begins with real first-return budget')
    stairs = j.visible_tiles(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_up')
    yield from j.walk(e,stairs,key)
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    home_entry = e.player.x,e.player.y
    yield from j.travel(e,target,key,choose)
    policy.record(e,'arrived at reported Ward square; light and water checked before search')
    entry = yield from j.discover(e,lambda x,y:str(e.local_map.tiles[x,y]['terrain'])=='stairs_down',key)
    yield from j.walk(e,{entry},key)
    yield from policy.light(e,True,key)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    inside_entry = e.player.x,e.player.y
    policy.context['submap'] = e.current_submap_id
    policy.record(e,'ordinary store entry')
    note_xy = yield from j.discover(e,lambda x,y:any(i.text_id=='barrow_ward_store_note_a'
                for i in e.local_map.floor_objects.get((x,y),[])),key,aim=inside_entry)
    yield from j.approach(e,note_xy,key)
    yield from interact(e,note_xy,key)
    if e.interaction_cursor._selection_prompt:
        yield from select_prompt(e,'letter',key)
    yield from close(e,key)
    note = next(i for i in e.player.inventory.items if i.text_id=='barrow_ward_store_note_a')
    ev.record['ward_note'] = yield from j.read_owned(e,note,key,choose,capture,'ward-note')
    reward = yield from j.discover(e,lambda x,y:any(i.item_id=='faceted_ward'
              for i in e.local_map.floor_objects.get((x,y),[])),key,
              aim=(inside_entry[0]+18,inside_entry[1]-8))
    yield from j.walk(e,{reward},key)
    yield from interact(e,reward,key)
    yield from close(e,key)
    ward_item = e.player.inventory.get_by_id('faceted_ward')
    assert ward_item
    policy.record(e,'actual Ward acquired through ordinary pickup')
    ev.record['ward_acquisition_turn'] = e.world_time.turn
    if policy.setback is None:
        try:
            validate_situation(e,policy.context,keeper_delay=True)
        except AssertionError as error:
            # No keeper, no forced delay/search/injury. Continue the same outing.
            policy.record(e,'preferred equipment-delay premise absent; natural surface contingency remains',premise=str(error))
        else:
            policy.armed_keeper = True
            yield from inventory(e,ward_item,key,choose)
            policy.record(e,'one premature Ward equipment action beside actually observed keeper')
    yield from j.walk(e,{inside_entry},key)
    policy.armed_keeper = False
    yield key(pygame.K_COMMA,'<',pygame.KMOD_SHIFT)
    policy.record(e,'living meaningful exit with acquired Ward')
    # Retrace the observed outbound row rather than assume a new return corridor.
    yield from j.cross(e,0,1,key)
    while e.world_x != home[0]:
        yield from j.cross(e,1 if home[0]>e.world_x else -1,0,key)
    yield from j.walk(e,{home_entry},key)
    yield from policy.light(e,True,key)
    yield key(pygame.K_PERIOD,'>',pygame.KMOD_SHIFT)
    assert e.current_submap_id == lab and e.player.inventory.contains(ward_item)
    assert policy.setback and policy.treated, 'No actual declared setback/treatment; do not manufacture one'
    policy.record(e,'alive return through original laboratory entrance with actual Ward')
    ev.record['original_laboratory'] = dict(square=home,submap=lab,surface_entrance=home_entry)
    capture('returned-ward')


def connected(e,key,capture,choose,ev,out):
    import pygame
    import g22_journey as j
    import g20_journey
    from g12_journey import archive_checkpoint
    policy = Policy(choose,ev)
    original_torch = g20_journey.torch
    j.POLICY = policy
    g20_journey.torch = policy.light
    ev.record['declaration'] = json.loads((ROOT/'evidence/gameplay-g22a/declaration.json').read_text())
    def tracked_key(*args,**kwargs):
        return key(*args,**kwargs)
    def actions():
        yield from j.read_start(e,tracked_key,capture,choose,ev,out)
        ev.record['completion'] = False
        yield from j.preparation(e,tracked_key,capture,choose,ev,out)
        ev.record['completion'] = False
        yield from ward(e,tracked_key,capture,choose,ev,out,policy)
        yield key(pygame.K_F5)
        ev.record['checkpoint'] = str(archive_checkpoint(e,out,'returned-ward'))
        ev.record['completion'] = True
    try:
        for action in actions():
            before = dict(hp=e.player.fighter.hp,threats=[dict(name=a.name,position=[a.x,a.y]) for a in visible_hostiles(e)])
            yield action
            policy.after_action(e,before,action)
    finally:
        j.POLICY = None
        g20_journey.torch = original_torch


def cold_audit(archive, out):
    """Full-state consequence audit only. No player decisions or future-RNG claim."""
    import tempfile
    from unittest.mock import patch
    from g12_journey import install_checkpoint,snapshot
    from test_effect_persistence import load_data,make_engine
    # Exact snapshot before any assistance; the save is the successful lineage.
    with tempfile.TemporaryDirectory(prefix='g22a-cold-') as root,patch('engine.save_manager.SAVE_DIR',Path(root)):
        install_checkpoint(archive,root)
        e = make_engine(load_data())
        assert e.save_manager.load(e),e.save_manager.last_error
        assert snapshot(e) == json.loads(archive.with_suffix('.json').read_text())
        assert e.player.fighter.hp > 0 and e.player.inventory.has('faceted_ward')
        assert not e.player.inventory.has('herbal_dressing')
        assert not e.player.inventory.has('musk_pellet')
        assert len(e.world_map.learned_reports)==2
        result = dict(passed=True,exact_snapshot=True,hp=e.player.fighter.hp,turn=e.world_time.turn,
            report_owner=e.world_map.report_owner,reports=copy.deepcopy(e.world_map.location_reports),
            inventory=dict(Counter(i.item_id for i in e.player.inventory.items)),
            assistance='Post-success full-state cached-scene inspection only; no gameplay continuation or route assistance.')
        # The ordinary transition cache owns depleted supplies and reward scenes.
        store = next(r['target'] for r in e.world_map.location_reports if r['role']=='ward_store')
        workshop = next(r['target'] for r in e.world_map.location_reports if r['role']=='workshop')
        cached = e.save_manager.cache.load_submap(store['id'])
        assert cached is not None, 'Visited Ward store missing'
        assert not any(i.item_id=='faceted_ward' for rows in cached.local_map.floor_objects.values() for i in rows)
        result['ward_store'] = dict(ward_on_floor=False,actors=cached.entities,zones=cached.local_map.disruption_zones)
        surface = e.save_manager.cache.load(workshop['x'],workshop['y'])
        assert surface is not None
        played=json.loads((archive.parent/'result.json').read_text())
        result['workshop_containers']=[]
        for opened in played['opened_crates']:
            xy=tuple(opened['position'])
            state=surface.local_map.container_state.get(xy)
            assert state is None or not state['items'], 'An actually emptied crate regained stock'
            result['workshop_containers'].append(dict(position=list(xy),remaining=[] if state is None else [i.item_id for i in state['items']],
                                                       dismantled=state is None))
        food=next(row for row in played['ledger'] if 'defeated animal supplies' in row['reason'])
        food_scene=e.save_manager.cache.load(*food['square'])
        remains=tuple(food['remains'])
        assert not any(getattr(i,'source_creature',None) for i in food_scene.local_map.floor_objects.get(remains,[]))
        result['harvested_animal']=dict(square=food['square'],remains=list(remains),corpse_still_absent=True,
            retained_outputs=[i.item_id for i in food_scene.local_map.floor_objects.get(remains,[])])
        # One focused assisted revisit after the exact cold-load assertion.
        # Debug relocation is verification assistance, never part of the outing.
        from g1_support import fingerprint
        from engine.save_manager import _deserialize_entities
        before=fingerprint(cached.local_map,_deserialize_entities(cached.entities,e))
        with patch('engine.scene_generation.create_submap',side_effect=AssertionError('Visited store regenerated')):
            e.overmap_cursor_x,e.overmap_cursor_y=store['x'],store['y']
            e._teleport_to_overmap_cursor()
            entrance=next(xy for xy,sid in e.local_map.submap_links.items() if sid==store['id'])
            e.player.x,e.player.y=entrance
            e._update_fov()
            e._try_descend()
        assert e.current_submap_id==store['id']
        assert before==fingerprint(e.local_map,[a for a in e.entities if a is not e.player])
        assert e.player.inventory.has('faceted_ward') and not e.player.inventory.has('herbal_dressing')
        result['assisted_revisit']=dict(exact_store_fingerprint=True,no_regeneration=True,
            assistance='Only after exact successful save cold-load: debug relocation to its reported square and positioning on its actual saved entrance, then production descent handler. No continued-survival claim.')
        (out/'cold-audit.json').write_text(json.dumps(result,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--cold',type=Path)
    a=p.parse_args()
    sys.path[:0]=[str(ROOT/'roguelike'),str(ROOT/'tools'),str(ROOT/'tools/critical_fix_regressions/tests')]
    os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',PYGAME_HIDE_SUPPORT_PROMPT='1',PYTHONHASHSEED='20261020')
    import config
    config.DEBUG_MODE=False
    out=a.evidence.resolve()
    out.mkdir(parents=True,exist_ok=True)
    if a.cold:
        cold_audit(a.cold.resolve(),out)
    else:
        from g12_journey import run_stage
        try:
            run_stage(out,'connected',connected,max_frames=14000,max_seconds=900,max_turns=4000)
        finally:
            # The inherited harness checks every frame. This task's receipt keeps
            # their totals/failures and its decision ledger, not repeated frames.
            path=out/'connected/result.json'
            if path.exists():
                result=json.loads(path.read_text())
                checks=result.pop('checks',[])
                result['input_checks']=dict(total=len(checks),passed=sum(r['passed'] for r in checks),
                    failures=[r for r in checks if not r['passed']])
                trace=result.pop('trace',[])
                result['input_trace_frames']=len(trace)
                path.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
