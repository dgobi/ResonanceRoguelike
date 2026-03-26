# engine/discharge.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine


def trigger_discharge(
        engine: "Engine",
        bx: int,
        by: int,
        bell_type: str,
        effects: dict,
) -> None:
    """
    A bell at (bx, by) discharges.
    bell_type: "intact" | "cracked"

    Intact discharge: major event.
    Cracked discharge: partial event.
    """
    from engine.resonance_system import _check_corruption_thresholds
    from components.ai import AIState

    if bell_type == "intact":
        radius           = 18
        exposure_spike   = 0.65
        corruption_spike = 0.08
        msg              = "THE BELL SPEAKS."
        msg_color        = OLD_GOLD   # old_gold
        screen_flash     = OLD_GOLD + (60,)
    else:   # cracked
        radius           = 10
        exposure_spike   = 0.30
        corruption_spike = 0.02
        msg              = "The crack opens. A partial tone."
        msg_color        = DUSTY_ROSE     # dusty_rose
        screen_flash     = DUSTY_ROSE + (30,)

    # Exposure and corruption spike
    engine.resonance_exposure = min(
        1.5, engine.resonance_exposure + exposure_spike)
    old_corruption = engine.corruption
    engine.corruption = min(1.0, engine.corruption + corruption_spike)

    # Message
    _merge_message(effects, msg, msg_color)

    # Screen flash
    engine._discharge_flash       = screen_flash
    engine._discharge_flash_turns = 2

    # Discharge ring — world-space expanding ring from bell position
    ps = getattr(engine, "particle_system", None)
    if ps is not None:
        from rendering.particles import make_discharge_ring
        ps.emit(make_discharge_ring(bx, by, bell_type))

    # Creature disturbance — alert all entities within radius of bell
    px, py = engine.player.x, engine.player.y
    for entity in engine.get_active_entities():
        if entity is engine.player:
            continue
        dist = math.sqrt(
            (entity.x - bx) ** 2 + (entity.y - by) ** 2)
        if dist > radius:
            continue
        ai = getattr(entity, "ai", None)
        if ai is None:
            continue
        state_val = ai.state.value if hasattr(ai.state, "value") else str(ai.state)
        if state_val not in ("hunting", "attacking"):
            ai.state          = AIState.ALERTED
            ai.last_known_x   = px
            ai.last_known_y   = py

    # Corruption threshold check
    _check_corruption_thresholds(engine, old_corruption,
                                 engine.corruption, effects)

    # Weather push
    weather = getattr(engine, "weather", None)
    if weather is not None:
        from config import DEBUG_MODE as _DM
        if _DM and bell_type == "intact" and getattr(engine, "corruption", 0.0) >= 0.40:
            roll = engine.rng.random()
            result = weather.discharge_push(engine.rng, bell_type)
            engine.log.add(
                f"[D] discharge_push roll={roll:.3f} (need<0.25 for storm)"
                f" → {weather.state}",
                OLD_GROWTH,
            )
            if result:
                if "add_message" not in effects:
                    effects["add_message"]   = result[0]
                    effects["message_color"] = result[1]
        else:
            weather.discharge_push(engine.rng, bell_type)

    # Pulse spawn effects
    _resolve_pulse_spawns(engine, bx, by, bell_type, radius, effects)


