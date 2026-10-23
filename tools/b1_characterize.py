"""Exact, separately reported B2/B3 observations on baseline and candidate."""
from __future__ import annotations
import copy
from b1_support import dump, hashes, read


def needs_state(e):
    n = e.player.needs
    return {"configured": n._configured, "hunger_rate": n._h_tick,
            "thirst_rate": n._t_tick, "hunger_label": n.hunger_state,
            "stages": len(n._h_stages)}


def perk_hooks(e):
    return sorted(h.__name__ for hs in e.hooks._handlers.values() for h in hs if getattr(h, "_is_perk_handler", False))


def characterize(e, ev):
    from engine.save_manager import ChunkCache
    from world.local_map import LocalMap
    phase = ev.job["phase"]
    if phase in ("write", "same"):
        e._ascend_from_submap()  # avoid baseline B1 scene alias in B2 controls
        e.entities = [e.player]
        e.player.needs.hunger = 0.2
        e.player.perks.acquired.add("hardened_step")
        e._register_player_perks()
        e.true_sight_turns = 17
        ev.record["configured_before"] = needs_state(e)
        ev.record["hooks_before"] = perk_hooks(e)
        ev.check("B01", "actual perk registered", True, "perk_hardened_step_tile_entered" in perk_hooks(e))
        e.local_map.set_tile(3, 3, "grass", True, True)
        e.save_manager.save(e)
        ev.record["checkpoint"] = hashes(e.save_manager.save_path)
        if phase == "write":
            return
        e.true_sight_turns = 3
        ev.check("B01", "direct load completed", True, e.save_manager.load(e))
    route = "fresh bootstrap" if phase == "read" else "direct SaveManager.load"
    ev.check("B01", route + " Needs configuration omitted", False, e.player.needs._configured)
    ev.check("B01", route + " fallback hunger label at 0.2", "Hungry", e.player.needs.hunger_state)
    ev.record["needs_after"] = needs_state(e)
    ev.defect("B01", "B2-NEEDS", "B2", {"route": route, **needs_state(e)})
    ev.check("B01", "omitted transient timer route signature", 0 if phase == "read" else 3, e.true_sight_turns)
    ev.defect("B01", "B2-TIMER", "B2", {"route": route, "saved": 17, "observed": e.true_sight_turns})
    ev.check("B01", "perk remains acquired", True, "hardened_step" in e.player.perks.acquired)
    ev.check("B01", "hook registration route signature", phase != "read", "perk_hardened_step_tile_entered" in perk_hooks(e))
    ev.defect("B01", "B2-HOOKS", "B2", {"route": route, "hooks": perk_hooks(e)})
    # Travel writes the later surface mutation before full load. This separate
    # reader branch is never treated as the untouched writer checkpoint.
    before = hashes(e.save_manager.save_path)
    e.local_map.set_tile(3, 3, "dirt", True, True)
    sub = e.world_map.get(e.world_x, e.world_y).submaps[0]
    e._descend_to_submap(sub.submap_id)
    after = hashes(e.save_manager.save_path)
    ev.check("B02", "travel changes persisted scene", True, before != after)
    ev.check("B02", "full reload after travel", True, e.save_manager.load(e))
    ev.check("B02", "travel-written surface is restored", "dirt", str(e.local_map.tiles[3, 3]["terrain"]))
    ev.defect("B02", "B3-GENERATIONS", "B3", {"saved_marker": "grass", "travel_marker": "dirt", "loaded_marker": "dirt"})
    # Inactive dirty map and actual wrong-cache-owner offscreen branch.
    wx, wy = e.world_x + 1, e.world_y
    other = LocalMap(80, 43)
    other.set_tile(3, 3, "grass", True, True)
    e.save_manager.cache.store(wx, wy, other, [])
    other.set_tile(3, 3, "mud", True, True)
    e.save_manager.cache.store_hot_only(wx, wy, other, [])
    e.save_manager.save(e)
    cold = ChunkCache(e.save_manager.save_path).load(wx, wy)
    ev.check("B03", "dirty inactive map not flushed", "grass", str(cold.local_map.tiles[3, 3]["terrain"]))
    ev.defect("B03", "B3-DIRTY-HOT", "B3", {"hot": "mud", "persisted": "grass"})
    other.processing_layer[(5, 5)] = {"item_id": "dried_bitter_herb", "turns_remaining": 2, "decor_id": "", "source": "drying"}
    ev.check("B03", "cache owner is SaveManager.cache.hot", [False, True], [hasattr(e.save_manager, "hot"), (wx, wy) in e.save_manager.cache.hot])
    e._advance_turn()
    ev.check("B03", "inactive processing does not advance", 2, other.processing_layer[(5, 5)]["turns_remaining"])
    ev.defect("B03", "B2-OFFSCREEN-OWNER", "B2/B3 simulation", {"before": 2, "after": 2, "actual_owner": "SaveManager.cache.hot"})
