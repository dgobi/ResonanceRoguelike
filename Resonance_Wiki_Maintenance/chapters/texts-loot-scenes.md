# Texts, loot, containers and small scenes

These systems share IDs, but use different formats and consumers. Keep three things separate: **the physical item**, **the readable text**, and **the rule that places it**. The item may be `letter`, the text may be `letter_a`, and the placement may come from a container, a structure special, or a procedural text table.

## Tutorial: add a readable letter

### 1. Write the text definition

Create `roguelike/data/texts/world/letters/owner_road_letter.json`:

```json
{
  "id": "owner_road_letter",
  "title": "A Note at the Roadside",
  "type": "letter",
  "condition": "worn",
  "reads_as": "single",
  "lacunae": false,
  "pages": [
    {
      "text": "The road is still passable. Follow the stones until the old wall.\n\nI left a little food where we agreed.",
      "damaged": false
    }
  ]
}
```

Use `pages[].text`; the historical example built from `pages[].lines` is not the current reader's ordinary format. Keep pages reasonably short. The current panel measures page zero when sizing the reader, and long-page clipping is a known limitation; adding extra prose does not create a scrolling text area automatically.

### 2. Add the item-type mapping

In the existing object in `roguelike/data/texts/text_item_map.json`, add:

```json
"owner_road_letter": "letter"
```

This is an entry inside the existing object, not a complete file. Keep commas valid. `letter` already exists as a physical item with `on_use: "read"`. The mapping is used by routes that request text mapping; it is not a universal replacement of every generated text item.

### 3. Choose a placement route

For authored structures, place an item special with `item_id: "letter"` and `text_id: "owner_road_letter"` at a valid accessible coordinate, using the structure chapter's complete record format. This is the most explicit connection between the physical item and its text.

For procedural common found texts, append this entry to `roguelike/data/loot/world_texts_common.json`:

```json
{"type": "text", "text_id": "owner_road_letter", "weight": 5}
```

That table is used by current cave, flooded-ruin and cellar text placement, as well as a fallback for some other submap types. It does not populate the authored laboratory. The BSP found-text route currently creates a `lab_note` physical item and assigns the selected `text_id`; the reader still opens the correct letter text. A text mapping entry does not change that hardcoded submap item choice.

### 4. Verify the content and route

Parse the edited files. Check that the text ID exists, the physical item exists and has `on_use: "read"`, and the authored placement or table entry references the intended ID. A new generated room is required for a changed procedural placement table; already generated rooms are not repopulated.

In the test game, pick up and read the item. Check title, paragraph breaks, all pages, closing controls and any damaged/Deep Tongue presentation. Changing the text body can affect an existing saved document because reading looks up its current definition by `text_id`.

## Text presentation fields and limits

| Field | Current authoring use |
|---|---|
| `title` | Heading; empty/null suppresses it |
| `condition` | Presentation such as pristine, worn, damaged or fragmentary; current tints also include burned |
| `pages[].text` | Actual ordinary page body |
| `[DAMAGED]` inside page text | Creates a damaged span rendered as corrupt glyphs unless stored recovery exists |
| `[REDACTED]` inside page text | Creates a redacted span |
| `pages[].trailing` | Shows the text-ends-here indicator |
| Top-level `deep_tongue` | Read by the current renderer for Deep Tongue page treatment |
| `teach_words` | Explicit learning configuration, separate from merely displaying a word |
| `render_mode: "alphabet"` | Existing phoneme-reference presentation |

Several shipped files include `pages[].deep_tongue`, `damaged`, `reads_as` or `lacunae` metadata. Do not assume each flag independently changes rendering: the current renderer uses the top-level Deep Tongue flag and textual damage markers for the described behavior. The debug loader also checks the first page's Deep Tongue flag for validation, which is a different consumer.

The recovery storage API exists, but an `effect_type`/`effect_params` declaration on a perk is not a generic engine that reconstructs damaged text. Do not promise automatic recovery based only on the historical perk description.

## Deep Tongue authoring

The current lexicon is a `version` object containing a `words` array, not the short historical list of `deep`/`translation` pairs. Entries use `id`, `deep`, `common`, `concept`, `category`, `tier`, `glyph_seed`, and `learn_sources`. The loader keys by `id`, falling back to `deep`. Existing words generally use matching ID and spelling; retain that convention for straightforward token recognition.