def _resolve_pulse_spawns(
        engine: "Engine",
        bx: int,
        by: int,
        bell_type: str,
        radius: int,
        effects: dict,
) -> None:
    """
    Data-driven spawns from data/resonance_spawns.json.
    Fires terrain scatter and creature spawns based on bell type,
    corruption level, and current biome.
    """
    spawn_table = getattr(engine.data, "resonance_spawns", [])
    if not spawn_table:
        return

    chunk    = engine.world_map.get(engine.world_x, engine.world_y)
    biome_id = getattr(chunk, "biome_id", None) if chunk else None
    corrupt  = engine.corruption

    # Separate terrain and creature entries that qualify
    terrain_pool:  list[dict] = []
    creature_pool: list[dict] = []

    for entry in spawn_table:
        if bell_type not in entry.get("bell_types", [bell_type]):
            continue
        if corrupt < entry.get("min_corruption", 0.0):
            continue
        allowed_biomes = entry.get("biomes")
        if allowed_biomes is not None and biome_id not in allowed_biomes:
            continue
        if entry["type"] == "terrain":
            terrain_pool.append(entry)
        elif entry["type"] == "creature":
            creature_pool.append(entry)

    spawned_creatures = False

    # --- Terrain scatter ---
    if terrain_pool:
        entry = _weighted_choice(engine.rng, terrain_pool)
        if entry:
            count = engine.rng.randint(1, entry.get("max_per_pulse", 3))
            _place_terrain_scatter(engine, bx, by, radius,
                                   entry["terrain_id"], count)

    # --- Creature spawns (intact only, gated by corruption) ---
    if creature_pool and bell_type == "intact":
        entry = _weighted_choice(engine.rng, creature_pool)
        if entry:
            count = engine.rng.randint(1, entry.get("max_per_pulse", 1))
            n = _spawn_creatures(engine, bx, by, radius,
                                 entry["creature_id"], count)
            if n > 0:
                spawned_creatures = True
                name = entry["creature_id"].replace("_", " ")
                _merge_message(
                    effects,
                    f"Something rises from the resonance.",
                    BLOOD_STONE,
                )


def _weighted_choice(rng, pool: list[dict]) -> dict | None:
    """Return one entry from pool using 'weight' field."""
    if not pool:
        return None
    weights = [e.get("weight", 1) for e in pool]
    total = sum(weights)
    r = rng.random() * total
    cumulative = 0.0
    for entry, w in zip(pool, weights):
        cumulative += w
        if r <= cumulative:
            return entry
    return pool[-1]


def _place_terrain_scatter(
        engine: "Engine",
        bx: int,
        by: int,
        radius: int,
        terrain_id: str,
        count: int,
) -> None:
    """Scatter terrain tiles randomly within radius of (bx, by) on walkable tiles."""
    terrain_data = engine.data.terrain.get(terrain_id, {})
    walkable = terrain_data.get("walkable", True)

    placed = 0
    attempts = 0
    max_attempts = count * 12

    while placed < count and attempts < max_attempts:
        attempts += 1
        dx = engine.rng.randint(-radius, radius)
        dy = engine.rng.randint(-radius, radius)
        tx, ty = bx + dx, by + dy
        if not engine.local_map.in_bounds(tx, ty):
            continue
        # Only scatter on currently walkable tiles (don't overwrite walls)
        if not engine.local_map.walkable[tx, ty]:
            continue
        # Don't place blocking terrain on the player's tile
        if not walkable and tx == engine.player.x and ty == engine.player.y:
            continue
        engine.place_ephemeral_tile(tx, ty, terrain_id)
        placed += 1


def _spawn_creatures(
        engine: "Engine",
        bx: int,
        by: int,
        radius: int,
        creature_id: str,
        count: int,
) -> int:
    """Spawn creatures within radius. Returns number actually spawned."""
    spawned = 0
    attempts = 0
    max_attempts = count * 16

    while spawned < count and attempts < max_attempts:
        attempts += 1
        dx = engine.rng.randint(-radius, radius)
        dy = engine.rng.randint(-radius, radius)
        tx, ty = bx + dx, by + dy
        if not engine.local_map.in_bounds(tx, ty):
            continue
        if not engine.local_map.walkable[tx, ty]:
            continue
        # Don't spawn on the player
        if tx == engine.player.x and ty == engine.player.y:
            continue
        # Don't spawn on an occupied tile
        occupied = any(
            e.x == tx and e.y == ty
            for e in engine.entities
            if e is not engine.player
        )
        if occupied:
            continue
        creature = engine.creature_factory.spawn(creature_id, tx, ty)
        if creature:
            engine.entities.append(creature)
            spawned += 1

    return spawned


def _merge_message(effects: dict, text: str, color: tuple) -> None:
    """Insert a message into an effects dict if slot is free."""
    if "add_message" not in effects:
        effects["add_message"]   = text
        effects["message_color"] = color
