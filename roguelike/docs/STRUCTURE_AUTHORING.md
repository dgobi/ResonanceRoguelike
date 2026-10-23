# Make a building or layout for Resonance

**Updated for generation revision `wg1` on production `main`, 23 October 2026.** The original review used `ce1ef760d411a0d1e9dfec93f1addf149955ac8c`; current G1 evidence and limits are in [WORLDGEN_G1](../../docs/owner/WORLDGEN_G1.md). This guide describes the active consumers. Start with the cottage below to add a building to random town generation without changing Python. Forest placement, new building categories, and randomly selecting new underground layouts need additional integration; a JSON file alone does not enable them.

The accompanying files are `examples/author_cottage_a.json` and `examples/validate_building.py`. The examples directory is intended to sit beside this document in `roguelike/docs/`. Source references below are relative to `roguelike/`, except the repository-root `layout_painter.html`.

## 1. Choose the right kind of asset

A **building** is a reusable stamp inside a larger town map. An **entrance** is the surface structure around a linked underground stair. An **authored submap** replaces an entire underground map. A **plaza** is a special central-town stamp. These share character grids but have different consumers.

| What you want | Put the JSON here | How it becomes eligible today |
|---|---|---|
| A randomly placed house, shop, shed, shrine, or ruin | `data/buildings/<existing-category>/<id>.json` | Existing town category pools select it automatically. |
| A central town plaza | `data/buildings/plaza/<id>.json` | The centre chunk selects a weighted plaza variant. |
| Another appearance for an existing underground entrance | `data/entrances/<id>.json` | Match an existing `entrance_type`; the entrance picker selects among matching files. |
| A complete underground room complex | `data/layouts/<layout_id>.json` | A `SubMap` must already name that `layout_id`. Adding the file does not register a random encounter. |
| A cabin that randomly appears in forest chunks | No complete JSON-only route exists | The current wilderness generators do not call the general structure placer. |

The snapshot contains **57 building files** in eight folders: `residential` 12, `religious` 8, `ruins` 8, `civic` 7, `commercial` 7, `storage` 7, `wilderness` 6, and `plaza` 2. It also contains **six entrance files**, **one authored submap** (`starting_lab`), and **11 loot pools**.

Code: `engine/data_loader.py`; `generation/region_gen.py`; `generation/town_gen.py`; `generation/local_gen.py`.

## 2. A complete building you can use now

Save this as **`data/buildings/residential/author_cottage_a.json`**. Its door is at column 4, row 6, on the southern edge. The floor contains a chair, a candle, one piece of jerky, and a supply crate. The container's contents are rolled from an existing pool.

```json
{
  "id": "author_cottage_a",
  "category": "residential",
  "description": "A small stone cottage with a south-facing door, a chair, a candle, food and a supply crate.",
  "width": 9,
  "height": 7,
  "allowed_in": "town",
  "weight": 1.0,
  "legend": {
    "#": "wall",
    ".": "floor",
    "+": "door_closed",
    " ": null
  },
  "layers": [
    "#########",
    "#.......#",
    "#.......#",
    "#.......#",
    "#.......#",
    "#.......#",
    "####+####"
  ],
  "decor_layer": [
    [null, null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null, null],
    [null, null, "overturned_chair", null, null, null, "decor_candle", null, null],
    [null, null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null, null],
    [null, null, null, null, null, null, null, null, null]
  ],
  "special_tiles": [
    {"x": 2, "y": 4, "type": "item", "item_id": "crow_jerky"},
    {"x": 6, "y": 4, "type": "container", "decor_id": "crate", "loot_pools": ["commoner_kitchen"]}
  ]
}
```

This exact example passed current-code checks for loading, stamping in both orientations, item creation, container loot, and reaching every usable interior tile with doors treated as openable. The seeded `generate_region()` fixture isolates this example as the only residential candidate and requires positive placement and supported item/container specifications. Its current count is recorded in `evidence/worldgen-g1/authoring.json`. That proves the placement route works; it is not a prediction of frequency in an ordinary mixed town.

