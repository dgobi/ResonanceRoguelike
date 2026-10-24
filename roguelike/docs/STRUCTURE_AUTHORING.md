# Make a building or layout for Resonance

Current: **G3 / generation revision `wg3`**, 23 October 2026.
The connected workflow below is active for new worlds. The later direct-stamp
sections retain the G2 legacy authoring route and its explicitly inactive fields.


## Connected frontage and landmark workflow (G3)

The active planner uses `data/generation/g3_config.json`. It selects assets once,
then stores routes, crossings, settlements, plots, entrance approaches and semantic
dependencies with the world checkpoint. Individual buildings **including their
buffer and approach** must fit one 80 × 43 storage chunk. Streets and settlements
cross chunk boundaries. Coordinates in assets are source tiles; plan coordinates
are world tiles (`wx * 80 + lx`, `wy * 43 + ly`). Rectangles exclude their right and
bottom edge. Full null-painted footprints still reserve space.

1. Import the complete [frontage example](examples/author_frontage_a.json) or
   [landmark example](examples/author_landmark_a.json). They are working copies of
   installed house/shrine assets, with new IDs and complete supported contents.
   Export edits into `authoring/` using the matching filename. Keep drafts outside
   `roguelike/data/`. Use **Apply ID** when changing the ID in the painter.
2. Paint terrain/decor and edit supported special records as in the direct workflow.
   Identify the real doorway; a south entrance lies on the final source row and
   points outward south. An entrance is distinct from an item target, generated
   player arrival and submap return link.
3. Select **placement** in the metadata panel. Apply the complete version-one
   object. `contexts` explicitly opts into `grid`, `roadside`, `civic` or `landmark`.
   The rectangular footprint is derived from the complete terrain grid. `buffer`
   and `approach` are tile counts; `rotations` contains allowed degrees (0/90/180/270),
   and `mirror_x` explicitly allows horizontal reflection before rotation.
   Each entrance has a unique ID, integer x/y, cardinal normal N/E/S/W, positive
   width, main/service role and required boolean. Width runs toward positive x on
   N/S edges and positive y on E/W edges. Every cell must lie on the outward edge.
   `targets` contains integer x/y, kind and required boolean; supported kinds are
   floor, item, readable, container, stairs_up and stairs_down. Required containers
   must be interactable under the game's stricter corner rule.
4. Run every permitted orientation through the actual stamper and population code,
   then preview an actual assigned plot. The planner filters by full footprint,
   buffer, approach ownership, permitted orientation and assigned road join before
   accepting a candidate. Unknown coordinate-bearing metadata cannot silently
   rotate. `road_relation` distinguishes frontage, bounded spur and remote. The
   shipped mandatory landmark uses a spur; optional remote placement is preserved
   in the contract but not selected by the required connected pools.
5. The exact active pools are arrays of structure IDs under `pools.grid`,
   `pools.roadside`, `pools.civic` and `pools.landmark` in `g3_config.json`. A draft
   `--planned --context ...` run adds its ID only in memory, retaining all installed
   pool choices. Weight is a positive selection weight, **not a guaranteed count**.
   Eligibility alone does not guarantee fit or selection. JSON records every
   rejected candidate reason and each explicit vacant garden; essential civic and
   landmark failures fail planning instead of quietly becoming vacancies.
6. Use both grid and roadside previews for the frontage example. Inspect assigned
   road IDs, footprint/clearance/approach rectangles, entrance spans/normals,
   required goals and materialization receipts. A nearby different road cannot
   satisfy a missing assigned join. The same production planner/materializer
   powers previews and ordinary new worlds. SVGs are diagnostic drawings, not
   played-game screenshots. Full realized objects and rejected choices are in JSON.
7. Install deliberately into the appropriate existing category folder, append the
   new ID to the intended pool in `g3_config.json`, validate and refresh the editor
   catalog. Existing inactive `allowed_in`, `facing`, `rotatable`, `district_weights`
   and legacy `weight` do not grant G3 eligibility or rotation permissions.

