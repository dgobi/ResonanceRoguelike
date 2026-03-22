# engine/combat.py
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from components.fighter import Fighter
    from engine.data_loader import DataLoader


@dataclass
class CombatResult:
    hit:               bool   = False
    location_id:       str    = ""
    location_name:     str    = ""
    layers_struck:     list   = field(default_factory=list)   # list of layer names that intercepted
    layers_bypassed:   list   = field(default_factory=list)   # list of layer names that didn't
    damage_raw:        int    = 0    # before armor
    damage_dealt:      int    = 0    # after armor
    impairments:       list   = field(default_factory=list)   # new impairments triggered
    essence_applied:   str    = ""   # which essence interacted
    essence_modifier:  float  = 1.0  # net modifier applied
    attacker_dead:     bool   = False
    defender_dead:     bool   = False
    messages:          list   = field(default_factory=list)   # archaic-register strings
    message_types:     list   = field(default_factory=list)   # parallel tags: "hit","deflect","impair","death"
    damage_number:     int    = 0    # damage dealt, logged separately
    is_player_hit:     bool   = False  # True when defender is the player


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

MATERIAL_DISPLAY = {
    "iron":      "iron",
    "bone":      "bone",
    "hide":      "hide",
    "flesh":     "flesh",
    "stone":     "stone",
    "wood":      "wood",
    "mist":      "nothing",
    "resonance": "the charge within it",
}

IMPAIRMENT_MESSAGES = {
    "dominant_hand_lost": "{name} cannot strike.",
    "off_hand_lost":      "{name}'s off hand fails.",
    "leg_lost":           "{name} staggers.",
    "legs_failing":       "{name} can barely stand.",
    "arms_failing":       "{name}'s arms fail.",
    "form_destabilising": "The form begins to come apart.",
    "form_dispersing":    "The form disperses at the edges.",
    "core_cracking":      "Something cracks within it.",
    "torso_wounded":      "{name} is gravely wounded.",
    "carapace_broken":    "The carapace shatters.",
    "forelegs_hamstrung": "The forelegs buckle.",
    "hindlegs_hamstrung": "The hindlegs give way.",
    "wings_broken":       "The wings hang broken.",
    "briars_stripped":    "The briars tear away.",
    "limbs_failing":      "The limbs fail.",
    "limbs_dissolving":   "The limbs begin to dissolve.",
    "head_destroyed":     "The head is destroyed.",
    "death":              "{name} is destroyed.",
}

