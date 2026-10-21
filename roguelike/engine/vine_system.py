# engine/vine_system.py
"""
Vine network spread system — growing terrain/decor pattern.

The vine is not a mobile entity. It is a collection of decor tiles
(vine_growth, vine_eyestalk, vine_spore_vent) that spread over time,
managed by tick_vine_networks() called from _advance_turn().

Pure functions + one tick function. No engine state imports at module level.
"""
from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.engine import Engine


# Terrain types vine can spread onto (walkable, non-infrastructure)
_VINE_VALID = frozenset({
    "grass", "varied_grass", "mud", "packed_earth", "dirt_path",
    "tall_grass", "brambles", "gravel", "ash",
})

_ORTHOGONAL = [(0, -1), (0, 1), (-1, 0), (1, 0)]


def tick_vine_networks(engine: "Engine") -> None:
    """Tick all vine networks in the current chunk.

    Called from _advance_turn(). Spread happens every spread_interval turns.
    Gas damage happens every turn.
    """
    from engine.palette import MSG_DANGER, LIFE_GREEN
    from generation.decor_utils import place_decor

    lm = engine.local_map
    if not lm.vine_networks:
        return

    vine_cfg = engine.data.entities.get("vine_network", {})
    interval = vine_cfg.get("spread_interval", 5)
    spread_chance = vine_cfg.get("spread_chance", 0.7)
    eyestalk_interval = vine_cfg.get("eyestalk_interval", 12)
    spore_interval = vine_cfg.get("spore_interval", 25)
    max_tiles = vine_cfg.get("max_tiles", 50)
    eyestalk_range = vine_cfg.get("eyestalk_attack_range", 3)
    eyestalk_dice = vine_cfg.get("eyestalk_damage_dice", "1d3")
    spore_dmg = vine_cfg.get("spore_damage_per_turn", 2)
    spore_range = vine_cfg.get("spore_player_range", 2)

    turn = engine.world_time.turn
    is_spread_tick = (turn % interval == 0)
    px, py = engine.player.x, engine.player.y
    rng = engine.rng

    # Gas damage — every turn, deduplicated across all vents
    _gas_applied = False
    for net in lm.vine_networks:
        for vx, vy in net.get("spore_vents", []):
            if not _gas_applied:
                dist = max(abs(px - vx), abs(py - vy))
                if dist <= spore_range:
                    fighter = getattr(engine.player, "fighter", None)
                    if fighter and not getattr(engine, "player_invincible", False):
                        fighter.hp = max(0, fighter.hp - spore_dmg)
                        engine.log.add("The air chokes.", MSG_DANGER)
                        _gas_applied = True
                        # Particle puff at vent
                        _emit_gas_particles(engine, vx, vy)

    if not is_spread_tick:
        return

    # Spread + structure checks — only on spread ticks
    for net in list(lm.vine_networks):
        net["age"] = net.get("age", 0) + interval
        tiles = net.get("tiles", [])
        eyestalks = net.get("eyestalks", [])
        spore_vents = net.get("spore_vents", [])
        origin = net.get("origin", (0, 0))

        # 1. Spread attempt
        if len(tiles) < max_tiles and rng.random() < spread_chance:
            candidates = []
            tile_set = set(map(tuple, tiles))
            for tx, ty in tiles:
                for dx, dy in _ORTHOGONAL:
                    nx, ny = tx + dx, ty + dy
                    if (nx, ny) in tile_set:
                        continue
                    if not lm.in_bounds(nx, ny):
                        continue
                    t = lm.tiles[nx, ny]["terrain"]
                    if isinstance(t, bytes):
                        t = t.decode()
                    if str(t) not in _VINE_VALID:
                        continue
                    # Don't spread onto existing decor
                    if lm.decor.get((nx, ny)):
                        continue
                    candidates.append((nx, ny))

            if candidates:
                nx, ny = rng.choice(candidates)
                place_decor(lm, nx, ny, "vine_growth")
                tiles.append([nx, ny])
                # Spread particle
                _emit_spread_particle(engine, nx, ny)

        # 2. Eyestalk interval spawning — one per eyestalk_interval vine tiles
        expected_eyes = len(tiles) // eyestalk_interval
        from generation.decor_utils import clear_decor
        while len(eyestalks) < expected_eyes and len(tiles) > 0:
            ox, oy = origin
            stalk_set = set(map(tuple, eyestalks))
            # Find vine_growth tile far from origin, not adjacent to existing eyestalk
            best = None
            best_dist = -1.0
            for tx, ty in tiles:
                if (tx, ty) in stalk_set:
                    continue
                adj_to_stalk = any(abs(tx - sx) + abs(ty - sy) <= 1 for sx, sy in stalk_set)
                if adj_to_stalk:
                    continue
                d = math.sqrt((tx - ox) ** 2 + (ty - oy) ** 2)
                if d > best_dist:
                    best_dist = d
                    best = (tx, ty)
            if best:
                clear_decor(lm, best[0], best[1])
                place_decor(lm, best[0], best[1], "vine_eyestalk")
                eyestalks.append(list(best))
            else:
                break

        # Eyestalk attacks — with callout and streak particles
        for ex, ey in eyestalks:
            dist = math.sqrt((px - ex) ** 2 + (py - ey) ** 2)
            if dist <= eyestalk_range:
                _eyestalk_attack(engine, ex, ey, eyestalk_dice)

        # 3. Spore vent interval spawning — one per spore_interval vine tiles
        expected_vents = len(tiles) // spore_interval
        vent_set = set(map(tuple, spore_vents))
        stalk_set2 = set(map(tuple, eyestalks))
        while len(spore_vents) < expected_vents and len(tiles) > 0:
            ox, oy = origin
            best = None
            best_dist = 999.0
            for tx, ty in tiles:
                if (tx, ty) in vent_set or (tx, ty) in stalk_set2:
                    continue
                d = math.sqrt((tx - ox) ** 2 + (ty - oy) ** 2)
                if d < best_dist:
                    best_dist = d
                    best = (tx, ty)
            if best:
                clear_decor(lm, best[0], best[1])
                place_decor(lm, best[0], best[1], "vine_spore_vent")
                spore_vents.append(list(best))
                vent_set.add(tuple(best))
            else:
                break

        # Update network
        net["tiles"] = tiles
        net["eyestalks"] = eyestalks
        net["spore_vents"] = spore_vents