From the repository root, these commands are complete and safe to repeat after
an edited draft exists (initialization cannot replace that draft):

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force authoring | Out-Null
if (-not (Test-Path -LiteralPath authoring/author_frontage_a.json)) {
  Copy-Item roguelike/docs/examples/author_frontage_a.json authoring/author_frontage_a.json
}
if (-not (Test-Path -LiteralPath authoring/author_landmark_a.json)) {
  Copy-Item roguelike/docs/examples/author_landmark_a.json authoring/author_landmark_a.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_frontage_a.json --route ordinary_building --category residential --orientations --output evidence/authoring/frontage-orientations.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_frontage_a.json --planned --category residential --context grid --seed 20261023 --output evidence/authoring/frontage-grid.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_frontage_a.json --planned --category residential --context roadside --seed 20261023 --output evidence/authoring/frontage-roadside.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_landmark_a.json --route ordinary_building --category wilderness --orientations --output evidence/authoring/landmark-orientations.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_landmark_a.json --planned --category wilderness --context landmark --seed 29417 --output evidence/authoring/landmark-plot.json
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --seed 20261023 --output evidence/authoring/world-plan.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
```

The landmark positive selection uses seed 29417. Seeds 20261023 and 0 kept the
existing shrine instead; those are valid unselected-candidate outcomes, not world
failures. This controlled example is not a frequency estimate.

For deliberate installation of an accepted frontage draft:

```powershell
Copy-Item authoring/author_frontage_a.json roguelike/data/buildings/residential/author_frontage_a.json
# Append "author_frontage_a" to pools.grid and/or pools.roadside in g3_config.json.
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/authoring/installed-catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
```

Catalog freshness compares raw checkout bytes, including LF/CRLF. Refresh after
an intentional edit or checkout conversion; do not suppress a stale result. Saved
plan compatibility uses separate semantic dependency digests, ignores JSON
formatting and inactive structure metadata, and does not use catalog hashes as RNG
seeds. Changes to unrelated unused assets do not move a road or invalidate a plot.

Authoring changes appear in previews immediately and in new worlds. Visited scenes
and moved/taken contents remain saved and never respawn from their plan. A pending
placement with changed required generation content fails **before departure** with
the placement/dependency name: restore matching definitions or start a new world.
Loading/F9 and unrelated pending placements still work. Runtime IDs used by saves
must remain available. Live text/presentation follows the current runtime policy;
there is no historical generator archive or campaign migration.

Absent-field, wg1 and wg2 worlds keep their saved origin revision and authoritative
scenes. Their unexplored chunks use the explicit legacy/no-plan path. G3 worlds
require their saved shared plan; missing/corrupt plans follow atomic checkpoint
recovery rather than regenerating from a seed. Travel does not publish an F5 save.

| Active setting | Units and scope |
|---|---|
| settlement_count | Inclusive [minimum, maximum], default 2–4, including roadside settlements. |
| minimum_separation_chunks | Euclidean anchor distance in coarse chunks, default 12. |
| near_start_radius_chunks | Inclusive Euclidean radius, default 10; one of the counted sites is reserved near start. |
| forms | Grid then roadside; additional counted settlements alternate. Both span chunks. |
| road_width_tiles / street_width_tiles | Full integer world-tile band widths, default 3. |
| plot_spacing_tiles | Plot center spacing, default 18; geometry still must fit. |
| setback_tiles | Minimum entrance-to-road clearance, default 2; profile approach can require more. |
| max_spur_tiles | Maximum connected approach length, default 12. |
| route_search_nodes | Bounded coarse A* expansion limit per route, default 16,384. |
| site_search_limit | Maximum ordered candidate sites examined, default 16,384. |
| pools | Explicit existing asset IDs with matching profile contexts; profile weight selects fitting candidates. |

`town_config.json` remains a preserved inactive legacy file. G3 does not activate
its nonexistent categories. Roads use terrain costs and exclude the VUKH peak;
capital gateway and starting laboratory remain reserved anchors. Bridges own their
water/channel intersection and are traversable by players and creatures. Existing
no-plan ford behavior remains separate. A required crossing/site that cannot meet
constraints yields a specific bounded failure before publishing a world.

To see the representative world using production code and a fresh disposable save
root, choose a new session name (existing names are refused):

```powershell
& $ResonancePython -X utf8 tools/play_disposable.py --seed 20261023 --session g3-first
```

This optional play command opens the game; autonomous verification does not depend
on it. The headless journey command is:

```powershell
& $ResonancePython -X utf8 tools/worldgen_g3_diagnostic.py --journey --evidence evidence/worldgen-g3/diagnostic
```

## Legacy direct-stamp workflow

The G2 direct-stamp workflow was introduced on 23 October 2026. Work in
`G:\GameDev\RoguelikeProject` on `main`; follow `AGENTS.md`. The current workflow
is local HTML editing, draft export, one Python validation/preview command, then
an explicit installation into an existing pool. No server or campaign is needed.
[G1 evidence](../../docs/owner/WORLDGEN_G1.md) remains historical;
[G2 delivery](../../docs/owner/WORLDGEN_G2.md) records the new checks and limits.

## First building: import, edit, preview, register

1. Open `G:\GameDev\RoguelikeProject\layout_painter.html` in a browser. It works
   offline; scripts and the generated catalog are adjacent under `tools/structure_editor/`.
2. Select **ordinary_building**, intended folder **residential**, and import
   `G:\GameDev\RoguelikeProject\roguelike\docs\examples\author_cottage_a.json`.
   Import keeps the entire document, including unknown fields. Use a new asset ID
   and filename together when creating a variation.
3. Select a terrain character and click cells. Select the **Decor** layer to paint
   complete decor IDs; **Erase (null)** removes only the selected decor cell.
   The grid readout shows coordinates and full IDs. Purple markers show decor;
   gold outlines show special records. Visibility switches do not change JSON.
4. Edit an individual special in its JSON panel and click **Apply record**.
   Catalog reference selectors insert item/text/pool/scene IDs into the panel;
   applying is a separate deliberate edit. Starts and metadata have their own
   field panel. An absent field stays absent until explicitly applied.
5. Export a **draft** using **Export draft JSON**. Save the download as
   `G:\GameDev\RoguelikeProject\authoring\author_cottage_a.json`. The paste/import
   and exported-text area are portable fallbacks. No direct-disk browser API is required.
6. Run these commands from the repository root. The data stays installed as-is;
   `--register` adds the candidate only to a caller-owned in-memory pool and keeps
   all 57 installed building candidates. No demonstration building is installed by G2.

```powershell
Set-Location 'G:\GameDev\RoguelikeProject'
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force authoring | Out-Null
# For a first run without browser edits, copy the complete example as your draft:
if (-not (Test-Path -LiteralPath authoring/author_cottage_a.json)) {
  Copy-Item roguelike/docs/examples/author_cottage_a.json authoring/author_cottage_a.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/author_cottage_a.json `
  --route ordinary_building --category residential `
  --access roguelike/docs/examples/author_cottage_access.json --register `
  --output evidence/authoring/author-cottage.json
```

The result must report `passed: true`. Inspect `evidence/authoring/author-cottage.json`
and the adjacent `author-cottage-0.svg` / `author-cottage-1.svg` previews. These are
**diagnostic glyph maps, not game-renderer screenshots**: `#` solid terrain,
`+` door, `<`/`>` stairs, `D` decor, `!` items, `C` containers, `A` actors, `@` arrival.
Hover for IDs and rolled contents; JSON lists complete item/container records,
blocking flags, links and access results. Green target outlines passed; red failed.
A direct stamp and the recorded generated town placement are separate evidence;
neither predicts ordinary-world frequency.

The sidecar asks for an exterior approach, food pickup, readable note and a usable
crate interaction position. If you move these objects, edit that sidecar's source
coordinates too. Omitting `--access` validates and realizes contents but **does not
certify intended physical access**. Invalid candidates never enter a campaign.

After reviewing a valid draft, deliberately install it (do not overwrite an
unrelated existing ID). This is an owner action, not an action performed by preview:

```powershell
Copy-Item authoring/author_cottage_a.json roguelike/data/buildings/residential/author_cottage_a.json
& $ResonancePython -X utf8 tools/structure_authoring.py `
  roguelike/data/buildings/residential/author_cottage_a.json --register `
  --access roguelike/docs/examples/author_cottage_access.json `
  --output evidence/authoring/installed-cottage.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
```

The second command infers the route/category from an installed catalog path.
External filenames cannot prove either: drafts require `--route` and ordinary
drafts also require `--category`. Review the source diff and checkpoint/commit
accepted content under the project rules. Local commits do not independently
authorize a push.

The compatibility command remains a thin wrapper over the same implementation:

```powershell
& $ResonancePython -X utf8 roguelike/docs/examples/validate_building.py `
  --game roguelike --building roguelike/docs/examples/author_cottage_a.json `
  --output evidence/authoring/compatibility-cottage.json
```

## Complete cottage example

The shipped example now includes a readable note, alongside its original food,
crate, chair and candle. The original G1 cottage remains frozen in the 65-document
round-trip corpus. This JSON is outside the live pools:

```json
{
  "id": "author_cottage_a",
  "category": "residential",
  "description": "A small stone cottage with a south-facing door, a chair, a candle, food, a readable note and a supply crate.",
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
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ],
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ],
    [
      null,
      null,
      "overturned_chair",
      null,
      null,
      null,
      "decor_candle",
      null,
      null
    ],
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ],
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ],
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ],
    [
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null,
      null
    ]
  ],
  "special_tiles": [
    {
      "x": 2,
      "y": 4,
      "type": "item",
      "item_id": "crow_jerky"
    },
    {
      "x": 6,
      "y": 4,
      "type": "container",
      "decor_id": "crate",
      "loot_pools": [
        "commoner_kitchen"
      ]
    },
    {
      "x": 4,
      "y": 2,
      "type": "item",
      "item_id": "research_note",
      "text_id": "lab_label_equipment"
    }
  ]
}
```

## Grids, contents and deliberate geometry edits

`layers` is an array of horizontal strings. Coordinates are zero-based: x is the
column and y is the row. The legend maps a single character to a terrain ID or
null. Null means **leave the existing base tile untouched**, not floor. Ordinary
buildings use the current vertical mirror for placements facing the other way;
no saved 90-degree rotation or wilderness placement was added.

`decor_layer` is a rectangular array of arrays containing full decor IDs or null.
It is never a character grid. Container specials need decor with `container: true`;
merely finding a chair ID in the catalog does not make it a container. Omitted
`decor_id` and `loot_pools` compile to `crate` and `[]` without altering raw JSON.
Items use `item_id`; a readable item also supplies a known `text_id`. The ordinary
route uses the existing text-item mapping (or its `letter` fallback), while authored
submaps use the specified item ID and attach text. Found-text and pool-specific
historical metadata is not silently activated.

The editor supports up to **256×256** cells; current runtime installation supports
at most the **80×43** local map and actual placement still needs fitting room.
Larger imports remain intact and exportable, with grid editing disabled. The lab's
60×16 grid can enlarge to 61×16. **Review resize** lists affected terrain, decor,
records and known anchors before applying. Enlargement and explicit ragged-grid
normalization pad with an existing null character (or explicitly add a new null
mapping). They do not floor-fill, shift contents or shrink another dimension.
Destructive crops are **refused**, with affected records listed. Cancel changes
nothing. Undo/redo covers the complete document and route view, not just terrain.
Unknown coordinate-bearing metadata is preserved unchanged and flagged for review.

Initial import/export does not normalize ragged rows or correct invalid definitions.
That preservation is separate from suitability for installation. Eight original
dimension mismatches were explicitly corrected in the live data; two ragged grids
were null-padded. Tests compare actual terrain, decor, transformed content and
materialized content before/after. The original 64 live files plus cottage remain
under `tools/critical_fix_regressions/fixtures/g2_original/` with pinned Git-blob hashes.

Removing a used legend character is refused. Repaint its cells first. Invalid or
cancelled imports leave the current document intact. Duplicate JSON keys, non-finite
numbers and numbers the browser cannot faithfully re-export are rejected clearly;
unknown nested metadata, missing fields, null, false, zero and ordered arrays survive.

## Supported scene and weighted example

`author_scene_weighted.json` demonstrates a scene and every supported weighted
outcome. All alternatives are validated before selection, including zero-weight
rows. Enclosing x/y owns the transform; choices cannot override it. Nested weighted
tables and weighted body/stele/creature kinds are invalid.

```json
{
  "id": "author_scene_weighted",
  "category": "residential",
  "width": 7,
  "height": 5,
  "legend": {
    "#": "wall",
    ".": "floor",
    "+": "door_closed"
  },
  "layers": [
    "#######",
    "#.....#",
    "#.....#",
    "#.....#",
    "###+###"
  ],
  "special_tiles": [
    {
      "type": "scene",
      "x": 2,
      "y": 2,
      "scene_id": "interrupted_meal"
    },
    {
      "type": "weighted",
      "x": 4,
      "y": 2,
      "spawn_table": [
        {
          "type": "item",
          "item_id": "flint_shard",
          "weight": 2
        },
        {
          "type": "container",
          "loot_pools": [
            "storage_tools"
          ],
          "weight": 1
        },
        {
          "type": "empty",
          "weight": 1
        }
      ]
    }
  ]
}
```

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py `
  roguelike/docs/examples/author_scene_weighted.json --route ordinary_building `
  --category residential --seed 20261023 --register `
  --output evidence/authoring/scene-weighted.json
