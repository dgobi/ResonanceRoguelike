"""B2 optional-v2 compatibility, explicit reset and invalid extension controls."""
import copy
from pathlib import Path
from b1_support import dump, read, hashes
from b2_cases import setup_components, component_snapshot, ENGINE_FIELDS


def run_case(e, ev):
    from engine.engine import Engine
    from engine.save_manager import ChunkCache
    import main
    if ev.job["variant"] == "legacy":
        from b1_characterize import perk_hooks
        expected = read(ev.job["expected"])["expected"]
        ev.check("B2-07", "actual B1 writer fresh bootstrap configured", True, e.player.needs._configured)
        ev.check("B2-07", "actual B1 writer fresh hooks", expected["hooks"], perk_hooks(e))
        ev.check("B2-07", "actual B1 writer HP preserved without healing", expected["hp"], e.player.fighter.hp)
        ev.check("B2-07", "actual B1 omitted timers explicitly default", [0, 0, 0, 0],
                 [e.true_sight_turns, e.player_speed_bonus_turns, e.player.chilled_turns, e.player._sickness_turns])
        ev.check("B2-07", "actual B1 bytes never migrated", read(ev.job["expected"])["checkpoint"], hashes(e.save_manager.save_path))
        return
    setup_components(e)
    e.save_manager.save(e)
    slot = e.save_manager.save_path
    original = read(slot / "player.json")
    ev.check("B2-07", "development format stays v2", 2, read(slot / "meta.json")["save_version"])
    variants = []
    for value in (None, [], {"version": 2}, {"version": True}):
        p = copy.deepcopy(original)
        p["component_state"] = value
        variants.append(("component block " + repr(value), p, "component", True))
    for field, value in (("true_sight_turns", True), ("true_sight_turns", -1), ("player_speed_bonus", "fast"),
                         ("_last_chunk_entry", [2]), ("rain_collection_progress", 1.5)):
        p = copy.deepcopy(original)
        p["component_state"]["engine"][field] = value
        variants.append((field + "=" + repr(value), p, field, False))
    p = copy.deepcopy(original)
    del p["component_state"]["player"]["chilled_turns"]
    variants.append(("missing new status", p, "chilled_turns", False))
    for field, value in (("item_state_version", 2), ("item_state_version", True), ("count", -1), ("count", False),
                         ("weight", float("nan")), ("nutrition", "food"), ("keywords", ["bad"]),
                         ("temporary_essence", [{"essence": "cutting", "strength": 0.5, "hits_remaining": -1}])):
        p = copy.deepcopy(original)
        p["inventory"]["items"][0][field] = value
        variants.append(("item " + field, p, "inventory row", field == "item_state_version"))
    p = copy.deepcopy(original)
    del p["inventory"]["items"][0]["weight"]
    variants.append(("missing new item field", p, "weight", False))
    p = copy.deepcopy(original)
    p["inventory"]["items"][p["equipment"]["offhand"]["inventory_index"]]["light_data"] = None
    variants.append(("active light with absent instance light", p, "light_data", True))
    for key, value in (("perks", []), ("needs", {"hunger": True, "thirst": 0.1}), ("fighter", None)):
        p = copy.deepcopy(original)
        p[key] = value
        variants.append((key, p, key, False))
    for name, payload, diagnostic, startup in variants:
        dump(slot / "player.json", payload)
        before = hashes(slot)
        for mode in ("hot", "cold"):
            if mode == "cold":
                e.save_manager.cache = ChunkCache(slot)
            refs = (e.player.fighter, e.player.needs, e.player.perks, e.player.inventory, e.entities, e.local_map, e.save_manager.cache)
            ev.check("B2-07", name + " " + mode + " rejected", False, e.save_manager.load(e))
            ev.check("B2-07", name + " diagnostic", True, diagnostic in e.save_manager.last_error)
            ev.check("B2-07", name + " preserves pre-load owners", True, all(a is b for a, b in zip(refs,
                     (e.player.fighter, e.player.needs, e.player.perks, e.player.inventory, e.entities, e.local_map, e.save_manager.cache))))
            ev.check("B2-07", name + " does not write", before, hashes(slot))
        if startup:
            entered = []
            run = Engine.run
            Engine.run = lambda engine: entered.append(True)
            code = None
            try:
                main.main()
            except SystemExit as error:
                code = error.code
            finally:
                Engine.run = run
            ev.check("B2-07", name + " bootstrap never enters loop", [1, []], [code, entered])
            ev.check("B2-07", name + " bootstrap keeps bytes", before, hashes(slot))
    # A synthetic older B1-v2 record is readable, but missing state resets rather
    # than retaining post-save values. No migration write or invented history.
    legacy = copy.deepcopy(original)
    legacy.pop("component_state")
    legacy["corruption"].pop("whisper_cooldown")
    old_fields = {"item_id", "name", "on_use", "turns_lit", "liquid", "liquid_volume", "text_id", "temporary_essence"}
    legacy["inventory"]["items"] = [{k: v for k, v in row.items() if k in old_fields} for row in legacy["inventory"]["items"]]
    dump(slot / "player.json", legacy)
    before = hashes(slot)
    ev.check("B2-07", "older v2 fields load", True, e.save_manager.load(e))
    ev.check("B2-07", "missing timer block resets session values", [0, 0.0, 0, 0.0, 0, 0, 0, 0, [0, 0]],
             [list(getattr(e, k)) if k == "_last_chunk_entry" else getattr(e, k) for k in ENGINE_FIELDS])
    ev.check("B2-07", "missing whisper cooldown resets", 0, e.player.corruption._whisper_cooldown)
    ev.check("B2-07", "old v2 still derives configured Needs and hooks", [True, True],
             [e.player.needs._configured, any(h.__name__ == "perk_hardened_step_tile_entered" for hs in e.hooks._handlers.values() for h in hs)])
    ev.check("B2-07", "loading old v2 does not migrate files", before, hashes(slot))
    # Explicit absence clears components; null/empty item values clear definitions.
    absent = copy.deepcopy(original)
    for key in ("needs", "corruption", "language", "perks", "level", "resonance", "weather"):
        absent[key] = None
    item = absent["inventory"]["items"][1]
    item.update(on_use=None, text_id="", nutrition=None, temporary_essence=[])
    dump(slot / "player.json", absent)
    e._pending_consume = {"item": e.player.inventory.items[0]}
    e._pending_throw = {"item": e.player.inventory.items[0]}
    e.inventory_screen.open = True
    ev.check("B2-07", "explicit absent components load", True, e.save_manager.load(e))
    ev.check("B2-07", "absent components replace old values", [None]*6,
             [getattr(e.player, k) for k in ("needs", "corruption", "language", "perks", "level")] + [e._pending_consume])
    ev.check("B2-07", "stale commands and modal reset", [None, False, []],
             [e._pending_throw, e.inventory_screen.open, e.inventory_screen._flat])
    item = e.player.inventory.items[1]
    ev.check("B2-07", "explicit null/empty item state", [None, "", None, []],
             [item.on_use, item.text_id, item.nutrition, item.temporary_essence])
    ev.check("B2-02", "no stale perk bonuses after absence", [0, 0, 0],
             [e.player.fighter.effective_av, e.player.fighter.corruption_damage_bonus, getattr(e.player.fighter, "corruption_channel_bonus", 0)])
    ev.check("B2-07", "weather absent derives a fresh configured system", ["clear", True],
             [e.weather.state, bool(e.weather._weather_defs)])
    # Every shipped factory item must fit the new explicit instance schema.
    # A full over-capacity replacement exercises production serialization and
    # reconstruction, rather than merely checking schema helper constants.
    from components.equipment import Equipment
    e.player.inventory.items = [e.item_factory.create(key) for key in sorted(e.data.items)]
    e.player.equipment = Equipment()
    e.player.light_source = None
    expected_ids = [i.item_id for i in e.player.inventory.items]
    e.save_manager.save(e)
    ev.check("B2-04", "entire shipped item catalog roundtrip", True, e.save_manager.load(e))
    ev.check("B2-04", "all catalog rows retained in order", expected_ids, [i.item_id for i in e.player.inventory.items])
