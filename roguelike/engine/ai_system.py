# engine/ai_system.py
from __future__ import annotations
import random
from typing import TYPE_CHECKING
from config import MAP_WIDTH, MAP_HEIGHT

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

            # Creature special abilities — passive effects, state changes
            if engine is not None:
                from engine.creature_abilities import process_abilities
                process_abilities(entity, engine)

            # Ambush attack — fires immediately on wake, before normal turn
            if getattr(entity, "_ambush_ready", False):
                entity._ambush_ready = False
                if engine is not None:
                    from components.ai import _monster_attack_entity
                    _monster_attack_entity(entity, player, engine)

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