`common` is the current translation field. `learn_sources` names the permitted routes, such as `waystone`, `text` and `corruption`. General automatic selection excludes tier-three-or-higher words; waystone selection also excludes the `ominous` category. Explicit corruption-threshold learning has its own tier-three route.

For a text that teaches a basic category word, the supported shape is:

```json
"teach_words": {"categories": ["legacy"], "tier": 1}
```

The existing `learn_from_text` function uses the **first category** and teaches one word on the first eligible read, provided a suitable unknown word exists. It can fall back to another source-eligible unknown word if the requested category/tier pool is exhausted. An arbitrary `count` field does not make it teach several words. The item's reading route records `taught_texts`, preventing repeat farming from the same text ID.

Ordinary display of an unfamiliar word does not automatically teach it. Learning, glyph rendering, translation and damaged-span recovery are distinct paths. Validate authored Deep Tongue tokens against the lexicon and test the correct learning source with a fresh language state.

## Two incompatible loot formats

### Container pools: `data/loot_pools/`

```json
{
  "id": "owner_road_supplies",
  "roll_count": [1, 2],
  "items": [
    {"item_id": "crow_jerky", "weight": 3},
    {"item_id": "flint_shard", "weight": 1}
  ]
}
```

This complete new pool uses shipped item IDs. Save it under `roguelike/data/loot_pools/owner_road_supplies.json` and reference it in a container special's `loot_pools` array. It rolls one or two entries **without replacement within that pool**, capped by the number of entries. The weight controls the relative chance of selection. This format does not implement arbitrary `quantity`, nested-table or `text_id` fields on each row.

The roller constructs items from their definitions. If a container must hold a specific document, a physical item definition with a fixed `text_id` is one supported building block; do not expect a `text_id` added to the pool row to be copied by `roll_pool`.

### Loot tables: `data/loot/`

```json
{
  "id": "owner_simple_supplies",
  "rolls": 1,
  "entries": [
    {"item": "crow_jerky", "weight": 3},
    {"item": "flint_shard", "weight": 1}
  ]
}
```

The general `LootResolver` supports `item`, nested `table`, and (through `resolve_with_texts`) `type: "text"` plus `text_id`. Repeated rolls use weighted selection with replacement. It stops nested recursion beyond depth five. A table must be called by an active consumer; creating this tutorial file alone does not register it with a particular dungeon.

Some generators read selected table entries directly rather than using `LootResolver`. The found-text scatterer, for example, selects one text entry per selected room and does not use the table's `rolls` count as a room-count control. Always identify the caller before tuning a table field.

## Containers are functional objects

A container special identifies its decor and one or more pool IDs. Population validates the referenced definitions, rolls contents once and publishes them into the map's container state. Opening a container displays that stored state; browsing it does not reroll loot. A decorative crate without a registered container state is not equivalent to a fully populated container.

Test opening, taking one item, rejected transfers when full, taking remaining items, the empty state and save/reload when changing container behavior. Pool balance changes should be observed in newly generated containers.

## Small environmental scenes

`roguelike/data/scenes.json` is a top-level object keyed by scene ID. Its current scenes are small sets of floor objects placed at one anchor. For example, `interrupted_meal` places dried provisions and a water skin.

To add a scene, create a new object entry with a description and `floor_objects` array of `{"item_id": "..."}` entries, then reference its key through a supported structure scene special. The current population consumer creates those items at the same anchor. Scene prose does not instantiate surrounding furniture, actors, quests, offsets or scripting; author those through their actual supported routes.

`body` and `stele` special records have explicit deferred behavior in current scene population. Do not use the existence of those type names as evidence of a complete arbitrary body/inscription object system; consult the structure chapter for the route-specific boundary.

## Source bindings

- [Text reader and damage-marker parser](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/text_reader.py)
- [Read action and one-time teaching](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/item_system.py)
- [Language selection and validation](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/language_system.py)
- [Found-text placement](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/generation/local_gen.py)
- [General loot resolver](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/loot_table.py)
- [Container pool roller](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/loot_roller.py)
- [Scene population and deferred record handling](https://github.com/dgobi/ResonanceRoguelike/blob/67263f03ec02f44857a707cdbba772d1481787a1/roguelike/engine/scene_generation.py)