`width`, `height`, `category`, and `allowed_in` make the file easier to understand, but the current placement rules below determine their actual influence. No proposed schema fields are required by this example.

## 3. Understand the grid before adding detail

`layers` is a list of strings. Each string is one horizontal row, read from top to bottom. Within a row, characters run from left to right. Coordinates start at zero: **`x` is the column; `y` is the row**. A nine-character row has columns 0 through 8.

The `legend` translates each character into a terrain ID from `data/terrain.json`. For ordinary town buildings, values must be a terrain-ID string or `null`. A missing character or `null` leaves the underlying map unchanged. Unknown characters are generally skipped silently; the engine does not provide a comprehensive schema error for them.

Keep every row the same width. Set `width` and `height` to match, although the ordinary stamper computes its footprint from the longest row and number of rows. JSON needs double quotes, commas between entries, and no comments or trailing commas. Use `description` or `note` for author notes.

Useful terrain choices:

| Terrain ID | Effect |
|---|---|
| `wall`, `old_wall`, `grey_stone` | Solid, opaque terrain. |
| `floor`, `flagstone` | Walkable interior ground. |
| `door_closed` | Solid and opaque until the player bumps it open. Opening the door does not itself move the player into it. |
| `door_open` | Already walkable and transparent. |
| `table` | Solid furniture terrain that permits sight. A floor item or container should be placed on an adjacent walkable cell. |

Use one exterior door or open gap near the middle of the **bottom row** for ordinary buildings. The generator expects southern entrances; for some plots south of a road it reverses the row order. This mirrors the building vertically, including decor and special-tile coordinates. It is not a 180-degree rotation: left and right remain unchanged. There is no current ordinary-town 90-degree rotation controlled by `rotatable` or `facing`.

Town corner paths start one tile below the building's bottom centre; they do not search for the actual door. A door elsewhere can be visually disconnected from its approach. The generator does not verify that the interior is reachable. The companion checker adds that check for the documented subset.

Code: `generation/town_gen.py`; `generation/layout_stamper.py`; `engine/engine.py`; `data/terrain.json`.

## 4. Add furniture, items, containers, and texts

### Decorative furniture

`decor_layer` is a **list of lists**, with one complete decor ID or `null` in each cell. It is not a second character grid. The example's `"overturned_chair"` occupies one cell; spelling it across a string would create separate invalid character IDs.

Choose IDs from `data/decoratives.json`. Their definitions distinguish movement-blocking objects, containers, sight blocking, and visual effects. For example, `crate` blocks movement; `overturned_chair` and `decor_candle` do not. A candle's visual entry is not, by itself, a promise of a working light-source component.

There is one decor value per cell. A container placed later replaces decor already at that position. An image of a barrel placed only in `decor_layer` does **not** create a stocked container; use a container special tile for that. Multiple floor items, however, can share a cell.

### Loose items

An item special uses `x`, `y`, `type: "item"`, and an existing `item_id`. Add another special entry for another item; the town handler has no general `quantity` field here. Place it on explicitly walkable floor.

For a readable item, also provide `text_id`. Town spawning consults `data/texts/text_item_map.json` and can replace the requested item type with its mapped text item. An unmapped nonempty text ID retains the fallback to `letter`. The text itself must also exist under `data/texts/`. Authored submaps use the requested item ID directly, so the two routes should not be assumed identical.

### Containers and loot

A container special uses `type: "container"`, `decor_id`, and `loot_pools`, a list of **exact pool IDs**. The shared G1 adapter defaults containers to `crate` if `decor_id` is omitted. Always write it explicitly.

The 11 current pools are `alchemist_reagents`, `alchemist_shop`, `commoner_bedroom`, `commoner_kitchen`, `noble_generic`, `ruins_scatter`, `shrine_equipment`, `shrine_offering`, `storage_general`, `storage_tools`, and `wilderness_cache`.

A pool file under `data/loot_pools/` has this working shape:

