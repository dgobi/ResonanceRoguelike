"""GUIDE-1's fixed production-input scenarios; not a substitute game engine."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import random
import time

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--session', type=Path, required=True)
parser.add_argument('--lesson', required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--cold', action='store_true')
parser.add_argument('--play', action='store_true')
args = parser.parse_args()
config = json.loads(args.session.read_text())
payload = args.session.parent / 'payload'
GAME = payload / 'roguelike'
sys.path.insert(0, str(payload / 'roguelike'))
os.chdir(payload / 'roguelike')
import pygame
from room_test import build_engine


def initialise(engine):
    pygame.display.set_mode((1280, 900))
    engine.display.init()
    engine.inventory_screen.init(engine.display)
    engine.perk_screen.init(engine.display)
    engine.craft_screen.init(engine.display)
    from rendering.ui_registry import UIRegistry
    engine.ui_registry = UIRegistry()
    engine.ui_registry.load()


def snapshot(e):
    from engine.save_manager import _serialize_player, _serialize_entity
    from engine.save_components import serialize_item
    return json.loads(json.dumps(dict(player=_serialize_player(e), turn=e.world_time.turn,
                scene=[e.world_x, e.world_y, e.current_submap_id],
                actors=[_serialize_entity(a) for a in e.entities if a is not e.player],
                floor=[[list(xy),[serialize_item(i) for i in items]] for xy,items in sorted(e.local_map.floor_objects.items())],
                processing=[[list(xy),record] for xy,record in sorted(e.local_map.processing_layer.items())])))


class Journey:
    def __init__(self, e):
        self.e = e
        self.rows = []
        self.events = 0

    def record(self, label, **observations):
        self.rows.append(dict(label=label, turn=self.e.world_time.turn, **observations))

    def key(self, key):
        self.e._handle_key(key)
        self.events += 1
        assert not self.e._player_is_dead

    def inventory(self, iid):
        if not self.e.inventory_screen.open:
            self.key(pygame.K_i)
        self.e.inventory_screen.render(pygame.Surface((1280, 900)), self.e)
        for _ in range(150):
            item = self.e.inventory_screen._selected_item()
            if item and item.item_id == iid:
                return item
            self.key(pygame.K_DOWN)
        raise AssertionError('Inventory selection could not reach ' + iid)

    def use(self, iid):
        item = self.inventory(iid)
        self.key(pygame.K_e)
        if self.e.inventory_screen.open and not self.e.text_reader.open:
            self.key(pygame.K_ESCAPE)
        return item

    def acquire(self, iid):
        # Controlled fixture provisioning, separately labelled from ordinary pickup.
        item = self.e.item_factory.create(iid)
        assert item is not None
        assert self.e.player.inventory.add(item)
        return item

    def pickup(self, iid, target=None):
        for _ in range(8):
            if self.e.player.inventory.has(iid):
                self.record('ordinary floor pickup', item=iid)
                return next(i for i in self.e.player.inventory.items if i.item_id == iid)
            self.key(pygame.K_COMMA)
            if target is not None and self.e._pickup_mode:
                delta = (target[0]-self.e.player.x,target[1]-self.e.player.y)
                keys = {(1,0):pygame.K_RIGHT,(-1,0):pygame.K_LEFT,(0,1):pygame.K_DOWN,(0,-1):pygame.K_UP}
                self.key(keys[delta])
            prompt = self.e.interaction_cursor._selection_prompt
            if prompt:
                for _ in range(30):
                    if prompt['items'][prompt['selected']].item_id == iid:
                        break
                    self.key(pygame.K_DOWN)
                self.key(pygame.K_RETURN)
        raise AssertionError('Floor pickup did not reach ' + iid)

    def buy(self, pid):
        self.key(pygame.K_k)
        self.e.perk_screen._flat = self.e.perk_screen._build_flat(self.e)
        for _ in range(200):
            if self.e.perk_screen._selected_perk_id() == pid:
                break
            self.key(pygame.K_DOWN)
        else:
            raise AssertionError('Perk not visible: ' + pid)
        self.key(pygame.K_RETURN)
        self.key(pygame.K_RETURN)
        assert self.e.player.perks.has(pid)
        self.key(pygame.K_ESCAPE)

    def walk(self, target):
        from collections import deque
        e = self.e
        keys = {(0,-1):pygame.K_UP, (0,1):pygame.K_DOWN, (-1,0):pygame.K_LEFT, (1,0):pygame.K_RIGHT}
        for _ in range(120):
            start = (e.player.x, e.player.y)
            if start == target:
                return
            blocked = {(a.x,a.y) for a in e.entities if a is not e.player and a.is_alive}
            q = deque([start]); parents = {start: None}
            while q:
                a = q.popleft()
                if a == target:
                    break
                for dx,dy in keys:
                    b = (a[0]+dx,a[1]+dy)
                    if b not in parents and b not in blocked and e.local_map.in_bounds(*b) and e.local_map.walkable[b] and not e._decor_blocks_movement(*b):
                        parents[b] = a; q.append(b)
            assert target in parents, ('no walkable route', start, target)
            step = target
            while parents[step] != start:
                step = parents[step]
            self.key(keys[step[0]-start[0],step[1]-start[1]])
        raise AssertionError('walk event limit')

    def return_scene(self):
        e = self.e
        stairs = next((x,y) for x in range(e.local_map.width) for y in range(e.local_map.height)
                      if str(e.local_map.tiles[x,y]['terrain']) == 'stairs_up')
        self.walk(stairs)
        e._handle_key(pygame.K_COMMA, text='<'); self.events += 1
        assert e.current_submap_id is None
        e._handle_key(pygame.K_PERIOD, text='>'); self.events += 1
        assert e.current_submap_id == 'room-test-instance'
        self.record('ordinary stairs leave and reenter', scene_owned=True)

    def checkpoint(self, label):
        before = snapshot(self.e)
        self.key(pygame.K_F5)
        self.key(pygame.K_F9)
        after = snapshot(self.e)
        if before != after:
            (args.output/'checkpoint-difference.json').write_text(json.dumps(dict(before=before,after=after),indent=2))
        assert before == after, self.e.save_manager.last_error
        expected = args.output / 'expected.json'
        expected.write_text(json.dumps(before), encoding='utf-8')
        child = subprocess.run([sys.executable, '-X', 'utf8', '-B', str(Path(__file__).resolve()),
                                '--session', str(args.session), '--lesson', args.lesson,
                                '--output', str(args.output), '--cold'],
                               capture_output=True, text=True, encoding='utf-8', timeout=100)
        assert child.returncode == 0, child.stdout + child.stderr
        cold = json.loads(child.stdout.splitlines()[-1])
        assert cold['pid'] != os.getpid()
        self.record(label, same_process_equal=True, cold=cold)


def food(j, *, ordinary=False):
    e = j.e
    item = j.pickup('guide1_ration') if ordinary else j.acquire('guide1_ration')
    # Controlled unmet need makes the nutrition difference visible without clamping.
    e.player.needs.hunger = .7
    before = e.player.needs.hunger
    turn = e.world_time.turn
    j.use(item.item_id)
    expected = max(0, before - item.nutrition / e.player.needs._h_max) + e.player.needs._h_tick
    assert abs(e.player.needs.hunger - expected) < 1e-9
    assert e.world_time.turn == turn + 1
    assert not e.player.inventory.contains(item)
    j.record('food through inventory input', nutrition=item.nutrition, hunger_before=before,
             hunger_after=e.player.needs.hunger, consumed_exact_object=True, paid_phases=1)
    j.checkpoint('food consumption cold restore')
    # Unknown capability is a real fault: syntax/construction still succeed.
    broken = j.acquire('guide1_ration')
    broken.on_use = 'guide1_missing'
    before = snapshot(e)
    j.use(broken.item_id)
    assert snapshot(e) == before
    assert any('Unknown effect' in m.text for m in e.log.messages)
    j.record('unknown handler rejected', time_and_resources_unchanged=True)


def writing(j):
    e = j.e
    item = j.pickup('guide1_note_carrier')
    turn = e.world_time.turn
    j.use(item.item_id)
    assert e.text_reader.open and e.world_time.turn == turn + 1
    assert e.player.inventory.contains(item)
    capture(e, args.output / 'reading.png')
    j.key(pygame.K_ESCAPE)
    if e.inventory_screen.open:
        j.key(pygame.K_ESCAPE)
    j.record('carrier opened ordinary reader', text_id=item.text_id, not_consumed=True, paid_phases=1)
    j.checkpoint('readable carrier cold restore')


def preparation(j):
    e = j.e
    meat = j.acquire('raw_meat_common')
    fire = next(xy for xy, d in e.local_map.decor.items() if (d.get('id') if isinstance(d,dict) else d) == 'campfire_lit')
    j.walk((fire[0]-1, fire[1]))
    def select_recipe():
        j.key(pygame.K_c)
        screen = e.craft_screen
        flat = screen._build_flat_items(screen._get_recipes(e))
        target = next(i for i,r in enumerate(flat) if r.get('recipe',{}).get('id') == 'guide1_meal')
        while screen.selected != target:
            j.key(pygame.K_DOWN if screen.selected < target else pygame.K_UP)
        j.key(pygame.K_RETURN)
        while screen._choosing:
            prompt = screen._choice_prompts[screen._choice_index]
            n = next(i for i,r in enumerate(prompt['options']) if r['item_id'] == 'raw_meat_common')
            while screen._choice_selected != n:
                j.key(pygame.K_DOWN if screen._choice_selected < n else pygame.K_UP)
            j.key(pygame.K_RETURN)
        assert e.mode.value == 'placement_cursor', [m.text for m in e.log.messages][-5:]
    turn = e.world_time.turn
    select_recipe(); j.key(pygame.K_ESCAPE)
    assert e.world_time.turn == turn and e.player.inventory.contains(meat)
    j.record('placement cancellation', materials_and_time_unchanged=True)
    select_recipe()
    while e._placement_cursor_x != fire[0]:
        j.key(pygame.K_RIGHT if e._placement_cursor_x < fire[0] else pygame.K_LEFT)
    while e._placement_cursor_y != fire[1]:
        j.key(pygame.K_DOWN if e._placement_cursor_y < fire[1] else pygame.K_UP)
    j.key(pygame.K_RETURN)
    assert e.world_time.turn == turn + 1 and not e.player.inventory.contains(meat)
    job = e.local_map.processing_layer[fire]
    duration=json.loads((GAME/'data/recipes/guide1_meal.json').read_text())['processing_turns']
    assert job['turns_remaining'] == duration-1, job
    j.record('passive work committed', first_phase_already_paid=True, remaining=duration-1)
    j.checkpoint('unfinished preparation')
    finish_preparation(j,fire)


def finish_preparation(j,fire):
    """Continue the owned job, then acquire and eat its exact physical output."""
    e=j.e
    remaining=e.local_map.processing_layer[fire]['turns_remaining']
    for _ in range(remaining):
        j.key(pygame.K_PERIOD)
    assert fire not in e.local_map.processing_layer
    result=next(i for i in e.local_map.floor_objects.get(fire,[]) if i.item_id=='guide1_ration')
    assert not e.player.inventory.has(result.item_id)
    acquired=j.pickup(result.item_id,target=fire)
    assert acquired is result and result not in e.local_map.floor_objects.get(fire,[])
    e.player.needs.hunger=.7  # controlled unmet need, as in L01
    before=e.player.needs.hunger;turn=e.world_time.turn
    assert j.use(result.item_id) is result
    expected=max(0,before-result.nutrition/e.player.needs._h_max)+e.player.needs._h_tick
    assert abs(e.player.needs.hunger-expected)<1e-9 and e.world_time.turn==turn+1
    assert not e.player.inventory.contains(result)
    row=dict(remaining_paid_phases=remaining,output=result.item_id,exact_output_acquired_and_consumed=True,
             hunger_before=before,hunger_after=e.player.needs.hunger,use_paid_phases=1)
    j.record('owned meal completed, acquired and eaten',**row)
    return row


def creature(j):
    e = j.e
    actor = next(a for a in e.entities if a is not e.player)
    before = actor.ai.snapshot()
    # Approach its defended ground, then retreat beyond its excursion boundary.
    # No teleport, target injection, damage replacement or AI-state override.
    safe=(e.player.x,e.player.y)
    radius=actor.ai.profile['defended_radius']
    j.walk((actor.ai.home_x-min(3,radius),actor.ai.home_y+min(2,radius)))
    engaged=actor.ai.snapshot()
    assert engaged['state']['target']['role']=='player'
    j.walk(safe)
    for _ in range(20):
        if actor.ai.territory['phase']=='guard' and actor.ai.target is None:
            break
        j.key(pygame.K_PERIOD)
    after = actor.ai.snapshot()
    assert actor.is_alive and actor.ai.__class__.__name__ == 'CompositeAI'
    assert after['state']['opportunities'] > before['state']['opportunities']
    assert after['state']['territory']['phase']=='guard' and after['state']['target'] is None
    j.record('authored guard approach and retreat', before=before, engaged=engaged,after=after,
             position=[actor.x,actor.y], hp=actor.fighter.hp,trace=actor.ai.trace[-16:])
    j.checkpoint('saved guard profile')


def enrollment(j):
    from world.world_map import WorldMap
    from generation.world_gen import generate_world
    from generation.building_preview import orientations
    from engine.scene_generation import create_surface, publish_metadata
    from engine.creature_factory import CreatureFactory
    from engine.save_manager import _serialize_world, _deserialize_world
    from config import MAP_WIDTH, MAP_HEIGHT
    e = j.e
    raw = e.data.structures['guide1_cottage']
    preview, problems = orientations(raw,e.data,category='residential')
    assert preview['passed'] and not problems
    policy=json.loads((GAME/'data/generation/authored_submap_selection.json').read_text())
    candidate_ids={r['layout_id'] for r in policy['candidates']}
    world = WorldMap(128,128); world.seed = config['seed']
    generate_world(world,e.data,random.Random(world.seed))
    assigned = [(xy,s) for xy,c in world.chunks.items() for s in c.submaps if s.layout_id in candidate_ids]
    built = [p for p in world.plan['placements'] if p['asset'] == 'guide1_cottage']
    assert assigned and built
    restored = WorldMap(128,128)
    _deserialize_world(json.loads(json.dumps(_serialize_world(world))),restored)
    xy,sm = assigned[0]
    assert any(s.layout_id == sm.layout_id for s in restored.get(*xy).submaps)
    # Real natural selection and real destination construction; initial player
    # location is disclosed staging, not an expedition from the campaign start.
    chunk = world.get(*xy)
    surface = create_surface(world,chunk,e.data,e.item_factory,CreatureFactory(e.data),MAP_WIDTH,MAP_HEIGHT)
    publish_metadata(chunk,surface.metadata)
    e.world_map=world; e.world_x,e.world_y=xy; e.local_map=surface.local_map
    e.entities=[e.player]+surface.actors; e.current_submap_id=None
    e.player.x,e.player.y=sm.surface_x,sm.surface_y
    e._handle_key(pygame.K_PERIOD,text='>');j.events+=1
    assert e.current_submap_id == sm.submap_id
    assert any(i.item_id == 'guide1_ration' for rows in e.local_map.floor_objects.values() for i in rows)
    p = built[0]; wx,wy=p['origin'][0]//MAP_WIDTH,p['origin'][1]//MAP_HEIGHT
    surface2=create_surface(world,world.get(wx,wy),e.data,e.item_factory,CreatureFactory(e.data),MAP_WIDTH,MAP_HEIGHT)
    assert any(i.item_id=='guide1_ration' for rows in surface2.local_map.floor_objects.values() for i in rows)
    j.record('ordinary world selection and construction', seed=world.seed,
             authored_assignments=len(assigned),surface_placements=len(built),orientations=len(preview['orientations']),
             underground_entry=True,surface_content_constructed=True,
             policy=policy,counts={iid:sum(s.layout_id==iid for _,s in assigned) for iid in sorted(candidate_ids)},
             staging='Disposable policy and residential-only practice membership; player staged at selected entrance.')
    (args.output/'enrollment.json').write_text(json.dumps(dict(assignment=dict(chunk=xy,id=sm.submap_id,layout=sm.layout_id),placement=p),indent=2))


def appearance(j):
    from engine.typography import load_candidate
    profile=json.loads(Path('data/display/typography.json').read_text())
    checked=load_candidate(payload,profile)
    assert not any(d['severity']=='error' for d in checked['diagnostics'])
    writing(j)
    j.record('actual reader with changed typography', role='font_ui_normal',resource=profile['font_ui_normal'],
             screenshot='reading.png',nominal_size_retained=True)


def expedition(j):
    # Complete authored content graph, with later persistent consequence.
    place(j)
    preparation(j)
    e=j.e
    from engine.guide1_practice import SURVEY,survey_state
    e.player.level.perk_points=1
    j.buy(SURVEY);j.acquire('guide1_survey')
    j.use('guide1_survey');j.key(pygame.K_PERIOD);j.key(pygame.K_PERIOD);j.use('guide1_survey')
    assert survey_state(e)['completed']==1
    j.checkpoint('expedition reward and later consequence')


def place(j):
    writing(j)
    creature(j)
    j.return_scene()
    assert j.e.player.inventory.has('guide1_note_carrier')
    assert not any(i.item_id == 'guide1_note_carrier' for items in j.e.local_map.floor_objects.values() for i in items)
    j.checkpoint('depleted place remains owned')


def technique(j):
    e = j.e
    blade = j.acquire('guide1_blade')
    j.use(blade.item_id)
    assert e.player.equipment.slots['weapon'] is blade
    actor = next(a for a in e.entities if a is not e.player)
    # Controlled target staging; no hit result or damage rule is replaced.
    actor.x, actor.y = e.player.x+1, e.player.y
    before = actor.fighter.hp; turn = e.world_time.turn
    j.key(e.display.MOVESET_KEY_1)
    assert actor.fighter.hp < before
    assert e.world_time.turn == turn+1
    assert e.moveset_cooldowns['guide1_opening'] == 3
    frozen = snapshot(e)
    j.key(e.display.MOVESET_KEY_1)
    assert snapshot(e) == frozen
    j.record('technique hit and cooldown rejection', damage=before-actor.fighter.hp,
             accepted_phases=1, rejected_phases=0)
    # Controlled boundaries, not a claim that a fixed seed guarantees a hit.
    e.moveset_cooldowns.clear()
    actor.x,actor.y=10+33,2+17  # far from fixture arrival in its centered map
    frozen=snapshot(e)
    j.key(e.display.MOVESET_KEY_1)
    assert snapshot(e)==frozen
    actor.x,actor.y=e.player.x+1,e.player.y
    action=e.data.items[blade.item_id]['movesets'][0]
    original_ignore=action['effects']['ignore_dodge']
    original_dodge=e.data.entities['guide1_watcher'].get('dodge_chance',0)
    action['effects']['ignore_dodge']=False
    e.data.entities['guide1_watcher']['dodge_chance']=1.0
    before_hp=actor.fighter.hp;turn=e.world_time.turn
    try:
        j.key(e.display.MOVESET_KEY_1)
        assert actor.fighter.hp==before_hp and e.world_time.turn==turn+1
        assert e.moveset_cooldowns['guide1_opening']==3
    finally:
        action['effects']['ignore_dodge']=original_ignore
        e.data.entities['guide1_watcher']['dodge_chance']=original_dodge
    j.record('no-target rejection and guaranteed dodge control', no_target_phases=0,
             dodge_phases=1, setup='target repositioned, fixture dodge=1, ignore_dodge disabled; real resolver unchanged')


def original_loop_key(e, key):
    """Post only to this game's queue; run the original loop and renderer."""
    class Done(Exception):
        pass
    frames = 0; began = time.monotonic()
    def frame(engine, screen):
        nonlocal frames
        frames += 1
        assert frames < 30 and time.monotonic()-began < 15
        if frames == 1:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, unicode='', mod=0))
            pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key, mod=0))
        elif frames == 3:
            pygame.image.save(screen, str(args.output/'original-loop.png'))
            raise Done()
    try:
        e.run(on_frame=frame)
    except Done:
        pass


