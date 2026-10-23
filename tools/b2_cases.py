"""B2 behavioral oracles, using real bootstrap/factories/save/load/turn consumers."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from b1_support import hashes, read, dump, gear
from b1_characterize import perk_hooks, needs_state


ENGINE_FIELDS = ("true_sight_turns", "player_speed_bonus", "player_speed_bonus_turns",
                 "_move_debt", "rain_collection_progress", "_wraith_overcorrect_turns",
                 "wind_turn", "_last_exposure_tier", "_last_chunk_entry")
ITEM_FIELDS = ("name", "tile", "weight", "stackable", "count", "on_use", "text_id",
               "nutrition", "hydration", "heal_amount", "eat_message", "drink_message",
               "burn_turns", "turns_lit", "light_data", "liquid", "liquid_volume", "qualities",
               "description", "harvest_from", "keywords", "decay_timer", "source_creature",
               "temporary_essence", "consumed_on_use", "_temp_av_bonus", "_temp_av_hits")


def plain(value):
    return json.loads(json.dumps(value))


def quiet(e):
    """Fixture setup, not an action under test: safe lab tile and no hostiles."""
    e.entities = [e.player]
    e.player.x, e.player.y = 45, 20
    e.local_map.set_tile(45, 20, "blood_pool", True, True)
    e.player_invincible = False
    e.player.needs.hunger = 0.2
    e.player.needs.thirst = 0.1
    e._update_fov()


def component_snapshot(e):
    p = e.player
    return plain({"engine": {k: getattr(e, k) for k in ENGINE_FIELDS},
        "status": {k: getattr(p, k, 0) for k in ("chilled_turns", "_sickness_turns")},
        "true_sight": p.true_sight, "needs": needs_state(e),
        "hunger": p.needs.hunger, "thirst": p.needs.thirst,
        "hooks": perk_hooks(e), "hp": p.fighter.hp,
        "bonuses": [p.fighter.effective_av, p.fighter.corruption_damage_bonus,
                    getattr(p.fighter, "corruption_channel_bonus", 0)],
        "perks": [sorted(p.perks.acquired), p.perks.perk_state, p.perks.affinity_scores],
        "corruption": [p.corruption.value, p.corruption._whisper_cooldown],
        "language": [sorted(p.language.known_deep_words), p.language.translation_events,
                     sorted(p.language.taught_texts), sorted(p.language.recovered_spans),
                     sorted((list(k), v) for k, v in p.language.recovered_text.items()), p.language.shown_lexicon_hint],
        "level": [p.level.level, p.level.exp, p.level.exp_to_next, p.level.perk_points, p.level.total_levels_gained],
        "turn": e.world_time.turn})


def setup_components(e, empty=False):
    quiet(e)
    p = e.player
    if empty:
        return
    p.perks.acquired = {"hardened_step", "attuned", "the_indifference", "corruption_channel", "marrow_drink"}
    p.perks.perk_state = {"hardened_step": {"uses": 7}}
    p.perks.affinity_scores = {"the_bound_name": 0.4}
    e.resonance_exposure, e.corruption = 0.5, 0.72
    e._corruption_thresholds = {0.15, 0.25, 0.4}
    e._register_player_perks()
    # The pre-B2 path needs its normal stat-only handlers to establish the same
    # legitimate pre-save state. Do not fire the whole ON_TURN event.
    from engine.perk_handlers import handle_attuned_turn, handle_indifference_turn, perk_corruption_channel_turn
    for handler in (handle_attuned_turn, handle_indifference_turn, perk_corruption_channel_turn):
        handler({"engine": e})
    values = (17, 0.2, 3, 0.25, 3, 2, 11, 3, (11, 12))
    for key, value in zip(ENGINE_FIELDS, values):
        setattr(e, key, value)
    p.true_sight = True
    p.chilled_turns, p._sickness_turns = 2, 3
    p.corruption.value, p.corruption._whisper_cooldown = 0.5, 8
    p.fighter.hp = 40
    p.language.known_deep_words = {"fixture_word"}
    p.language.translation_events = {"fixture_word": 4}
    p.language.taught_texts = {"lab_label_sarcophagus"}
    p.language.recovered_spans = {("lab_label_sarcophagus", 0, 1)}
    p.language.recovered_text = {("lab_label_sarcophagus", 0): "remembered"}
    p.language.shown_lexicon_hint = True
    p.level.level, p.level.exp, p.level.exp_to_next = 3, 23, 200
    p.level.perk_points, p.level.total_levels_gained = 2, 2


def components(e, ev):
    phase, empty = ev.job["phase"], ev.job["variant"] == "empty"
    if phase in ("write", "same"):
        setup_components(e, empty)
        expected = component_snapshot(e)
        ev.record["expected"] = expected
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        ev.check("B2-01", "writer completed supported save", True, e.save_manager.save_exists())
        if phase == "write":
            return
        setup_components(e, not empty)
        e.true_sight_turns = 99
        e.player._sickness_turns = 99
        e.player.needs.hunger = 0.8
        e.player.corruption._whisper_cooldown = 99
        ev.record["mutated"] = component_snapshot(e)
        ev.check("B2-01", "direct load completes", True, e.save_manager.load(e))
    else:
        expected = read(ev.job["expected"])["expected"]
    ev.check("B2-01", "Needs configured on every route", True, e.player.needs._configured)
    ev.check("B2-02", "acquired hooks reconstructed exactly once", expected["hooks"], perk_hooks(e))
    observed = component_snapshot(e)
    for key in expected:
        case = "B2-02" if key in ("hooks", "bonuses", "perks") else "B2-03" if key in ("engine", "status", "true_sight", "corruption") else "B2-01"
        ev.check(case, "immediate replacement: " + key, expected[key], observed[key])
    old_turn, old_hp = e.world_time.turn, e.player.fighter.hp
    old_h, old_t = e.player.needs.hunger, e.player.needs.thirst
    # Repeated load must neither stack hooks/bonuses nor replay healing/turn events.
    for _ in range(3):
        ev.check("B2-02", "repeated load completes", True, e.save_manager.load(e))
        ev.check("B2-02", "repeated load same derived state", expected, component_snapshot(e))
    e._advance_turn()
    ev.check("B2-03", "one actual turn", old_turn + 1, e.world_time.turn)
    if not empty:
        ev.check("B2-02", "Marrow Drink fires once after load", old_hp + 1, e.player.fighter.hp)
        ev.check("B2-03", "first timer tick uses restored durations", [16, 2, 1, 2, 7, 1],
                 [e.true_sight_turns, e.player_speed_bonus_turns, e.player.chilled_turns,
                  getattr(e.player, "_sickness_turns", 0), e.player.corruption._whisper_cooldown, e._wraith_overcorrect_turns])
        biome = e.world_map.get(e.world_x, e.world_y).biome_id
        mods = e.data.survival.get("biome_modifiers", {}).get(biome, {})
        ev.check("B2-01", "configured hunger and sickness consume next turn", round(old_h + e.player.needs._h_tick * mods.get("hunger", 1) + 0.003, 8), round(e.player.needs.hunger, 8))
        ev.check("B2-01", "configured thirst and sickness consume next turn", round(old_t + e.player.needs._t_tick * mods.get("thirst", 1) + 0.005, 8), round(e.player.needs.thirst, 8))
        for _ in range(16):
            e._advance_turn()
        ev.check("B2-03", "durations expire without becoming permanent", [0, False, 0, 0.0, 0, 0],
                 [e.true_sight_turns, e.player.true_sight, e.player_speed_bonus_turns,
                  e.player_speed_bonus, e.player.chilled_turns, getattr(e.player, "_sickness_turns", 0)])
    else:
        ev.check("B2-02", "removed healing perk never fires", old_hp, e.player.fighter.hp)


def item_snapshot(e):
    return plain([{k: getattr(i, k, 0 if k.startswith("_temp") else None) for k in ITEM_FIELDS}
                  for i in e.player.inventory.items])


def setup_items(e):
    quiet(e)
    from components.equipment import Equipment
    e.player.inventory.items = []
    e.player.equipment = Equipment()
    e.player.light_source = None
    for n in range(2):
        item = e.item_factory.create("crow_jerky")
        item.name = f"B2 distinct ration {n}"
        item.nutrition, item.hydration, item.heal_amount = 137 + n*100, 53+n, 2+n
        item.weight, item.count, item.stackable = 0.25+n, 2+n, True
        item.eat_message, item.drink_message = "Fixture ration consumed.", "Fixture drink."
        item.decay_timer, item.source_creature = 9+n, "plague_crow"
        item.harvest_from, item.description = "corpse", "Distinct preserved instance."
        item.qualities, item.keywords = {"fixture": n}, [{"tag": "edible", "tier": 2+n}]
        item.consumed_on_use = False
        item.temporary_essence = [{"essence": "cutting", "strength": 0.4, "hits_remaining": 3+n}]
        item._temp_av_bonus, item._temp_av_hits = 2+n, 4+n
        e.player.inventory.items.append(item)
    armor = e.item_factory.create("leather_jack")
    armor._temp_av_bonus, armor._temp_av_hits = 3, 7
    e.player.inventory.items.append(armor)
    e.player.equipment.equip(armor, "armor_torso")
    torch = e.item_factory.create("tallow_torch")
    torch.burn_turns, torch.turns_lit = 37, 11
    torch.light_data["radius"] = 4
    e.player.inventory.items.append(torch)
    e.item_system._use_equip_light(torch, e)
    from engine.item_system import _recompute_effective_av
    _recompute_effective_av(e.player, e.data)


def items(e, ev):
    phase = ev.job["phase"]
    if phase in ("write", "same"):
        setup_items(e)
        expected = item_snapshot(e)
        ev.record["expected"] = expected
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        ev.check("B2-04", "writer contains four distinct rows", 4, len(expected))
        if phase == "write":
            return
        e.player.inventory.items[0].nutrition = 999
        e.player.inventory.items[1].keywords.append({"tag": "unsaved", "tier": 1})
        ev.check("B2-04", "item direct load", True, e.save_manager.load(e))
    else:
        expected = read(ev.job["expected"])["expected"]
    for index, row in enumerate(expected):
        for key, value in row.items():
            ev.check("B2-04", f"row {index} {key}", value, item_snapshot(e)[index][key])
    ev.check("B2-04", "equipped armor exact instance", True, e.player.equipment.slots["armor_torso"] is e.player.inventory.items[2])
    ev.check("B2-04", "restored light exact instance and custom burn limit", [True, 37],
             [e.player.light_source._item_ref is e.player.inventory.items[3], e.player.light_source._burn_turns])
    # Mutating one row must not change another row or shared factory definition.
    fresh = e.item_factory.create("tallow_torch")
    before_radius = copy.deepcopy(e.data.items["tallow_torch"]["light"])
    fresh.light_data["radius"] = 99
    ev.check("B2-04", "factory instance owns its light data", before_radius, e.data.items["tallow_torch"]["light"])
    hunger = e.player.needs.hunger
    ev.check("B2-04", "real consumable handler uses restored instance", True, e.item_system.use(e.player.inventory.items[0], e))
    ev.check("B2-04", "restored nutrition affects hunger", round(max(0.0, hunger - 137/e.data.survival["hunger"]["max"]), 8), round(e.player.needs.hunger, 8))
    e._advance_turn()
    ev.check("B2-04", "custom fuel ticks on restored item", 12, e.player.equipment.slots["offhand"].turns_lit)


def processing(e, ev):
    from world.local_map import LocalMap
    from engine.save_manager import CachedChunk
    quiet(e)
    def record():
        return {"item_id": "dried_bitter_herb", "turns_remaining": 2, "decor_id": "", "source": "drying"}
    current, surface, underground = e.local_map, LocalMap(80, 43), LocalMap(80, 43)
    for m in (current, surface, underground):
        m.processing_layer[(5, 5)] = record()
    cache = e.save_manager.cache
    cache.hot[(e.world_x, e.world_y)] = CachedChunk(surface, [])
    cache.submap_hot[e.current_submap_id] = CachedChunk(current, [])
    cache.submap_hot["fixture-inactive"] = CachedChunk(underground, [])
    cache.hot[(e.world_x+1, e.world_y)] = CachedChunk(underground, [])  # deliberate alias control
    e._advance_turn()
    ev.check("B2-05", "all three maps tick exactly once including paired surface", [1, 1, 1],
             [m.processing_layer[(5, 5)]["turns_remaining"] for m in (current, surface, underground)])
    e._advance_turn()
    for label, m in (("current", current), ("paired surface", surface), ("inactive submap", underground)):
        ev.check("B2-05", label + " finishes", {}, m.processing_layer)
        ev.check("B2-05", label + " owns exactly one completed item", ["dried_bitter_herb"],
                 [i.item_id for i in m.floor_objects.get((5, 5), [])])
    e._advance_turn()
    ev.check("B2-05", "completion never duplicated", [1, 1, 1], [len(m.floor_objects.get((5, 5), [])) for m in (current, surface, underground)])
    # Save/load active processing and inspect exactly the saved remaining duration.
    current.processing_layer[(6, 6)] = record()
    e.save_manager.save(e)
    current.processing_layer[(6, 6)]["turns_remaining"] = 99
    ev.check("B2-05", "processing full load", True, e.save_manager.load(e))
    e._advance_turn()
    ev.check("B2-05", "active processing resumes persisted remaining turn", 1, e.local_map.processing_layer[(6, 6)]["turns_remaining"])


def actor_snapshot(a):
    return plain({"fighter": [a.fighter.max_hp, a.fighter.hp, a.fighter.power, a.fighter.defense, a.fighter.effective_av],
        "perception": [a.perception.faction, a.perception.hostile_to, a.perception.sight_radius, a.perception.hearing_radius, a.perception.sees_in_dark],
        "ai": [a.ai.target_x, a.ai.target_y, a.ai.memory_turns, a.ai.alert_memory, a.ai.wander_radius],
        "status": [getattr(a, k, 0) for k in ("_arrival_cooldown", "_ability_suppressed_turns", "_disrupted_turns")],
        "last_target": [getattr(a, "_last_known_px", None), getattr(a, "_last_known_py", None)]})


def actors(e, ev):
    phase = ev.job["phase"]
    if phase in ("write", "same"):
        quiet(e)
        a = e.creature_factory.spawn("hollow_revenant", 10, 10)
        a.fighter.max_hp, a.fighter.hp, a.fighter.power, a.fighter.defense = 71, 37, 8, 4
        a.fighter.effective_av = 6
        a.perception.faction, a.perception.hostile_to = "fixture", ["fixture_enemy"]
        a.perception.sight_radius, a.perception.hearing_radius, a.perception.sees_in_dark = 3, 12, True
        a.ai.target_x, a.ai.target_y, a.ai.memory_turns, a.ai.alert_memory, a.ai.wander_radius = 13, 14, 6, 19, 2
        a._arrival_cooldown, a._ability_suppressed_turns, a._disrupted_turns = 2, 4, 5
        a._last_known_px, a._last_known_py = 13, 14
        e.entities.append(a)
        expected = actor_snapshot(a)
        ev.record["expected"] = expected
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        ev.check("B2-06", "modified actor writer", 1, len(e.entities)-1)
        if phase == "write":
            return
        a.fighter.power = 99
        ev.check("B2-06", "actor full load", True, e.save_manager.load(e))
    else:
        expected = read(ev.job["expected"])["expected"]
    a = next(a for a in e.entities if a is not e.player)
    for key in expected:
        ev.check("B2-06", "actor restored " + key, expected[key], actor_snapshot(a)[key])
    e._advance_turn()
    ev.check("B2-06", "arrival countdown advances from restored value", 1, getattr(a, "_arrival_cooldown", 0))


def run_case(e, ev):
    ev.record["fixture_setup"] = "Controlled values via real components/factories in disposable laboratory; outcomes use actual save/load and consumers."
    {"components": components, "items": items, "processing": processing, "actors": actors}[ev.job["scenario"]](e, ev)