```json
{
  "id": "author_supplies",
  "roll_count": [1, 2],
  "items": [
    {"item_id": "crow_jerky", "weight": 3},
    {"item_id": "tallow_torch", "weight": 1}
  ]
}
```

`roll_count` chooses an inclusive minimum/maximum number of entries. Selection is weighted **without replacement within that pool**, capped at the number of entries. Each selected entry creates one item. The optional entry `weight` defaults to 1; missing `roll_count` defaults to `[1, 1]`. Use positive weights and valid item IDs. Each pool in `loot_pools` is rolled separately, then combined. The pool system does not resolve tags or nested loot tables. This format differs from the older `data/loot/` tables.

A container must sit on walkable terrain when it is created. A crate on a wall or solid `table` tile rejects the candidate scene with an asset/index diagnostic, before publication. The crate's own movement blocking is applied through its decor definition afterward. `interior_loot_table` on a building is merely carried into town metadata; it does not stock the building.

Code: `generation/town_gen.py`; `engine/engine.py`; `engine/loot_roller.py`; `generation/floor_object_utils.py`; `data/decoratives.json`.

## 5. What each route actually supports

**“Ignored” means the current consumer does not implement that field.** It does not mean the file will be rejected. This distinction is why a file can load successfully but lose its intended content.

| Field or feature | Ordinary town building | Central plaza | Surface submap entrance | Authored underground submap |
|---|---|---|---|---|
| `layers` + string/null `legend` | Supported | Supported | Supported | Supported |
| `layout` as an alternative name | Loader accepts it, but active placement requires `layers` | Accepted by plaza loader | Not accepted | Not accepted |
| `width`, `height` | Footprint computed from rows | Computed from rows | Computed from rows | Computed from rows; `width` also used by debug diagnostics |
| `decor_layer` as ID/null arrays | Supported | Ignored | Ignored | Ignored |
| `special_tiles`: `item`, `container` | Supported | Ignored | Ignored | Supported |
| `special_tiles`: `scene` | Creates each declared `floor_objects.item_id` at the scene anchor | Ignored | Ignored | Same shared materialization |
| `special_tiles`: `body` | Explicit deferred record; no physical object | Ignored | Ignored | Explicit deferred record; no physical object |
| `special_tiles`: `stele` | Explicit deferred record; no physical object | Ignored | Ignored | Preserves inscription metadata; no new physical object |
| `special_tiles`: `weighted` | One-level item/container/scene/empty table | Ignored | Ignored | Same shared resolver, including the lab table |
| `special_tiles`: `inscription`, live creature | Unsupported authored kind: actionable rejection | Ignored | Ignored | Unsupported authored kind: actionable rejection |
| `legend_weights` | Ignored | Ignored | Supported by the entrance stamper | Ignored by the active submap parser |
| `player_start` | Ignored | Ignored | Ignored by interior entrance placement | Supported; defaults to the layout centre |
| Top-level `stairs_up` coordinates | Ignored | Ignored | Ignored | Ignored; paint a `stairs_up` terrain tile instead |
| `connection_point`, `spawn_offset` | Ignored | Ignored | Used only by the separate edge-stamping API, not ordinary interior entrances | Ignored |
| `type`, `edges`, `variant`, descriptive notes | Do not select the runtime route | Do not select the runtime route | `entrance_type` selects the pool; `variant` and `edges` do not | Filename plus `SubMap.layout_id` selects the layout; `type` does not |

G1 resolves exactly one `spawn_table` entry using scene-owned randomness. Each choice uses `type` and the concrete kind's fields; weights default to 1 and must be finite, nonnegative, with positive total. Empty/all-zero/non-finite tables, unsupported choices and nesting are errors. The enclosing x/y is preserved and vertical mirroring happens once. Inputs are not mutated. The four town scene definitions now materialize through the same adapter. `interrupted_meal` contributes one dried provisions item and one water skin. Unknown item/scene/pool references reject a newly generated scene; known deferred body/stele records remain explicit compatibility limits. No shipped building currently uses weighted specials; the starting lab does.

