# engine/movesets.py
"""
Weapon moveset system — pure functions for moveset action execution.

Each weapon JSON may contain a "movesets" array. Each entry defines an
action bound to Q or R with: id, name, description, key, turn_cost,
cooldown, range, damage_mult, effects.

The engine calls execute_moveset() which dispatches to the appropriate
action handler, returning a MovesetResult the engine applies.
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.engine import Engine
    from entities.actor import Actor


@dataclass
class MovesetResult:
    """Result of executing a moveset action."""
    hit:            bool  = False
    damage:         int   = 0
    turn_cost:      float = 1.0
    messages:       list  = field(default_factory=list)  # (text, colour)
    callout:        str   = ""
    callout_colour: tuple = (200, 200, 200)
    # Post-hit effects for engine to apply
    free_move:          bool = False   # player gets free move on kill
    destroy_armour:     bool = False   # remove outermost armour layer
    reduce_av:          int  = 0       # permanently reduce target AV
    suppress_ability:   int  = 0       # suppress special ability for N turns
    ignore_armour:      bool = False   # bypass AV entirely
    ignore_dodge:       bool = False   # bypass dodge roll
    reveal_knowledge:   bool = False   # reveal creature weakness/strength
    aoe_disrupt_range:  int  = 0       # disrupt same-type creatures in range
    aoe_disrupt_turns:  int  = 0
    place_pool:         str  = ""      # decor to place on kill
    pool_turns:         int  = 0
    on_kill_only:       bool = False   # effect only fires on kill
    hp_gate:            float = 0.0    # only usable below this HP fraction (0 = no gate)
    screen_shake:       int  = 0


def get_moveset_action(weapon_def: dict, key: str) -> dict | None:
    """Return the moveset entry for the given key ("Q" or "R"), or None."""
    for ms in weapon_def.get("movesets", []):
        if ms.get("key", "").upper() == key.upper():
            return ms
    return None


def execute_moveset(
    action:  dict,
    engine:  "Engine",
    target:  "Actor",
    weapon:  dict,
) -> MovesetResult | None:
    """Execute a moveset action. Returns MovesetResult or None if blocked.

    Checks positioning/HP gates. Does NOT resolve damage — that is done
    by the caller using resolve_attack() with the result's modifiers.
    """
    from engine.palette import (MSG_DEFAULT, MSG_COMBAT_OUT, MSG_DANGER,
                                MSG_ANCIENT, RESONANCE_HIGH, UI_TEXT_DIM)
    result = MovesetResult()
    result.turn_cost = action.get("turn_cost", 1.0)
    result.callout = action.get("callout", action.get("name", ""))
    aid = action.get("id", "")

    # HP gate check
    hp_gate = action.get("hp_gate", 0.0)
    if hp_gate > 0.0:
        fighter = getattr(engine.player, "fighter", None)
        if fighter and fighter.hp_fraction > hp_gate:
            result.messages.append(("Not yet desperate enough.", MSG_DEFAULT))
            return None  # blocked — no turn spent

    # Positioning check
    positioning = action.get("positioning")
    if positioning == "behind":
        # Target must not be facing player
        ai = getattr(target, "ai", None)
        if ai:
            tx = getattr(ai, "target_x", None)
            ty = getattr(ai, "target_y", None)
            if tx is not None and ty is not None:
                # If target is moving toward player, positioning fails
                px, py = engine.player.x, engine.player.y
                d_to_player = math.sqrt((tx - px) ** 2 + (ty - py) ** 2)
                d_from_target = math.sqrt((tx - target.x) ** 2 + (ty - target.y) ** 2)
                if d_to_player < d_from_target:
                    result.messages.append(("No opening.", MSG_DEFAULT))
                    return None  # blocked

    # Apply action effects
    effects = action.get("effects", {})
    result.damage = 0  # damage is calculated by caller via resolve_attack
    result.ignore_armour = effects.get("ignore_armour", False)
    result.ignore_dodge = effects.get("ignore_dodge", False)
    result.free_move = effects.get("free_move_on_kill", False)
    result.on_kill_only = effects.get("on_kill_only", False)
    result.destroy_armour = effects.get("destroy_armour", False)
    result.reduce_av = effects.get("reduce_av", 0)
    result.suppress_ability = effects.get("suppress_ability_turns", 0)
    result.reveal_knowledge = effects.get("reveal_knowledge", False)
    result.aoe_disrupt_range = effects.get("aoe_disrupt_range", 0)
    result.aoe_disrupt_turns = effects.get("aoe_disrupt_turns", 0)
    result.place_pool = effects.get("place_pool", "")
    result.pool_turns = effects.get("pool_turns", 0)
    result.hp_gate = hp_gate
    result.screen_shake = effects.get("screen_shake", 0)

    # Callout colour — use weapon essence colour or default
    from engine.palette import (RESONANCE_HIGH, COMBAT_OUTGOING,
                                CORRUPTION_COLOUR, SPIRIT_BLUE, OLD_GOLD)
    _essence_colors = {
        "Dissolution": CORRUPTION_COLOUR,
        "Binding": SPIRIT_BLUE,
        "Severance": OLD_GOLD,
        "Revelation": RESONANCE_HIGH,
        "Quickening": (120, 200, 120),
        "Consumption": (200, 80, 80),
    }
    essence = weapon.get("essence", "")
    result.callout_colour = _essence_colors.get(essence, COMBAT_OUTGOING)

    return result


def apply_damage_mult(base_damage: int, action: dict) -> int:
    """Apply moveset damage multiplier to base damage."""
    mult = action.get("damage_mult", 1.0)
    return max(1, int(base_damage * mult))
