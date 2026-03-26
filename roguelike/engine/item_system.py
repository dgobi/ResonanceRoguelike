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
        return False   # not consumed

    def _use_eat(self, item: "Item", engine: "Engine") -> bool:
        needs = getattr(engine.player, "needs", None)
        if not needs:
            return False

        nutrition = item.nutrition or 0.3
        needs.eat(nutrition)
        engine.log.add(
            f"You eat the {item.name}.",
            AGED_WOOD,
        )

        if needs.hunger < 0.15:
            engine.log.add("You are sated.", AGED_WOOD)
        return True   # consumed

    def _use_drink(self, item: "Item", engine: "Engine") -> bool:
        needs = getattr(engine.player, "needs", None)
        if not needs:
            return False

        hydration = item.hydration or 0.3
        needs.drink(hydration)
        engine.log.add(
            f"You drink from the {item.name}.",
            CLEAR_WATER,
        )

        if needs.thirst < 0.15:
            engine.log.add("Your thirst is slaked.", CLEAR_WATER)

        # Empty the flask
        item.liquid        = None
        item.liquid_volume = 0.0
        item.hydration     = None
        item.on_use        = None
        item.name          = f"empty {item.name}"
        return False   # not consumed — flask remains as empty container

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

        # Check off-hand availability before lighting
        if equipment:
            offhand_item = equipment.slots.get("offhand")
            if offhand_item is not None and offhand_item is not item:
                engine.log.add("Off hand is full.", STONE_BLUE)
                return False

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

        if equipment.is_equipped(item):
            # Unequip
            equipment.unequip(slot)
            _remove_armor_from_fighter(engine.player, item_def)
            if slot == "light":
                _deactivate_light(item, engine)
            engine.log.add(
                f"Thou removest {item.name}.",
                WORN_STONE,
            )
        else:
            # Equip — unequip whatever is currently in that slot first
            prev = equipment.slots.get(slot)
            if prev:
                prev_def = engine.data.items.get(prev.item_id, {})
                _remove_armor_from_fighter(engine.player, prev_def)
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
            _apply_armor_to_fighter(engine.player, item_def)
            if slot == "light":
                _activate_light(item, engine)
            engine.log.add(
                f"Thou takest up {item.name}.",
                WORN_STONE,
            )

        return False  # not consumed


# ------------------------------------------------------------------ #
#  Equipment armor helpers (module-level, not ItemSystem methods)
# ------------------------------------------------------------------ #

SLOT_TO_LOCATION: dict[str, list[str]] = {
    "armor_head":  ["head"],
    "armor_torso": ["torso"],
    "armor_arms":  ["right_arm", "left_arm", "arms"],
    "armor_legs":  ["right_leg", "left_leg", "legs"],
    # belt_1/belt_2/belt_3 and light are intentionally absent — they carry no armor layers
}


def _apply_armor_to_fighter(player, item_def: dict) -> None:
    """Prepend armor layers to player fighter for relevant locations."""
    fighter = getattr(player, "fighter", None)
    if not fighter:
        return
    slot   = item_def.get("slot", "")
    layers = item_def.get("armor_layers", [])
    if not layers:
        return
    layer_names = {l["name"] for l in layers}
    for loc in SLOT_TO_LOCATION.get(slot, []):
        if loc not in fighter.armor_layers:
            continue
        # Don't add if already present — prevents doubling on repeated load
        existing_names = {l["name"] for l in fighter.armor_layers[loc]}
        if layer_names & existing_names:
            continue
        # Prepend — equipment goes outermost
        fighter.armor_layers[loc] = list(layers) + fighter.armor_layers[loc]


def _remove_armor_from_fighter(player, item_def: dict) -> None:
    """Remove armor layers added by an item from player fighter."""
    fighter = getattr(player, "fighter", None)
    if not fighter:
        return
    slot        = item_def.get("slot", "")
    layers      = item_def.get("armor_layers", [])
    if not layers:
        return
    layer_names = {l["name"] for l in layers}
    for loc in SLOT_TO_LOCATION.get(slot, []):
        if loc in fighter.armor_layers:
            fighter.armor_layers[loc] = [
                l for l in fighter.armor_layers[loc]
                if l["name"] not in layer_names
            ]


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