Native terrain, objects, actors and metadata are staged together. The Engine's surface/submap creation helpers publish only a complete candidate. Cached or active maps, including empty and looted maps, are authoritative and never replay these specifications. Per-container scene/coordinate RNG is independent of combat and decoration draws.

Older helpers can be misleading: `engine/structure_placer.py` understands dictionary legend entries containing `terrain`, `furniture`, and `loot`, but no current generation caller uses that class. `engine/starting_location.py` contains other weighted/body logic, but the current start goes through `main.py` → `engine.scene_generation.create_submap()` → shared `populate()`. Copying fields supported only by those unused helpers will not activate them.

Code: `generation/town_gen.py`; `generation/layout_stamper.py`; `generation/local_gen.py`; `engine/engine.py`; `main.py`; `engine/structure_placer.py`; `engine/starting_location.py`.

## 6. Get a building into the random placement pool

For ordinary buildings, **the immediate folder below `data/buildings/` selects the category**. The JSON `category` label does not move a file between pools. Keep one object per file, one globally unique `id`, and use a matching filename. Do not create a deeper subfolder: the flat structure loader scans recursively, but the active category loader only reads immediate `*.json` files inside each category.

Current 3×3 towns use these pools:

| Town chunk | Eligible ordinary folders | Choice and ceiling |
|---|---|---|
| Centre `C` | `civic`, `religious`, `commercial` | Uniform choice among fitting definitions; up to 5 per quadrant. Plaza chosen separately. |
| North/south `N`, `S` | `residential`, `commercial`, `storage` | Uniform choice among fitting definitions; up to 8 per street-bounded subzone. |
| East/west `E`, `W` | `commercial`, `storage`, `residential` | Same fitting rule and per-subzone ceiling. |
| Corners `NW`, `NE`, `SW`, `SE`, interior | `residential`, `storage` | Random category, then building `weight`; shares the corner ceiling. |
| Corner positions classified as edge | `residential`, `storage`, `ruins`, `wilderness` | Random category, then building `weight`; at most 15 buildings in 40 attempts per corner. |

A building is eligible, not guaranteed. Its entire rectangular footprint must fit inside the map on permitted base terrain, and a one-tile surrounding clearance must avoid other building terrain. The clearance may extend beyond the map; the footprint may not. Blank/null cells still occupy part of that rectangle. Street positions, fitting dimensions, and failed attempts reduce the result below the ceiling. The tested 9×7 cottage is a useful starting size.

`weight` defaults to 1 for weighted picks. It affects plaza and corner selection, but **does not tune centre/cardinal row packing**, which uses `rng.choice(fits)`. `allowed_in` does not filter that active ordinary-town path. `district_weights` belongs to the legacy town route for chunks without a current 3×3 role. `facing`, `condition`, `tags`, `rotatable`, `bell_state_override`, and `allow_adjacent` do not provide the suggested ordinary-placement controls. A `submap` field is only noted as an unprocessed stub by `BuildingLoader`; a painted stair does not create an attached level.

New category folders are discovered on disk but are absent from these hard-coded pools. Likewise, `data/generation/town_config.json` is loaded, but no current generation caller reads its stored values. Its category lists, weights, street dimensions, and lamp settings therefore cannot be used as working tuning controls. The corresponding active values are Python constants and lists in `town_gen.py`.

### Wilderness and biome placement

The `wilderness` building folder supplies **town corner edges**, not a forest scatter system. A structure's `tags: ["forest"]`, a zone's `structures` list, or a new biome label does not place it in wilderness. `DataLoader.structures_with_tags()`, `zone_structures()`, and `StructurePlacer` have no current generation callers. `CAPITAL` currently uses the open-terrain generator rather than the town-building path.

The biome-level submap selection also uses Python `SUBMAP_WEIGHTS` and `SUBMAP_TYPES`; similarly named fields in biome JSON do not control that selection. This is separate from entrance appearance: another file with an existing `entrance_type` does join that entrance's variant pool.

Code: `engine/data_loader.py`; `generation/town_gen.py`; `generation/region_gen.py`; `generation/world_gen.py`.

