# engine/item_system.py
from __future__ import annotations
from typing import TYPE_CHECKING
from engine.palette import *

if TYPE_CHECKING:
    from engine.engine import Engine
    from entities.item import Item


class ItemSystem:
    """
    Resolves item use effects.
    Called by the engine when the player uses an item.
    """

    def use(self, item: "Item", engine: "Engine") -> bool:
        """
        Apply item use effect.
        Returns True if the item was consumed/used successfully.
        """
        effect = item.on_use
        if not effect:
            engine.log.add(
                f"You hold the {item.name}. Nothing happens.",
                WORN_STONE,
            )
            return False

        handler = getattr(self, f"_use_{effect}", None)
        if not handler:
            engine.log.add(
                f"[DEBUG] Unknown effect: {effect}",
                AGED_WOOD,
            )
            return False

        return handler(item, engine)

    # ------------------------------------------------------------------ #
    #  Effect handlers
    # ------------------------------------------------------------------ #

    def _use_read(self, item: "Item", engine: "Engine") -> bool:
        text_id = getattr(item, "text_id", "")
        if not text_id:
            engine.log.add(
                f"The {item.name} hath nothing legible upon it.",
                WORN_STONE,
            )
            return False
        text_def = engine.data.texts.get(text_id)
        if not text_def:
            engine.log.add(f"[DEBUG] text '{text_id}' not found.", AGED_WOOD)
            return False
        engine.text_reader.open_text(text_def)
        # Teach deep tongue words if text has teach_words block — once per text_id
        if text_def.get("teach_words"):
            lang = getattr(engine.player, "language", None)
            if lang is not None and text_id not in lang.taught_texts:
                from engine.language_system import learn_from_text
                learned = learn_from_text(
                    text_def, lang, engine.data.deep_tongue, engine.rng,
                )
                lang.taught_texts.add(text_id)
                for wid in learned:
                    wdef = engine.data.deep_tongue.get(wid, {})
                    deep = wdef.get("deep", wid)
                    common = wdef.get("common", "")
                    lang.translation_events[wid] = engine.world_time.turn
                    engine.log.add(
                        f"Something stirs in the bone. A word surfaces — [{deep}]: {common}.",
                        DEEP_TONGUE_COLOUR,
                    )
        return False   # not consumed

    def _use_eat(self, item: "Item", engine: "Engine") -> bool:
        needs = getattr(engine.player, "needs", None)
        if not needs:
            return False

        raw = item.nutrition if item.nutrition is not None else 300
        survival = getattr(engine.data, "survival", {})
        h_max = survival.get("hunger", {}).get("max", 1000)
        # Values <= 1.0 are legacy float fractions; values > 1.0 are integers to normalise
        fraction = raw if raw <= 1.0 else raw / h_max
        needs.eat(fraction)

        msg = getattr(item, "eat_message", None)
        if msg:
            engine.log.add(msg, AGED_WOOD)
        else:
            engine.log.add(f"{item.name.capitalize()}. Something in it helps.", AGED_WOOD)
        return True   # consumed

    def _use_drink(self, item: "Item", engine: "Engine") -> bool:
        needs = getattr(engine.player, "needs", None)
        if not needs:
            return False

        raw = item.hydration if item.hydration is not None else 400
        survival = getattr(engine.data, "survival", {})
        t_max = survival.get("thirst", {}).get("max", 800)
        # Values <= 1.0 are legacy float fractions; values > 1.0 are integers to normalise
        fraction = raw if raw <= 1.0 else raw / t_max
        needs.drink(fraction)

        msg = getattr(item, "drink_message", None)
        if msg:
            engine.log.add(msg, CLEAR_WATER)
        else:
            engine.log.add("The liquid steadies something.", CLEAR_WATER)
        return True   # consumed

    def _use_heal_minor(self, item: "Item", engine: "Engine") -> bool:
        fighter = getattr(engine.player, "fighter", None)
        if not fighter:
            return False

        amount = item.heal_amount or 3
        actual = fighter.heal(amount)

        if actual == 0:
            engine.log.add(
                f"You take the {item.name}. Your wounds are already closed.",
                LIFE_GREEN,
            )
        else:
            engine.log.add(
                f"You take the {item.name}. "
                f"You recover {actual} HP.",
                LIFE_GREEN,
            )
        return True   # consumed

    def _use_equip_light(
        self, item: "Item", engine: "Engine"
    ) -> bool:
        """
        Light a torch or lantern.
        Equips to off-hand slot while lit. Frees off-hand on extinguish.
        """
        from components.light_source import LightSource

        if not item.light_data:
            return False

        equipment = getattr(engine.player, "equipment", None)
        current   = engine.player.light_source

        # If already lit — extinguish and unequip from off-hand
        if (current and current.active and
                getattr(current, "_item_ref", None) is item):
            current.active = False
            if equipment and equipment.slots.get("offhand") is item:
                equipment.unequip("offhand")
            engine.log.add(
                f"You extinguish the {item.name}.",
                AGED_WOOD,
            )
            engine._update_fov()
            return False

        # Displace whatever is currently in offhand (shield, another torch, etc.)
        if equipment:
            offhand_item = equipment.slots.get("offhand")
            if offhand_item is not None and offhand_item is not item:
                if getattr(offhand_item, "light_data", None):
                    # Another lit light source — extinguish it first
                    _deactivate_light(offhand_item, engine)
                    engine.log.add(f"The {offhand_item.name} goes out.", STONE_BLUE)
                else:
                    # Non-light item (shield, etc.) — simply remove it
                    engine.log.add(f"Thou removest {offhand_item.name}.", EARTH_BROWN)
                equipment.unequip("offhand")

        # Light it
        ld = item.light_data
        light = LightSource(
            radius  = ld.get("radius",  8),
            color   = tuple(ld.get("color", [255, 180, 60])),
            falloff = ld.get("falloff", 1.8),
            flicker = ld.get("flicker", True),
            active  = True,
        )
        light._item_id    = item.item_id
        light._item_ref   = item
        light._burn_turns = item.burn_turns or 600
        light._turns_used = item.turns_lit

        engine.player.light_source = light
        engine._update_fov()

        # Equip to off-hand slot
        if equipment:
            equipment.equip(item, "offhand")

        engine.log.add(
            f"You light the {item.name}.",
            RESONANCE_GOLD,
        )
        return False   # not consumed — torch remains until burned out

    def _use_grant_perk_point(self, item: "Item", engine: "Engine") -> bool:
        """Consumable that grants one perk point."""
        level_comp = getattr(engine.player, "level", None)
        if level_comp is None:
            return False
        level_comp.perk_points += 1
        engine.log.add("A point waits to be spent. Press K.", OLD_GOLD)
        return True   # consumed

    def _use_equip_toggle(self, item: "Item", engine: "Engine") -> bool:
        """Equip or unequip an item. Returns False (not consumed)."""
        equipment = getattr(engine.player, "equipment", None)
        if not equipment:
            return False

        item_def = engine.data.items.get(item.item_id, {})
        slot = item_def.get("slot")
        if not slot:
            engine.log.add("This cannot be equipped.", EARTH_BROWN)
            return False

        _TALISMAN_SLOTS = ("talisman_1", "talisman_2", "talisman_3")
        is_talisman = (item_def.get("category") == "talisman")

        if equipment.is_equipped(item):
            # Find the actual slot this item occupies (important for talismans)
            actual_slot = slot
            for s, occupant in equipment.slots.items():
                if occupant is item:
                    actual_slot = s
                    break
            equipment.unequip(actual_slot)
            _remove_armor_from_fighter(engine.player, item_def, engine.data)
            if actual_slot == "light":
                _deactivate_light(item, engine)
            engine.log.add(
                f"Thou removest {item.name}.",
                WORN_STONE,
            )
        else:
            if is_talisman:
                # Find first free talisman slot
                target_slot = None
                for ts in _TALISMAN_SLOTS:
                    if equipment.slots.get(ts) is None:
                        target_slot = ts
                        break
                if target_slot is None:
                    engine.log.add("No talisman slot is free.", EARTH_BROWN)
                    return False
                slot = target_slot

            # Equip — unequip whatever is currently in that slot first
            prev = equipment.slots.get(slot)
            if prev:
                prev_def = engine.data.items.get(prev.item_id, {})
                _remove_armor_from_fighter(engine.player, prev_def, engine.data)
                if slot == "light":
                    _deactivate_light(prev, engine)
                elif slot == "offhand" and prev.light_data:
                    # Displacing a torch from the off-hand — extinguish it first
                    _deactivate_light(prev, engine)
                    engine.log.add("The torch goes out.", STONE_BLUE)
                else:
                    engine.log.add(
                        f"Thou removest {prev.name}.",
                        EARTH_BROWN,
                    )
            equipment.equip(item, slot)
            _apply_armor_to_fighter(engine.player, item_def, engine.data)
            if slot == "light":
                _activate_light(item, engine)
            engine.log.add(
                f"Thou takest up {item.name}.",
                WORN_STONE,
            )

        return False  # not consumed

    def _use_reduce_resonance_exposure(self, item: "Item", engine: "Engine") -> bool:
        """Consume item, reduce resonance_exposure by reduce_exposure_amount."""
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        amount   = float(item_def.get("reduce_exposure_amount", 0.2))
        engine.resonance_exposure = max(0.0, engine.resonance_exposure - amount)
        msg = getattr(item, "drink_message", None) or "The resonance in you eases."
        engine.log.add(msg, RESONANCE_LOW)
        return True  # consumed

    def _use_apply_to_weapon(self, item: "Item", engine: "Engine") -> bool:
        """Coat the equipped weapon with temporary essence charges."""
        equip = getattr(engine.player, "equipment", None)
        if equip is None:
            engine.log.add("Nothing to apply it to.", WORN_STONE)
            return False
        weapon = equip.slots.get("weapon")
        if weapon is None:
            engine.log.add("No weapon equipped.", WORN_STONE)
            return False

        item_def  = engine.data.items.get(getattr(item, "item_id", ""), {})
        temp_ess  = item_def.get("temporary_essence", [])
        if not temp_ess:
            engine.log.add("The preparation has no effect on the blade.", WORN_STONE)
            return False

        # Merge onto weapon's temporary_essence list, replacing matching essences
        existing = getattr(weapon, "temporary_essence", [])
        for te in temp_ess:
            ess = te.get("essence", "")
            existing = [e for e in existing if e.get("essence") != ess]
            existing.append({
                "essence":        ess,
                "strength":       float(te.get("strength", 0.5)),
                "hits_remaining": int(te.get("hits", 5)),
            })
        weapon.temporary_essence = existing

        apply_msg = item_def.get("apply_message", f"The blade is coated.")
        engine.log.add(apply_msg, RESONANCE_MID)
        return True  # consumed


