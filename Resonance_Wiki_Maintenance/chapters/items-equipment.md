# Items, equipment and preparations

For isolated learning, use [Start creating](#learning-path) and its complete GUIDE-1 examples. The older authoring recipes below describe intentional production content edits; do not install them merely to run a lesson.

An item definition supplies defaults; `ItemFactory` creates a physical instance; `ItemSystem` dispatches its `on_use` to an implemented Python handler. The item's route into play is a separate choice. Most manual changes belong under `roguelike/data/items/`.

## First tutorial: add a trail ration

This example adds ordinary food using existing art and the existing eating behavior. `owner_trail_ration` is a new tutorial ID, not shipped content.

### 1. Create the definition

Save this as `roguelike/data/items/consumables/owner_trail_ration.json`:

```json
{
  "id": "owner_trail_ration",
  "name": "Trail Ration",
  "description": "A compact ration wrapped for the road.",
  "tile": "food_item",
  "category": "consumable",
  "weight": 0.2,
  "stackable": true,
  "on_use": "eat",
  "nutrition": 300,
  "eat_message": "The ration is dry, but sustaining.",
  "keywords": [{"tag": "edible", "tier": 2}],
  "consumed_on_use": true
}
```

The food restores 300 hunger points with the current configured hunger maximum of 1000: a reduction of `0.3` in the internal hunger fraction. Values at or below `1.0` are treated as legacy fractions, so `nutrition: 1` means the full range, not one point. Use a value clearly in the intended unit convention.

### 2. Give it an acquisition route

Choose at least one route:

- Add `{"item_id": "owner_trail_ration", "weight": 20}` to the existing `items` array in `roguelike/data/loot_pools/storage_general.json`. This makes it eligible in newly populated containers that use that pool. Weight is relative; it is not a percentage or a guarantee.
- Place an item special in an authored building using `item_id: "owner_trail_ration"` and valid local coordinates. Follow the structure chapter's current special-record format and validation steps.
- Use the cooking recipe in the crafting chapter to create it from qualifying raw food.

Simply adding the file does not put the ration in the starting inventory or any existing container.

### 3. Verify the definition

From the repository root:

```powershell
& $ResonancePython -m json.tool roguelike/data/items/consumables/owner_trail_ration.json
& $ResonancePython -c "import sys; sys.path.insert(0, 'roguelike'); from engine.data_loader import DataLoader; from engine.item_factory import ItemFactory; d=DataLoader('roguelike/data'); i=ItemFactory(d).create('owner_trail_ration'); assert i is not None and i.on_use == 'eat' and i.nutrition == 300; print(i.name, i.weight, i.nutrition)"
```

Expect `Trail Ration`, `0.2`, `300` after the loader's ordinary startup messages. This proves loading and default creation. Then inspect the selected acquisition route in a new disposable game. Eat the ration with some hunger present; it should restore the intended amount and the inventory should lose that exact ration instance. The turn spent using it also advances needs, so a before/after display may differ slightly from the raw restoration amount.

## Common fields that are actually copied

| Field | Purpose and authoring rule |
|---|---|
| `id` | Unique stable definition key |
| `name`, `description` | Player-facing text |
| `tile` | Existing rendering tile ID; defaults to `generic_item` if absent |
| `weight` | Per-instance inventory weight; keep nonnegative |
| `stackable` | Supports UI grouping; current inventory still owns individual item objects |
| `on_use` | Name of a supported item handler, without the `_use_` prefix |
| `text_id` | Readable text definition ID when the item is a document |
| `nutrition`, `hydration` | Restoration; values `<=1` are fractions and `>1` are configured points |
| `heal_amount` | HP restored by `heal_minor` |
| `eat_message`, `drink_message` | Optional messages for those handlers |
| `keywords` | Array of `{"tag": "...", "tier": n}` for crafting and other specific consumers |
| `qualities` | Copied tool-quality data; use the shape of a working example and verify its consumer |
| `consumed_on_use` | False protects from automatic material selection; an explicit protected component choice can still consume it |
| `burn_turns` | Torch/lantern fuel default, with a working `equip_light` handler |
| `light` | Light configuration object copied into the item |
| `liquid`, `liquid_volume` | Saved liquid-instance data; does not by itself implement a new liquid action |

`consumed_on_use: false` does not make an edible item inexhaustible. Eating consumption follows the item's use-handler result. Retained crafting tools use the distinct `tools` role; do not assume all ingredient uses of a protected object retain it.

Do not infer behavior from every field present in a shipped file. Fresh held-light reach comes from `light_radius`, captured as `held_light: {version: 1, radius: N}`. The nested `light` object supplies visual properties, not authoritative reach. A decorative `sprite` field is not a substitute for confirming a working tile mapping.

## Equipment: use `slot`, not `equip_slot`

To create ordinary equippable gear, copy a working definition and retain `on_use: "equip_toggle"`, a real `slot`, and `consumed_on_use: false`. The currently declared slots are:

`weapon`, `offhand`, `armor_head`, `armor_torso`, `armor_arms`, `armor_legs`, `belt_1`, `belt_2`, `belt_3`, `light`, `talisman_1`, `talisman_2`, `talisman_3`, `satchel`.

A slot existing does not guarantee that every intended mechanic for its item category is implemented. `ItemSystem` provides special selection behavior for talismans, and lit torches/lanterns use the **offhand** slot through their own handler. Equipping a shield displaces an offhand light and vice versa.

For armour, `roguelike/data/items/armor/leather_jack.json` is a working example:

```json
"category": "armor",
"slot": "armor_torso",
"armor_layers": [
  {"name": "leather jack", "coverage": 1.0, "armor_value": 2, "material": "leather"}
],
"on_use": "equip_toggle"
```

These are fields within the existing item, not a complete standalone item file. Current armour recomputation sums each equipped armour item's `armor_layers[].armor_value` into a single effective armour value, plus applicable temporary/perk bonuses. `coverage` and material prose do not turn this into a per-location armour simulation. The older `av` field in historical examples is not the current summation key.

## Light sources

Use `roguelike/data/items/tools/tallow_torch.json` or `oil_lantern.json`. A light needs `on_use: "equip_light"`, `burn_turns`, top-level `light_radius` for mechanical reach, and a nested `light` object for visuals. The following excerpt supplies visuals only; its radius is not authoritative reach:

```json
"light": {
  "radius": 8,
  "color": [255, 180, 60],
  "falloff": 1.8,
  "flicker": true
}
```

Toggling the same light off releases its offhand slot. Fuel use and the link to the exact item instance are stateful; verify that equipping, dropping, transferring and loading do not leave a detached light behind after a related implementation change.

**Current light ownership:** the exact active offhand object, its captured reach, fuel and visual data survive save/load. Active fueled held lights can supply their declared `provides_burning` tier. Passive processing still requires stationary fire; carrying a torch does not replace that requirement. See [L08](#L08) and the [system atlas](#system-atlas) for shared illumination and [L12](#L12) for the vessel state-owner comparison.

## Existing item-use behaviors

| Handler | Working template or role |
|---|---|
| `eat`, `drink`, `heal_minor` | Nutrition, hydration or healing |
| `read` | Opens the definition named by `text_id` |
| `equip_toggle`, `equip_light` | Ordinary equipment or light-specific ownership |
| `grant_perk_point` | Grants one perk point |
| `reduce_resonance_exposure` | Uses `reduce_exposure_amount` |
| `apply_to_weapon` | Applies `temporary_essence` entries to the equipped weapon |
| `learn_deep_word` | Existing biome/category-directed word-learning behavior |
| `apply_to_armor` | Adds temporary armour protection to equipped torso armour |
| `consume_wight_concentrate` | Opens the existing confirmation and concentrate effect path |
| `apply_stalker_unguent` | Applies the implemented movement effect |
| `throw_musk_pellet` | Opens the existing throw-targeting path |

An unknown handler produces an unknown-effect diagnostic. It does not execute arbitrary JSON, and renaming the handler to a new effect name is an implementation task.

## Tune an existing preparation

| Template | Active tuning fields | Unit |
|---|---|---|
| `consumables/bile_coating.json` | `temporary_essence[].strength`, `.hits` | Essence strength; successful weapon contacts |
| `consumables/marrow_seal.json` | `armor_bonus`, `armor_hits` | Added torso armour; incoming contacts protected |
| `consumables/stalker_unguent.json` | `speed_bonus`, `duration_turns` | Movement bonus; player turns |
| `consumables/wight_concentrate.json` | `true_sight_turns`, `resonance_add`, `corruption_add` | Turns and immediate resource changes |
| `consumables/musk_pellet.json` | `zone_radius`, `zone_turns` | Tiles and zone lifetime |

A weapon coating spends no charge on a miss or dodge, but armour fully deflecting a contact still spends a charge. The last armour-seal charge protects its triggering contact. Reapplying the same essence replaces its coating entry instead of adding a second identical one. Player-duration effects include the applying action; do not equate hit counters with turn durations.

After changing a preparation, test a newly used instance. Already active effects retain saved remaining counters.

## Source bindings

- [Item creation defaults](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/item_factory.py)
- [Item-use and armour consumers](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/engine/item_system.py)
- [Equipment slots and identity](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/components/equipment.py)
- [Inventory ownership and weight](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/components/inventory.py)
- [Crafting ambient source lookup](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/rendering/craft_screen.py)
- [Food template](https://github.com/dgobi/ResonanceRoguelike/blob/c166ec650b98156d53b8ea72e715c028d27db905/roguelike/data/items/consumables/crow_jerky.json)