## 7. Register and validate your first building

Work in the existing project on **`main`**, following `AGENTS.md`: preserve unrelated changes and make appropriate named checkpoints before substantial edits. This guide does not require a new branch or development copy.

1. Start from the complete cottage example. Rename its `id` and filename together if making a variant.
2. Keep `category: "residential"` for this first exercise. Change the grid, then adjust width/height, decor, and special coordinates together.
3. Run the checker before installing the asset. It adds the file only to temporary copied data, imports the actual project's code, and generates maps in memory.
4. Put the finished JSON directly in `roguelike/data/buildings/residential/` and run the same checker against that file.
5. Review the resulting diff and checkpoint/commit accepted content according to the project workflow. Start a fresh preview process for data changes to load.

### Windows commands

Run from the **repository root**, the directory containing `AGENTS.md`, `tools`, and `roguelike`. Use the Python interpreter already used for this project. The recorded installation is below; change only this path if your current interpreter lives elsewhere.

```powershell
Set-Location 'G:\GameDev\RoguelikeProject'
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'

& $ResonancePython .\roguelike\docs\examples\validate_building.py `
  --game .\roguelike `
  --building .\roguelike\docs\examples\author_cottage_a.json
```

After choosing a fresh filename and ID, copy the file to its category folder. Then check the registered copy:

```powershell
& $ResonancePython .\roguelike\docs\examples\validate_building.py `
  --game .\roguelike `
  --building .\roguelike\data\buildings\residential\author_cottage_a.json
```

A successful run prints `"passed": true`, both normal and flipped stamp checks, and a nonzero town placement count. The checker uses existing dependencies and never reads saves, imports `main`, opens a window, or writes game source. It checks a deliberately supported ordinary-building subset, not every historical field. Its connectivity check follows the runtime's eight-way movement, including diagonal corner cutting, treats closed doors as openable, and includes movement-blocking decor. It is not full gameplay or visual certification.

### New generation versus a cached world

New worlds and completed scenes carry `wg1` provenance. Absent fields mean `legacy-unversioned`; saving an older world does not relabel it. New exploration can therefore mix revisions; historic cross-version seams are not certified and old maps are never regenerated to force a match. Existing B3 save-version restrictions still apply.

Loaded data and entrance definitions are cached in a running process. Previously visited chunks are also restored from saved map state; changing their JSON does not rebuild them. F9 reloads saved state rather than regenerating the layout. A new process and a fresh, disposable world are the dependable preview conditions.

For an optional visual preview using the actual main source and a temporary save root, change into `roguelike` and run:

```powershell
Set-Location .\roguelike
@'
from pathlib import Path
from tempfile import TemporaryDirectory
import engine.save_manager as save_manager
import main
with TemporaryDirectory(prefix="resonance-author-preview-") as folder:
    save_manager.SAVE_DIR = Path(folder) / "saves"
    main.main()
'@ | & $ResonancePython -
```

This preview starts a separate temporary campaign and removes it when the process closes. It does not require deleting a personal campaign or using a historical source-copy launcher. The automatic checker is the repeatable first check; a random mixed town need not contain any particular variant on one visit.

Code: `engine/engine.py`; `generation/entrance_gen.py`; `engine/data_loader.py`; `engine/save_manager.py`; `main.py`.

## 8. Use the layout painter for terrain, then finish the JSON

Open repository-root `layout_painter.html` in a browser. Use **SIZE** to choose dimensions, **legend** to map characters to real terrain IDs, then **paint**, **fill**, and **erase** to build the grid. Keyboard shortcuts are P, F, and E; T selects terrain. The **json** panel provides text to copy into a file. The tool does not save directly into the game's folders or validate IDs against game data.

For the currently reliable workflow:

1. Paint the terrain grid with the decor-layer checkbox off.
2. Copy the exported `layers` and `legend` into your complete building file.
3. Preserve or add `width`, `height`, `decor_layer`, and `special_tiles` in a text editor.
4. Run the checker on the completed JSON.