```

## Routes and current eligibility

The live catalog has 55 ordinary buildings, two plazas, six entrances and one
60×16 authored lab. It retains the original 12 residential definitions. There are
11 loot pools. One object per file is required. Duplicate building/plaza IDs are
rejected together, with all source paths; entrances and submaps have their own
namespaces. Generic item/entity list loaders are unaffected.

| Route | Installed folder / selection | Consumed author fields | Retained inactive fields |
|---|---|---|---|
| Ordinary building | `roguelike/data/buildings/<existing-category>/` | `layers`, string/null `legend`, full-ID/null `decor_layer`, supported `special_tiles` | `allowed_in`, `facing`, `rotatable`, tags, `condition`, `interior_loot_table`, `submap`; `district_weights` only belongs to the legacy non-nine-role town route |
| Plaza | `roguelike/data/buildings/plaza/`; weighted centre selection | `layers` or existing `layout` alias, `legend`, `weight` | ordinary decor, specials, starts, rotation, allowed_in metadata |
| Interior entrance | `roguelike/data/entrances/`; uniform matching `entrance_type` | `layers`, `legend`, `legend_weights`, `entrance_type` | `variant`, `connection_point`, `spawn_offset`, `edges` do not control interior placement; anchors are used by the separate edge API |
| Authored submap | `roguelike/data/layouts/`; explicit `SubMap.layout_id` | terrain, `player_start`, supported specials, exit fallback fields; retained stele text metadata | decor layer, `legend_weights`, top-level `stairs_up` metadata, descriptive `type` |

Unknown fields are preserved. Recognized inactive fields produce warnings, not
promises of behavior. Top-level body/stele records retain explicit deferred
physical semantics; no creature, body or stele creation was invented. Paint real
stairs in terrain: merely adding top-level `stairs_up` coordinates does not do so.
A painted ordinary stair does not create an underground level or link.

| Town role | Eligible ordinary folders | Current selection |
|---|---|---|
| C | civic, religious, commercial | Uniform among fitting definitions, up to five per quadrant; plaza separately weighted |
| N/S/E/W | residential, commercial, storage | Uniform among fitting definitions, up to eight per street-bounded subzone |
| Corner interiors | residential, storage | Random category then weighted definition |
| Corner edges | residential, storage, ruins, wilderness | Same weighted definition rule; at most 15 buildings in 40 attempts per corner |

`weight` affects corner/plaza picks, not centre/cardinal row packing. Eligibility
is not guaranteed selection. Full footprints and surrounding clearance must fit.
The immediate existing category folder controls eligibility; the metadata label
does not move a definition to another pool. New categories are outside G2.
`wilderness` is a town-edge category, not a forest-scatter route.

**`town_config.json` remains inactive.** Its categories and street/lamp policy
are not working tuning controls. The current lists/constants in `town_gen.py`
remain authoritative. Settlement/plot planning, new rotations, rural POIs, town-count
policy, WFC palette redesign and saint-alcove/dock/foundation intent remain deferred.
Optional ruin cells are not universally required access targets.

## Entrances and the laboratory

Import the entrance or lab directly; no building fields or decor are inherited
from the previous import. Select the corresponding profile and edit its original
metadata deliberately. Entrances need actual down-stairs, and required surface
stairs must connect to the pre-stamp arrival and declared road approaches, then
pass the check again after native content/startup additions. The eight-way player
movement graph treats doors as openable and blocking decor as obstacles. Bounded
valid fallback is allowed; an isolated two-cell rock pocket is rejected. Dynamic
creatures are reported as occupants, not used as permanent walls in static access.

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py `
  roguelike/data/entrances/barrow_mound_a.json --output evidence/authoring/entrance.json