def destroy_vine_tile(engine: "Engine", x: int, y: int) -> None:
    """Remove a vine tile at (x,y) from its network. Clear decor."""
    from generation.decor_utils import clear_decor

    lm = engine.local_map
    clear_decor(lm, x, y)

    for net in list(lm.vine_networks):
        tiles = net.get("tiles", [])
        eyestalks = net.get("eyestalks", [])
        spore_vents = net.get("spore_vents", [])

        pos = [x, y]
        if pos in tiles:
            tiles.remove(pos)
        if pos in eyestalks:
            eyestalks.remove(pos)
        if pos in spore_vents:
            spore_vents.remove(pos)

        net["tiles"] = tiles
        net["eyestalks"] = eyestalks
        net["spore_vents"] = spore_vents

        if not tiles:
            lm.vine_networks.remove(net)


def spawn_vine_network(engine: "Engine") -> bool:
    """Attempt to spawn a vine seed in the current chunk.

    Called after resonance pulse if biome is valid. 20% chance.
    Returns True if a vine was spawned.
    """
    from generation.decor_utils import place_decor

    lm = engine.local_map
    rng = engine.rng

    if rng.random() > 0.20:
        return False

    # Find a random walkable tile not on road/building
    candidates = []
    for x in range(2, lm.width - 2):
        for y in range(2, lm.height - 2):
            t = lm.tiles[x, y]["terrain"]
            if isinstance(t, bytes):
                t = t.decode()
            if str(t) not in _VINE_VALID:
                continue
            if lm.decor.get((x, y)):
                continue
            candidates.append((x, y))

    if not candidates:
        return False

    ox, oy = rng.choice(candidates)
    place_decor(lm, ox, oy, "vine_growth")

    lm.vine_networks.append({
        "tiles": [[ox, oy]],
        "eyestalks": [],
        "spore_vents": [],
        "origin": [ox, oy],
        "age": 0,
    })
    return True


# ------------------------------------------------------------------ #
#  Combat + particle helpers
# ------------------------------------------------------------------ #