The current painter is **not a lossless editor for a complete asset**. Its export only preserves the metadata it knows, the legend, the terrain grid, and its own decor representation. A direct import/export of the valid cottage removed `width`, `height`, and `special_tiles`. It also turned the nested decor arrays into strings; feeding that result to the current stamper produced invalid single-character decor IDs. Other unsupported fields, such as submap starts or entrance anchors, are likewise absent from the exporter.

The painter's Allowed In menu (`town`, `capital`, `any`) also does not describe an active placement filter. Its default legend contains `town_plaza`, which is not a current terrain definition; choose a valid terrain such as `flagstone` or `cobblestone` before painting with that symbol.

These findings came from executing the exact import/export function bodies with a minimal DOM fixture, followed by the actual Python stamper. They do not claim that the browser UI itself was visually tested.

Code: `layout_painter.html:149–164,193–207,261–274,553–574,591–642,650–659`.

## 9. Author plazas, entrances, or complete underground spaces

### Plazas

Place a single object in `data/buildings/plaza/`. The loader accepts `layers` or `layout`, computes dimensions from rows, and uses `weight` for selection. The actual plaza stamper reads its terrain legend only; ordinary-building decor and special-tile examples do not apply. It recognizes certain waystone/lamp IDs as decor. Centre-generation logic also normalizes the physical terrain/decor of a located bell to the cracked state. G1 synchronizes `TownData.bell_state` to `cracked` before guardian selection, or `missing` if no bell was placed. Non-centre roles remain `spent`. `bell_state_override` is not a working per-file override.

### Surface entrances

The current interior entrance route chooses variants uniformly by `entrance_type`:

| Underground type | Entrance pool |
|---|---|
| `barrow`, `deep_vault` | `barrow_mound` |
| `cave` | `rock_face_cut` |
| `vault`, `sunken_ruin`, `cellar`, `crypt`, `laboratory` | `sunken_ruin` |
| `flooded_ruin` | `drowned_threshold` |

Use a unique ID and an existing pool to add another appearance. Include exactly one `stairs_down` terrain cell. The low-level stamper returns the last such cell if there are several. G1 validates an actual accessible stair before registering a link; a layout without one cannot register its generic centre. If no full layout fits, a documented bare stair fallback must have legal free ground and an approach; otherwise creation fails without publication. The separate `overgrown_gatehouse` asset is not selected by this submap-type mapping.

Normal entrances are centred with **no rotation**. They ignore `connection_point`, `spawn_offset`, `edges`, `decor_layer`, and `special_tiles`. The separate edge API rotates terrain plus both anchor points; there `spawn_offset` is a layout coordinate, not a vector relative to `connection_point`.

`legend_weights` works on the entrance stamper, with per-character lists of `{ "tile": "gravel", "weight": 2 }`. Both supported entrance stampers accept an explicit RNG and use deterministic map context as their fallback. G1 checks row-derived full bounds, protected roads/buildings/objects and their approaches before committing a bounded candidate. Natural vegetation within a legal footprint may be replaced. Declared width/height do not enforce a size cap.

Code: `generation/entrance_gen.py`; `generation/region_gen.py`; `generation/layout_stamper.py`.

### Authored submaps

`SubMap.layout_id = "my_chamber"` selects `data/layouts/my_chamber.json`. The loader centres `layers` within a wall-filled local map; it does not discover layouts as a random pool. The existing starting laboratory is explicitly assigned in `generation/world_gen.py`. New random authored submaps require integration at SubMap creation.

Paint `stairs_up` directly in the grid and place `player_start` on reachable floor. The top-level `stairs_up` object in the older guide and shipped lab is ignored. If no up-stair is painted, fallback placement reads `exit_direction`, `exit_y`, and sometimes `exit_x`: north/south use the layout's centre x with `exit_y`, while east/west use `exit_x` with centre y. Merely writing `"north"` does not move the default exit to the northern edge. Explicit painting is clearer.

