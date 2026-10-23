# engine/debug.py
from __future__ import annotations
import pygame
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine


# ------------------------------------------------------------------ #
#  Console command functions
#  Each takes (parts: list[str], engine: Engine) and logs results.
# ------------------------------------------------------------------ #

def _cc_spawn_creature(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: spawn_creature <id>", FRESH_WOUND)
        return
    creature_id = parts[1]
    px, py = engine.player.x, engine.player.y
    for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
        tx, ty = px + dx, py + dy
        if engine.local_map.in_bounds(tx, ty) and engine.local_map.walkable[tx, ty]:
            creature = engine.creature_factory.spawn(creature_id, tx, ty)
            if creature:
                engine.entities.append(creature)
                engine.log.add(f"[DEBUG] Spawned {creature_id} at ({tx},{ty}).", AGED_WOOD)
            else:
                engine.log.add(f"[DEBUG] Unknown creature: {creature_id}.", FRESH_WOUND)
            return
    engine.log.add("[DEBUG] No adjacent walkable tile.", FRESH_WOUND)


def _cc_spawn_item(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: spawn_item <id>", FRESH_WOUND)
        return
    item_id = parts[1]
    px, py = engine.player.x, engine.player.y
    item = engine.item_factory.create(item_id, px, py)
    if item:
        engine.entities.append(item)
        engine.log.add(f"[DEBUG] Spawned {item_id} at ({px},{py}).", AGED_WOOD)
    else:
        engine.log.add(f"[DEBUG] Unknown item: {item_id}.", FRESH_WOUND)


def _cc_place_decor(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: place_decor <id>  (places at player pos)", FRESH_WOUND)
        engine.log.add("[DEBUG]        place_decor clear  (removes at player pos)", FRESH_WOUND)
        return
    from generation.decor_utils import place_decor, clear_decor
    px, py = engine.player.x, engine.player.y
    decor_id = parts[1]
    if decor_id == "clear":
        clear_decor(engine.local_map, px, py)
        engine.log.add(f"[DEBUG] Cleared decor at ({px},{py}).", AGED_WOOD)
    elif decor_id not in engine.data.decoratives:
        engine.log.add(f"[DEBUG] Unknown decor id: {decor_id}.", FRESH_WOUND)
        ids = ", ".join(sorted(engine.data.decoratives.keys()))
        engine.log.add(f"[DEBUG] Known: {ids}", AGED_WOOD)
    else:
        place_decor(engine.local_map, px, py, decor_id)
        engine.log.add(f"[DEBUG] Placed {decor_id} at ({px},{py}).", AGED_WOOD)


def _cc_grant_perk(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: grant_perk <id>", FRESH_WOUND)
        return
    perk_id = parts[1]
    perks_comp = getattr(engine.player, "perks", None)
    if perks_comp is None:
        engine.log.add("[DEBUG] Player has no perks component.", FRESH_WOUND)
    elif perk_id not in engine.data.perks:
        engine.log.add(f"[DEBUG] Unknown perk: {perk_id}.", FRESH_WOUND)
    else:
        perks_comp.add_perk(perk_id)
        engine._register_player_perks()
        engine.log.add(f"[DEBUG] perk granted: {perk_id}", AGED_WOOD)


def _cc_remove_perk(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: remove_perk <id>", FRESH_WOUND)
        return
    perk_id = parts[1]
    perks_comp = getattr(engine.player, "perks", None)
    if perks_comp is None:
        engine.log.add("[DEBUG] Player has no perks component.", FRESH_WOUND)
    else:
        perks_comp.remove_perk(perk_id)
        engine._register_player_perks()
        engine.log.add(f"[DEBUG] perk removed: {perk_id}", AGED_WOOD)


def _cc_list_perks(parts: list[str], engine: "Engine") -> None:
    perks_comp = getattr(engine.player, "perks", None)
    if perks_comp is None or not perks_comp.active_perks:
        engine.log.add("[DEBUG] No active perks.", AGED_WOOD)
    else:
        for pid in perks_comp.active_perks:
            engine.log.add(f"  {pid}", AGED_WOOD)


def _cc_set_exposure(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: set_exposure <0.0-1.5>", FRESH_WOUND)
        return
    try:
        val = float(parts[1])
        engine.resonance_exposure = max(0.0, min(1.5, val))
        engine._last_exposure_tier = 0   # force tier re-check next turn
        engine.log.add(
            f"[DEBUG] exposure={engine.resonance_exposure:.3f}", AGED_WOOD)
    except ValueError:
        engine.log.add("[DEBUG] Invalid value.", FRESH_WOUND)


def _cc_set_corruption(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: set_corruption <0.0-1.0>", FRESH_WOUND)
        return
    try:
        val = float(parts[1])
        from engine.resonance_system import _check_corruption_thresholds
        old = engine.corruption
        engine.corruption = max(0.0, min(1.0, val))
        # Sync player corruption component so UI reflects the change
        player_corr = getattr(engine.player, "corruption", None)
        if player_corr is not None:
            player_corr.value = engine.corruption
        effects: dict = {}
        _check_corruption_thresholds(engine, old, engine.corruption, effects)
        if effects.get("add_message"):
            engine.log.add(effects["add_message"],
                           effects.get("message_color", AGED_WOOD))
        engine.log.add(
            f"[DEBUG] corruption={engine.corruption:.3f}", AGED_WOOD)
    except ValueError:
        engine.log.add("[DEBUG] Invalid value.", FRESH_WOUND)


def _cc_pulse_bell(parts: list[str], engine: "Engine") -> None:
    from engine.discharge import trigger_discharge
    effects: dict = {}
    trigger_discharge(engine, engine.player.x, engine.player.y, "intact", effects)
    msg = effects.get("add_message")
    col = effects.get("message_color", AGED_WOOD)
    if msg:
        engine.log.add(msg, col)
    engine.log.add("[DEBUG] Intact bell pulse triggered.", AGED_WOOD)


def _cc_pulse_cracked(parts: list[str], engine: "Engine") -> None:
    from engine.discharge import trigger_discharge
    effects: dict = {}
    trigger_discharge(engine, engine.player.x, engine.player.y, "cracked", effects)
    msg = effects.get("add_message")
    col = effects.get("message_color", AGED_WOOD)
    if msg:
        engine.log.add(msg, col)
    engine.log.add("[DEBUG] Cracked bell pulse triggered.", AGED_WOOD)


def _cc_show_resonance(parts: list[str], engine: "Engine") -> None:
    exp  = getattr(engine, "resonance_exposure", 0.0)
    corr = getattr(engine, "corruption",         0.0)
    wind = getattr(engine, "wind_turn",          0)
    tier = getattr(engine, "_last_exposure_tier", 0)
    thresholds = getattr(engine, "_corruption_thresholds", set())
    engine.log.add(
        f"[DEBUG] exposure={exp:.3f}  corruption={corr:.3f}  "
        f"wind={wind}/40  tier={tier}",
        AGED_WOOD,
    )
    engine.log.add(
        f"[DEBUG] thresholds: {', '.join(sorted(thresholds)) or 'none'}",
        STONE_BLUE,
    )


def _cc_scan_resonance(_parts: list[str], engine: "Engine") -> None:
    """Scan all tiles within 20 tiles for resonant terrain."""
    import math
    px, py = engine.player.x, engine.player.y
    found = []
    for x in range(engine.local_map.width):
        for y in range(engine.local_map.height):
            dist = math.sqrt((x - px) ** 2 + (y - py) ** 2)
            if dist > 20.0:
                continue
            terrain_id = str(engine.local_map.tiles["terrain"][x, y])
            td = engine.data.terrain.get(terrain_id, {})
            emit = td.get("resonance_emit", 0.0)
            # Also check decor layer
            _dbg_did = engine.local_map.decor.get((x, y))
            if _dbg_did:
                _dbg_demit = engine.data.decoratives.get(_dbg_did, {}).get("resonance_emit", 0.0)
                if _dbg_demit > emit:
                    emit = _dbg_demit
                    terrain_id = _dbg_did
            if emit > 0.0:
                found.append((dist, terrain_id, x, y, emit))
    if not found:
        engine.log.add("No resonant terrain in range.", STONE_BLUE)
        return
    found.sort()
    for dist, tid, x, y, emit in found[:10]:
        engine.log.add(
            f"  {tid} at ({x},{y}) emit={emit:.2f} dist={dist:.1f}",
            VERDANT_MID,
        )


def _cc_show_corruption_rate(_parts: list[str], engine: "Engine") -> None:
    """Show current per-turn corruption growth/decay rate."""
    exp  = getattr(engine, "resonance_exposure", 0.0)
    corr = getattr(engine, "corruption",         0.0)
    # Mirror resonance_system.py logic to compute tick
    decay = -0.008   # base per-turn decay
    from engine.resonance_system import _scan_resonant_terrain
    try:
        nearest_emit, nearest_dist = _scan_resonant_terrain(engine)
    except Exception:
        nearest_emit, nearest_dist = 0.0, 999.0
    if nearest_emit > 0.0 and nearest_dist <= 20.0:
        proximity  = 1.0 - (nearest_dist / 20.0)
        exp_tick   = nearest_emit * proximity * 0.015
        decay_net  = exp_tick   # no net decay when near resonant terrain
    else:
        exp_tick   = 0.0
        decay_net  = decay
    engine.log.add(
        f"[DEBUG] corruption={corr:.4f}  exposure={exp:.4f}  "
        f"exp_tick/turn={decay_net:+.4f}",
        AGED_WOOD,
    )
    engine.log.add(
        f"[DEBUG] nearest_emit={nearest_emit:.3f}  dist={nearest_dist:.1f}",
        STONE_BLUE,
    )


def _cc_set_weather(parts: list[str], engine: "Engine") -> None:
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system present.", FRESH_WOUND)
        return
    if len(parts) < 2:
        valid = ", ".join(weather.VALID_STATES)
        engine.log.add(f"[DEBUG] Usage: set_weather <state>  valid: {valid}", FRESH_WOUND)
        return
    state = parts[1]
    if state not in weather.VALID_STATES:
        engine.log.add(f"[DEBUG] Unknown weather state: {state}.", FRESH_WOUND)
        return
    weather.force_state(state)
    engine.log.add(f"[DEBUG] Weather set to: {state}", AGED_WOOD)


def _cc_show_weather(parts: list[str], engine: "Engine") -> None:
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system present.", FRESH_WOUND)
        return
    engine.log.add(
        f"[DEBUG] weather={weather.state}  "
        f"intensity={weather.intensity:.2f}  "
        f"turns_left={weather.turns_remaining}",
        AGED_WOOD,
    )


def _cc_stop_weather(_parts: list[str], engine: "Engine") -> None:
    """Clear all weather: force clear state, remove emitters, clear particles and fog cache."""
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system present.", FRESH_WOUND)
        return
    weather.force_state("clear")
    from rendering.particles import update_weather_emitters
    update_weather_emitters(engine)
    ps = getattr(engine, "particle_system", None)
    if ps is not None:
        ps.clear()
    engine._fog_surface = None
    engine.log.add("[debug] weather cleared â€” sky blank, particles gone.", AGED_WOOD)


def _cc_force_weird_weather(_parts: list[str], engine: "Engine") -> None:
    import random as _random
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system present.", FRESH_WOUND)
        return
    _WEIRD = ["resonance_storm", "forgetting_fog", "bone_snow", "dead_calm"]
    state = _random.choice(_WEIRD)
    weather.force_state(state)
    engine.log.add(f"[DEBUG] Weird weather forced: {state}", AGED_WOOD)


def _cc_toggle_move_log(_parts: list[str], engine: "Engine") -> None:
    engine.debug_move_log = not getattr(engine, "debug_move_log", False)
    state = "ON" if engine.debug_move_log else "OFF"
    engine.log.add(f"[DEBUG] Move log {state}.", AGED_WOOD)


def _cc_give_debug_weapon(_parts: list[str], engine: "Engine") -> None:
    item = engine.item_factory.create("debug_blade", engine.player.x, engine.player.y)
    if item is None:
        engine.log.add("[DEBUG] debug_blade not found in data.", FRESH_WOUND)
        return
    inv = getattr(engine.player, "inventory", None)
    if inv is None:
        engine.entities.append(item)
        engine.log.add("[DEBUG] debug_blade dropped at feet (no inventory).", AGED_WOOD)
        return
    inv.add(item)
    engine.log.add("[DEBUG] debug_blade added to inventory.", AGED_WOOD)


def _cc_particle_stats(_parts: list[str], engine: "Engine") -> None:
    ps = getattr(engine, "particle_system", None)
    if ps is None:
        engine.log.add("[DEBUG] No particle system.", FRESH_WOUND)
        return
    n_particles = len(ps.particles)
    n_ambient   = ps._pool_count("ambient")
    n_combat    = ps._pool_count("combat")
    n_emitters  = len(ps.emitters)
    engine.log.add(
        f"[particles] total={n_particles}/{ps.MAX_PARTICLES}  "
        f"ambient={n_ambient}/{ps.AMBIENT_CAP}  "
        f"combat={n_combat}/{ps.COMBAT_CAP}  "
        f"emitters={n_emitters}",
        AGED_WOOD,
    )


def _cc_test_rain(parts: list[str], engine: "Engine") -> None:
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system.", FRESH_WOUND)
        return
    kind = parts[1].lower() if len(parts) > 1 else "light"
    state_map = {
        "light": "light_rain",
        "heavy": "heavy_rain",
        "storm": "resonance_storm",
    }
    state = state_map.get(kind, "light_rain")
    weather.force_state(state)
    engine.log.add(f"[debug] rain test: {kind}", AGED_WOOD)


def _cc_test_fog(parts: list[str], engine: "Engine") -> None:
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system.", FRESH_WOUND)
        return
    kind = parts[1].lower() if len(parts) > 1 else "fog"
    state = "forgetting_fog" if kind in ("forgetting", "forgetting_fog") else "fog"
    weather.force_state(state)
    engine.log.add(f"[debug] fog test: {state}", AGED_WOOD)


def _cc_test_snow(_parts: list[str], engine: "Engine") -> None:
    weather = getattr(engine, "weather", None)
    if weather is None:
        engine.log.add("[DEBUG] No weather system.", FRESH_WOUND)
        return
    weather.force_state("bone_snow")
    engine.log.add("[debug] bone snow test", AGED_WOOD)


def _cc_test_waystone_ring(_parts: list[str], engine: "Engine") -> None:
    ps = getattr(engine, "particle_system", None)
    if ps is None:
        engine.log.add("[DEBUG] No particle system.", FRESH_WOUND)
        return
    import random as _rand
    from rendering.particles import make_waystone_ring
    ring = make_waystone_ring(
        float(engine.player.x), float(engine.player.y), _rand.Random())
    ps.emit(ring)
    engine.log.add("[debug] waystone ring emitted at player position.", AGED_WOOD)


def _cc_clear_particles(_parts: list[str], engine: "Engine") -> None:
    ps = getattr(engine, "particle_system", None)
    if ps is None:
        engine.log.add("[DEBUG] No particle system.", FRESH_WOUND)
        return
    ps.clear()
    engine.log.add("[debug] particles cleared", AGED_WOOD)


def _cc_toggle_resonance_sight(_parts: list[str], engine: "Engine") -> None:
    engine._resonance_sight_active = not getattr(engine, "_resonance_sight_active", False)
    state = "ON" if engine._resonance_sight_active else "OFF"
    engine.log.add(f"[debug] resonance sight {state}.", RESONANCE_MID)


def _cc_test_camera_drift(_parts: list[str], engine: "Engine") -> None:
    """
    Teleport player 15 tiles N/S/E/W and back, then visually flag the
    four corners of the viewport for manual inspection.
    Reports the player's start position to console â€” the player ends up
    back there after the round trip.
    """
    ox, oy = engine.player.x, engine.player.y
    lm = engine.local_map
    DIST = 15

    def _try_move(dx, dy):
        nx = max(0, min(lm.width  - 1, engine.player.x + dx))
        ny = max(0, min(lm.height - 1, engine.player.y + dy))
        engine.player.x, engine.player.y = nx, ny

    # Move in 4 cardinal directions and back each time
    for dx, dy in ((0, -DIST), (0, DIST), (-DIST, 0), (DIST, 0)):
        _try_move(dx, dy)
        _try_move(-dx, -dy)

    # Return to origin
    engine.player.x, engine.player.y = ox, oy

    engine.log.add(
        "[debug] Camera drift test complete â€” inspect viewport corners for "
        "pixel accumulation. Origin: ({ox},{oy})".format(ox=ox, oy=oy),
        AGED_WOOD,
    )


def _cc_toggle_callouts(parts: list[str], engine: "Engine") -> None:
    which = parts[1].lower() if len(parts) > 1 else "all"
    d = engine.display
    if which in ("damage", "all"):
        d.CALLOUT_DAMAGE_NUMBERS  = not d.CALLOUT_DAMAGE_NUMBERS
    if which in ("sounds", "all"):
        d.CALLOUT_CREATURE_SOUNDS = not d.CALLOUT_CREATURE_SOUNDS
    if which in ("status", "all"):
        d.CALLOUT_STATUS_EFFECTS  = not d.CALLOUT_STATUS_EFFECTS
    engine.log.add(
        f"[callouts] damage={d.CALLOUT_DAMAGE_NUMBERS}  "
        f"sounds={d.CALLOUT_CREATURE_SOUNDS}  "
        f"status={d.CALLOUT_STATUS_EFFECTS}",
        AGED_WOOD,
    )


def _cc_teach_word(parts: list[str], engine: "Engine") -> None:
    if len(parts) < 2:
        engine.log.add("[DEBUG] Usage: teach_word <word_id>", FRESH_WOUND)
        return
    word_id = parts[1].lower()
    wdef = engine.data.deep_tongue.get(word_id)
    if wdef is None:
        engine.log.add(f"[DEBUG] Unknown word: {word_id}", FRESH_WOUND)
        return
    lang = getattr(engine.player, "language", None)
    if lang is None:
        engine.log.add("[DEBUG] Player has no language component.", FRESH_WOUND)
        return
    if lang.knows(word_id):
        engine.log.add(f"[DEBUG] {word_id}: already known", AGED_WOOD)
        return
    lang.learn(word_id, engine.world_time.turn)
    deep = wdef.get("deep", word_id)
    common = wdef.get("common", "?")
    engine.log.add(f"[DEBUG] {word_id}: learned ({deep} / {common})", AGED_WOOD)


def _cc_list_known(parts: list[str], engine: "Engine") -> None:
    lang = getattr(engine.player, "language", None)
    if lang is None or not lang.known_deep_words:
        engine.log.add("[DEBUG] No words known.", AGED_WOOD)
        return
    _CATS = ["cosmic", "body", "time", "place", "people",
             "action", "essence", "number", "ominous", "legacy"]
    for cat in _CATS:
        cat_all = [w for w in engine.data.deep_tongue.values()
                   if w.get("category") == cat]
        cat_known = [w for w in cat_all if lang.knows(w["id"])]
        if not cat_known:
            continue
        engine.log.add(
            f"  {cat.upper()} ({len(cat_known)} known / {len(cat_all)} total)",
            STEEL_WATER,
        )
        for w in cat_known:
            engine.log.add(
                f"    {w['id']}: {w.get('deep', '?')} = "
                f"{w.get('common', '?')} [tier {w.get('tier', 1)}]",
                STONE_BLUE,
            )


def _cc_show_lexicon(parts: list[str], engine: "Engine") -> None:
    lang = getattr(engine.player, "language", None)
    _CATS = ["cosmic", "body", "time", "place", "people",
             "action", "essence", "number", "ominous", "legacy"]
    for cat in _CATS:
        cat_words = [w for w in engine.data.deep_tongue.values()
                     if w.get("category") == cat]
        if not cat_words:
            continue
        engine.log.add(f"  {cat.upper()} ({len(cat_words)})", STEEL_WATER)
        for w in cat_words:
            known = lang and lang.knows(w["id"])
            mark = "\u2713" if known else " "
            if known:
                line = f"    [{mark}] {w['id']}: {w.get('deep', '?')} = {w.get('common', '?')}"
            else:
                line = f"    [{mark}] {w['id']}: ???"
            engine.log.add(line, STONE_BLUE if known else SLATE_DARK)


def _cc_help(parts: list[str], engine: "Engine") -> None:
    for cat in ("RESONANCE", "ENTITIES", "PERKS", "WEATHER", "VISUAL", "LANGUAGE", "SYSTEM"):
        items = [(n, m) for n, m in CONSOLE_COMMANDS.items()
                 if m["category"] == cat]
        if not items:
            continue
        engine.log.add(f"  [{cat}]", STEEL_WATER)
        for _name, meta in items:
            engine.log.add(
                f"    {meta['usage']:<34} {meta['desc']}",
                STONE_BLUE,
            )


# ------------------------------------------------------------------ #
#  Command registry â€” edit here to add / remove console commands
# ------------------------------------------------------------------ #

CONSOLE_COMMANDS: dict = {
    # RESONANCE -------------------------------------------------------
    "set_exposure":   {
        "fn":       _cc_set_exposure,
        "usage":    "set_exposure <0.0-1.5>",
        "desc":     "Set resonance exposure directly.",
        "category": "RESONANCE",
    },
    "set_corruption": {
        "fn":       _cc_set_corruption,
        "usage":    "set_corruption <0.0-1.0>",
        "desc":     "Set corruption, fire thresholds.",
        "category": "RESONANCE",
    },
    "pulse_bell": {
        "fn":       _cc_pulse_bell,
        "usage":    "pulse_bell",
        "desc":     "Simulate intact bell discharge.",
        "category": "RESONANCE",
    },
    "pulse_cracked": {
        "fn":       _cc_pulse_cracked,
        "usage":    "pulse_cracked",
        "desc":     "Simulate cracked bell partial discharge.",
        "category": "RESONANCE",
    },
    "show_resonance": {
        "fn":       _cc_show_resonance,
        "usage":    "show_resonance",
        "desc":     "Print resonance/corruption/wind state.",
        "category": "RESONANCE",
    },
    "scan_resonance": {
        "fn":       _cc_scan_resonance,
        "usage":    "scan_resonance",
        "desc":     "List resonant tiles within 20 tiles of player.",
        "category": "RESONANCE",
    },
    "show_corruption_rate": {
        "fn":       _cc_show_corruption_rate,
        "usage":    "show_corruption_rate",
        "desc":     "Show per-turn corruption/exposure rate.",
        "category": "RESONANCE",
    },
    # ENTITIES --------------------------------------------------------
    "spawn_creature": {
        "fn":       _cc_spawn_creature,
        "usage":    "spawn_creature <id>",
        "desc":     "Spawn creature on adjacent walkable tile.",
        "category": "ENTITIES",
    },
    "spawn_item": {
        "fn":       _cc_spawn_item,
        "usage":    "spawn_item <id>",
        "desc":     "Drop item at player position.",
        "category": "ENTITIES",
    },
    "place_decor": {
        "fn":       _cc_place_decor,
        "usage":    "place_decor <id>|clear",
        "desc":     "Place or clear a decorative tile at player position.",
        "category": "VISUAL",
    },
    "give_debug_weapon": {
        "fn":       _cc_give_debug_weapon,
        "usage":    "give_debug_weapon",
        "desc":     "Add debug_blade to inventory.",
        "category": "ENTITIES",
    },
    "toggle_move_log": {
        "fn":       _cc_toggle_move_log,
        "usage":    "toggle_move_log",
        "desc":     "Toggle per-step terrain/cost logging.",
        "category": "SYSTEM",
    },
    "stop_weather": {
        "fn":       _cc_stop_weather,
        "usage":    "stop_weather",
        "desc":     "Force clear sky, remove emitters, clear particles and fog.",
        "category": "WEATHER",
    },
    "force_weird_weather": {
        "fn":       _cc_force_weird_weather,
        "usage":    "force_weird_weather",
        "desc":     "Force a random rare weather state.",
        "category": "WEATHER",
    },
    # PERKS -----------------------------------------------------------
    "grant_perk": {
        "fn":       _cc_grant_perk,
        "usage":    "grant_perk <id>",
        "desc":     "Grant perk to player.",
        "category": "PERKS",
    },
    "remove_perk": {
        "fn":       _cc_remove_perk,
        "usage":    "remove_perk <id>",
        "desc":     "Remove perk from player.",
        "category": "PERKS",
    },
    "list_perks": {
        "fn":       _cc_list_perks,
        "usage":    "list_perks",
        "desc":     "List active perks.",
        "category": "PERKS",
    },
    # WEATHER ---------------------------------------------------------
    "set_weather": {
        "fn":       _cc_set_weather,
        "usage":    "set_weather <state>",
        "desc":     "Force a weather state.",
        "category": "WEATHER",
    },
    "show_weather": {
        "fn":       _cc_show_weather,
        "usage":    "show_weather",
        "desc":     "Print current weather state.",
        "category": "WEATHER",
    },
    # VISUAL ----------------------------------------------------------
    "particle_stats": {
        "fn":       _cc_particle_stats,
        "usage":    "particle_stats",
        "desc":     "Show active particle count, cap, emitters, avg fps.",
        "category": "VISUAL",
    },
    "test_rain": {
        "fn":       _cc_test_rain,
        "usage":    "test_rain [light|heavy|storm]",
        "desc":     "Set weather to rain state.",
        "category": "VISUAL",
    },
    "test_fog": {
        "fn":       _cc_test_fog,
        "usage":    "test_fog [fog|forgetting]",
        "desc":     "Set weather to fog state.",
        "category": "VISUAL",
    },
    "test_snow": {
        "fn":       _cc_test_snow,
        "usage":    "test_snow",
        "desc":     "Set weather to bone_snow.",
        "category": "VISUAL",
    },
    "test_waystone_ring": {
        "fn":       _cc_test_waystone_ring,
        "usage":    "test_waystone_ring",
        "desc":     "Emit one waystone ring at player position.",
        "category": "VISUAL",
    },
    "clear_particles": {
        "fn":       _cc_clear_particles,
        "usage":    "clear_particles",
        "desc":     "Remove all active particles and emitters.",
        "category": "VISUAL",
    },
    "toggle_callouts": {
        "fn":       _cc_toggle_callouts,
        "usage":    "toggle_callouts [damage|sounds|status|all]",
        "desc":     "Toggle floating callout categories.",
        "category": "VISUAL",
    },
    "toggle_resonance_sight": {
        "fn":       _cc_toggle_resonance_sight,
        "usage":    "toggle_resonance_sight",
        "desc":     "Toggle resonance emit overlay (purple pulse on resonant tiles).",
        "category": "VISUAL",
    },
    "test_camera_drift": {
        "fn":       _cc_test_camera_drift,
        "usage":    "test_camera_drift",
        "desc":     "Teleport player 15 tiles in 4 directions and back. Check corners for drift.",
        "category": "VISUAL",
    },
    # LANGUAGE --------------------------------------------------------
    "teach_word": {
        "fn":       _cc_teach_word,
        "usage":    "teach_word <word_id>",
        "desc":     "Teach a deep tongue word to the player.",
        "category": "LANGUAGE",
    },
    "list_known": {
        "fn":       _cc_list_known,
        "usage":    "list_known",
        "desc":     "List all known deep tongue words by category.",
        "category": "LANGUAGE",
    },
    "show_lexicon": {
        "fn":       _cc_show_lexicon,
        "usage":    "show_lexicon",
        "desc":     "Show full lexicon with known/unknown status.",
        "category": "LANGUAGE",
    },
    # SYSTEM ----------------------------------------------------------
    "help": {
        "fn":       _cc_help,
        "usage":    "help",
        "desc":     "List all console commands by category.",
        "category": "SYSTEM",
    },
}


class DebugOverlay:
    """
    Debug tools. Only active when config.DEBUG_MODE = True.
    All F-key handlers live here.
    The engine checks debug.handle_key() before normal input.
    """

    def __init__(self) -> None:
        self.show_overlay:           bool = False
        self.show_fov_viz:           bool = False
        self.show_submap_highlights: bool = False
        self._font: pygame.font.Font | None = None
        self._input_mode:    str  = ""
        self._input_buffer:  str  = ""
        self._input_prompt:  str  = ""
        self._console_history:     list[str] = []
        self._console_history_idx: int       = -1   # -1 = not browsing

    def init(self) -> None:
        self._font = pygame.font.SysFont("monospace", 13)

    # ------------------------------------------------------------------ #
    #  Key handling â€” returns True if the key was consumed
    # ------------------------------------------------------------------ #

    def handle_key(self, key: int, engine: "Engine") -> bool:
        """
        Handle a keypress. Returns True if consumed by debug system.
        Call this BEFORE normal input handling.
        """
        if self._input_mode:
            return self._handle_input(key, engine)

        if key == pygame.K_ESCAPE and self.show_overlay:
            self.show_overlay = False
            return True

        if key == pygame.K_F1:
            self.show_overlay = not self.show_overlay
            return True

        if key == pygame.K_F2:
            self.show_fov_viz = not self.show_fov_viz
            return True

        if key == pygame.K_F3:
            self._reveal_local_map(engine)
            return True

        if key == pygame.K_F4:
            self._reveal_world_map_submaps(engine)
            return True

        if key == pygame.K_F5:
            self._teleport_to_nearest_submap(engine)
            return True

        if key == pygame.K_F6:
            self._start_input(
                "set_time",
                "Set hour (0-23): "
            )
            return True

        if key == pygame.K_F7:
            self._start_input(
                "set_values",
                "Set values â€” hunger,thirst,corruption (0.0-1.0 each, e.g. 0.5,0.8,0.3): "
            )
            return True

        if key == pygame.K_F8:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                engine.player_invincible = not engine.player_invincible
                state = "ON" if engine.player_invincible else "OFF"
                engine.log.add(f"[DEBUG] Invincibility {state}.", AGED_WOOD)
            else:
                self._force_regen(engine)
            return True

        if key == pygame.K_F9:
            self._dump_state(engine)
            return True

        if key == pygame.K_F10:
            self._start_input(
                "teleport",
                "Teleport to chunk wx,wy (e.g. 3,7): "
            )
            return True

        if key == pygame.K_F11:
            try:
                engine.save_manager.delete_slot()
            except Exception as error:
                engine.log.add(f"[DEBUG] Slot clear failed: {error}", FRESH_WOUND)
            else:
                engine.log.add("[DEBUG] Current save slot cleared.", FRESH_WOUND)
            return True

        if key == pygame.K_F12:
            self._start_input(
                "remap_tile",
                "Remap tile: tile_id sheet col row (e.g. floor obj 0 15): "
            )
            return True

        if key == pygame.K_BACKQUOTE:
            self._start_input("debug_cmd", "Debug> ")
            return True

        return False

    # ------------------------------------------------------------------ #
    #  Text input handling
    # ------------------------------------------------------------------ #

    def _start_input(self, mode: str, prompt: str) -> None:
        self._input_mode          = mode
        self._input_buffer        = ""
        self._input_prompt        = prompt
        self._console_history_idx = -1

    def _handle_input(self, key: int, engine: "Engine") -> bool:
        if key == pygame.K_ESCAPE:
            self._input_mode          = ""
            self._input_buffer        = ""
            self._console_history_idx = -1
            return True

        if key == pygame.K_RETURN:
            buf = self._input_buffer.strip()
            if buf and self._input_mode == "debug_cmd":
                # Prepend to history, cap at 20
                if not self._console_history or self._console_history[0] != buf:
                    self._console_history.insert(0, buf)
                    if len(self._console_history) > 20:
                        self._console_history = self._console_history[:20]
            self._console_history_idx = -1
            self._execute_input(engine)
            self._input_mode   = ""
            self._input_buffer = ""
            return True

        if key == pygame.K_BACKSPACE:
            self._input_buffer        = self._input_buffer[:-1]
            self._console_history_idx = -1
            return True

        if key == pygame.K_UP and self._input_mode == "debug_cmd":
            if self._console_history:
                self._console_history_idx = min(
                    self._console_history_idx + 1,
                    len(self._console_history) - 1,
                )
                self._input_buffer = self._console_history[self._console_history_idx]
            return True

        if key == pygame.K_DOWN and self._input_mode == "debug_cmd":
            if self._console_history_idx > 0:
                self._console_history_idx -= 1
                self._input_buffer = self._console_history[self._console_history_idx]
            else:
                self._console_history_idx = -1
                self._input_buffer = ""
            return True

        char = self._key_to_char(key)
        if char:
            self._input_buffer        += char
            self._console_history_idx  = -1
        return True

    def _execute_input(self, engine: "Engine") -> None:
        buf = self._input_buffer.strip()

        if self._input_mode == "teleport":
            try:
                parts = buf.split(",")
                wx, wy = int(parts[0].strip()), int(parts[1].strip())
                if engine.world_map.in_bounds(wx, wy):
                    from generation.region_gen import generate_region
                    from config import MAP_WIDTH, MAP_HEIGHT
                    chunk = engine.world_map.get(wx, wy)
                    if chunk:
                        new_map, (sx, sy) = generate_region(
                            chunk, MAP_WIDTH, MAP_HEIGHT,
                            engine.data.terrain
                        )
                        sx, sy = engine._find_walkable_near(new_map, sx, sy)
                        engine.player.x           = sx
                        engine.player.y           = sy
                        engine.local_map          = new_map
                        engine.world_x            = wx
                        engine.world_y            = wy
                        engine.current_submap_id  = None   # surface teleport â€” clear stale submap state
                        engine.world_map.mark_explored_radius(wx, wy, radius=2)
                        chunk.visited             = True
                        engine.entities           = [engine.player]
                        engine._update_fov()
                        engine.log.add(
                            f"[DEBUG] Teleported to chunk ({wx},{wy}).",
                            AGED_WOOD
                        )
                else:
                    engine.log.add(
                        f"[DEBUG] Chunk ({wx},{wy}) out of bounds.",
                        FRESH_WOUND
                    )
            except Exception as e:
                engine.log.add(f"[DEBUG] Teleport failed: {e}", FRESH_WOUND)

        elif self._input_mode == "set_time":
            try:
                hour = float(buf)
                hour = max(0.0, min(23.9, hour))
                from engine.world_time import TURNS_PER_HOUR, TURNS_PER_DAY
                current_day_start = (engine.world_time.turn
                                     // TURNS_PER_DAY) * TURNS_PER_DAY
                engine.world_time.turn = (current_day_start
                                          + int(hour * TURNS_PER_HOUR))
                engine._update_fov()
                engine.log.add(
                    f"[DEBUG] Time set to {engine.world_time.time_string}.",
                    AGED_WOOD
                )
            except Exception as e:
                engine.log.add(f"[DEBUG] Set time failed: {e}", FRESH_WOUND)

        elif self._input_mode == "set_values":
            try:
                parts  = buf.split(",")
                hunger = float(parts[0].strip())
                thirst = float(parts[1].strip())
                corrupt= float(parts[2].strip())

                needs = getattr(engine.player, "needs", None)
                corr  = getattr(engine.player, "corruption", None)

                if needs:
                    needs.hunger = max(0.0, min(1.0, hunger))
                    needs.thirst = max(0.0, min(1.0, thirst))
                if corr:
                    corr.value   = max(0.0, min(1.0, corrupt))

                engine._update_fov()
                engine.log.add(
                    f"[DEBUG] Set hunger={hunger:.2f} "
                    f"thirst={thirst:.2f} corruption={corrupt:.2f}.",
                    AGED_WOOD
                )
            except Exception as e:
                engine.log.add(
                    f"[DEBUG] Set values failed: {e}", FRESH_WOUND
                )

        elif self._input_mode == "debug_cmd":
            self._dispatch_console(buf, engine)

        elif self._input_mode == "remap_tile":
            try:
                parts    = buf.split()
                tile_id  = parts[0]
                sheet_id = parts[1]
                col      = int(parts[2])
                row      = int(parts[3])
                sr       = getattr(engine, "sprite_registry", None)
                if sr:
                    sr.remap(tile_id, sheet_id, col, row)
                    engine.log.add(
                        f"[DEBUG] Remapped {tile_id} â†’ {sheet_id} "
                        f"({col},{row})",
                        AGED_WOOD,
                    )
                else:
                    engine.log.add(
                        "[DEBUG] No sprite registry loaded.",
                        FRESH_WOUND,
                    )
            except Exception as e:
                engine.log.add(f"[DEBUG] Remap failed: {e}", FRESH_WOUND)

    def _dispatch_console(self, buf: str, engine: "Engine") -> None:
        """Look up and execute a command from CONSOLE_COMMANDS."""
        parts = buf.strip().split()
        if not parts:
            return
        cmd   = parts[0]
        entry = CONSOLE_COMMANDS.get(cmd)
        if entry is None:
            engine.log.add(
                f"[DEBUG] Unknown command '{cmd}'. Type 'help' for list.",
                FRESH_WOUND,
            )
            return
        try:
            entry["fn"](parts, engine)
        except Exception as e:
            engine.log.add(f"[DEBUG] {cmd} error: {e}", FRESH_WOUND)

    @staticmethod
    def _key_to_char(key: int) -> str:
        """Convert pygame key code to character for text input."""
        if pygame.K_a <= key <= pygame.K_z:
            return chr(key)
        if pygame.K_0 <= key <= pygame.K_9:
            return chr(key)
        if key == pygame.K_PERIOD:
            return "."
        if key == pygame.K_COMMA:
            return ","
        if key == pygame.K_MINUS or key == pygame.K_UNDERSCORE:
            return "_"
        if key == pygame.K_SPACE:
            return " "
        return ""

    # ------------------------------------------------------------------ #
    #  Actions
    # ------------------------------------------------------------------ #

    def _reveal_local_map(self, engine: "Engine") -> None:
        engine.local_map.tiles["explored"][:] = True
        engine.log.add("[DEBUG] Local map revealed.", AGED_WOOD)

    def _reveal_world_map_submaps(self, engine: "Engine") -> None:
        for chunk in engine.world_map.chunks.values():
            chunk.explored = True
        self.show_submap_highlights = not self.show_submap_highlights
        from engine.engine import GameMode
        engine.mode = GameMode.OVERMAP
        engine.overmap_cursor_x = engine.world_x
        engine.overmap_cursor_y = engine.world_y
        engine.overmap_cam_x    = engine.world_x
        engine.overmap_cam_y    = engine.world_y
        status = "on" if self.show_submap_highlights else "off"
        engine.log.add(
            f"[DEBUG] World map revealed. SubMap highlights {status}.",
            AGED_WOOD,
        )

    def _teleport_to_nearest_submap(self, engine: "Engine") -> None:
        """Teleport to the nearest chunk that has a SubMap entry."""
        from config import MAP_WIDTH, MAP_HEIGHT

        candidates = []
        for (wx, wy), chunk in engine.world_map.chunks.items():
            if chunk.submaps:
                dist = abs(wx - engine.world_x) + abs(wy - engine.world_y)
                candidates.append((dist, wx, wy, chunk))

        if not candidates:
            engine.log.add("[DEBUG] No submaps found in world.", FRESH_WOUND)
            return

        candidates.sort()
        _, wx, wy, chunk = candidates[0]

        from generation.region_gen import generate_region
        local_map, _ = generate_region(
            chunk, MAP_WIDTH, MAP_HEIGHT, engine.data.terrain
        )

        spawn_x, spawn_y = MAP_WIDTH // 2, MAP_HEIGHT // 2
        if local_map.submap_links:
            sx, sy = next(iter(local_map.submap_links))
            spawn_x, spawn_y = engine._find_walkable_near(local_map, sx, sy)
        else:
            spawn_x, spawn_y = engine._find_walkable_near(
                local_map, MAP_WIDTH // 2, MAP_HEIGHT // 2
            )

        engine.world_x            = wx
        engine.world_y            = wy
        engine.local_map          = local_map
        engine.entities           = [engine.player]
        engine.player.x           = spawn_x
        engine.player.y           = spawn_y
        engine.current_submap_id  = None   # surface teleport â€” clear stale submap state
        chunk.visited             = True
        engine.world_map.mark_explored_radius(wx, wy, radius=2)
        engine._update_fov()
        name = chunk.submaps[0].name if chunk.submaps[0].name else chunk.submaps[0].submap_type
        engine.log.add(
            f"[DEBUG] Teleported to submap chunk ({wx},{wy}): {name}",
            AGED_WOOD,
        )

    def _force_regen(self, engine: "Engine") -> None:
        from generation.region_gen import generate_region
        from config import MAP_WIDTH, MAP_HEIGHT
        chunk = engine.world_map.get(engine.world_x, engine.world_y)
        if chunk:
            chunk.seed += 1
            new_map, (sx, sy) = generate_region(
                chunk, MAP_WIDTH, MAP_HEIGHT, engine.data.terrain
            )
            sx, sy = engine._find_walkable_near(new_map, sx, sy)
            engine.player.x           = sx
            engine.player.y           = sy
            engine.local_map          = new_map
            engine.current_submap_id  = None   # force regen always produces surface map
            engine.entities           = [engine.player]
            engine._update_fov()
            engine.log.add(
                f"[DEBUG] Chunk regenerated (seed {chunk.seed}).",
                AGED_WOOD
            )

    def _dump_state(self, engine: "Engine") -> None:
        chunk = engine.world_map.get(engine.world_x, engine.world_y)
        needs = getattr(engine.player, "needs", None)
        corr  = getattr(engine.player, "corruption", None)

        print("\n=== DEBUG STATE DUMP ===")
        print(f"World pos:    ({engine.world_x}, {engine.world_y})")
        print(f"Local pos:    ({engine.player.x}, {engine.player.y})")
        print(f"Region type:  {chunk.region_type.value if chunk else 'N/A'}")
        print(f"Zones:        {chunk.zones if chunk else 'N/A'}")
        print(f"Edges:        {chunk.edges if chunk else 'N/A'}")
        print(f"Turn:         {engine.world_time.turn}")
        print(f"Time:         {engine.world_time.time_string}")
        print(f"Moon:         {engine.world_time.moon_phase_name}")
        print(f"Sun:          {engine.world_time.sun_intensity:.3f}")
        print(f"Moon int:     {engine.world_time.moon_intensity:.3f}")
        if needs:
            print(f"Hunger:       {needs.hunger:.4f} ({needs.hunger_state})")
            print(f"Thirst:       {needs.thirst:.4f} ({needs.thirst_state})")
        if corr:
            print(f"Corruption:   {corr.value:.4f} ({corr.state})")
        # Resonance state
        print(f"Res. exposure:{getattr(engine, 'resonance_exposure', 0.0):.4f}")
        print(f"Res. corrupt: {getattr(engine, 'corruption', 0.0):.4f}")
        print(f"Thresholds:   {sorted(getattr(engine, '_corruption_thresholds', set()))}")
        weather = getattr(engine, "weather", None)
        if weather:
            print(f"Weather:      {weather.state} (intensity {weather.intensity:.2f}, {weather.turns_remaining} turns)")
        lm = engine.local_map.light_map
        px, py = engine.player.x, engine.player.y
        print(f"Light at @:   {lm[px, py]}")
        print(f"Entities:     {len(engine.entities)}")
        print(f"Explored:     {engine.local_map.tiles['explored'].sum()} tiles")
        print(f"Submap ID:    {engine.current_submap_id or 'surface'}")
        if chunk and chunk.submaps:
            print(f"Submaps ({len(chunk.submaps)}):")
            for sm in chunk.submaps:
                print(f"  [{sm.submap_id}] type={sm.submap_type}"
                      f" layout={sm.layout_id or 'bsp'}"
                      f" generated={sm.generated}"
                      f" entry=({sm.entry_x},{sm.entry_y})"
                      f" depth={sm.depth}")
        myth = engine.world_myth
        if myth:
            print(f"WorldMyth:")
            print(f"  Age:       {myth.age_name}")
            print(f"  Sundering: {myth.sundering_epithet}")
            print(f"  Shape:     {myth.myth_shape}")
            print(f"  God:       {myth.prominent_god}")
            print(f"  Locus:     {myth.locus_name} at ({myth.locus_wx},{myth.locus_wy})")
            print(f"  Factions:  {myth.faction_a} vs {myth.faction_b}")
        print("========================\n")
        engine.log.add("[DEBUG] State dumped to console.", AGED_WOOD)

    # ------------------------------------------------------------------ #
    #  Overlay rendering
    # ------------------------------------------------------------------ #

    def render(
        self,
        screen:  pygame.Surface,
        engine:  "Engine",
    ) -> None:
        """Render all active debug visuals onto screen."""
        if self.show_fov_viz:
            self._render_fov_viz(screen, engine)

        if self.show_overlay:
            self._render_overlay(screen, engine)

        if self._input_mode:
            self._render_input_prompt(screen)

    @staticmethod
    def _draw_rune_sigil(surf: pygame.Surface, cx: int, cy: int, size: int = 32) -> None:
        """Draw the debug registry sigil â€” asymmetric angular rune."""
        import math
        s = size / 32
        col_dim    = DEEP_STONE_BLUE
        col_mid    = STEEL_WATER
        col_bright = STEEL_WATER
        pygame.draw.circle(surf, col_dim, (cx, cy), int(30 * s), 1)
        for i in range(24):
            if i % 3 == 2:
                continue
            a  = (i / 24) * 2 * math.pi
            px = int(cx + 20 * s * math.cos(a))
            py = int(cy + 20 * s * math.sin(a))
            pygame.draw.circle(surf, col_dim, (px, py), 1)
        pygame.draw.line(surf, col_mid, (cx, int(cy - 28 * s)), (cx, int(cy + 28 * s)), 1)
        pygame.draw.line(surf, col_mid, (cx, int(cy - 14 * s)), (int(cx - 20 * s), cy), 1)
        pygame.draw.line(surf, col_mid, (cx, int(cy - 14 * s)), (int(cx + 16 * s), int(cy - 6 * s)), 1)
        pygame.draw.line(surf, col_mid, (cx, int(cy + 12 * s)), (int(cx - 18 * s), int(cy + 20 * s)), 1)
        pygame.draw.line(surf, col_dim, (int(cx - 14 * s), int(cy - 2 * s)), (int(cx + 16 * s), int(cy + 3 * s)), 1)
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy - 10 * s)), (cx, int(cy - 10 * s)), 1)
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy + 2 * s)),  (cx, int(cy + 2 * s)),  1)
        pygame.draw.line(surf, col_mid, (int(cx - 4 * s), int(cy + 14 * s)), (int(cx + 4 * s), int(cy + 14 * s)), 1)
        pygame.draw.circle(surf, col_bright, (cx, int(cy - 28 * s)), 3)
        pygame.draw.circle(surf, col_mid,    (cx, int(cy - 14 * s)), 2)
        pygame.draw.circle(surf, col_mid,    (int(cx - 20 * s), cy), 2)
        pygame.draw.circle(surf, col_mid,    (cx, int(cy + 12 * s)), 2)
        pygame.draw.line(surf, col_bright, (cx, int(cy - 28 * s)), (cx, int(cy - 14 * s)), 2)
        pygame.draw.line(surf, col_bright, (cx, int(cy - 14 * s)), (int(cx - 20 * s), cy), 1)

    def _render_overlay(
        self,
        screen: pygame.Surface,
        engine: "Engine",
    ) -> None:
        display   = getattr(engine, "display", None)
        fn_small  = getattr(display, "font_ui_small",      None) or self._font
        fn_bold   = getattr(display, "font_ui_bold",       None) or self._font
        fn_blarge = getattr(display, "font_ui_bold_large", None) or fn_bold
        if not fn_small:
            return

        sw, sh   = screen.get_width(), screen.get_height()
        VOID     = VOID_BLACK
        STEEL    = STEEL_WATER
        DIM      = STONE_BLUE
        BRIGHT   = PALE_RESONANCE
        RED_DIM  = BLOOD_STONE
        GREEN    = LIFE_GREEN
        SECTION  = STEEL_WATER
        pad      = 14
        lh       = 16
        sh_lh    = 18

        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        panel.fill((*VOID, 230))
        pygame.draw.rect(panel, STEEL, (0, 0, sw, sh), 2)
        screen.blit(panel, (0, 0))

        # â”€â”€ Header â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        SIG_CX, SIG_CY, SIG_R = 44, 44, 32
        self._draw_rune_sigil(screen, SIG_CX, SIG_CY, SIG_R)
        pygame.draw.line(screen, STEEL, (SIG_CX * 2 + 4, 0), (SIG_CX * 2 + 4, 88), 1)

        title = fn_blarge.render("DEBUG REGISTRY", True, STEEL)
        screen.blit(title, (SIG_CX * 2 + 14, pad))
        sub   = fn_small.render("engine/debug.py  Â·  DEBUG_MODE = True", True, DIM)
        screen.blit(sub, (SIG_CX * 2 + 14, pad + 26))

        inv   = getattr(engine, "player_invincible", False)
        dot_x = sw - pad - 8
        dot_y = pad + 8
        pygame.draw.circle(screen, GREEN if inv else SLATE_DARK, (dot_x, dot_y), 6)
        pygame.draw.circle(screen, STEEL, (dot_x, dot_y), 6, 1)
        inv_label = fn_small.render("INVINCIBLE" if inv else "mortal", True, GREEN if inv else DIM)
        screen.blit(inv_label, (dot_x - inv_label.get_width() - 10, dot_y - 6))

        header_h = 88
        pygame.draw.line(screen, STEEL, (0, header_h), (sw, header_h), 1)

        # â”€â”€ Two-column key grid â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        col_w   = (sw - pad * 3) // 2
        col1_x  = pad
        col2_x  = pad * 2 + col_w
        y1 = header_h + pad
        y2 = header_h + pad

        def draw_section(x: int, y: int, heading: str, rows: list[tuple[str, str]]) -> int:
            h = fn_bold.render(heading, True, SECTION)
            screen.blit(h, (x, y))
            y += sh_lh
            for key, desc in rows:
                k_surf = fn_small.render(key, True, BRIGHT)
                d_surf = fn_small.render(desc, True, DIM)
                screen.blit(k_surf, (x, y))
                screen.blit(d_surf, (x + 80, y))
                y += lh
            return y + 6

        y1 = draw_section(col1_x, y1, "NAVIGATION", [
            ("F2",        "FOV visualization overlay"),
            ("F3",        "Reveal full local map"),
            ("F4",        "SubMap highlights on overmap"),
            ("F10",       "Teleport to chunk coords"),
        ])
        y1 = draw_section(col1_x, y1, "INSPECTION", [
            ("F1",        "Toggle this overlay"),
            ("F9",        "Full state dump to terminal"),
            ("F12",       "Remap sprite tile at runtime"),
            ("Shift+F8",  "Toggle invincibility"),
        ])

        y2 = draw_section(col2_x, y2, "WORLD & TIME", [
            ("F5",        "Teleport to nearest SubMap"),
            ("F6",        "Set world time (0-23)"),
            ("F7",        "Set needs / corruption"),
            ("F8",        "Force chunk regeneration"),
        ])
        dest_y = y2
        h = fn_bold.render("DESTRUCTIVE", True, RED_DIM)
        screen.blit(h, (col2_x, dest_y))
        dest_y += sh_lh
        k = fn_small.render("F11", True, DUSTY_ROSE)
        d = fn_small.render("Clear current save slot", True, BLOOD_STONE)
        screen.blit(k, (col2_x, dest_y))
        screen.blit(d, (col2_x + 80, dest_y))
        dest_y += lh

        content_bottom = max(y1, dest_y) + pad

        # â”€â”€ Console section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        pygame.draw.line(screen, STEEL, (0, content_bottom), (sw, content_bottom), 1)
        cy = content_bottom + pad

        h_surf = fn_bold.render("DEBUG CONSOLE", True, SECTION)
        screen.blit(h_surf, (pad, cy))
        trig = fn_small.render("trigger: ` (backtick)  â€”  type 'help' for full list", True, DIM)
        screen.blit(trig, (pad + h_surf.get_width() + 20, cy + 2))
        cy += sh_lh

        # Commands grouped by category, two columns
        cat_order  = ["RESONANCE", "ENTITIES", "PERKS", "WEATHER", "SYSTEM"]
        col_half   = (sw - pad * 3) // 2
        cc_col1_x  = pad + 12
        cc_col2_x  = pad * 2 + col_half + 12
        cy1 = cy
        cy2 = cy
        col_toggle = 0

        for cat in cat_order:
            items = [(n, m) for n, m in CONSOLE_COMMANDS.items()
                     if m["category"] == cat]
            if not items:
                continue
            if col_toggle == 0:
                hdr = fn_bold.render(cat, True, SECTION)
                screen.blit(hdr, (cc_col1_x, cy1))
                cy1 += sh_lh
                for _, meta in items:
                    u_surf = fn_small.render(meta["usage"], True, BRIGHT)
                    d_surf = fn_small.render(f"â€” {meta['desc']}", True, DIM)
                    screen.blit(u_surf, (cc_col1_x, cy1))
                    screen.blit(d_surf, (cc_col1_x + u_surf.get_width() + 6, cy1))
                    cy1 += lh
                cy1 += 4
                col_toggle = 1
            else:
                hdr = fn_bold.render(cat, True, SECTION)
                screen.blit(hdr, (cc_col2_x, cy2))
                cy2 += sh_lh
                for _, meta in items:
                    u_surf = fn_small.render(meta["usage"], True, BRIGHT)
                    d_surf = fn_small.render(f"â€” {meta['desc']}", True, DIM)
                    screen.blit(u_surf, (cc_col2_x, cy2))
                    screen.blit(d_surf, (cc_col2_x + u_surf.get_width() + 6, cy2))
                    cy2 += lh
                cy2 += 4
                col_toggle = 0

        cy = max(cy1, cy2) + pad

        # â”€â”€ Footer status bar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        footer_y = sh - lh - pad - 4
        pygame.draw.line(screen, STEEL, (0, footer_y - 6), (sw, footer_y - 6), 1)

        chunk       = engine.world_map.get(engine.world_x, engine.world_y)
        corr        = getattr(engine.player, "corruption", None)
        weather     = getattr(engine, "weather", None)
        submap_label = engine.current_submap_id or "surface"
        region_label = chunk.region_type.value if chunk else "?"
        corr_label   = corr.state if corr else "?"
        weather_label = weather.state if weather else "â€”"

        footer = fn_small.render(
            f"mode: {engine.mode.value}  |  submap: {submap_label}  |  "
            f"chunk: ({engine.world_x},{engine.world_y}) {region_label}  |  "
            f"corruption: {corr_label}  |  weather: {weather_label}  |  "
            f"turn: {engine.world_time.turn}",
            True, DIM,
        )
        screen.blit(footer, (pad, footer_y))

    def _render_fov_viz(
        self,
        screen: pygame.Surface,
        engine: "Engine",
    ) -> None:
        """Tint visible tiles green, FOV boundary cyan."""
        from engine.engine import GameMode
        if engine.mode != GameMode.LOCAL:
            return

        tw = engine.display.tile_width
        th = engine.display.tile_height

        vp = getattr(engine, "_viewport", None)
        vp_x = vp.x if vp else 0
        vp_y = vp.y if vp else 0
        viewport_w = vp.width  if vp else screen.get_width()
        viewport_h = vp.height if vp else screen.get_height()

        cam_x = engine.player.x - (viewport_w // tw) // 2
        cam_y = engine.player.y - (viewport_h // th) // 2
        cam_x = max(0, min(cam_x, engine.local_map.width  - viewport_w // tw))
        cam_y = max(0, min(cam_y, engine.local_map.height - viewport_h // th))

        tiles_x = viewport_w // tw + 2
        tiles_y = viewport_h // th + 2

        viz_surf = pygame.Surface((viewport_w, viewport_h), pygame.SRCALPHA)

        for tx in range(tiles_x):
            for ty in range(tiles_y):
                mx = tx + cam_x
                my = ty + cam_y
                if not engine.local_map.in_bounds(mx, my):
                    continue
                if engine.local_map.tiles[mx, my]["visible"]:
                    px_x = tx * tw
                    px_y = ty * th
                    pygame.draw.rect(
                        viz_surf, (0, 255, 0, 40),
                        (px_x, px_y, tw, th)
                    )

        # Blit at viewport origin, not (0,0) â€” viewport is inset from screen edge.
        screen.blit(viz_surf, (vp_x, vp_y))

    def _render_input_prompt(self, screen: pygame.Surface) -> None:
        if not self._font:
            return
        text = f"{self._input_prompt}{self._input_buffer}_"
        surf = self._font.render(text, True, RESONANCE_GOLD)
        bg   = pygame.Surface(
            (surf.get_width() + 12, surf.get_height() + 8),
            pygame.SRCALPHA
        )
        bg.fill(DEEP_NOTHING + (230,))
        y = screen.get_height() // 2
        screen.blit(bg,  (10, y))
        screen.blit(surf, (16, y + 4))