# Second-person versions used when the player is the defender
IMPAIRMENT_MESSAGES_PLAYER = {
    "dominant_hand_lost": "Thy dominant hand fails.",
    "off_hand_lost":      "Thy off hand fails.",
    "leg_lost":           "Thou stagger.",
    "legs_failing":       "Thou canst barely stand.",
    "arms_failing":       "Thy arms fail.",
    "form_destabilising": "Something is coming apart in thee.",
    "form_dispersing":    "Thee disperses at the edges.",
    "core_cracking":      "Something cracks within thee.",
    "torso_wounded":      "Thou art gravely wounded.",
    "carapace_broken":    "Something shatters.",
    "forelegs_hamstrung": "Thy legs buckle.",
    "hindlegs_hamstrung": "Thy legs give way.",
    "wings_broken":       "Thy wings hang broken.",
    "briars_stripped":    "The briars tear away.",
    "limbs_failing":      "Thy limbs fail.",
    "limbs_dissolving":   "Thy limbs begin to dissolve.",
    "head_destroyed":     "Thy head is destroyed.",
    "death":              "Thou art destroyed.",
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


def roll_layers(
    layers: list,
    damage: int,
    rng: random.Random,
) -> tuple[int, list, list]:
    """
    Roll damage through armor layers.
    Returns (damage_remaining, layers_struck, layers_bypassed).
    """
    struck    = []
    bypassed  = []
    remaining = damage

    for layer in layers:
        coverage = layer.get("coverage", 1.0)
        if rng.random() < coverage:
            av = layer.get("armor_value", 0)
            remaining = max(0, remaining - av)
            struck.append(layer["name"])
            if remaining <= 0:
                break
        else:
            bypassed.append(layer["name"])

    return remaining, struck, bypassed


def apply_essence(
    damage: int,
    weapon_essence: str | None,
    weapon_strength: float,
    creature_modifiers: dict,
) -> tuple[int, float]:
    """
    Apply essence modifier to damage.
    Returns (modified_damage, net_modifier_applied).
    """
    if not weapon_essence or not weapon_strength:
        return damage, 1.0

    creature_mod = creature_modifiers.get(weapon_essence, 1.0)
    # Blend toward modifier based on strength
    net = 1.0 + (creature_mod - 1.0) * weapon_strength
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
    attacker_disrupted: bool = False,
) -> CombatResult:
    """
    Full combat resolution.
    attacker_name, defender_name: display names.
    weapon: item dict with damage_dice, damage_bonus, essence, essence_strength.
    body_def: the defender's body definition JSON.
    """
    result = CombatResult(hit=True)

    # 1. Select location
    loc_def = select_location(body_def, rng)
    if not loc_def:
        result.hit = False
        return result

    loc_id   = loc_def["id"]
    loc_name = LOCATION_DISPLAY.get(loc_id, loc_id)
    result.location_id   = loc_id
    result.location_name = loc_name

    # 2. Base damage from weapon or fallback
    if weapon and weapon.get("damage_dice"):
        if attacker_disrupted:
            # Hollow knight disruption — roll twice, take lower
            roll1 = roll_dice(weapon["damage_dice"], rng)
            roll2 = roll_dice(weapon["damage_dice"], rng)
            raw = min(roll1, roll2) + weapon.get("damage_bonus", 0)
        else:
            raw = roll_dice(weapon["damage_dice"], rng) + weapon.get("damage_bonus", 0)
    else:
        raw = rng.randint(1, 4)  # unarmed fallback
    result.damage_raw = raw

    # 3. Essence modifier
    essence          = weapon.get("essence") if weapon else None
    essence_strength = weapon.get("essence_strength", 0.0) if weapon else 0.0
    raw, ess_mod     = apply_essence(raw, essence, essence_strength,
                                     creature_essence_mods)
    result.essence_applied  = essence or ""
    result.essence_modifier = ess_mod

    # 4. Roll through armor layers
    layers = defender_fighter.armor_layers.get(loc_id, [])
    damage_after, struck, bypassed = roll_layers(layers, raw, rng)
    result.layers_struck   = struck
    result.layers_bypassed = bypassed
    result.damage_dealt    = damage_after

    # 5. Apply to location HP
    if damage_after > 0:
        impairments = defender_fighter.take_location_damage(
            loc_id, damage_after, body_def
        )
        result.impairments = impairments
        result.defender_dead = defender_fighter.is_dead

    # 6. Build messages
    is_player = (defender_name == "thee")
    result.is_player_hit = is_player
    # For player: "thy head", "thy body" etc — replace "the " with "thy "
    if is_player:
        loc_display = loc_name.replace("the ", "thy ", 1)
    else:
        loc_display = loc_name

    def _msg(text: str, mtype: str) -> None:
        result.messages.append(text)
        result.message_types.append(mtype)

    if damage_after <= 0:
        # Distinguish essence resistance from armor deflection
        if ess_mod < 0.5 and essence:
            _msg(
                f"This thing resists {essence.lower()}. "
                f"The blow finds no purchase.",
                "deflect",
            )
        else:
            _msg("The blow finds no purchase.", "deflect")
    elif struck:
        _msg(f"The strike catches {loc_display}.", "hit")
        if damage_after < raw // 2:
            _msg("Much is turned aside.", "deflect")
    else:
        _msg(f"The strike finds {loc_display}.", "hit")

    # Essence effectiveness signal — fires rarely so it feels meaningful
    if ess_mod > 1.8 and damage_after > 0 and rng.random() < 0.40:
        _msg(rng.choice(EFFECTIVE_MESSAGES), "hit")

    # Impairment messages
    imp_dict = IMPAIRMENT_MESSAGES_PLAYER if is_player else IMPAIRMENT_MESSAGES
    for imp in result.impairments:
        msg_template = imp_dict.get(imp, "")
        if msg_template:
            _msg(msg_template.format(name=defender_name), "impair")

    if result.defender_dead and "death" not in result.impairments:
        if not is_player:
            _msg(f"The {defender_name} is destroyed.", "death")

    result.damage_number = result.damage_dealt

    return result
