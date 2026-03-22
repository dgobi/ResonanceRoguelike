# engine/creature_abilities.py
from __future__ import annotations
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.actor import Actor
    from engine.engine import Engine


def process_abilities(entity: "Actor", engine: "Engine") -> None:
    """
    Process passive and triggered abilities for a creature.
    Called each turn the creature takes an action, before movement.
    """
    ability_fn = ABILITY_REGISTRY.get(entity.tile)
    if ability_fn:
        ability_fn(entity, engine)


# ------------------------------------------------------------------ #
#  Ability implementations
# ------------------------------------------------------------------ #

def _ability_bog_wraith(entity: "Actor", engine: "Engine") -> None:
    """
    Proximity to the wraith interferes with perception (radius 8).
    Penalty is recalculated inside _update_fov() on every FOV call —
    this ability only manages the atmospheric message threshold.
    On wraith death: brief FOV overcorrection (+3 for 3 turns).
    """
    player = engine.player
    dist = math.sqrt(
        (entity.x - player.x) ** 2 +
        (entity.y - player.y) ** 2
    )

    penalty = max(0, int(8 - dist)) if dist <= 8 else 0

    warned = getattr(player, "_wraith_warned", False)
    if penalty >= 4 and not warned:
        player._wraith_warned = True
        engine.log.add(
            "Something bleeds from thy sight. "
            "The edges of the world soften.",
            (41, 21, 70),
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
            (99, 34, 64),
        )

    # Visual pulse — slow blood-rose discharge emanating from wight
    from engine.visual_events import VisualEvent
    engine.visual_events.add(VisualEvent(
        type="pulse", x=entity.x, y=entity.y,
        color=(99, 34, 64), duration=8, intensity=0.6,
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
            (68, 99, 116),
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
                (100, 100, 110),
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
