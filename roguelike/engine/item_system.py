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
        self.last_use_committed = False
        inv = getattr(engine.player, "inventory", None)
        if inv is None or not inv.contains(item):
            if item.on_use == "heal_minor":
                engine.log.add("That treatment is no longer in your pack.", WORN_STONE)
            return False  # stale modal selection cannot apply effects or equip
        from entities.item import repair_selected_equipment_use, use_capability
        repair_selected_equipment_use(item)
        effect = use_capability(item)
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

        consumed = handler(item, engine)
        self.last_use_committed = self.last_use_committed or bool(consumed)
        return consumed

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
        # Check item definition for render_mode — deep_tongue items use ziggurat panel
        self.last_use_committed = True
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        item_render_mode = item_def.get("render_mode", "")
        if item_render_mode == "deep_tongue":
            engine.text_reader.open_text(
                text_def,
                panel_style="ziggurat",
                text_align="center",
                line_spacing_bonus=6,
                panel_size="inscription",
            )
        else:
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

        # Exchange first so the old vessel's weight is released before checking
        # the empty form. A failed factory/capacity check has no thirst effect.
        empty_id = engine.data.items.get(item.item_id, {}).get("empty_form")
        if empty_id:
            from engine.item_transfers import exchange
            empty = engine.item_factory.create(empty_id)
            if empty is None or not exchange(engine, [item], [empty]):
                return False

        raw = item.hydration if item.hydration is not None else 400
        self.last_use_committed = True
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

        return not bool(empty_id)  # replacement already committed above

    def _use_heal_minor(self, item: "Item", engine: "Engine") -> bool:
        fighter = getattr(engine.player, "fighter", None)
        if not fighter or fighter.is_dead or fighter.hp <= 0:
            engine.log.add("Only the living can use this treatment.", WORN_STONE)
            return False
        if fighter.hp >= fighter.max_hp:
            engine.log.add("Your wounds are already closed. The treatment remains unused.", LIFE_GREEN)
            return False

        amount = item.heal_amount or 3
        actual = fighter.heal(amount)

        engine.log.add(
            f"You take the {item.name}. You recover {actual} HP.",
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

        self.last_use_committed = True

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
            _recompute_effective_av(engine.player, engine.data)

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

        self.last_use_committed = True
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

    def _use_learn_deep_word(self, item: "Item", engine: "Engine") -> bool:
        """Consume tincture to learn a random tier-1 deep tongue word."""
        lang = getattr(engine.player, "language", None)
        if lang is None:
            engine.log.add("Nothing stirs.", WORN_STONE)
            return False
        from engine.language_system import learn_from_category
        # Use waystone category pool for the current biome
        chunk = engine.world_map.get(engine.world_x, engine.world_y) if engine.world_map else None
        biome_id = getattr(chunk, "biome_id", "forest") if chunk else "forest"
        cats = engine._WAYSTONE_CATEGORIES.get(biome_id, engine._WAYSTONE_DEFAULT)
        cat = engine.rng.choice(cats)
        ok, wid = learn_from_category(cat, 1, "text", lang,
                                       engine.data.deep_tongue, engine.rng)
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        msg = item_def.get("use_message", "A word rises from the marrow. It was always there.")
        if ok:
            wdef = engine.data.deep_tongue.get(wid, {})
            deep = wdef.get("deep", wid)
            common = wdef.get("common", "")
            lang.translation_events[wid] = engine.world_time.turn
            engine.log.add(msg, DEEP_TONGUE_COLOUR)
            engine.log.add(
                f"  [{deep}]: {common}.",
                DEEP_TONGUE_COLOUR,
            )
            engine._maybe_show_lexicon_hint()
        else:
            engine.log.add("The liquid is inert. Nothing remains to learn from it.", WORN_STONE)
        return True  # consumed

    def _use_apply_to_armor(self, item: "Item", engine: "Engine") -> bool:
        """Apply a temporary AV bonus to equipped torso armour."""
        equip = getattr(engine.player, "equipment", None)
        if equip is None:
            engine.log.add("Nothing to apply it to.", WORN_STONE)
            return False
        torso = equip.slots.get("armor_torso")
        if torso is None:
            engine.log.add("No armour worn.", WORN_STONE)
            return False
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        bonus = item_def.get("armor_bonus", 1)
        hits = item_def.get("armor_hits", 20)
        # Store temporary armor bonus on the armor item
        torso._temp_av_bonus = max(getattr(torso, "_temp_av_bonus", 0), bonus)
        torso._temp_av_hits = max(getattr(torso, "_temp_av_hits", 0), hits)
        _recompute_effective_av(engine.player, engine.data)
        msg = item_def.get("apply_message", "The armour hardens. Briefly.")
        engine.log.add(msg, OLD_GOLD)
        return True  # consumed

    def _use_consume_wight_concentrate(self, item: "Item", engine: "Engine") -> bool:
        """Consume wight concentrate: resonance, corruption, temporary true_sight."""
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        # Warning prompt
        warning = item_def.get("warning_prompt", "This will change you.")
        engine.log.add(f"{warning} [Y/N]", MSG_DANGER)
        engine._pending_consume = {
            "item": item,
            "item_def": item_def,
        }
        engine.inventory_screen.open = False
        return False  # not consumed yet — awaiting confirmation

    def _use_apply_stalker_unguent(self, item: "Item", engine: "Engine") -> bool:
        """Apply speed bonus to player for N turns."""
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        bonus = item_def.get("speed_bonus", 0.2)
        duration = item_def.get("duration_turns", 15)
        engine.player_speed_bonus = bonus
        engine.player_speed_bonus_turns = duration
        msg = item_def.get("use_message", "The unguent sinks in. Something quickens.")
        engine.log.add(msg, LIFE_GREEN)
        return True  # consumed

    def _use_throw_musk_pellet(self, item: "Item", engine: "Engine") -> bool:
        return self._begin_throw(item, engine, 'musk')

    def _use_throw_flint_shard(self, item: "Item", engine: "Engine") -> bool:
        return self._begin_throw(item, engine, 'flint')

    def _begin_throw(self, item: "Item", engine: "Engine", kind: str) -> bool:
        """Owned map-bound cursor; only confirmation commits item/time/effects."""
        item_def = engine.data.items.get(getattr(item, "item_id", ""), {})
        engine._pending_throw = {
            "item": item,
            "item_def": item_def,
            "kind": kind,
        }
        from engine.engine import GameMode
        engine._pending_throw['map'] = engine.local_map
        engine.inventory_screen.open = False
        engine.mode = GameMode.PLACEMENT_CURSOR
        engine._placement_mode = 'throw'
        engine._placement_cursor_x = engine.player.x
        engine._placement_cursor_y = max(0, engine.player.y - 1)
        # Activate placement cursor for throw targeting
        engine.log.add(f"Throw one {item.name}: choose a target tile. ESC keeps it.", UI_TEXT_MID)
        return False  # not consumed yet — awaiting target selection


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
            if getattr(item, "_temp_av_hits", 0) > 0:
                total += getattr(item, "_temp_av_bonus", 0)
    fighter.effective_av = total + getattr(fighter, "attuned_av_bonus", 0)


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