& $ResonancePython -X utf8 tools/structure_authoring.py `
  roguelike/data/layouts/starting_lab.json --output evidence/authoring/lab.json
& $ResonancePython -X utf8 tools/structure_authoring.py `
  roguelike/data/buildings/plaza/plaza_market_a.json --output evidence/authoring/plaza.json
```

For access expectations, use a sidecar with `coordinates: "source"` (default) or
`"map"`, an `entry: {x,y}`, and `targets: [{name,kind,x,y}]`. Source coordinates are
transformed with the preview origin/mirror and can put an exterior entry just
outside the footprint. Supported target kinds are item, readable, container,
arrival, stairs_up and stairs_down. Containers require a reachable legal adjacent
interaction position; the check calls the engine's corner/range rule rather than
walking through the blocking crate. Tests also execute actual pickup/read,
container transfer and stair travel/return actions. See `author_cottage_access.json`.

## Validation, diagnostics and troubleshooting

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/authoring/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
```

The generated browser catalog includes source identity, route capabilities and IDs.
After data/contract changes, refresh it and reload the HTML page. Browser hints
never claim final validation: export and run the Python command on those bytes.
`--data-root <directory>` binds a separate data catalog explicitly. Preview never
copies game source or accesses a campaign. Runtime loading uses the same contract;
plazas, entrances and submaps no longer depend on a global loader/cache or hidden CWD.