def primitive(j):
    from engine.guide1_practice import parse_exchange
    e = j.e
    item = j.acquire('guide1_exchange'); sibling = j.acquire('guide1_exchange')
    j.use(item.item_id)  # full HP rejects
    before = e.world_time.turn
    assert not e.item_system.last_use_committed
    e.player.fighter.hp -= 8; e.player.needs.thirst = .2
    hp = e.player.fighter.hp
    j.inventory(item.item_id)
    original_loop_key(e, pygame.K_e)
    assert e.world_time.turn == before+1 and e.player.fighter.hp == hp+3
    biome = e.world_map.get(e.world_x,e.world_y).biome_id
    tick = e.player.needs._t_tick * e.data.survival.get('biome_modifiers',{}).get(biome,{}).get('thirst',1)
    assert abs(e.player.needs.thirst - (.3+tick)) < 1e-9, (e.player.needs.thirst,tick)
    assert e.player.inventory.contains(item) and e.player.inventory.contains(sibling)
    if e.inventory_screen.open:
        j.key(pygame.K_ESCAPE)
    j.record('new primitive through original Engine.run', hp_recovered=3, thirst_cost=.1,
             paid_phases=1, consumed=False, same_id_sibling_untouched=True)
    e.player.needs.thirst = .99
    frozen = snapshot(e); j.use(item.item_id)
    assert snapshot(e) == frozen
    e.player.inventory.remove(item)
    frozen = snapshot(e)
    assert e.item_system.use(item,e) is False and not e.item_system.last_use_committed
    assert snapshot(e) == frozen
    for bad in (True, 0, float('nan')):
        config_bad = copy.deepcopy(e.data.items['guide1_exchange']); config_bad['guide_exchange']['thirst_cost'] = bad
        try:
            parse_exchange(config_bad)
        except ValueError:
            pass
        else:
            raise AssertionError('bad primitive config accepted')
    j.record('resource, stale-object and malformed-definition rejection', unchanged=True)
    j.checkpoint('new primitive reusable tool restore')


