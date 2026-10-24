# Structure geometry, contents and access

The current authoring contract is shared by runtime loading and the offline Python preview command. It **validates rather than silently repairs** source JSON. Unknown metadata can be retained without becoming executable behavior. For planned buildings, the terrain/content contract is combined with an explicit `placement` profile.

## Choose one of the four routes

| Route | Installation location | Actual purpose |
|---|---|---|
| `ordinary_building` | `roguelike/data/buildings/<existing-category>/<id>.json` | Modern planned buildings and the preserved legacy town route. Modern selection additionally requires explicit placement and policy membership. |
| `plaza` | `roguelike/data/buildings/plaza/<id>.json` | Legacy plaza selection and direct previews; current shared towns use their planned civic anchor. |
| `interior_entrance` | `roguelike/data/entrances/<id>.json` | Small surface structures associated with existing submaps. |
| `authored_submap` | `roguelike/data/layouts/<id>.json` | A complete authored underground layout named by `SubMap.layout_id`. |

Ordinary category folders currently recognized are `civic`, `religious`, `commercial`, `residential`, `storage`, `ruins` and `wilderness`. Structure catalog files must be in their immediate supported folder; arbitrary deeper nesting is rejected. Building and plaza IDs share one namespace. Entrances and authored submaps have separate namespaces. One JSON object per structure file is required.

## Terrain and dimensions

`layers` is an array of equal-length strings. Each string is a horizontal row, with `(0,0)` at the upper left, positive x toward the right/east and positive y downward/south. `width` and `height`, when present, must match the actual row dimensions. The runtime limit is 80 × 43; fitting a building plus its buffer and approach usually imposes a much smaller practical limit.

`legend` maps a **single character** to a known terrain ID or `null`. Null preserves the underlying tile. It does not make an owned plot cell available to another building, and it does not imply walkable floor. Every used character must be defined. An unknown terrain used in the grid is an error; a retained unknown terrain in an unused legend entry is a warning.

Only the plaza route accepts `layout` as an alias for `layers`. A generic `grid` field from an old guide is not the active structure schema. Duplicate JSON keys, non-finite numbers, ragged rows and mismatched dimensions are rejected. Current compiler numeric safety also rejects numbers outside the browser-safe range `±(2^53−1)`.

## Decorative cells

`decor_layer` is an optional matching array of arrays containing **full decor IDs or null**, never character strings:

```json
"decor_layer": [
  [null, null, null],
  [null, "decor_candle", null],
  [null, null, null]
]
```

This small illustration belongs only in a matching 3 × 3 layout. For a larger structure, supply the complete matching rectangle. The ordinary-building stamper consumes this layer; retaining it on the plaza, entrance or authored-submap route does not give those routes ordinary-building decor support.

A painted table, shelf or hearth is not automatically a container. Container capability comes from its decor definition and an explicit supported content record. `waystone_plinth` is a special example where the ordinary stamper converts a legend terrain ID into decor on a base tile; its eventual representation matters when choosing an access target.

## Supported special records

Every top-level special has integer source `x` and `y` inside the grid. Use existing IDs and validate every reference.

| Kind | Example | Meaning |
|---|---|---|
| Item | `{"x":2,"y":3,"type":"item","item_id":"crow_jerky"}` | Creates an item through the normal factory. |
| Readable item | `{"x":2,"y":3,"type":"item","item_id":"research_note","text_id":"lab_label_equipment"}` | Supplies text identity. The ordinary route uses the text-to-item map or its `letter` fallback; the authored-submap route uses the specified item with text attached. |
| Container | `{"x":2,"y":3,"type":"container","decor_id":"crate","loot_pools":["storage_tools"]}` | Creates a container-capable decor instance and rolls the named pools. |
| Scene | `{"x":2,"y":3,"type":"scene","scene_id":"interrupted_meal"}` | Expands the scene's supported `floor_objects` item rows. It is not a general entity scene graph. |
| Empty | `{"x":2,"y":3,"type":"empty"}` | Places nothing; useful as a weighted outcome. |
| Weighted | An enclosing position plus `spawn_table` | Chooses one supported item/container/scene/empty outcome. One level only. |

If a container omits `decor_id` or `loot_pools`, compiled defaults are `crate` and `[]`. This preserves the raw source rather than rewriting it. An empty pool or zero-roll range can intentionally yield no contents. To promise a useful populated container, choose pools and counts that actually produce items, and check the realized preview.

Top-level `body` and `stele` records retain explicitly deferred physical semantics. Authored submap stele text metadata is retained, but these records are not a general mechanism to create corpses or functional steles. Arbitrary creature specials and the old guide's `inscription` kind are not accepted alternatives. Use supported physical item records or implement the missing route deliberately.

### Weighted contents

```json
{
  "x":4,"y":2,"type":"weighted",
  "spawn_table":[
    {"type":"item","item_id":"flint_shard","weight":2},
    {"type":"container","decor_id":"crate","loot_pools":["storage_tools"],"weight":1},
    {"type":"empty","weight":1}
  ]
}
```

