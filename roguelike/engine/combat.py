# engine/combat.py
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.fighter import Fighter


# Extra crit chance added when a head hit is rolled.
HEAD_CRIT_BONUS: float = 0.15


@dataclass
class CombatResult:
    hit:               bool  = False
    location_id:       str   = ""
    location_name:     str   = ""
    damage_raw:        int   = 0    # before armour
    damage_dealt:      int   = 0    # after armour × location multiplier
    essence_applied:   str   = ""
    essence_modifier:  float = 1.0
    attacker_dead:     bool  = False
    defender_dead:     bool  = False
    messages:          list  = field(default_factory=list)
    message_types:     list  = field(default_factory=list)
    damage_number:     int   = 0
    is_player_hit:     bool  = False
    damage_raw_post_essence: int = 0
    debug_formula:     str   = ""
    is_crit:           bool  = False
    dodged:            bool  = False
    blocked:           bool  = False
    block_reduction:   int   = 0


LOCATION_DISPLAY = {
    "head":       "the head",
    "torso":      "the body",
    "right_arm":  "the right arm",
    "left_arm":   "the left arm",
    "right_leg":  "the right leg",
    "left_leg":   "the left leg",
    "form":       "the form",
    "limbs":      "the limbs",
    "core":       "the core",
    "briars":     "the briars",
    "carapace":   "the carapace",
    "forelegs":   "the forelegs",
    "hindlegs":   "the hindlegs",
    "wings":      "the wings",
    "appendages": "the appendages",
    "arms":       "the arms",
    "legs":       "the legs",
    "hide":       "the hide",
}


EFFECTIVE_MESSAGES = [
    "It recoils.",
    "Something in it comes apart.",
    "The form shudders.",
    "This is the right wound for this thing.",
    "It does not like this.",
]


def roll_dice(dice_str: str, rng: random.Random) -> int:
    """Roll NdM dice. e.g. '2d6', '1d4'."""
    try:
        n, m = dice_str.lower().split('d')
        return sum(rng.randint(1, int(m)) for _ in range(int(n)))
    except (ValueError, AttributeError):
        return 1


def get_body_def(fighter: "Fighter", bodies: dict) -> dict:
    """Return the body definition dict for a fighter.
    Checks fighter.body_limbs first (inline limbs from creature JSON).
    Falls back to loading from the bodies registry via fighter.body_id.
    """
    limbs = getattr(fighter, "body_limbs", [])
    if limbs:
        return {"locations": limbs}
    return bodies.get(getattr(fighter, "body_id", ""), {})


def select_location(body_def: dict, rng: random.Random) -> dict:
    """Weighted random location selection by size."""
    locations = body_def.get("locations", [])
    if not locations:
        return {}
    total = sum(loc.get("size", 1) for loc in locations)
    roll  = rng.randint(1, total)
    cumul = 0
    for loc in locations:
        cumul += loc.get("size", 1)
        if roll <= cumul:
            return loc
    return locations[-1]


def apply_essence(
    damage: int,
    weapon_essence: str | None,
    weapon_strength: float,
    creature_modifiers: dict,
) -> tuple[int, float]:
    """Apply essence modifier to damage. Returns (modified_damage, net_modifier)."""
    if not weapon_essence or not weapon_strength:
        return damage, 1.0
    creature_mod = creature_modifiers.get(weapon_essence, 1.0)
    net      = 1.0 + (creature_mod - 1.0) * weapon_strength
    modified = max(0, int(damage * net))
    return modified, net