def event_response(j):
    from engine.guide1_practice import CADENCE, cadence_turn
    from engine.hooks import HookEvent
    e = j.e; e.player.level.perk_points = 2  # disclosed purchase prerequisite
    turn = e.world_time.turn
    j.buy(CADENCE)
    assert e.world_time.turn == turn and e.player.level.perk_points == 1
    e._register_player_perks(); e._register_player_perks()
    assert e.hooks._handlers[HookEvent.ON_TURN].count(cadence_turn) == 1
    for _ in range(3):
        j.key(pygame.K_PERIOD)
    assert e.player.perks.perk_state[CADENCE]['paid'] == 3
    assert any('Practice cadence: 3' in m.text for m in e.log.messages)
    j.record('real purchase, dispatch and effect consumption', paid=3, duplicate_handlers=0)
    j.checkpoint('cadence cold restore and continuation')
    e.player.perks.remove_perk(CADENCE); e._register_player_perks()
    j.key(pygame.K_PERIOD)
    assert e.player.perks.perk_state[CADENCE]['paid'] == 3
    assert cadence_turn not in e.hooks._handlers[HookEvent.ON_TURN]
    j.record('removal detaches handler and preserves history', paid=3)


def persistent(j):
    from engine.guide1_practice import SURVEY, survey_state, validate_states
    from engine.save_manager import _serialize_player
    e = j.e; e.player.level.perk_points = 2
    j.buy(SURVEY)
    for iid in ('guide1_survey','guide1_inspect','guide1_cancel'):
        j.acquire(iid)
    j.use('guide1_survey')
    assert survey_state(e)['left'] == 2
    turn = e.world_time.turn
    j.use('guide1_survey'); j.use('guide1_inspect')
    assert survey_state(e)['left'] == 2 and e.world_time.turn == turn
    j.checkpoint('working survey cold continuation')
    j.key(pygame.K_PERIOD); j.key(pygame.K_PERIOD)
    assert survey_state(e)['phase'] == 'ready'
    j.use('guide1_survey')
    assert survey_state(e)['completed'] == 1
    j.use('guide1_survey'); turn=e.world_time.turn; j.use('guide1_cancel')
    assert survey_state(e)['phase'] == 'idle' and e.world_time.turn==turn
    j.use('guide1_survey'); j.key(pygame.K_UP)
    assert survey_state(e)['phase'] == 'idle'
    j.return_scene()
    assert survey_state(e)['completed'] == 1
    j.checkpoint('collected history across scene and cold restore')
    validate_states({})
    from engine.save_manager import SaveManager
    from engine.checkpoints import encoded
    original_manager=e.save_manager
    checkpoint_path=original_manager._candidates()[0][1]
    members=json.loads((checkpoint_path/'manifest.json').read_text())['files']
    payloads={name:(checkpoint_path/name).read_bytes() for name in members}
    for index,bad in enumerate((dict(version=1,phase='working',left=0,anchor=None,completed=0),
                dict(version=1,phase='idle',left=False,anchor=None,completed=0),
                dict(version=2,phase='idle',left=0,anchor=None,completed=0))):
        raw = copy.deepcopy(_serialize_player(e)); raw['perks']['perk_state'][SURVEY] = bad
        from engine import save_manager
        before_player = e.player; before = snapshot(e)
        try:
            save_manager._validate_player_references(raw,e.data)
        except ValueError:
            pass
        else:
            raise AssertionError('malformed inner save accepted')
        assert e.player is before_player and snapshot(e) == before
        # Publish a correctly checksummed, semantically invalid checkpoint in a
        # separate disposable store with no valid fallback. Exercise actual load.
        manager=SaveManager(save_root=args.session.parent/f'malformed-{index}')
        manager.store.publish({**payloads,'player.json':encoded(raw)},None,None)
        loaded=manager.load(e)
        assert not loaded and 'guide-1' in manager.last_error.lower(),manager.last_error
        assert e.player is before_player and snapshot(e)==before
    absent=copy.deepcopy(_serialize_player(e))
    absent['perks']['perk_state'].pop(SURVEY,None)
    manager=SaveManager(save_root=args.session.parent/'absent-state')
    manager.store.publish({**payloads,'player.json':encoded(absent)},None,None)
    e.save_manager=manager
    try:
        assert manager.load(e),manager.last_error
        assert survey_state(e)==dict(version=1,phase='idle',left=0,anchor=None,completed=0)
    finally:
        e.save_manager=original_manager
        assert original_manager.load(e),original_manager.last_error
    assert survey_state(e)['completed']==1
    j.record('subsystem transitions and validation', phases=3, first_tick=1,
             cancellation='movement or explicit free cancel, zero cancel phases', absent='actual isolated checkpoint load then idle default', malformed='production preflight and actual isolated checksum-valid checkpoint load refused before replacement')