The map is currently 80×43. A 78×41 layout with its own enclosing wall border is a conservative authoring maximum, not an enforced schema limit. Oversized terrain can still be clipped by the low-level stamper, so keep within that authoring limit. G1 validates arrival and a door-aware return route after materialization. Item specials retain bounded nearby relocation; invalid containers and scenes reject creation rather than silently disappearing. Avoid relying on either recovery behavior.

For supported submap scenes, `scene_id` names an entry in `data/scenes.json`. The scene coordinate must be in bounds and walkable. The handler creates each `floor_objects` entry using only its `item_id`, placing every item at that one coordinate; it does not interpret other scene metadata or interaction flags. Body/stele physical objects and ordinary building decor layers remain deferred here. One-level weighted item/container/scene/empty specials are supported; unsupported kinds reject the candidate. Missing authored layout files also reject creation with a destination diagnostic rather than silently substituting another scene.

Code: `generation/local_gen.py`; `engine/engine.py`; `world/world_map.py`.

## 10. WFC palettes are background data, not building pools

Town WFC files supply background patterns before buildings are placed. Their symbolic tile names are translated through hard-coded maps in `town_gen.py`, rather than used automatically as terrain IDs.

| WFC file | Current translation |
|---|---|
| `town_block.json` | `packed_earth`, `dirt_path`, `weedy_cobble`, `tall_grass` keep their names; `mud_patch` → `mud`; `debris` → `debris_scatter`. |
| `town_outskirts.json` | `packed_earth`, `tall_grass`, `weedy_cobble`, `gravel` keep their names; `debris` → `debris_scatter`. |
| `town_plaza.json` | `cobble_clean` → `cobblestone`; `cobble_cracked` → `cobblestone_cracked`; `cobble_mossy` → `cobblestone_mossy`; `puddle` stays; `debris` → `debris_scatter`; `waystone_base` → `waystone_plinth`. |

An unknown symbol falls back to `packed_earth` for block/outskirts fills or `cobblestone_cracked` for plaza fills. Filling only overwrites eligible grass/varied-grass cells and preserves protected routes, stairs, functional decor and object layers. The solver has ten deterministic attempts; results are adjacency-checked and staged before painting. `generation_diagnostics` records palette, rectangle, stable RNG-state key, revision, solved/fallback and reason. Fallback is valid fill, not a successful solve. Adding a tile to a WFC JSON does not add it to the Python translation map, a building category, or a structure spawn pool.

Code: `generation/town_gen.py`.

## 11. Troubleshoot the symptom you see

| Symptom | Check first |
|---|---|
| File loads but building never appears | Immediate category folder, `layers` spelling, existing pool membership, size and clearance. New folders and forest tags do not enable placement. |
| Changing `weight` has no visible effect | Centre/cardinal fitting ignores it; corner and plaza picks use it. One town visit is not a frequency test. |
| Changing town-config JSON does nothing | The file is loaded but its values are not consumed by current generation. |
| Items disappear after editing in painter | Export dropped `special_tiles`; preserve the complete file and replace only the painted fields. |
| Decor vanishes or appears as nonsense | Use nested arrays of full IDs/null, not painter strings or legend characters. |
| Barrel looks present but has no inventory | A decor image alone is not container state. Add a container special on walkable floor. |
| Scene/body/stele detail is missing in town | Scenes materialize supported floor items; body/stele physical objects remain deferred. Cached scenes are not backfilled. |
| Weighted special rejects generation | Check one-level supported kinds, positive finite total weights and valid references; read the asset/index diagnostic. |
| Door faces the wrong way | Author south-facing; account for vertical mirroring. `facing` and `rotatable` do not change current ordinary placement. |
| Stair looks right but cannot descend | A terrain stamp alone has no `submap_links` destination. Use the actual SubMap/entrance route. |
| File changes are absent in the world | Restart to reload definitions and inspect a newly generated disposable map, not a cached saved chunk. |

The supplied examples were validated against the referenced snapshot. The checker deliberately imposes clearer constraints than the permissive engine, such as rectangular grids and explicit valid references. It provides a reliable starting point for authoring; it does not introduce new runtime fields or implement missing placement features.
