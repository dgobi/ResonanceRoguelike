# engine/creature_factory.py
from __future__ import annotations
import random
from entities.actor import Actor
from components.fighter import Fighter
from components.perception import Perception
from components.ai import (
    WanderingAI, AmbushAI, FleeingAI, CirclingAI, AIState
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.data_loader import DataLoader

AI_TYPES = {
    "wandering": WanderingAI,
    "ambush":    AmbushAI,
    "fleeing":   FleeingAI,
    "circling":  CirclingAI,
}


class CreatureFactory:
    """
    Assembles Actor instances from creature JSON definitions.
    Single source of truth for creature construction.
    """

    def __init__(self, data: DataLoader) -> None:
        self.data = data

    def spawn(
        self,
        creature_id: str,
        x:           int,
        y:           int,
        rng:         random.Random | None = None,
    ) -> Actor | None:
        """
        Create a fully assembled Actor for the given creature id.
        Returns None if creature_id not found.
        """
        defn = self.data.entities.get(creature_id)
        if not defn:
            print(f"Warning: creature '{creature_id}' not found.")
            return None

        rng = rng or random.Random()

        actor = Actor(
            x    = x,
            y    = y,
            tile = defn.get("tile", "hollow_knight"),
            name = defn.get("name", creature_id),
        )
        actor.is_alive    = True
        actor._creature_id = creature_id  # stable; never changes even if tile changes

        # Fighter component — hp from base_hp in creature JSON (preferred) or fighter block
        f        = defn.get("fighter", {})
        base_hp  = defn.get("base_hp", f.get("max_hp", 10))
        body_id  = defn.get("body_id", "body_human")
        actor.fighter = Fighter(
            max_hp  = base_hp,
            power   = f.get("power",   3),
            defense = f.get("defense", 0),
        )
        actor.fighter.body_id    = body_id
        actor.fighter.body_limbs = defn.get("limbs", [])
        actor.fighter.effective_av = defn.get("armour_value", 0)

        # Perception component
        p = defn.get("perception", {})
        if p:
            actor.perception = Perception(
                sight_radius   = p.get("sight_radius",   8),
                hearing_radius = p.get("hearing_radius", 5),
                sees_in_dark   = p.get("sees_in_dark",   False),
                faction        = p.get("faction",        "hostile"),
                hostile_to     = p.get("hostile_to",     ["player"]),
            )

        # AI component
        ai_type    = defn.get("ai_type", "wandering")
        ai_class   = AI_TYPES.get(ai_type, WanderingAI)
        wander_r   = defn.get("wander_radius", 8)
        actor.ai   = ai_class(wander_radius=wander_r)
        actor.ai.set_home(x, y)

        return actor

    def spawn_for_zone(
        self,
        zone_id:   str,
        local_map: "LocalMap",
        rng:       random.Random,
        max_count: int = 4,
    ) -> list[Actor]:
        """
        Spawn creatures appropriate for a zone.
        Uses zone creature list with weighted random selection.
        """
        zone = self.data.zones.get(zone_id)
        if not zone:
            return []

        creature_list = zone.get("creatures", [])
        if not creature_list:
            return []

        spawned = []
        for entry in creature_list:
            if len(spawned) >= max_count:
                break

            if rng.random() > entry.get("chance", 0.3):
                continue

            creature_id = entry.get("id")
            if not creature_id:
                continue

            attempts = 0
            while attempts < 20:
                attempts += 1
                x = rng.randint(1, local_map.width  - 2)
                y = rng.randint(1, local_map.height - 2)
                if local_map.walkable[x, y]:
                    actor = self.spawn(creature_id, x, y, rng)
                    if actor:
                        spawned.append(actor)
                    break

        return spawned