Errors include severity, stable code, source path/asset, field/index and correction:

| Diagnostic | Correction |
|---|---|
| JSON_READ / ROOT | Use UTF-8 JSON, one object, unique keys and finite supported numbers. Fix the named syntax error; do not flatten a list silently. |
| DUPLICATE_ID | Rename/remove the accidental duplicate after reviewing all listed source files. |
| GRID / RAGGED_GRID / DIMENSION | Match row-derived dimensions; explicitly null-pad ragged rows without cropping. |
| LEGEND_MISSING / TERRAIN_USED | Add the missing character mapping or select an existing used terrain ID. TERRAIN_UNUSED is a warning for an unused legacy entry. |
| DECOR_GRID / CONTAINER_CAPABILITY | Use nested full-ID/null arrays; choose actual container-capable decor for a container special. |
| COORDINATE / CHOICE_COORDINATE | Fix source coordinates before offset/mirroring. Alternatives inherit the enclosing coordinate. |
| REFERENCE / POOL_COUNT / WEIGHTS | Fix every referenced item/text/scene/pool and every nested row, including unselected alternatives; use nonnegative finite weights with positive total. |
| LAYOUT_ALIAS / LAYOUT_CONFLICT | For an ordinary layout-only draft explicitly rename `layout` to `layers`; conflicting grids are errors. Only plazas retain the existing alias. |
| INACTIVE_FIELD / DEFERRED_SPECIAL | Data is retained; select a supported route/record for actual behavior. |
| Failed access / blocked placement | Inspect the named target in JSON/SVG; open a legitimate approach or move content deliberately. Do not clear all ruins or teleport the player as a repair. |
| No positive registration | Check category and fitting dimensions. The bounded 32-seed search is a route test, not a frequency estimate. |

