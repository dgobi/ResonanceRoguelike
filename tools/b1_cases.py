"""Real-bootstrap/API integration cases. No factories or persistence mocks."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pickle
from b1_support import actor_state, boot, dump, gear, hashes, read, scene_state, SEED


def clean_gear(e):
    from components.inventory import Inventory
    from components.equipment import Equipment
    e.player.inventory = Inventory(13.5)
    e.player.equipment = Equipment()
    e.player.light_source = None
    e.player.fighter.effective_av = 0


def setup_gear(e, variant):
    clean_gear(e)
    p = e.player
    if variant == "empty":
        return
    if variant == "jerky":
        p.inventory.add(e.item_factory.create("crow_jerky"))
        return
    first, second = [e.item_factory.create("tallow_torch") for _ in range(2)]
    first.turns_lit, second.turns_lit = 10, 90
    if variant == "burnout":
        second.turns_lit = second.burn_turns - 1
    for i in (first, second):
        assert p.inventory.add(i)
    selected = first if variant == "first" else second
    e.item_system.use(selected, e)
    if variant == "reordered":
        p.inventory.items.reverse()
    if variant == "inactive":
        e.item_system.use(selected, e)  # actual extinguish route
    if variant == "gear":
        for name in ("crude_blade", "leather_jack"):
            i = e.item_factory.create(name)
            assert p.inventory.add(i)
            e.item_system.use(i, e)


def prepare_scenes(e):
    from world.world_map import SubMap
    from components.ai import AIState
    from generation.region_gen import generate_region
    from generation.local_gen import generate_submap
    from config import MAP_WIDTH, MAP_HEIGHT
    wx, wy = e.world_x, e.world_y
    sid = e.current_submap_id
    surface = e.save_manager.cache.load(wx, wy).local_map
    lab = e.local_map
    other = e.world_map.get(wx + 1, wy)
    sm = SubMap(f"b1_{wx+1}_{wy}", "laboratory", "B1 fixture lab", SEED, layout_id="starting_lab")
    other.submaps.append(sm)
    om, _ = generate_region(other, MAP_WIDTH, MAP_HEIGHT, e.data.terrain)
    um, _ = generate_submap(sm, MAP_WIDTH, MAP_HEIGHT, e.data.terrain, data=e.data)
    fixtures = [(wx, wy, None, surface, "grass", "hollow_revenant", 9),
                (wx, wy, sid, lab, "flagstone", "grave_thing", 7),
                (wx+1, wy, None, om, "dirt", None, 0),
                (wx+1, wy, sm.submap_id, um, "stone", "bog_wraith", 5)]
    expected = []
    for fx, fy, sub, m, terrain, creature, hp in fixtures:
        m.set_tile(3, 3, terrain, True, True)
        m.explored[2, 2] = True
        actors = []
        if creature:
            a = e.creature_factory.spawn(creature, 4, 4)
            a.fighter.hp = hp
            a.ai.state = AIState.WAITING
            actors.append(a)
        torch, water = (e.item_factory.create(n) for n in ("tallow_torch", "water_flask"))
        torch.turns_lit, water.liquid_volume = 37, 0.25
        m.floor_objects[(6, 6)] = [torch, water]
        m.decor[(7, 7)] = "crate"
        m.container_state[(7, 7)] = {"state": "open", "items": [{"item_id": "crow_jerky", "text_id": ""}]}
        if creature is None:
            m.floor_objects[(6, 6)] = []
            m.container_state[(7, 7)]["items"] = []
        if sub is None:
            e.save_manager.cache.store(fx, fy, m, [e.player] + actors)
        else:
            e.save_manager.cache.store_submap(sub, m, [e.player] + actors)
        expected.append({"address": [fx, fy, sub], "state": scene_state(m, actors)})
        if sub == sid:
            e.entities = [e.player] + actors
    return expected


def inspect_scenes(e, expected, ev):
    from engine.save_manager import _deserialize_entities
    for row in expected:
        wx, wy, sid = row["address"]
        cached = (e.save_manager.cache.load(wx, wy) if sid is None else e.save_manager.cache.load_submap(sid))
        ev.check("S03", f"address {row['address']} contents", row["state"],
                 scene_state(cached.local_map, _deserialize_entities(cached.entities, e)))


def scene_case(e, ev):
    from engine.save_manager import ChunkCache
    job = ev.job
    phase, variant = job["phase"], job["variant"]
    if phase in ("write", "same"):
        expected = prepare_scenes(e)
        if variant == "surface":
            e._ascend_from_submap()
        e.save_manager.save(e)
        ev.record["expected"] = {"scenes": expected, "address": [e.world_x, e.world_y, e.current_submap_id],
                                 "active": scene_state(e.local_map, e.entities)}
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        ev.check("F01", "writer version", 2, read((e.save_manager.checkpoint_path() if hasattr(e.save_manager, "checkpoint_path") else e.save_manager.save_path) / "meta.json")["save_version"])
        if phase == "write":
            ev.check("H04", "writer records checkpoint then stops", True, bool(ev.record["checkpoint"]))
            return
        expected_record = ev.record["expected"]
        # Memory-only mutation branch; nested values distinguish shallow copies.
        old_cache, old_map, old_actor = e.save_manager.cache, e.local_map, e.entities[-1]
        e.local_map.set_tile(3, 3, "mud", True, True)
        e.local_map.floor_objects[(6, 6)][0].turns_lit = 555
        e.local_map.container_state[(7, 7)]["items"].clear()
        old_actor.fighter.hp = 1
        ghost = e.creature_factory.spawn("stone_lurker", 60, 30)
        ghost.name = "B1 stale actor"
        e.entities.append(ghost)
        e._live_pursuers = [(ghost, 12, 12, None)]
        e._pending_pursuer_arrivals = [{"entity": ghost, "entry_x": 3, "entry_y": 3, "delay": 1}]
        e._pending_transfer = [ghost]
        ev.record["mutation"] = scene_state(e.local_map, e.entities)
        ev.check("S05", "same-process full load", True, e.save_manager.load(e))
        ev.check("S05", "map and cache detached", True, e.local_map is not old_map and e.save_manager.cache is not old_cache)
        ev.check("S05", "load did not write memory mutations", ev.record["checkpoint"], hashes(e.save_manager.save_path))
        ev.check("S06", "unsaved pursuer collections replaced", [0, 0, 0],
                 [len(e._live_pursuers), len(e._pending_pursuer_arrivals), len(e._pending_transfer)])
    else:
        expected_record = read(job["expected"])["expected"]
        expected = expected_record["scenes"]
    case = "S01" if variant == "surface" else "S02"
    ev.check(case, "complete scene address", expected_record["address"], [e.world_x, e.world_y, e.current_submap_id])
    ev.check(case, "active scene contents", expected_record["active"], scene_state(e.local_map, e.entities))
    ev.check(case, "exactly one engine player", 1, sum(a is e.player for a in e.entities))
    ev.check(case, "visibility recomputed", True, bool(e.local_map.visible.any()))
    inspect_scenes(e, expected, ev)
    if e.current_submap_id is None:
        sub = e.world_map.get(e.world_x, e.world_y).submaps[0]
        e._descend_to_submap(sub.submap_id)
    for cycle in range(3):
        e._ascend_from_submap()
        ev.check("S04", f"cycle {cycle} surface", expected[0]["state"], scene_state(e.local_map, e.entities))
        e._descend_to_submap(expected[1]["address"][2])
        ev.check("S04", f"cycle {cycle} lab", expected[1]["state"], scene_state(e.local_map, e.entities))
        ev.check("S04", f"cycle {cycle} single player", 1, sum(a is e.player for a in e.entities))
    e.save_manager.save(e)
    ev.check("S04", "sequence reload", True, e.save_manager.load(e))
    ev.check("S04", "sequence contents after disk reload", expected[1]["state"], scene_state(e.local_map, e.entities))


def gear_case(e, ev):
    variant, phase = ev.job["variant"], ev.job["phase"]
    case = {"empty": "R01", "jerky": "R02", "gear": "R03", "inactive": "R05",
            "first": "R04", "second": "R04", "reordered": "R04", "burnout": "R06"}[variant]
    if phase in ("write", "same"):
        setup_gear(e, variant)
        ev.record["expected"] = gear(e)
        if variant == "inactive":
            ev.record["before_save"] = copy.deepcopy(ev.record["expected"])
            # Contract: an extinguished, unequipped light retains its parameters
            # but has no owner reference after reconstruction. It must not relight.
            ev.record["expected"]["light"]["item_index"] = None
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        payload = read((e.save_manager.checkpoint_path() if hasattr(e.save_manager, "checkpoint_path") else e.save_manager.save_path) / "player.json")
        ev.check(case, "inventory object exists even when empty", True, isinstance(payload["inventory"], dict))
        if phase == "write":
            return
        old_items = list(e.player.inventory.items)
        armor = e.item_factory.create("leather_jack")
        e.player.inventory.add(armor)
        e.item_system.use(armor, e)
        torch = e.item_factory.create("tallow_torch")
        e.player.inventory.add(torch)
        e.item_system.use(torch, e)
        old_items += [armor, torch]
        ev.check(case, "same-process load", True, e.save_manager.load(e))
        ev.check(case, "old equipped flags cleared", True, all(not i.equipped for i in old_items))
        ev.check(case, "restored objects are fresh", True, all(all(n is not o for o in old_items) for n in e.player.inventory.items))
        expected = ev.record["expected"]
    else:
        expected = read(ev.job["expected"])["expected"]
    ev.check(case, "complete gear replacement and exact row identity", expected, gear(e))
    if variant in ("empty", "jerky", "inactive"):
        old = e.player.light_source
        fuel = [i.turns_lit for i in e.player.inventory.items]
        e._advance_turn()
        ev.check("R05", "absent or inactive light stays dark", True, old is None or not old.active)
        ev.check("R05", "dark action consumes no torch fuel", fuel, [i.turns_lit for i in e.player.inventory.items])
    else:
        selected = e.player.equipment.slots["offhand"]
        others = [(i, i.turns_lit) for i in e.player.inventory.items if i is not selected]
        ev.check("R06", "light references exact equipped row", True, e.player.light_source._item_ref is selected)
        before = selected.turns_lit
        e.entities = [e.player]  # explicitly remove unrelated lab actors for fuel tick
        e._advance_turn()
        ev.check("R06", "one turn burns exactly selected torch", before + 1, selected.turns_lit)
        ev.check("R06", "other inventory fuel unchanged", True, all(i.turns_lit == n for i, n in others))
        if variant == "burnout":
            ev.check("R06", "burnout clears exact offhand", None, e.player.equipment.slots["offhand"])
            ev.check("R06", "burnout removes selected, retains duplicate", True,
                     selected not in e.player.inventory.items and all(i in e.player.inventory.items for i, _ in others))
            ev.check("R06", "burnout extinguishes and releases owner reference", True,
                     e.player.light_source is None or (not e.player.light_source.active and
                     getattr(e.player.light_source, "_item_ref", None) is None))


def lurker_case(e, ev):
    from engine.creature_abilities import _ability_stone_lurker
    from engine.save_manager import _serialize_entity, _deserialize_entities
    variant, phase = ev.job["variant"], ev.job["phase"]
    if phase in ("write", "same"):
        a = e.creature_factory.spawn("stone_lurker", 60, 30)
        a.fighter.hp = 11
        _ability_stone_lurker(a, e)
        if variant in ("awake", "pending"):
            e.player.x, e.player.y = 59, 30
            _ability_stone_lurker(a, e)
            a.ai._triggered = True
            if variant == "awake":
                a._ambush_ready = False
            e.player.x, e.player.y = 15, 20
        payload = _serialize_entity(a)
        ev.check("K01", "stable identity in component payload", "stone_lurker", payload["id"])
        rebuilt = _deserialize_entities([payload], e)
        ev.check("K01" if variant == "dormant" else "K02", "immediate component state", actor_state(a), actor_state(rebuilt[0]))
        e.entities = [e.player, a]
        if variant == "owners":
            live, pending = (_deserialize_entities([payload], e)[0] for _ in range(2))
            live.x, pending.x = 58, 57
            e._live_pursuers = [(live, 1, 64, None)]
            e._pending_pursuer_arrivals = [{"entity": pending, "entry_x": 30, "entry_y": 20, "delay": 100}]
            surface = e.save_manager.cache.load(e.world_x, e.world_y).local_map
            sa = _deserialize_entities([payload], e)[0]
            sa.x = 56
            e.save_manager.cache.store(e.world_x, e.world_y, surface, [e.player, sa])
        ev.record["expected"] = {"actor": actor_state(a)}
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        if phase == "write":
            return
        ghost = e.creature_factory.spawn("grave_thing", 50, 30)
        e.entities.append(ghost)
        e._live_pursuers.append((ghost, 9, 9, None))
        e._pending_pursuer_arrivals.append({"entity": ghost, "entry_x": 2, "entry_y": 2, "delay": 1})
        ev.check("S06", "load replaces actor owners", True, e.save_manager.load(e))
        expected = ev.record["expected"]
    else:
        expected = read(ev.job["expected"])["expected"]
    actors = [a for a in e.entities if a is not e.player]
    ev.check("K01", "one restored scene lurker", 1, len(actors))
    a = actors[0]
    ev.check("K01" if variant in ("dormant", "owners") else "K02", "immediate scene lifecycle", expected["actor"], actor_state(a))
    if variant == "owners":
        surface = e.save_manager.cache.load(e.world_x, e.world_y)
        all_actors = actors + [x[0] for x in e._live_pursuers] + [x["entity"] for x in e._pending_pursuer_arrivals] + _deserialize_entities(surface.entities, e)
        ev.check("K04", "all four serialization owners retain distinct lurkers", [56, 57, 58, 60], sorted(a.x for a in all_actors))
        ev.check("K04", "all owners keep dormant definition", True, all(a._creature_id == "stone_lurker" and a._hibernating for a in all_actors))
        e._tick_pending_pursuer_arrivals()
        ev.check("S06", "no stale arrival on next tick", 1, len(e._pending_pursuer_arrivals))
        return
    _ability_stone_lurker(a, e)
    ev.check("K01" if variant == "dormant" else "K02", "distant ability retains lifecycle", expected["actor"], actor_state(a))
    # Observe actual attack calls, forwarding every call to actual combat.
    import components.ai as ai_module
    original = ai_module._monster_attack_entity
    calls = []
    def observed(*args, **kwargs):
        import inspect
        calls.append(inspect.currentframe().f_back.f_code.co_name)
        return original(*args, **kwargs)
    ai_module._monster_attack_entity = observed
    try:
        if variant == "dormant":
            e.player.x, e.player.y = a.x - 3, a.y
        def tick():
            e.ai_system.process(e.entities, e.player, e.local_map, e.world_map,
                                e.world_x, e.world_y, e.log, e.world_time, e.data, engine=e)
        e.reality_bubble.update(e.world_x, e.world_y, e.world_map)
        tick()
        ev.check("K03", "one pending ambush or none if consumed", 0 if variant == "awake" else 1, calls.count("process"))
        ev.check("K03", "awake after actual AI action", False, a._hibernating)
        ev.check("K03", "ambush consumed", False, a._ambush_ready)
        tick()
        ev.check("K03", "second AI tick never repeats free ambush", 0 if variant == "awake" else 1, calls.count("process"))
        ev.record["attack_callers"] = calls
    finally:
        ai_module._monster_attack_entity = original


def run_case(e, ev):
    {"scenes": scene_case, "gear": gear_case, "lurker": lurker_case}[ev.job["scenario"]](e, ev)
