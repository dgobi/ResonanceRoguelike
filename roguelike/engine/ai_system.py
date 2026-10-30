# engine/ai_system.py
from __future__ import annotations
import random
from typing import TYPE_CHECKING
from config import MAP_WIDTH, MAP_HEIGHT
from engine.effect_lifecycle import disrupted, ability_enabled, creature_id

if TYPE_CHECKING:
    from entities.actor import Actor
    from world.local_map import LocalMap
    from world.world_map import WorldMap
    from engine.message_log import MessageLog
    from engine.world_time import WorldTime
    from engine.data_loader import DataLoader


class AISystem:
    """
    Processes all non-player actor AI each turn.
    Called by Engine._advance_turn() after player action.
    """

    def __init__(self) -> None:
        self._rng = random.Random()

    def process(
        self,
        entities:      list[Actor],
        player:        Actor,
        local_map:     LocalMap,
        world_map:     WorldMap,
        world_x:       int,
        world_y:       int,
        log:           MessageLog,
        world_time:    WorldTime,
        data:          DataLoader,
        engine=None,
    ) -> None:
        # Get ambient light for perception calculations
        chunk       = world_map.get(world_x, world_y)
        is_outdoor  = True
        zone_ambient = 1.0

        if chunk:
            for zone_id, _ in chunk.zones:
                zone = data.zones.get(zone_id)
                if zone:
                    zone_ambient = zone.get("ambient_light", 1.0)
                    if zone.get("category") == "dungeon":
                        is_outdoor = False
                    break

        intensity, _ = world_time.get_ambient_light(
            zone_ambient, is_outdoor
        )

        ACTIVE_RADIUS = 30   # fallback constant — kept for Tier 3 bubble radius use

        # Process each non-player actor with an AI component
        for entity in list(entities):
            if entity is player:
                continue
            if not getattr(entity, "is_alive", True):
                continue
            ai = getattr(entity, "ai", None)
            if ai is None:
                continue

            # Chunk membership gate — replaces ACTIVE_RADIUS tile-distance check.
            # Step A: entities have local-map coordinates, so all loaded entities
            #         belong to the player's current chunk (world_x, world_y).
            # Step B: use global coords → ent_wx = entity.x // MAP_WIDTH
            if engine is not None and hasattr(engine, "reality_bubble"):
                ent_wx, ent_wy = world_x, world_y  # Step B: entity.x // MAP_WIDTH
                if not engine.reality_bubble.is_active(ent_wx, ent_wy):
                    continue
            else:
                if abs(entity.x - player.x) + abs(entity.y - player.y) > ACTIVE_RADIUS:
                    continue

            from engine.sound import current_interest
            current_interest(ai, world_time.turn)
            if disrupted(entity, local_map):
                continue

            # Creature special abilities — passive effects, state changes
            if engine is not None:
                from engine.creature_abilities import process_abilities
                process_abilities(entity, engine)

            # One bonus opportunity, before the unchanged normal speed budget.
            # Waking arms it; only a legal committed melee attempt consumes it.
            if getattr(entity, "_ambush_ready", False) and ability_enabled(entity, local_map):
                if engine is not None:
                    from engine.spatial import melee_attack_legal
                    from components.ai import _monster_attack_entity
                    if (melee_attack_legal(local_map, entity, player)
                            and _monster_attack_entity(entity, player, engine)):
                        entity._ambush_ready = False

            # Speed accumulator — creatures with speed < 1.0 skip turns,
            # creatures with speed > 1.0 occasionally get a second step.
            _speed = 1.0
            if engine is not None:
                _speed = engine.data.entities.get(creature_id(entity), {}).get("speed", 1.0)
            ai.move_accumulator += _speed
            if ai.move_accumulator < 1.0:
                continue  # not enough accumulated movement this turn
            _steps = 0
            while ai.move_accumulator >= 1.0 and _steps < 2:
                ai.move_accumulator -= 1.0
                _steps += 1
                ai.take_turn(
                    actor         = entity,
                    local_map     = local_map,
                    entities      = entities,
                    player        = player,
                    log           = log,
                    rng           = self._rng,
                    ambient_light = intensity,
                    engine        = engine,
                )
                if not getattr(entity, "is_alive", True):
                    break

    def process_single(
        self,
        entity,
        local_map,
        player_x:      int,
        player_y:      int,
        entities:      list,
        log,
        ambient_light: float = 1.0,
        engine=None,
    ) -> None:
        """Tick a single entity with explicit player coordinates.

        Used by _tick_live_pursuers() to advance pursuing entities that are
        not in the player's current chunk.  A phantom player is placed at
        (player_x, player_y) with fighter=None so attacks are no-ops.
        """
        from types import SimpleNamespace

        ai = getattr(entity, "ai", None)
        if ai is None:
            return
        if not getattr(entity, "is_alive", True):
            return

        if disrupted(entity, local_map):
            return

        phantom = SimpleNamespace(
            x               = player_x,
            y               = player_y,
            is_alive        = True,
            fighter         = None,
            _in_concealment = False,
            blocks_movement = False,
            tile            = "",
            name            = "__live_pursuer_target__",
        )

        if engine is not None and local_map is engine.local_map:
            from engine.creature_abilities import process_abilities
            process_abilities(entity, engine)

        ai.take_turn(
            actor         = entity,
            local_map     = local_map,
            entities      = entities,
            player        = phantom,
            log           = log,
            rng           = self._rng,
            ambient_light = ambient_light,
            engine        = engine,
        )
