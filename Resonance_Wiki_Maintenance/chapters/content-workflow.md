# The content editing workflow

Most everyday authoring begins in `roguelike/data/`. The working route is **definition → loader → runtime consumer → acquisition or placement → a fresh instance → verification**. Creating a JSON file completes only the definition step. For example, a new food item can load correctly while remaining absent from every loot pool, recipe and authored building.

This chapter and its linked recipes describe commit `4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`. Paths in this chapter start at the repository root. The original manuals remain useful for design history, but some examples in them use older field names.

## Choose the right edit

| Goal | Begin here | What connects it to play |
|---|---|---|
| Change a weapon's damage | `roguelike/data/items/weapons/` | Equipped weapon definition is read during attacks |
| Add food, medicine, a tool or equipment | `roguelike/data/items/` | Loot, recipe result, authored item special or code-controlled starting inventory |
| Make a creature tougher | `roguelike/data/entities/creatures/` | A newly spawned creature receives factory defaults |
| Change wilderness population | `roguelike/data/zones/` | The generated chunk must actually use that zone |
| Change town population | `roguelike/generation/town_gen.py` | Current town district tables are Python constants |
| Add a crafting recipe | `roguelike/data/recipes/` | Craft screen discovers nondeprecated recipes; `known` and ingredients determine use |
| Change container contents | `roguelike/data/loot_pools/` | A container special names the pool through `loot_pools` |
| Change random floor loot/text | `roguelike/data/loot/` | An active generator must call that table |
| Add a readable letter | `roguelike/data/texts/` | A readable item has the text's `text_id`; a placement or loot route creates it |
| Add a language word | `roguelike/data/deep_tongue.json` | Text, waystone or corruption learning pools must allow it |
| Tune hunger and thirst | `roguelike/data/survival.json` | Needs configuration and the engine's per-turn update |
| Change an implemented perk's price | `roguelike/data/perks/` | Perk screen reads its `cost` |
| Invent a new effect, AI, interaction or progression rule | The relevant Python consumer | JSON cannot create new behavior by naming it |

## Before the first edit

1. Work in the current production checkout on `main`. Check `git status --short` and `git branch --show-current` so you know whether unrelated work is already present.
2. Make a named Git checkpoint for a coherent change. Stage only the files involved. The wiki does not require editing or replacing historical evidence files.
3. Select a shipped example that already does the closest working thing. Prefer the current recipes in this wiki over schematic examples in historical documents.
4. Identify both its definition ID and the places referencing that ID. Search with your editor's “find in files” or `rg`.
5. Decide how you will obtain a newly created instance. For structural/generation changes, use a new disposable world. A saved actor or item may retain old instance values.

Use strict JSON: double quotes, no comments and no trailing commas. Fields beginning with an underscore can be useful explanatory notes when a consumer ignores them, but they are still ordinary JSON fields; they do not grant a new capability.

## IDs, names and filenames

`DataLoader._load_dir` recursively loads JSON under items, entities, zones, recipes, texts, perks, bodies, biomes, loot and loot pools. A file can contain one object or an array of objects. The registry key is the object's **`id`**, not its filename. `texts/text_item_map.json` is specially excluded from the text-definition scan and loaded as a mapping instead.

Use stable, unique IDs such as `owner_trail_ration`. Keep a matching filename for readability. Changing the displayed `name` is different from renaming the ID: saved objects, recipes, loot and text links may retain the ID. Rename or remove an ID only as a deliberate migration task.

The ordinary recursive loader does not reject duplicate IDs; a later discovered definition overwrites an earlier one. A successful startup is therefore insufficient evidence of uniqueness. This limitation does not describe the stricter structure catalog, which has its own validation contract.

The default loader caches data for the lifetime of the process. Restart after an edit. The game also contains direct-file readers and generation/module caches, so a blanket “all changes hot reload” rule would be incorrect.

## Four kinds of verification

| Check | What it establishes | What it does not establish |
|---|---|---|
| JSON parsing | The syntax is valid | ID uniqueness, references, effect support |
| Definition/factory check | The selected ID loads and creates an item/actor with expected defaults | It is placed in the world or behaves correctly in every interaction |
| Focused behavior check | The exercised action, transfer, effect or recipe follows its contract | Visual quality or broad balance |
| Fresh-world inspection | The actual content appears and can be reached/used in context | Unexercised save or edge-case behavior |

From the repository root, using the configured game interpreter:

```powershell
& $ResonancePython -m json.tool roguelike/data/items/consumables/crow_jerky.json
git diff -- roguelike/data/items/consumables/crow_jerky.json
```

For supported runtime regression checks, the repository provides:

```powershell
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike
```

That is a substantial focused suite, including generation tests; it is not a new-item discovery tool. A passing suite does not automatically verify an arbitrary definition you just added. Add an appropriate bounded probe or exercise the authored route as well. The full established gate is documented in the verification chapter.

## Why your edit may not appear

| Symptom | First checks |
|---|---|
| New file seems ignored | Correct directory? Valid JSON? Unique `id`? Restarted the process? |
| Loaded ID never appears | Is there an actual acquisition/spawn/placement reference? Is that route active in this world? |
| Changed number has no effect | Is the field consumed by current code? Is this an existing saved instance? |
| New recipe appears but cannot be made | Correct tags/tiers and distinct ingredient instances? Ambient conditions actually supplied? `known: true`? |
| Text shows an unexpected physical object | Distinguish the readable item's `item_id` from the document's `text_id`, and check the route's mapping behavior |
| A previously generated container still has old contents | Container contents were rolled once and persisted; editing its pool does not reroll it |
| New creature has ordinary wandering behavior | `ai_type` must name one of the four implemented classes; special abilities may depend on exact creature IDs |
| Game uses an older copy of your data | An old `baseline.py --resume` session is a copied historical game, not live production code; use the current disposable launcher |

## Definition changes versus saved state

Saved player-owned item rows restore instance properties such as weight, nutrition, hydration, description, keywords, qualities, `on_use`, liquid, remaining fuel and applied-effect state. Existing actors restore health, armour and perception state. A new factory-created instance receives current defaults.

Other behavior intentionally consults current definitions: weapon damage/movesets, readable text bodies by `text_id`, and recipe definitions for newly started jobs. Existing processing jobs retain their remaining time. Generated worlds also have saved plans and content compatibility rules; do not assume that a new structural definition can safely replace an asset already selected by an older plan.

After testing, record what you changed, how you obtained fresh content, which automated check ran, and any intentionally untested aspect. This small record makes the next wiki update much more reliable.

## Source bindings

- [Current data loader](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/data_loader.py)
- [Current item factory](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/item_factory.py)
- [Save component reconstruction](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/engine/save_components.py)
- [Owner tuning guide](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/docs/owner/TUNING_EXISTING_FEATURES.md)
- [Regression driver](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/tools/critical_fix_regressions/verify_fixes.py)

## Network policy authoring

Use the complete separate `country_network.json` policy and the [network workflow](#settlement-tuning). `--network-preview` accepts an optional `--network-policy` draft; `--init-network` preserves existing draft edits. JSON/SVG/PNG outputs use the same protected destinations and staged publication as building previews. These commands do not install policy or mutate a campaign. The building painter remains the export source for building contents, including compound children.