# ------------------------------------------------------------------ #
#  Equipment armor helpers (module-level, not ItemSystem methods)
# ------------------------------------------------------------------ #

def _sum_item_av(item_def: dict) -> int:
    """Sum all armor_value entries in an item's armor_layers list."""
    return sum(
        layer.get("armor_value", 0)
        for layer in item_def.get("armor_layers", [])
    )


def _recompute_effective_av(player, data) -> None:
    """
    Recompute fighter.effective_av from all currently equipped armor items.
    Called after any equip/unequip action.
    """
    fighter   = getattr(player, "fighter", None)
    equipment = getattr(player, "equipment", None)
    if not fighter or not equipment:
        return

    total = 0
    for slot, item in equipment.slots.items():
        if item is None:
            continue
        item_def = data.items.get(getattr(item, "item_id", ""), {})
        if item_def.get("category") == "armor":
            total += _sum_item_av(item_def)
    fighter.effective_av = total


# Legacy names kept so save_manager._restore_equipment can call _apply_armor_to_fighter.
# They now simply trigger a full recompute.
def _apply_armor_to_fighter(player, item_def: dict, data=None) -> None:
    """Equip path: recompute effective_av if data is available."""
    if data is not None:
        _recompute_effective_av(player, data)
    else:
        # Fallback: add the item's AV directly (used during save restore
        # where data is not passed through).
        fighter = getattr(player, "fighter", None)
        if fighter:
            fighter.effective_av += _sum_item_av(item_def)


def _remove_armor_from_fighter(player, item_def: dict, data=None) -> None:
    """Unequip path: recompute effective_av if data is available."""
    if data is not None:
        _recompute_effective_av(player, data)
    else:
        fighter = getattr(player, "fighter", None)
        if fighter:
            fighter.effective_av = max(0, fighter.effective_av - _sum_item_av(item_def))


def _activate_light(item, engine) -> None:
    """Activate a light-slot item's LightSource on the player."""
    from components.light_source import LightSource
    if not item.light_data:
        return
    ld = item.light_data
    light = LightSource(
        radius  = ld.get("radius",  8),
        color   = tuple(ld.get("color", [255, 180, 60])),
        falloff = ld.get("falloff", 1.8),
        flicker = ld.get("flicker", True),
        active  = True,
    )
    light._item_id    = item.item_id
    light._item_ref   = item
    light._burn_turns = item.burn_turns or 600
    light._turns_used = item.turns_lit
    engine.player.light_source = light
    engine._update_fov()


def _deactivate_light(item, engine) -> None:
    """Deactivate the player's light if it belongs to the given item."""
    current = getattr(engine.player, "light_source", None)
    if current and getattr(current, "_item_ref", None) is item:
        current.active = False
        engine._update_fov()