def resolve_attack(
    attacker_name:  str,
    defender_name:  str,
    defender_fighter: "Fighter",
    body_def:       dict,
    weapon:         dict | None,
    creature_essence_mods: dict,
    rng:            random.Random,
    attacker_disrupted:    bool  = False,
    defender_dodge_chance: float = 0.0,
    shield_def:            dict | None = None,
) -> CombatResult:
    """
    Full combat resolution — single HP pool, single effective_av.

    Resolution order:
    1. Dodge roll        → if success: return dodged result
    2. Select hit location
    3. Base damage roll
    4. Essence modifier
    5. Critical hit check
    6. Block roll        → if success: apply block_reduction
    7. Subtract AV       → max(0, raw - block_reduction - effective_av)
    8. Apply location multiplier
    9. Apply to HP pool
    10. Build messages + debug formula
    """
    result = CombatResult(hit=True)

    # ── 1. Dodge roll ──────────────────────────────────────────────
    if defender_dodge_chance > 0.0 and rng.random() < defender_dodge_chance:
        result.dodged      = True
        result.hit         = False
        result.damage_dealt = 0
        is_player = (defender_name == "thee")
        result.is_player_hit = is_player
        if is_player:
            result.messages.append(f"The {attacker_name}'s blow goes wide.")
        else:
            result.messages.append(f"The {defender_name} evades the strike.")
        result.message_types.append("deflect")
        result.debug_formula = "[dodge: miss]"
        return result

    # ── 2. Select hit location ──────────────────────────────────────
    loc_def = select_location(body_def, rng)
    if not loc_def:
        result.hit = False
        return result

    loc_id   = loc_def["id"]
    loc_name = LOCATION_DISPLAY.get(loc_id, loc_id)
    loc_mult = float(loc_def.get("damage_multiplier", 1.0))
    result.location_id   = loc_id
    result.location_name = loc_name

    # ── 3. Base damage roll ─────────────────────────────────────────
    if weapon and weapon.get("damage_dice"):
        if attacker_disrupted:
            roll1 = roll_dice(weapon["damage_dice"], rng)
            roll2 = roll_dice(weapon["damage_dice"], rng)
            raw = min(roll1, roll2) + weapon.get("damage_bonus", 0)
        else:
            raw = roll_dice(weapon["damage_dice"], rng) + weapon.get("damage_bonus", 0)
    else:
        raw = rng.randint(1, 4)   # unarmed fallback
    result.damage_raw = raw

    # ── 4. Essence modifier ─────────────────────────────────────────
    if weapon:
        essences_list = weapon.get("essences", [])
        if essences_list:
            best_raw = -1
            best_ess = ""
            best_mod = 1.0
            for ess_entry in essences_list:
                ename = ess_entry.get("name", "")
                estr  = float(ess_entry.get("strength", 0.0))
                d, m  = apply_essence(raw, ename, estr, creature_essence_mods)
                if d > best_raw:
                    best_raw = d
                    best_ess = ename
                    best_mod = m
            raw     = best_raw
            essence = best_ess
            ess_mod = best_mod
        else:
            essence = weapon.get("essence") or None
            estr    = weapon.get("essence_strength", 0.0)
            raw, ess_mod = apply_essence(raw, essence, estr, creature_essence_mods)
    else:
        essence = None
        raw, ess_mod = apply_essence(raw, None, 0.0, creature_essence_mods)

    result.essence_applied        = essence or ""
    result.essence_modifier       = ess_mod
    result.damage_raw_post_essence = raw

    # ── 5. Critical hit check — head shots add HEAD_CRIT_BONUS ──────
    _base_crit   = 0.05
    _weapon_crit = (weapon.get("crit_chance", 0.0) if weapon else 0.0)
    _head_bonus  = HEAD_CRIT_BONUS if loc_id == "head" else 0.0
    _total_crit  = _base_crit + _weapon_crit + _head_bonus
    if rng.random() < _total_crit:
        raw = int(raw * 2.5)
        result.is_crit = True

    # ── 6. Block roll ───────────────────────────────────────────────
    block_reduction = 0
    if shield_def:
        block_chance = float(shield_def.get("block_chance", 0.0))
        if block_chance > 0.0 and rng.random() < block_chance:
            block_reduction         = int(shield_def.get("block_value", 0))
            result.blocked          = True
            result.block_reduction  = block_reduction

    # ── 7. Apply effective_av + block reduction + location mult ─────
    effective_av = getattr(defender_fighter, "effective_av", 0)
    after_mitigation = max(0, raw - block_reduction - effective_av)
    damage_dealt     = int(after_mitigation * loc_mult)
    result.damage_dealt = damage_dealt

    # ── 8. Apply to HP pool ─────────────────────────────────────────
    if damage_dealt > 0:
        defender_fighter.take_damage(damage_dealt)
        result.defender_dead = defender_fighter.is_dead

    # ── 9. Build messages ───────────────────────────────────────────
    is_player = (defender_name == "thee")
    result.is_player_hit = is_player
    loc_display = loc_name.replace("the ", "thy ", 1) if is_player else loc_name

    def _msg(text: str, mtype: str) -> None:
        result.messages.append(text)
        result.message_types.append(mtype)

    # Block message first
    if result.blocked:
        _msg("The blow glances off the shield.", "deflect")

    if damage_dealt <= 0:
        if ess_mod < 0.5 and essence:
            _msg(
                f"This thing resists {essence.lower()}. The blow finds no purchase.",
                "deflect",
            )
        elif effective_av > 0 and raw > 0:
            _msg("The blow is turned aside.", "deflect")
        elif raw <= 0:
            _msg("Thy blow carries no force enough to matter.", "deflect")
        else:
            _msg("The blow finds no purchase.", "deflect")
    else:
        _msg(f"The strike finds {loc_display}.", "hit")
        if (effective_av > 0 or block_reduction > 0) and after_mitigation < raw // 2:
            _msg("Much is turned aside.", "deflect")

    # Essence effectiveness signal
    if ess_mod > 1.8 and damage_dealt > 0 and rng.random() < 0.40:
        _msg(rng.choice(EFFECTIVE_MESSAGES), "hit")

    if result.defender_dead:
        if not is_player:
            _msg(f"The {defender_name} is destroyed.", "death")

    result.damage_number = damage_dealt

    # ── 10. Debug formula ───────────────────────────────────────────
    if weapon and weapon.get("damage_dice"):
        _d_str = weapon["damage_dice"]
        _mod   = weapon.get("damage_bonus", 0)
    else:
        _d_str = "1d4"
        _mod   = 0
    _roll = result.damage_raw
    if _mod > 0:
        _formula = f"[{_d_str}+{_mod} \u2192 {_roll}]"
    elif _mod < 0:
        _formula = f"[{_d_str}{_mod} \u2192 {_roll}]"
    else:
        _formula = f"[{_d_str} \u2192 {_roll}]"

    _block_str = f" [block:-{block_reduction}]" if block_reduction > 0 else ""
    _mult_str  = f"\u00d7{loc_mult:.1f}" if loc_mult != 1.0 else ""
    result.debug_formula = (
        f"{_formula}{_block_str} \u2212 AV={effective_av} \u2192 {after_mitigation}"
        + (f" {_mult_str}" if _mult_str else "")
        + f" \u2192 {damage_dealt}"
    )
    if result.is_crit:
        result.debug_formula += " \u00d72.5 !!CRIT!!"
    elif result.essence_applied and ess_mod != 1.0:
        _ess_delta = result.damage_raw - result.damage_raw_post_essence
        if _ess_delta != 0:
            sign = "+" if _ess_delta < 0 else "-"
            result.debug_formula += f" ({result.essence_applied} {sign}{abs(_ess_delta)})"

    return result
