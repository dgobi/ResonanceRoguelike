# Make a building or layout for Resonance

Updated for **G2 / generation revision `wg2`**, 23 October 2026. Work in
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
Copy-Item roguelike/docs/examples/author_cottage_a.json authoring/author_cottage_a.json
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

New worlds and newly created scenes record **wg2**. Whole mouths now shift as a unit
into the non-corner interval: for axis length L, first quantize the requested centre
as `clamp(floor(p*(L-2))+1,1,L-2)`, then clamp its start to `[1,L-1-width]`.
The resulting centre is `start + width//2`; width is unchanged. Omitted/zero width
uses road 3 or river 9. Widths outside `1..L-2` and malformed positions are errors.
Consumers share the resolved mouth; river-bank expansion clips only its derived
bank margin. Reciprocal masks, inward approaches and ford player/creature semantics
remain tested. Current emitted macro positions avoided the original extreme probes.

Absent-field legacy maps and explicitly wg1 maps remain authoritative. Their
mutations/provenance survive load, revisit and F9. New exploration can be wg2 while
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