Weights default to one; they must be finite and nonnegative with a positive total. Every branch is validated, even a zero-weight branch or one not chosen in the current seed. Nested weighted tables and weighted body/stele/creature outcomes are unsupported. Child coordinates normally should be omitted: if supplied, each must equal its enclosing coordinate. Transforming the enclosing record also transforms any explicitly supplied matching child coordinates.

Loot pools use `roll_count` and item rows containing `item_id` and `weight`. Other retained row fields, including text-binding fields, do not acquire behavior. Scene `floor_objects` rows consume only `item_id`; use a direct readable special when a particular text is required.

## Placement profile reference

Current `placement` objects require the following known fields. Unknown keys inside this profile are errors.

| Field | Accepted form | Author's decision |
|---|---|---|
| `version` | Integer `1` | Use the supported contract. |
| `contexts` | Nonempty list of `grid`, `roadside`, `civic`, `landmark` | The allowed fitting contexts; policy membership is separate. |
| `weight` | Positive number at most 1000 | Base relative weight, multiplied by the role/site policy. |
| `rotations` | Explicit subset of `0,90,180,270` | Permitted clockwise quarter turns in screen/map coordinates. |
| `mirror_x` | Boolean | Allows horizontal reflection before rotation. |
| `buffer` | Integer 0–8 tiles | Reserved clearance around the footprint. |
| `approach` | Integer 0–8 tiles | Minimum profile approach consideration; planner setback and maximum spur also apply. |
| `road_relation` | `frontage`, `spur`, `remote` | Connected pools cannot use a deliberately remote profile. |
| `entrances` | Nonempty array | Explicit full doorway spans and outward normals. |
| `targets` | Nonempty array | Typed positions to check; declare required usable goals deliberately. |

### Entrances

An entrance object has exactly `id`, `x`, `y`, `normal`, `width`, `role` and `required`. The ID is unique within the structure. The normal is `N`, `E`, `S` or `W`; role is `main` or `service`; required is boolean.

The full span must lie on the matching outer footprint edge. For a north/south entrance, width extends toward positive x. For an east/west entrance, it extends toward positive y. **Two doors separated by a wall are two entrances.** A width-three declaration across door–wall–door claims all three cells are the opening and will fail appropriate checks.

The fitter chooses one eligible required doorway as the primary frontage, preferring `main`, then lexical ID. Its full span must fit the assigned approach. Other required doors must be reachable from the same road join; the path may go through the building. Declaring a service door does not promise a separate exterior service road.

### Targets

Each target has exactly `x`, `y`, `kind` and `required`. Kinds are `floor`, `item`, `readable`, `container`, `stairs_up` and `stairs_down`. A floor target requires reachability to that tile. Content targets require the corresponding actual object and supported access. For a blocking coffer or waystone, distinguish the object's position from a floor position beside it.

Use `required: true` for the intended usable content. A target is an obligation to verify, not a command to create content. Likewise, painting stairs in an ordinary building does not create a submap or establish a travel link.

## Transforming a whole structure

The shared transform moves terrain, full-ID decor, supported special coordinates, starts/exits, entrance spans/normals and target coordinates together. A 90° or 270° rotation swaps width and height. Source JSON remains unchanged.

Unknown coordinate-bearing metadata cannot be safely guessed. A nontrivial transformation rejects such metadata rather than leaving hidden positions wrong. Unknown scalar descriptive metadata can remain. The legacy `facing` or `rotatable` field is not a substitute for this profile.

## Sources

- [Shared structure compiler and route capabilities](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/generation/structure_contract.py)
- [Placement validator, frontage and transforms](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/generation/placement.py)
- [Final complete-scene access checks](https://github.com/dgobi/ResonanceRoguelike/blob/f76aac1976a1c9b68adb00ed859398bbd60d6ee2/roguelike/generation/planned_scene.py)

## G7 composition integration

The current mixed parent workflow is documented in [Compounds](#compounds). A building export supplies the consumed child structure; a separate recipe supplies two required slots, an optional third slot, common paths, private bounds and permitted parent/child transforms. The existing painter edits the building, not the recipe. Use actual exported bytes in `--child`. Run `tools/verify_g7_authoring.py` for inherited and compound workflows; direct focused discovery now supplies its own absolute tools import path. Keep previous evidence immutable.

## G8 lot and common checks

A complete building buffer and approach must fit its one-member lot. The entire doorway span must project into the assigned straight segment and frontage interval; a nearby parallel road cannot substitute. The protected civic common is public circulation, not overflow private land. Read `rejected` and `composition_work` in a complete settlement preview for cap, transform, capacity and bounded-search outcomes. See [Settlement layouts](#settlement-layouts). A valid candidate can remain unselected; use a declared controlled preview policy when demonstrating one asset, and keep ordinary seed evidence separate.