def capture(e, target):
    class Finished(Exception):
        pass
    before = snapshot(e)
    def frame(engine, screen):
        pygame.image.save(screen, str(target))
        raise Finished()
    try:
        e.run(on_frame=frame)
    except Finished:
        pass
    assert before == snapshot(e), 'rendering advanced state'


def main():
    args.output.mkdir(parents=True, exist_ok=True)
    if int(args.lesson[1:]) >= 10:
        import engine.engine  # captured installation.patch installs before construction/load
    e = build_engine(config, load=args.cold)
    initialise(e)
    j = Journey(e)
    if args.cold:
        expected = json.loads((args.output / 'expected.json').read_text())
        assert snapshot(e) == expected
        continued = None
        if args.lesson in ('L04','L13') and e.local_map.processing_layer:
            fire=next(iter(e.local_map.processing_layer))
            continued=dict(preparation=finish_preparation(j,fire))
        elif args.lesson == 'L11':
            from engine.guide1_practice import CADENCE
            previous = e.player.perks.perk_state[CADENCE]['paid']
            j.key(pygame.K_PERIOD)
            assert e.player.perks.perk_state[CADENCE]['paid'] == previous+1
            continued = dict(paid=previous+1)
        elif args.lesson == 'L12':
            from engine.guide1_practice import survey_state
            previous = copy.deepcopy(survey_state(e))
            if previous['phase'] == 'working':
                for _ in range(previous['left']):
                    j.key(pygame.K_PERIOD)
                j.use('guide1_survey')
                assert survey_state(e)['completed'] == previous['completed']+1
            continued = dict(survey=survey_state(e))
        print(json.dumps(dict(pid=os.getpid(), state_equal=True, continuation=continued)))
        return
    if args.play:
        # Visible practice setup, not a natural acquisition claim.
        if args.lesson in ('L04','L13'):
            j.acquire('raw_meat_common')
        if args.lesson=='L09':
            j.acquire('guide1_blade')
        if int(args.lesson[1:])>=10:
            e.player.level.perk_points=3
            for item in ('guide1_exchange','guide1_survey','guide1_inspect','guide1_cancel'):
                j.acquire(item)
            e.player.fighter.hp=max(1,e.player.fighter.hp-4)
            e.player.needs.thirst=0.2
        print('Controlled practice: supplies and advanced perk points are staged. Press K to purchase the lesson perks; I opens the tool inventory.',flush=True)
        e.run()
        return
    routes = {'L01': lambda j: food(j), 'L02': lambda j: food(j,ordinary=True),
              'L03': writing, 'L04': preparation, 'L05': creature, 'L06': place,
              'L07': enrollment, 'L08': appearance, 'L09': technique, 'L10': primitive,
              'L11': event_response, 'L12': persistent, 'L13': expedition,
              'L14': lambda j: food(j,ordinary=True)}
    routes[args.lesson](j)
    capture(e, args.output / 'game.png')
    report = dict(passed=True, lesson=args.lesson, evidence_kind='production input handlers in bounded room fixture',
                  events=j.events, observations=j.rows, solution_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  limits=['Initial resources/needs may be staged as labelled; this is not natural world discovery.',
                          'Screenshot uses the original renderer; automation cannot establish human learning.'])
    (args.output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(passed=True, lesson=args.lesson)))


if __name__ == '__main__':
    main()