An authored source coordinate cannot escape its grid and place an item in unrelated
map space. Runtime's bounded relocation of a valid item anchor off solid terrain
remains separate. Preview reports blocked floor items and blocked/overlapping actors.
No measured shipped-world overlap failure rate is claimed.

## Revision and existing saves

Historically, G2 new worlds and scenes recorded **wg2**. G3 new worlds use the
shared plan described above; the following mouth rules still govern no-plan worlds. Whole mouths now shift as a unit
into the non-corner interval: for axis length L, first quantize the requested centre
as `clamp(floor(p*(L-2))+1,1,L-2)`, then clamp its start to `[1,L-1-width]`.
The resulting centre is `start + width//2`; width is unchanged. Omitted/zero width
uses road 3 or river 9. Widths outside `1..L-2` and malformed positions are errors.
Consumers share the resolved mouth; river-bank expansion clips only its derived
bank margin. Reciprocal masks, inward approaches and ford player/creature semantics
remain tested. Current emitted macro positions avoided the original extreme probes.

Absent-field legacy maps and explicitly wg1 maps remain authoritative. Their
mutations/provenance survive load, revisit and F9. New exploration now records wg3 while
the world's origin remains wg1; no relabeling, backfill or historic seam guarantee
is implied. JSON changes affect new previews and new locations, not visited maps.
Loading F9's saved wraith encounter restores exposure; actual debug departure clears
it before source serialization, without consuming a turn or advancing checkpoint HEAD.

