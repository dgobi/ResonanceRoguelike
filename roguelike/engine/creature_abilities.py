# engine/creature_abilities.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from entities.actor import Actor
    from engine.engine import Engine


def process_abilities(entity: "Actor", engine: "Engine") -> None:
    """
    Process passive and triggered abilities for a creature.
    Called each turn the creature takes an action, before movement.
    Uses _creature_id (set at spawn) as the stable registry key so that
    creatures whose tile changes (e.g. stone_lurker → rock) keep their ability.
    """
    key = getattr(entity, "_creature_id", entity.tile)
    ability_fn = ABILITY_REGISTRY.get(key)
    if ability_fn:
        ability_fn(entity, engine)


# ------------------------------------------------------------------ #
#  Ability implementations
# ------------------------------------------------------------------ #

def _ability_bog_wraith(entity: "Actor", engine: "Engine") -> None:
    """
    Proximity to the wraith interferes with perception.
    Drain radius is read from ability_range in the creature JSON
    (same value as sight_radius — awareness and drain activate together).
    Penalty is recalculated inside _update_fov() on every FOV call —
    this ability only manages the atmospheric message threshold.
    On wraith death: brief FOV overcorrection (+3 for 3 turns).
    """
    drain_radius = engine.data.entities.get("bog_wraith", {}).get("ability_range", 8)
    player = engine.player
    dist = math.sqrt(
        (entity.x - player.x) ** 2 +
        (entity.y - player.y) ** 2
    )

    penalty = max(0, int(drain_radius - dist)) if dist <= drain_radius else 0

    warned = getattr(player, "_wraith_warned", False)
    if penalty >= 4 and not warned:
        player._wraith_warned = True
        engine.log.add(
            "Something bleeds from thy sight. "
            "The edges of the world soften.",
            DEEP_PURPLE,
        )
    elif penalty < 2:
        player._wraith_warned = False


def _ability_barrow_wight(entity: "Actor", engine: "Engine") -> None:
    """
    The wight's accumulated resonance discharges into nearby living things.
    Passive corruption gain per turn of adjacency.
    The wight does not know it is doing this.
    """
    player = engine.player
    dist = math.sqrt(
        (entity.x - player.x) ** 2 +
        (entity.y - player.y) ** 2
    )

    if dist > 2:
        return

    corrupt = getattr(player, "corruption", None)
    if not corrupt:
        return

    corrupt.value = min(1.0, corrupt.value + 0.005)

    turn = engine.world_time.turn
    if turn % 20 == 0:
        engine.log.add(
            "The wight presses close. "
            "Something in thy bones answers it.",
            DRIED_BLOOD,
        )

    # Visual pulse — slow blood-rose discharge emanating from wight
    from engine.visual_events import VisualEvent
    engine.visual_events.add(VisualEvent(
        type="pulse", x=entity.x, y=entity.y,
        color=DRIED_BLOOD, duration=8, intensity=0.6,
    ))


def _ability_hollow_knight(entity: "Actor", engine: "Engine") -> None:
    """
    The grinding from fused armor creates subsonic disruption within 5 tiles.
    Player attack rolls use the lower of two dice while in range.
    """
    player = engine.player
    dist = math.sqrt(
        (entity.x - player.x) ** 2 +
        (entity.y - player.y) ** 2
    )

    in_range    = dist <= 5
    was_in_range = getattr(player, "_hollow_knight_disruption", False)
    player._hollow_knight_disruption = in_range

    if in_range and not was_in_range:
        engine.log.add(
            "A grinding sound. Below hearing, almost. "
            "Thy hands feel wrong.",
            STONE_BLUE,
        )
    elif not in_range and was_in_range:
        player._hollow_knight_disruption = False


def _ability_plague_crow(entity: "Actor", engine: "Engine") -> None:
    """Passive sickness carrier — applied in _monster_attack_entity on hit."""
    pass


def _ability_stone_lurker(entity: "Actor", engine: "Engine") -> None:
    """
    Hibernates as a rock formation until player is within 3 tiles.
    While hibernating: renders as rock tile, stays motionless.
    First attack after waking is free (ambush).
    """
    # Ensure hibernation is set up on first call regardless of AI default state
    if not hasattr(entity, "_hibernating"):
        entity._hibernating = True
        entity.tile = "rock"
        if hasattr(entity, "ai"):
            from components.ai import AIState
            entity.ai.state = AIState.WAITING

    player = engine.player
    dist = math.sqrt(
        (entity.x - player.x) ** 2 +
        (entity.y - player.y) ** 2
    )

    hibernating = getattr(entity, "_hibernating", True)

    if hibernating:
        if dist <= 3:
            entity._hibernating = False
            entity._ambush_ready = True
            entity.tile = "stone_lurker"
            engine.log.add(
                "The stone moves. It was never stone.",
                DUNGEON_SHADOW,
            )
        else:
            entity.tile = "rock"


def _ability_briar_lurker(entity: "Actor", engine: "Engine") -> None:
    """Passive retaliation thorns — handled in engine._player_attack()."""
    pass


# ------------------------------------------------------------------ #
#  Registry
# ------------------------------------------------------------------ #

ABILITY_REGISTRY = {
    "bog_wraith":    _ability_bog_wraith,
    "barrow_wight":  _ability_barrow_wight,
    "hollow_knight": _ability_hollow_knight,
    "plague_crow":   _ability_plague_crow,
    "stone_lurker":  _ability_stone_lurker,
    "briar_lurker":  _ability_briar_lurker,
}