def _eyestalk_attack(engine: "Engine", ex: int, ey: int, damage_dice: str) -> None:
    """Eyestalk lashes at the player."""
    from engine.combat import roll_dice
    from engine.palette import MSG_DANGER, BLOOD_VERDIGRIS

    fighter = getattr(engine.player, "fighter", None)
    if not fighter or getattr(engine, "player_invincible", False):
        return

    dmg = roll_dice(damage_dice, engine.rng)
    actual = fighter.take_damage(dmg)
    if actual > 0:
        engine.log.add(f"The eyestalk lashes at thee for {actual} damage.", MSG_DANGER)
        engine.player.took_damage_this_turn = True
        # Callout at eyestalk
        engine.callouts.add("LASHES", float(ex), float(ey) - 0.3,
                            BLOOD_VERDIGRIS, lifetime=1.0, font_size="status")
        # 4-6 streak particles from eyestalk to player
        _emit_attack_streak(engine, ex, ey)
        # Impact burst at player
        _emit_impact_burst(engine, engine.player.x, engine.player.y)


def _emit_spread_particle(engine: "Engine", x: int, y: int) -> None:
    """Small green sparkle at new vine tile."""
    try:
        from rendering.particles import Particle
        ps = engine.particle_system
        rng = engine.rng
        for _ in range(rng.randint(2, 3)):
            ps.emit(Particle(
                x=x + 0.5 + rng.uniform(-0.3, 0.3),
                y=y + 0.5 + rng.uniform(-0.3, 0.3),
                vx=0.0, vy=0.0,
                lifetime=0.5, max_lifetime=0.5,
                r=80, g=130, b=60, alpha=180,
                size=rng.uniform(1.5, 3.0),
                space="world", shape="sparkle",
                pool="ambient",
            ))
    except Exception:
        pass


def _emit_impact_burst(engine: "Engine", x: int, y: int) -> None:
    """Impact burst at player position on eyestalk hit."""
    try:
        from rendering.particles import Particle
        ps = engine.particle_system
        rng = engine.rng
        for _ in range(rng.randint(3, 4)):
            ps.emit(Particle(
                x=x + 0.5 + rng.uniform(-0.2, 0.2),
                y=y + 0.5 + rng.uniform(-0.2, 0.2),
                vx=rng.uniform(-1.0, 1.0), vy=rng.uniform(-1.0, 1.0),
                lifetime=0.2, max_lifetime=0.2,
                r=60, g=100, b=50, alpha=120,
                size=rng.uniform(1.5, 2.5),
                space="world", shape="circle",
                pool="combat",
            ))
    except Exception:
        pass


def _emit_attack_streak(engine: "Engine", ex: int, ey: int) -> None:
    """4-6 streak particles from eyestalk to player."""
    try:
        from rendering.particles import Particle
        ps = engine.particle_system
        rng = engine.rng
        px, py = engine.player.x, engine.player.y
        dx = px - ex
        dy = py - ey
        length = math.sqrt(dx * dx + dy * dy) or 1.0
        speed = 4.0
        for _ in range(rng.randint(4, 6)):
            _spd = speed + rng.uniform(-0.5, 0.5)
            ps.emit(Particle(
                x=ex + 0.5 + rng.uniform(-0.2, 0.2),
                y=ey + 0.5 + rng.uniform(-0.2, 0.2),
                vx=dx / length * _spd + rng.uniform(-0.3, 0.3),
                vy=dy / length * _spd + rng.uniform(-0.3, 0.3),
                lifetime=rng.uniform(0.12, 0.2), max_lifetime=0.2,
                r=60, g=100, b=50, alpha=200,
                size=rng.uniform(2.0, 4.0),
                space="world", shape="streak",
                pool="combat",
        ))
    except Exception:
        pass


def _emit_gas_particles(engine: "Engine", vx: int, vy: int) -> None:
    """Sickly gas puff at spore vent."""
    try:
        from rendering.particles import Particle
        ps = engine.particle_system
        rng = engine.rng
        for _ in range(rng.randint(2, 4)):
            ps.emit(Particle(
                x=vx + 0.5 + rng.uniform(-0.4, 0.4),
                y=vy + 0.5 + rng.uniform(-0.2, 0.2),
                vx=rng.uniform(-0.3, 0.3),
                vy=rng.uniform(-1.5, -0.5),
                lifetime=rng.uniform(0.6, 1.2),
                max_lifetime=1.2,
                r=90, g=120, b=70, alpha=100,
                size=rng.uniform(2.0, 4.0),
                space="world", shape="circle",
                pool="ambient",
            ))
    except Exception:
        pass