## Autonomous regression commands

```powershell
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py `
  --game roguelike --evidence evidence/worldgen-g2/focused
& $ResonancePython -X utf8 tools/verify_structure_editor.py `
  --evidence evidence/worldgen-g2/browser
& $ResonancePython -X utf8 tools/verify_d.py
```

The browser test uses pinned **Playwright 1.64.1**, Chromium and Firefox with isolated
headless profiles. It drives real file input, editing, download, resize cancellation,
undo/redo and the width60 lab. Downloaded JSON then crosses the same Python command
and current random pool. The 65 original plus 64 delivered round-trips are supplementary
model checks. Browser tests have 150-second per-browser bounds; the focused Python
suite retains its 180-second bound. The unfiltered full D gate includes B1/B2/B3/C.

If the development browser tooling is missing, install it outside the game environment:

```powershell
$BrowserTools = Join-Path $env:LOCALAPPDATA 'ResonanceAuthoring'
& $ResonancePython -m pip install --target "$BrowserTools\python" playwright==1.64.1
$env:PYTHONPATH = "$BrowserTools\python;$env:PYTHONPATH"
$env:PLAYWRIGHT_BROWSERS_PATH = "$BrowserTools\browsers"
& $ResonancePython -m playwright install chromium firefox
```

The test runner resolves the physical dependency path, including redirected Windows
LocalAppData. This avoids Firefox's native side-by-side lookup error in a packaged
host; no browser binary or system security setting needs alteration. No packages,
browsers, profiles, personal saves or source archives belong in Git. The game remains
on Python 3.11.0, pygame 2.6.1, tcod 19.3.0 and NumPy 2.4.6.

The headless file/download approach follows the official
[Playwright actions](https://playwright.dev/python/docs/input) and
[download](https://playwright.dev/python/docs/downloads) APIs. Windows resolves private
assemblies according to its [assembly search rules](https://learn.microsoft.com/en-us/windows/win32/sbscs/assembly-searching-sequence).

For entrance `legend_weights`, a selected `tile: null` uses the fixed legend
fallback. A null fixed legend preserves the underlying terrain. These legacy
semantics are distinct. Direct stamps have no generated player arrival; access
sidecars choose a validation entry. Only authored submap previews certify arrival.
