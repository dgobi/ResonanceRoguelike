# Crafting, ingredients and processing

Recipes live in `roguelike/data/recipes/`. The crafting screen reads them automatically through `DataLoader.recipes`; a new recipe does not need a central registration list. It still needs valid ingredients, an implemented result route and an available `known` state.

## Understand the three result routes

| Recipe type | Fields | Result |
|---|---|---|
| Immediate item | `result_item`, no passive processing | Creates the result through the inventory transaction |
| Placed object | `places_in_world: true`, `result_tile` | Enters the existing placement confirmation route |
| Timed processing | `passive_processing: true`, `result_item`, processing fields | Places a job that later produces the result on its owning map |

Use shipped templates: `bile_coating.json` for an immediate item, `campfire.json` for world placement, `cook_meat.json` or `dry_bitter_herb.json` for timed work.

## Tutorial: cook the trail ration

This tutorial assumes the `owner_trail_ration` item from the items chapter exists. Save the following as `roguelike/data/recipes/owner_cook_trail_ration.json`:

```json
{
  "id": "owner_cook_trail_ration",
  "name": "cook a trail ration",
  "category": "cooking",
  "description": "Cook a piece of suitable raw food for the road.",
  "known": true,
  "requires_single_item": {
    "tags": [
      {"tag": "edible", "min_tier": 1},
      {"tag": "vital", "min_tier": 1}
    ],
    "max_quantity": 1
  },
  "requires_ambient": [{"tag": "burning", "min_tier": 2}],
  "result_item": "owner_trail_ration",
  "passive_processing": true,
  "processing_turns": 8,
  "processing_source": "cooking",
  "processing_decor": "cooking_meat",
  "placement_message": "Set the ration on the fire."
}
```

The recipe accepts one instance carrying **both** `edible` tier one and `vital` tier one. `raw_meat_common` is a shipped qualifying item. It is not an exact-ID recipe: any other item satisfying both tags is eligible. If the intended ingredients need a narrower class, add a deliberate keyword to the relevant items and require it; test all intended inclusions and exclusions.

Restart, obtain qualifying raw food, stand near a lit campfire, open the craft screen with `C`, select the recipe and confirm a legal cooking location. Cooking placement requires the lit fire itself. Merely being near the fire supplies the ambient condition but does not make every nearby tile a cooking target.

On successful placement, the exact input is consumed and a job is created. Inspect the completed result after the relevant turns. Also test cancellation: leaving placement before confirmation should not spend the ingredient. If you change processing or ownership code, test travel and save/load as well, not just completion while standing beside the fire.

## Ingredient semantics

### Separate component slots

```json
"components": [
  {"tag": "caustic", "min_tier": 1, "quantity": 1},
  {"tag": "viscous", "min_tier": 1, "quantity": 1}
]
```

Each physical slot needs a distinct item instance. A crow-bile sac carrying both tags cannot pay for both slots at once. Two qualifying sacs can. The current matching algorithm can move a multitag item to another requirement so it does not greedily consume the only item able to satisfy a later requirement.

### All tags on one item

Use `requires_single_item.tags` when one item must meet several tag requirements simultaneously. In the current implementation, the object's `max_quantity` is used as the number of physical slots to allocate; it is not an optional “up to” ceiling. Keep it `1` for the standard single-item recipes.

### Reusable tools

`consumed_on_use: false` on an item makes it reusable as a crafting input. The keyword, tier and exact-instance matching rules still apply. The item being called a “tool” is not what prevents consumption.

Reusable inventory items also provide their keywords as ambient sources. This is why a reusable `clay_pot` can satisfy a `vessel` ambient requirement. Ambient conditions do not consume a physical item. A component requirement may use an ambient source for a shortfall, but the planner prefers a complete solution using the maximum available physical allocation; if you intend an exclusively nonconsuming condition, express it in `requires_ambient`.

## Ambient sources in this revision

| Source | What the craft screen supplies |
|---|---|
| `campfire_lit` decor within three tiles, including diagonals | `burning`, tier two |
| Reusable inventory item | Its keyword tag/tier pairs |
| Item in `equipment.slots['light']` with `provides_burning` | Burning tier from that declaration |
| Normally lit torch in `offhand` | **Not found by that light-slot lookup** |

The last row is a current implementation gap. Both the item-light code and the craft screen were checked. Use a campfire when verifying heat-dependent recipes. A `provides_burning` flag on a normal offhand torch does not bridge the mismatch.

The world ambient check is currently a specific nearby-campfire rule, not a generic heating-workstation registry. A new decor object with a plausible `burning` field does not automatically become a source.

## Processing fields

| Field | Meaning |
|---|---|
| `processing_turns` | Initial remaining turn count for newly started jobs |
| `processing_source: "cooking"` | Selects the lit-fire placement path |
| Other processing-source values | Currently follow the drying-placement branch; a new string does not implement a new workstation |
| `processing_decor` | Existing decor to display during the job |
| `result_item` | Existing item definition to create on completion |
| `placement_message` | Player prompt |

Current processing advances on the active and hot cached maps through the implemented per-turn ownership path. Cold stored maps do not gain a universal elapsed-time catch-up simulation. Existing jobs restore their saved remaining state. Changing a recipe's `processing_turns` affects new jobs; it does not rewrite every saved job.

Do not confuse a job's output with inventory capacity: processing produces a floor object on the owning map, while immediate crafting uses its inventory exchange path.

## Visibility and prerequisites

The screen excludes recipes marked `_deprecated`. It groups known category names `campfire`, `cooking`, `wildcrafting`, and `alchemy`, with other categories in a fallback group. `known: false` prevents crafting through the current screen; it does not automatically create a research/unlock system.

The final commit checks that selected items still belong to the inventory and revalidates the plan. Pending placement does not persist a material reservation: cancellation/load discards the pending plan rather than consuming and refunding items.

## Verify and troubleshoot

Parse the recipe and result item. Inspect their IDs and keywords. A valid result ID with an unknown tag can leave a recipe permanently unsatisfied. A valid item definition without a result route is not enough.

```powershell
& $ResonancePython -m json.tool roguelike/data/recipes/owner_cook_trail_ration.json
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike
```

The focused suite contains specific crafting, action-route and effect-persistence cases. Your new recipe still needs a direct positive check, a missing-input check, an ambient-condition check, and a cancellation check when it uses placement.

| Symptom | Likely cause to inspect |
|---|---|
| Recipe absent | Malformed/duplicate ID; stale process; `_deprecated`; category collapsed |
| Recipe present but locked | `known: false`; required tag/tier; distinct-instance requirement; ambient source |
| Torch lit but heat requirement fails | Current `light`/`offhand` mismatch |
| Placement rejected near a campfire | Cooking must target the lit-fire tile |
| Output never appears in inventory | Processing results are placed on the owning map |
| Old job duration unchanged | The saved job owns its remaining turns |

## Source bindings

- [Matching and exact-instance commit](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/crafting.py)
- [Craft screen, ambient sources and result routing](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/rendering/craft_screen.py)
- [Placement and processing completion](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/engine/engine.py)
- [Cooking template](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/recipes/cook_meat.json)
- [Single-item template](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/data/recipes/dry_bitter_herb.json)
- [Current B2 state reconstruction record](https://github.com/dgobi/ResonanceRoguelike/blob/24c3053e9a138d18677c1872688fdd1f09c8a206/roguelike/docs/owner/B2_STATE.md)
