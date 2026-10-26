# Make a building or layout for Resonance

## G17: one creature in an authored underground room

The complete editable [room](examples/g17_authored_creature_room.json) and
[access sidecar](examples/g17_authored_creature_room.access.json) demonstrate
the `authored_submap` route. A direct top-level special creates exactly one real
`CreatureFactory` actor:

```json
{"type":"creature","x":7,"y":2,"creature_id":"hollow_revenant"}
```

Coordinates are integers in the source grid (booleans are invalid).
`creature_id` must name an existing non-player definition in the selected data
root. `player`, unknown IDs, missing coordinates, contradictory `type`/`kind`,
weighted creatures and unsupported fields such as count, groups or overrides
fail validation. Creatures in ordinary buildings, plazas and entrance layouts
remain unsupported, including specials those routes otherwise leave inactive.
An authored room is centered and translated into the 80×43 scene; it is never
rotated or mirrored. A requested vertical-mirror preview fails explicitly.

Before any batch objects are committed, initial actor cells must be walkable,
free of blocking decor/containers (including later records), distinct from
other authored actors, the actual player arrival and every physical up/down
stair. Terrain with `creature_passable:false` also requires `can_swim:true` on
the creature; swimming never permits walls or blocking decor. Floor items can
share an actor cell, as the example's wood bundle does. A corridor guard is
legal: the whole route to the exit is not reserved from enemies. These are
construction rules; movement, combat and internal native populations keep
their existing policies. A failed record/factory leaves the candidate's object
layers and live scene publication untouched.

From the repository root, using the established interpreter:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/structure_authoring.py roguelike/docs/examples/g17_authored_creature_room.json --route authored_submap --access roguelike/docs/examples/g17_authored_creature_room.access.json --output .baseline/g17-room-preview.json
```

The existing CLI compiles the candidate and uses the production layout transform,
scene builder and factory. `population_receipts` retain source asset/path,
record identity, original `source_xy`, final `xy`, serialized actual actors and
their count, plus the consumed creature definition's semantic SHA-256. The
report supplies world/scene seeds, scene address and candidate/catalog identity.
Actor receipts use actor serialization, separately from item/container objects.
The revealed diagram and static access checks inspect geometry and initial
occupancy. They do not imply safe passage past a hostile actor or establish
encounter balance.

The example is documentation, outside `data/layouts/`; it adds no native
destination or catalogue membership. To use an authored layout in play, explicit
`SubMap.layout_id` binding is still required. Blank saved IDs keep BSP generation,
regardless of `submap_type`. G17 changes the authoring manifest to `g2-2` and
refreshes its editor catalogue without changing `structure-v1` placement hashes,
world/scene revisions, save schema or old source definitions. Existing authored
layouts without creatures, including the starting laboratory, retain their route.

G16's `commercial/workshop_b.json` is a complete versioned furnishing example:
12×9 envelope, double southern entrance, all four rotations, table terrain,
hanging-cloth decor, supported item/text/scene specials and one real crate.
The crate uses independent `workshop_b_musk` and `workshop_b_fuel` pools, each
`roll_count: [1,1]` with one positive-weight item. This guarantees both goods;
they never compete in one weighted draw. `interior_loot_table` is not used.
Clear southern floor supports the existing paid fire/drying route; scenery
supplies neither a functional workbench nor heat. Required targets and the full
door span pass populated access in every rotation. Only grid/roadside commercial
membership changes from `workshop_a` to `workshop_b`, preserving order, weight
1.0 and cap 5. Keep the old definition and its dependencies for saved plans;
never retrofit stock into old pending/visited workshops. The new readable note
is local to this variant and changes no recipe-known or unlock flags.

Current: **G7, world/scene revision `wg7`, shared plan format 5**.
For the installed mixed single/compound policy, start with the
[G7 workflows](#g7-compounds-a-place-with-shared-access-and-two-or-three-buildings).
The six G5 recipes remain supported for towns and the featured landmark. The
[G6 workflows](#g6-additional-country-road-sites) retain the explicit version-1
single-site policy. The later direct-stamp
sections describe the supported legacy route, not the current selection policy.

## Saved worlds first

G15 demonstrates a versioned stock change: `apothecary_b` copies the original
apothecary geometry, access and other containers. Its medicine chest adds a
separate guaranteed `apothecary_b_treatment` pool alongside `alchemist_reagents`.
Each pool rolls independently, so the one dressing does not replace reagents.
Only the two grid/roadside commercial memberships change (weight 1.0, cap 5).
`apothecary_a`, shared pools and old saved selections remain available unchanged;
visited containers are never backfilled. Use a new asset/dedicated pool for this
kind of new-plan reward change rather than changing an old dependency in place.

Role membership, frequency, caps and repetition settings affect **new plans**.
Visited maps retain actors, changes and taken contents. Pending old placements
keep their saved asset, transform, geometry and identity. No selection runs on
load, F9, scene arrival or revisit. Changing a consumed layout, item, container,
terrain rule or other structural dependency blocks only affected pending
placements; restoring compatible definitions makes them usable again. Loading,
visited maps and unrelated pending scenes remain supported. Keep referenced
factory IDs available. There is no automatic personal-campaign migration.

Format-1 G3, format-2 G4, format-3 G5 and format-4 G6 plans retain their exact values.
Existing saved `wg3`, `wg4`, `wg5` and `wg6` scenes retain their original provenance.
Newly created scenes use `g3-to-g7-v1`, `g4-to-g7-v1`, `g5-to-g7-v1`,
`g6-to-g7-v1` or `g7-v1` as appropriate, with the unchanged
`structure-v1` dependency projection. Absent/wg1/wg2 origins keep legacy/no-plan
dispatch. Travel never writes an F5 checkpoint.

## What makes a building eligible

A drawn rectangular layout supplies terrain and supported contents. Its explicit
`placement` profile opts into contexts and defines transforms, buffer, entrances
and goals. A role entry in `data/generation/settlement_profiles.json` makes it a
selection candidate. The production fitter must still find room for the entire
building, buffer and primary approach within one 80×43 storage chunk.

Contexts (`grid`, `roadside`, `civic`, `landmark`, `compound`) describe placement geometry.
Compound slots use recipe memberships in `data/generation/compounds/`; the mixed
parent policy is `data/generation/poi_profiles.json`. A compound child must have a
required usable target and is certified through its complete parent preview.
Plot roles (`residential`, `commercial`, `support`, `civic`, `landmark`) select
eligible assets before fitting. A commercial plot does not create a merchant,
shop UI or quest. Native member roles still use `native-town-v1`: the standard
grid is civic plus residential members; roadside is market plus residential.
The grid's civic anchor remains `bell_tower_a` with a physical spent bell.

New geometry settings use version 2 in the existing `g3_config.json` filename.
The separate selection file is the authoritative role membership source.
Version-1 explicit geometry overrides retain their historical flat-pool meaning
and produce format-2 plans; they are an explicit compatibility path. Saved
format-3 `settings.pools` is a derived diagnostic projection, not another editable
source. Do not add pools to the version-2 configuration.

## 1. Add a house with a service door

G8 note: the roadside demonstration uses seed 0; the former seed 20261023 leaves this valid draft unselected under the new lot distribution. This is a controlled authoring example, separate from the fixed ordinary seed matrix.

The complete [g5_service_house.json](examples/g5_service_house.json) has a south
main door and a north required service door. Start from it in a draft directory.
All commands below run from `G:\GameDev\RoguelikeProject`:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force authoring | Out-Null
if (-not (Test-Path -LiteralPath authoring/g5_service_house.json)) {
  Copy-Item roguelike/docs/examples/g5_service_house.json authoring/g5_service_house.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_service_house.json --route ordinary_building --category residential --orientations --output evidence/authoring/g5-house-orientations.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_service_house.json --planned --category residential --role residential --context grid --seed 20261023 --output evidence/authoring/g5-house-grid.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_service_house.json --planned --category residential --role residential --context roadside --seed 0 --output evidence/authoring/g5-house-roadside.json
```

Import that draft into `layout_painter.html`. Give copies unique IDs with **Apply
ID**; paint a complete rectangle and declare each full doorway span separately
in the **placement** metadata panel. `width` runs toward positive x on N/S edges
and positive y on E/W edges. Never span a wall between doors. Main/service is an
entrance role, independent of the plot role. The fitter prefers the eligible main
door, then lexical entrance ID, and records `frontage_entrance`. Old plans derive
that choice from their saved normal and approach without rewriting any data.

Only that selected span must occupy the primary approach. Every required door
must still be reachable from the same assigned road join, including through the
interior. An independent exterior service route is not promised. Required goals
use `floor`, `item`, `readable`, `container`, `stairs_up` or `stairs_down`; choose
actual interaction positions for blocking objects. `--orientations` checks all
declared door cells and goals in every permitted transform. Unsupported opaque
coordinate metadata fails rather than silently rotating incorrectly.

## 2. Add commercial or support content

The complete [g5_workshop.json](examples/g5_workshop.json) retains the workshop's
two-cell entrance, readables and `scholar_desk` scene, and adds a real tool crate.
Its supported records include:

```json
{"x":8,"y":5,"type":"container","decor_id":"crate","loot_pools":["storage_tools"]}
```

The matching required target is `{"x":8,"y":5,"kind":"container","required":true}`.
The full example also contains readable `item` records with real `text_id`s and
a `scene` record, so it can be tested without reconstructing snippets.

```powershell
if (-not (Test-Path -LiteralPath authoring/g5_workshop.json)) {
  Copy-Item roguelike/docs/examples/g5_workshop.json authoring/g5_workshop.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_workshop.json --route ordinary_building --category commercial --orientations --output evidence/authoring/g5-workshop-orientations.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_workshop.json --planned --category commercial --role commercial --context grid --seed 20261023 --output evidence/authoring/g5-workshop-grid.json
```

Containers require reachable interaction positions under the engine's range and
corner rule. Painted furniture is not automatically a populated container.
House hearths are obstacles; the shepherd's explicit hearth-container special is
populated. The hunter cabin's furniture glyphs remain floor and its only authored
content is a readable. Legacy hunting loot metadata supplies no stock here.
Shop and apothecary entries currently use legal diagonal movement around an
inward wall. Their actual routes are certified; no new trading/crafting service
is implied by counters or tools.

### A stocked, versioned example (G13)

`data/buildings/storage/tool_shed_b.json` preserves the old shed's 8×6 envelope,
entrance, rotations, buffer and frontage approach. Its two crates and provision
barrel use real `special_tiles` container records at the three required container
targets. A table is actual `table` terrain, the candle is `decor_candle` in
`decor_layer`, and the wood beside the table is a real floor item. Use existing
visible assets: some other decor IDs have descriptions and interaction support
but no current sprite or tile fallback. Painted letters mapped to floor do not
make furniture.

The three `tool_shed_b_*` loot pools are local to this version. The bag crate
uses a singleton pool with `roll_count: [1,1]` and one `leather_satchel` entry;
the tool and provision pools contain no bags. The existing 0.8 kg satchel gives
its ordinary 10% effective carrying reduction when equipped.

Only the grid and roadside support memberships select `tool_shed_b`, retaining
weight 1.0 and cap 3. `tool_shed_a`, its shared dependencies and compound recipe
memberships remain intact. Saved selections and visited contents keep their
existing version. For a content change, copy to a new ID and use new local pools;
do not edit the old version or a shared pool to replenish saved worlds.

Validate this installed version with the orientation check and a fresh world;
an assigned preview alone does not establish ordinary selection:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py roguelike/data/buildings/storage/tool_shed_b.json --route ordinary_building --category storage --orientations --output evidence/authoring/g13-shed-orientations.json
```

At seed 20261023 the installed fresh support cohort includes chunk `(75,99)`;
this is a reproducible example, not an all-seed nearby-start guarantee. The
bounded real-input acquisition and persistence record is in
[`docs/owner/GAMEPLAY_G13.md`](../../docs/owner/GAMEPLAY_G13.md).

## 3. Offer another landmark

[g5_landmark.json](examples/g5_landmark.json) copies the certified waymarker
shelter to a unique draft ID. It has two separated required doors, a readable,
a coffer and a blocking waystone declared in the terrain legend. The production
stamper converts that legend ID into decor on its base tile. Its floor goal is beside the waystone,
not on it. The real interaction handler recognizes the realized decor representation.
The static handoff described it as terrain; runtime evidence corrects that claim.

```powershell
if (-not (Test-Path -LiteralPath authoring/g5_landmark.json)) {
  Copy-Item roguelike/docs/examples/g5_landmark.json authoring/g5_landmark.json
}
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_landmark.json --route ordinary_building --category wilderness --orientations --output evidence/authoring/g5-landmark-orientations.json
& $ResonancePython -X utf8 tools/structure_authoring.py authoring/g5_landmark.json --planned --category wilderness --role landmark --context landmark --selection-config roguelike/docs/examples/g8_landmark_preview_selection.json --seed 29417 --output evidence/authoring/g5-landmark.json
```

Register an installed alternative in `profiles.landmark.roles.landmark`. Its
profile must explicitly permit `landmark` and a connected `spur`. The assigned
road join, bounded approach, all required doors and usable goal must pass. There
is still exactly **one geographical landmark**. Three sample worlds cannot
establish the natural frequency of every alternative.

## 4. Tune settlement character

Use [g5_selection_example.json](examples/g5_selection_example.json), a complete
working configuration. It doubles the grid apothecary role multiplier, reduces
the original house cap to four, and changes the local repeat multiplier to 0.1.
Preview this policy without installing it:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --selection-config roguelike/docs/examples/g5_selection_example.json --output evidence/authoring/g5-tuned-world.json
```

In `profiles.grid.roles.commercial`, the apothecary entry becomes:

```json
{"asset":"apothecary_a","weight":2,"max_per_settlement":5}
```

The installed `schedule` is `["commercial","residential","support","residential"]`.
Slots are stably ordered by Manhattan distance from the original civic/arrival
slot, with coordinate/normal tie breaks. Required civic, commercial and residential
assignments are reserved first. The schedule applies to remaining slot indices,
giving a commercial focus near arrival and a residential/support mix farther out.
Minima are one residential and one commercial per settlement, plus one grid bell.
Support is optional. Required transform-fit trials use bounded backtracking (256 by
default), revisiting an earlier asset's alternative transforms when a later role fails.
Exhaustion rejects the candidate world atomically and distinguishes an exhausted
budget (feasibility unresolved) from exhausting all enumerated alternatives.

## 5. Control repetition

The effective draw weight is **placement base weight × role weight × repeat
multiplier**. The penalty applies if the asset matches the nearest accepted plot
in stable slot order (ties use the earlier order). Draw the asset once, then try
its permitted transforms; more orientations do not multiply its weight. Failed
trials consume no accepted cap. Unordered asset membership order, process hash seeds and gameplay RNG
do not change the saved result.

Set `max_per_settlement` in an asset's role entry for a hard limit. It counts
accepted instances across all members of that one settlement. The landmark has
its own one-site scope. Duplicate asset membership across roles within one
profile is rejected. `repeat_multiplier` is soft: the repeated asset remains
eligible at lower weight. A single remaining eligible choice records an explicit
soft fallback; other repeats are labeled weighted repeats. Hard caps are never
exceeded. Optional plots become explicit vacant gardens if nothing fits. Required
minima either fit within the budget or fail with the role, budget and last reasons.

## Active controls

All paths below are under `roguelike/data`. Except structural edits noted below,
these controls affect **new planning only**, never saved selection or visited maps.

| File/key | Units, default and valid range | Effect |
|---|---|---|
| `generation/g3_config.json:version` | 2; explicit legacy override 1 | Geometry/selection schema dispatch. |
| `selection_profile_version` | 1 | Requires the separate profile schema. |
| `settlement_count` | inclusive [2,4], integer endpoints 2..8 | Number of existing-form settlements. |
| `minimum_separation_chunks` | 12, 3..128 chunks | Euclidean settlement-anchor separation. |
| `near_start_radius_chunks` | 10, 2..128 chunks | One counted site near the start. |
| `forms` | exactly [grid,roadside] | Alternating existing forms. |
| `road_width_tiles`, `street_width_tiles` | 3, integer 1..5 tiles | Actual full assigned road bands. |
| `plot_spacing_tiles` | 18, integer 14..40 tiles | Slot spacing, not an occupancy promise. |
| `setback_tiles` | 2, integer 1..8 tiles | Minimum setback; profile approach may increase it. |
| `max_spur_tiles` | 12, integer 2..24 tiles | Maximum complete primary approach length. |
| `route_search_nodes` | 16384, integer 16..65536 | Per-route search bound. |
| `site_search_limit` | 16384, integer 1..16384 | Candidate site bound. |
| `generation/settlement_profiles.json:version` | 1 | Selection schema; profiles stored once per plan. |
| `profiles.<form>.id` | nonempty string; `<form>-mixed-v1` | Persisted profile identity. |
| `roles.<role>[].asset` | unique installed ID with explicit context | Candidate membership. |
| `roles.<role>[].weight` | 1, finite >0..1000 | Multiplier on base placement weight. |
| `roles.<role>[].max_per_settlement` | 5 ordinary, 3 support, 1 civic/landmark; integer 1..128 | Hard accepted-instance cap. |
| `minimum.<role>` | residential/commercial/civic/landmark 1, support 0; integer 0..8 with obligations retained | Required accepted count; total caps must suffice. |
| `schedule` | commercial,residential,support,residential | Nonempty optional role sequence; civic excluded. |
| `repeat_multiplier` | 0.2, finite (0,1] | Soft nearest-occupied-slot repeat preference. |
| `required_fit_budget` | 256, integer 1..4096 transform-fit trials | Required-role backtracking bound. |
| `buildings/...:placement.version` | 1 | Explicit supported structural contract. |
| `placement.contexts`, `placement.weight` | explicit contexts; base weight finite >0..1000 | New-plan selection only; excluded from structural hashes. |
| `placement.rotations`, `mirror_x` | explicit quarter turns; boolean mirror before rotation | Consumed geometry; changing affects pending dependency compatibility. |
| `placement.buffer`, `approach` | integer 0..8 tiles | Reserved geometry; affects pending compatibility. |
| `placement.road_relation` | frontage/spur/remote | Remote cannot satisfy connected pools. |
| `placement.entrances`, `targets` | source coordinates, outward spans, typed goals | Required access; affects pending compatibility. |

Legacy `allowed_in`, `rotatable`, `facing`, `district_weights`, top-level `weight`
and `town_config.json` do not acquire new shared-plan meanings. Native population,
presentation and text retain their established policies.

## 6. Diagnose and install deliberately

Run a known context mismatch to see a real error: the landmark example with
`--planned --context grid --category wilderness` fails. Use its declared landmark
context instead. Other reasons remain distinct:

| Diagnostic | Actual cause and repair |
|---|---|
| missing explicit context / candidate eligibility | Add a deliberate supported context or choose the correct one. |
| role membership / hard cap | Register the intended role, correct its ID, or deliberately change its cap; geometry edits cannot fix this exclusion. |
| no eligible permitted transform | No declared orientation faces that assigned road; permit a meaningful orientation. |
| footprint/buffer or private approach conflict | Exclusive reserved space overlaps; alter footprint/buffer or slot spacing. Assigned public road cells alone may be shared. |
| buildable plot / storage chunk | Insufficient width/depth for footprint, buffer or approach; inspect the exact half-open rectangles. |
| complete required entrance / content inaccessible | Inspect full spans, blocking decor and actual interaction corners; preserve separate doors instead of making them optional. |
| required role minima infeasible | Read exhausted role and transform-fit trial budget; provide a fitting eligible asset/cap. Do not silently remove the role. |
| changed dependency | Restore compatible consumed definitions for that pending saved placement, or create a fresh disposable world for edited content. |

`--planned` registers a draft only in memory in the selected role, retaining the
installed mixed policy. It can honestly report “not selected/fitted” for the
chosen seed. Controlled cohort tests are labeled separately from natural samples.
Inspect the JSON plan's plots, rejections, roles, frontage IDs and receipts; SVG
diagrams show the assigned roads, joins, approaches and vacancies. Production
renderer PNGs are labeled separately in the G5 evidence.

To install a reviewed draft, copy it to a **new** filename in the existing category
folder only if that filename is absent, then add its exact ID to the intended
role array. For example `profiles.grid.roles.residential` can include:

```json
{"asset":"g5_service_house","weight":1,"max_per_settlement":4}
```

```powershell
if (-not (Test-Path -LiteralPath roguelike/data/buildings/residential/g5_service_house.json)) {
  Copy-Item authoring/g5_service_house.json roguelike/data/buildings/residential/g5_service_house.json
}
# After the deliberate role-table edit:
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/authoring/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
```

Catalog freshness uses current raw checkout bytes, separately from semantic save
compatibility. Reload the painter after refreshing. The live corpus remains 64
documents; the frozen 65 original codec documents remain untouched. Both browser
tests import/edit/download real JSON with separated entrances and a weighted
special, then feed those downloaded bytes through the Python compiler and mixed
planned preview. This does not claim every control was tested on every asset.

Autonomous recipe and acceptance commands:

```powershell
& $ResonancePython -X utf8 tools/verify_g5_authoring.py --evidence evidence/worldgen-g5/authoring
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --game roguelike --evidence evidence/worldgen-g5/focused
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/worldgen-g5/browser
& $ResonancePython -X utf8 tools/worldgen_g5_diagnostic.py --journey --evidence evidence/worldgen-g5/diagnostic
& $ResonancePython -X utf8 tools/verify_d.py
```

The expanded focused gate has a 600-second bound and runs alone; browser workers
retain 150-second bounds. The recipe verifier uses disposable drafts and a
disposable data catalog for installation, retains exact commands/hashes and checks
that repeated initialization preserves edit sentinels. Optional play uses
`tools/play_disposable.py --seed 20261023 --session g5-first` with a fresh session
name; routine verification does not depend on owner play or a desktop takeover.

G4 correction: its timed scene sample included the capital gateway, not the
required crossing. G5 labels that timed set accurately and records crossing
coverage separately. The standard grid's non-civic native members are residential.


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
   all 58 installed building candidates. No demonstration building is installed by G2.

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

The live catalog has 56 ordinary buildings, two plazas, six entrances and one
60×16 authored lab. It retains the original 12 residential definitions. There are
14 loot pools. One object per file is required. Duplicate building/plaza IDs are
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
  --game roguelike --evidence evidence/worldgen-g7/focused
& $ResonancePython -X utf8 tools/verify_structure_editor.py `
  --evidence evidence/worldgen-g7/browser
& $ResonancePython -X utf8 tools/verify_d.py
```

The browser test uses pinned **Playwright 1.64.1**, Chromium and Firefox with isolated
headless profiles. It drives real file input, editing, download, resize cancellation,
undo/redo and the width60 lab. Downloaded JSON then crosses the same Python command
and current random pool. The 65 original plus 64 delivered round-trips are supplementary
model checks. Browser tests have 240-second per-browser bounds; the expanded focused
Python suite has a 1200-second bound. The unfiltered full D gate includes B1/B2/B3/C.

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

G6 selection correction: required search revisits each feasible transform of an
asset before moving to the next weighted asset. One budget unit is one geometric
transform fit, or one asset trial with no eligible frontage. Transform-profile
inspection is bounded to eight options per asset. Exhausting the budget reports
that feasibility remains unresolved; exhausting all enumerated alternatives is
a separate failure. Failed branches own no placements, dependencies or caps.
Asset membership lists are canonicalized for fresh plans; optional role schedules
remain intentionally ordered. Saved G5 selections are never normalized on load.

## G6 additional country-road sites

This section preserves the explicit **version-1 single-site workflow**. G7's
installed default is version 2 and includes compounds; deliberately installing a
version-1 example is an explicit opt-out from compounds for new worlds. Existing
saves retain their resolved policy. See the G7 section below for the current default.

New worlds keep one required featured landmark and draw a separate desired count
of **two through four additional sites**. Every accepted site has one building,
one rural storage chunk and its own mutable contents. The planner reserves towns,
special anchors, bridges and the featured landmark first. It samples existing
straight country roads; it does not build new country routes to chase extra sites.
Sites stay rural: no merchant, town district, quest or new native AI policy is implied.

### 1. Create and edit a complete site draft

Start in `G:\GameDev\RoguelikeProject`. The complete example is
`roguelike/docs/examples/g6_wayhouse.json`: a 6×5 shelter, four quarter turns,
south primary and separate required service door, readable road marker, populated
coffer using `shrine_offering`, and a reachable floor goal. Its explicit placement
context is `landmark`, which certifies a rural-capable layout. Membership in the
additional-site policy is separate from membership in the featured-landmark pool.

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
New-Item -ItemType Directory -Force authoring/g6 | Out-Null
if (-not (Test-Path -LiteralPath authoring/g6/g6_wayhouse.json)) {
  Copy-Item -LiteralPath roguelike/docs/examples/g6_wayhouse.json -Destination authoring/g6/g6_wayhouse.json
}
if (-not (Test-Path -LiteralPath authoring/g6/poi_profiles.json)) {
  Copy-Item -LiteralPath roguelike/docs/examples/g6_poi_example.json -Destination authoring/g6/poi_profiles.json
}
```

Open `layout_painter.html`, import the draft, edit terrain/content and Placement
metadata, then use **Export** to download JSON. Keep the original draft and download
separate until validation succeeds. Repeating the initialization above preserves
your edits. Unknown metadata and ordered arrays retain the existing codec rules.
A painted shelf, hearth, `c` or counter is not a usable container. Use a real
`special_tiles` container with a valid `decor_id` and nonempty loot-pool contents;
declare its required target as `container`. Doors and goals must be explicit.

### 2. Preview the actual downloaded file and both road axes

Use the download's real path in place of `$Candidate`; do not reconstruct it by hand.
`--assigned-site` is a disclosed controlled preview with count one, that asset only,
and a required frontage normal. It still runs the production fitter, protection,
complete contents, native population and final access checks.

```powershell
$Candidate = 'authoring/g6/g6_wayhouse.json'
& $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --route ordinary_building --category wilderness --orientations --output evidence/g6-owner/direct.json
foreach ($Normal in @('N','E','S','W')) {
  & $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --assigned-site $Normal --category wilderness --output "evidence/g6-owner/assigned-$Normal.json"
}
& $ResonancePython -X utf8 tools/structure_authoring.py $Candidate --site --category wilderness --poi-config authoring/g6/poi_profiles.json --output evidence/g6-owner/selected.json
```

N/S entrances face horizontal roads; E/W face vertical roads. JSON includes the
parent route, segment, exact join, side, canonical placement and content receipts.
The adjacent SVGs distinguish whole-world plan diagrams, detailed attachment
diagrams and complete-scene diagnostic snapshots. Actual gameplay-renderer PNGs
are retained separately in G6 verification. A successful direct preview does not
guarantee ordinary selection. A valid but unselected draft exits with an explicit
message; inspect a world-plan report to see the accepted cohort and exclusions.

### 3. Register and deliberately install after validation

Active files are `roguelike/data/buildings/wilderness/<id>.json` and
`roguelike/data/generation/poi_profiles.json`. Each `assets` member contains
`asset`, positive `weight` and integer `cap`. The complete example policy adds
`{"asset":"g6_wayhouse","weight":1,"cap":2}` to the four installed assets.
Previewing drafts does not install them. When satisfied, these commands deliberately
install the draft and policy; retain your edited drafts as the authoring originals.

```powershell
Copy-Item -LiteralPath authoring/g6/g6_wayhouse.json -Destination roguelike/data/buildings/wilderness/g6_wayhouse.json
Copy-Item -LiteralPath authoring/g6/poi_profiles.json -Destination roguelike/data/generation/poi_profiles.json
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/g6-owner/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --output evidence/g6-owner/installed-world.json
```

The automated authoring verification executes installation in a disposable **data
catalog**, preserving production assets. A new world editor is unnecessary.

### 4. Tune counts, repetition and space

Edit a draft policy, preview using `--world-plan --poi-config <draft>`, then install
it. The inclusive desired count is drawn once and saved. Reaching it completes
selection. Falling short may still publish if the configured minimum was reached;
the saved `site_selection.shortfall_reason` explains why. Falling below the minimum
rejects the entire new world. Even extras above the minimum become durable obligations.

| Control | Default and limits | Meaning |
|---|---|---|
| `minimum`, `maximum` | 2, 4; integers 0..8, minimum ≤ maximum | Desired count range. Zero minimum is an explicit owner choice. |
| asset `weight` | 1; finite positive ≤1000 | Multiplied by the layout's placement base weight. More transforms do not add weight. |
| asset `cap` | 2; integer 1..8 | Hard accepted count across additional sites. Featured landmark excluded. Sum must satisfy minimum, not maximum. |
| `repeat_multiplier` | 0.2; finite (0,1] | Soft penalty for matching the nearest already accepted site's asset. Manhattan join distance; ties by site ID. |
| `spacing_tiles` | 80; integer 1..4096 | Minimum Manhattan distance between additional-site joins, in world tiles. |
| `town_clearance_tiles` | 24; integer 0..256 | Manhattan distance from join to the town's protected outer rectangle. |
| `junction_clearance_tiles` | 12; integer 1..80 | Manhattan distance from join to perpendicular road intersections/bends. Straight collinear overlap is not a junction. |
| `locations` | plains, forest, heath | Supported rural biome IDs; no water chunks, towns or special-anchor chunks. |
| `sample_step_tiles` | 16; integer 8..80 | Fixed world-coordinate sampling lattice along existing roads. |
| `enumeration_limit` | 8192; integer 1..65536 | Maximum raw road-side sample examinations, then deduplication. |
| `candidate_limit` | 512; integer 1..4096 | Maximum seeded, canonical candidate joins considered. |
| `fit_budget` | 1024; integer 1..4096 | Maximum real transform fits, including empty-frontage asset trials. |

The single spur-length authority remains `max_spur_tiles` in
`roguelike/data/generation/g3_config.json` (default 12). Buffer/entrance geometry
belongs to each consumed layout. There is no second POI spur-length setting.
The default 80/24/12 spacing and 16-tile sampling meet the minimum for ordinary
seeds 0, 20261023 and 29417 without geometry relaxation. The 80-tile join spacing
roughly equals one horizontal storage chunk; one-site-per-chunk also applies on
the shorter 43-tile vertical dimension. Local repetition is a preference, not a
distinct-asset quota. Discarded trials spend no cap and create no map destinations.

To demonstrate an allowed shortfall, use only `hunter_cabin` with cap 2, minimum 2
and maximum 4. Seed 20261023 requests 3 and accepts 2, reporting hard-cap exhaustion.
To demonstrate valid nonselection, set both count bounds to zero and run the same
draft with `--site`; the candidate is eligible but unselected. To test a rejected
minimum, keep minimum 2 and set `fit_budget` to 1. These are controlled examples,
not ordinary installed-policy frequency measurements.

### 5. Diagnose a failed attachment

Read `site_selection.rejections` and its bounded `examples`, then the accepted
plot's rejected-transform messages. `--assigned-site E` cannot admit an asset
whose permitted entrances only face N/S. Both sides must fit the complete building,
buffer, full doorway span and access inside one 80×43 storage chunk.

| Message | What to inspect |
|---|---|
| parent/join mismatch, join outside actual parent segment | Exact saved country-route ID and segment; a nearby different road cannot satisfy it. |
| approach is blocked, entrance span inaccessible | Full main/service doorway spans and blocking container/decor placement after all content. |
| footprint/buffer or approach conflicts | Named water/bank, private reservation or assigned road; do not erase required space. |
| bridge deck or approach clearance | Choose an ordinary road segment away from the protected crossing. |
| spans a storage chunk | Move the join or choose a fitting permitted orientation/layout. |
| no eligible permitted transform | Declare only orientations that have actually passed direct previews. |
| hard cohort caps exhausted | Raise a deliberate cap/add an eligible asset, or accept the recorded shortfall above minimum. |
| POI minimum failure | No world was published. Check budget, candidate geometry, eligibility and minimum. |

### 6. Understand what an edit changes

Counts, memberships, weights, caps, spacing and search limits affect **new worlds**.
Saved pending sites use their saved resolved policy and exact chosen placement.
Consumed layout or item/container/factory changes can block only an affected pending
scene, with asset/dependency context. Visited scenes keep player mutations, objects
and their actual creation revision. Revisit, cold load and F9 do not refill, reselect,
rebuild a road or run generation again for a visited scene. Historic G3/G4/G5 worlds
gain no new sites. G6 sites never become fake towns or duplicate Chunk blueprints.

Execute all workflows and both actual browser-download paths with:

```powershell
& $ResonancePython -X utf8 tools/verify_g6_authoring.py --evidence evidence/g6-owner/workflows
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/g6-owner/browser
```

The workflow log records positive and expected-negative exit codes separately,
commands, cwd, environment and output hashes. Existing 65-document round trips and
the six G5 recipes remain part of verification. `UI-TEXT-HEIGHT` and large-world
retention/streaming remain deferred; G6 does not implement multi-building compounds.

## G7 compounds: a place with shared access and two or three buildings

A compound is one additional destination with one country-road entrance, one
reserved envelope and one complete saved chunk scene. Child buildings have stable
slot identities and separate containers/items. Their doors face a named common
path inside that envelope. Two required child slots and at most one optional slot
are supported; an admitted optional child is just as durable as a required child.
These places remain rural. Parent counts, child counts and container counts are
different quantities; none creates a merchant, quest or town district.

The installed files are:

- `roguelike/data/generation/compounds/homestead_workyard.json`: 44×16, rotations
  0/180, hearth house and tool shed, optional storehouse, a three-tile external gate.
- `roguelike/data/generation/compounds/wayside_shrine_court.json`: 18×14, all four
  rotations, shrine and shelter, a two-tile gate and common court.
- `roguelike/data/generation/poi_profiles.json`: version-2 mixed parent policy.
- Child layouts remain in `roguelike/data/buildings/<category>/<id>.json`.

Every declared recipe rotation has passed production fitting and full population.
The house, shed and storehouse still permit only 0/180; the homestead cannot turn
sideways. Context eligibility was extended without changing `structure-v1`
geometry, content or transform permissions. Recipes themselves are resolved once
into saved placements/paths and are not dependencies of unseen saved scenes.

### 1. Create complete drafts without replacing your edits

Run from `G:\GameDev\RoguelikeProject` with the established environment:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/structure_authoring.py --init-compound authoring/g7
```

This creates three complete files, copying only missing files:
`g7_travellers_court.json`, `g7_wayhouse.json`, and `g7_poi_example.json`.
Repeating the command preserves every existing file, including deliberate edits.
The complete originals are in `roguelike/docs/examples/`. Initialization does not
install anything. Keep the drafts as your editable originals.

Recipe coordinates are local integer tile cells. `size` is the outer width/height;
rectangles are `[left, top, right, bottom]` with the right/bottom excluded. The
gate's `normal` points outward from the envelope, and `width` covers its full span.
The gate names its common `path`. A path has named reciprocal `joins` when there
are multiple paths; physical diagonal contact alone is insufficient. Its `rects`
are actual protected walkable ground, not a suggestion to find empty terrain.

Each child slot declares a stable `id`, a purpose in `role`, `required`, a private
`buildable` rectangle, a `path`, a tile `join` on that path, an outward building
`normal`, base child `rotations`, and weighted `assets`. Slots are intentionally
ordered: the two required slots first, then the optional slot. Do not reorder IDs
to tune weighting. Asset memberships, path memberships and rotation sets are
unordered and canonicalized. A child must fit its full buffer inside its buildable
region. Neither a private region nor a sibling buffer may consume circulation.

`fit_budget` is 2..256 actual child transform attempts per parent trial, including
backtracking. Active recipes are first certified in isolated geometry for every
declared rotation under that same finite limit. Country-location search then has
the shared policy budget; one parent transform plus its child attempts consumes
that budget. The sole external spur-length authority remains `max_spur_tiles` in
`g3_config.json`; recipes do not override it. There is no mirroring of whole recipes.

### 2. Reuse or paint a real child

Open `layout_painter.html`, import `authoring/g7/g7_wayhouse.json`, edit, and use
**Export**. Keep the actual downloaded file and use its path as `$Child` below.
The placement panel displays the `compound` context; it preserves the complete
object and unknown metadata. The production CLI is the validator.

```powershell
$Child = 'authoring/g7/g7_wayhouse.json' # replace with the actual browser download
& $ResonancePython -X utf8 tools/structure_authoring.py $Child --route ordinary_building --category wilderness --orientations --output evidence/g7-owner/child.json
```

A painted shelf/counter is only decoration. Populate a container through a real
`special_tiles` container with valid `decor_id` and `loot_pools`, then declare a
reachable required container target. Keep at least one `required: true` usable
target in every child/additional-site candidate. Optional targets can coexist.
An all-optional document remains legal for direct/legacy consumers, but connected
parent/child admission rejects it before fitting with the asset, context and fix.

The downloaded child's `id` must match the recipe slot membership. If you rename
it in the painter, edit the recipe's asset membership to that exact ID. Base child
rotation plus parent rotation must be permitted by the child's own profile; the
recipe cannot grant new rotations. Required secondary doors and wide main doors
are checked after all children, contents, dressing and native actors are created.

### 3. Preview the complete place on both road axes

```powershell
$Recipe = 'authoring/g7/g7_travellers_court.json'
& $ResonancePython -X utf8 tools/structure_authoring.py --compound $Recipe --child $Child --assigned-compound S --output evidence/g7-owner/court-horizontal.json
& $ResonancePython -X utf8 tools/structure_authoring.py --compound $Recipe --child $Child --assigned-compound E --output evidence/g7-owner/court-vertical.json
& $ResonancePython -X utf8 tools/structure_authoring.py --compound $Recipe --child $Child --poi-config authoring/g7/g7_poi_example.json --seed 20261023 --output evidence/g7-owner/natural.json
```

`--child` may be repeated for multiple actual drafts. `--assigned-compound` is a
labelled one-parent controlled policy using ordinary protected country candidates,
the shared production fitter and the complete materializer. N/S gates face
horizontal roads; E/W face vertical roads. `--compound-rotation 90` optionally
restricts the assigned preview to one already-permitted orientation (the example's
90° gate faces W). A preview never installs a recipe/child/policy.

Outputs include the entire resolved plan, child receipts, status, detailed parent
plans and populated diagnostic SVGs. These SVGs are diagrams; production-renderer
PNG evidence is separate. Ordinary eligible but unselected drafts return success
with `status: "valid but unselected"`, zero preview scenes and the actual plan.
For a reproducible nonselection, copy the policy and set both count bounds and both
kind minima to zero. A rejected definition/fitting minimum exits 1 with a diagnosis.

### 4. Register and install deliberately

After successful previews, install the complete files explicitly:

```powershell
Copy-Item -LiteralPath $Child -Destination roguelike/data/buildings/wilderness/g7_wayhouse.json
Copy-Item -LiteralPath $Recipe -Destination roguelike/data/generation/compounds/g7_travellers_court.json
Copy-Item -LiteralPath authoring/g7/g7_poi_example.json -Destination roguelike/data/generation/poi_profiles.json
& $ResonancePython -X utf8 tools/structure_authoring.py --catalog --output evidence/g7-owner/catalog.json
& $ResonancePython -X utf8 tools/structure_authoring.py --refresh-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --check-editor-catalog
& $ResonancePython -X utf8 tools/structure_authoring.py --world-plan --seed 20261023 --output evidence/g7-owner/installed.json
```

Match the destination filename to the child's declared ID if renamed. For a
disposable catalog, use `--data-root <copied-data-directory>` and
`--editor-catalog <review-directory>/catalog.js` with refresh/check. This verifies
installation without altering the production editor catalog. Only data is copied;
game code always imports the production checkout. A new graphical recipe editor
or separate game checkout is unnecessary.

### 5. Replace children, expand the yard and tune selection

Replace a slot's `assets` entry with another eligible child (for example, a second
`roadside_shrine_a` in the shelter slot), then repeat direct/assigned previews.
Children of the same asset still get distinct slot-prefixed mutable content.
For a third building, start with the homestead template's two required slots and
then append its complete `stores` slot; its explicit private region and yard join
are already certified. An optional slot may be omitted with a saved reason if its
asset cannot fit. Its failed plot/dependency/reservation branch leaves no residue.

The shrine example's court can move/resize from `[1,8,17,14]` to `[2,8,17,14]`
while retaining both joins and its gate connection. Restrict `rotations` to `[90]`
and preview with `--assigned-compound W --compound-rotation 90` to certify that
orientation. More ambitious edits must still satisfy envelope, path, private
buffer, complete doorway and final populated-access checks.

Version 2 has one `choices` list. A row is either
`{"kind":"single","asset":"hunter_cabin","weight":1,"cap":2}` or
`{"kind":"compound","recipe":"wayside_shrine_court","weight":2,"cap":2}`.
The shipped complete example shows both kinds. Parent choice weight is single
placement base weight × policy weight, or implicit compound base 1 × policy weight.
The nearest accepted parent with the same `(kind, ID)` applies `repeat_multiplier`
(default .2; Manhattan join distance with stable parent-ID ties). More child slots
or permitted transforms do not multiply the parent's chance. Child membership
weights independently multiply each child's placement base weight within its slot.

The default desired parent count is one inclusive draw from 2..4, with
`kind_minimum: {"single":1,"compound":1}`. Kind minima must fit the total minimum
and available caps. Weights cannot guarantee that mix; unmet kind obligations are
served first. Parent caps count accepted parents only, not their children; featured
landmark is excluded. A compound and a single site both consume one parent slot.
Setting a kind minimum to zero explicitly opts out of its guarantee. Set both
total bounds and kind minima to zero to opt out of all extra destinations.

Spacing/location controls retain their G6 values (80 join spacing, 24 town extent,
12 junction clearance, 16 sampling step, 8192 raw samples, 512 candidates).
`fit_budget` defaults to 1024 combined parent/child attempts, integer 1..4096.
A desired shortfall is valid only above **all** total/kind minima. Diagnostics
distinguish hard caps, bounded candidate search and fit-budget exhaustion; budget
exhaustion is not a proof that no geometric solution exists. Nothing relaxes town
spacing, water, bridge, anchor, private-space or storage-chunk constraints.

### 6. Diagnose errors and understand saved worlds

| Diagnosis | Correction |
|---|---|
| Unknown child/path or duplicate slot/membership | Match installed/draft IDs and keep stable unique slot IDs. |
| Required usable target missing | Mark at least one reachable target `required: true`; retain other optional targets. |
| Gate/common path disconnected | Connect the full gate span to its named path; add reciprocal joins for additional paths. Corner contact is insufficient. |
| Private overlap / buffer consumes path | Separate private regions and keep each full child buffer outside common circulation. |
| Outside envelope / spans storage chunk | Resize/reposition the authored bounds; every accepted parent stays within one 80×43 chunk. |
| Forbidden effective transform | Restrict parent/base-child rotations to the asset's actual allowed transforms. |
| Unfit mandatory child capacity | Enlarge that slot or choose a smaller eligible asset; required children cannot be dropped. |
| Required-child/global budget exhausted | Inspect bounded failure examples, then change the authored geometry or deliberately raise a finite budget. |
| Final approach/door/content blocked | Inspect real `special_tiles`, full primary/service spans and interactions after all population. |
| Valid optional omission | Inspect the saved slot reason; increase its space/budget only if you want it admitted. |

Policy/recipe/weight edits affect new plans. Unseen saved compounds use their exact
saved envelope, paths, slots, assets and transforms even if today's recipe is
changed or removed; no re-selection occurs. Changed consumed child structure or
factory definitions block only affected unseen scenes under unchanged
`structure-v1`. Unaffected unseen scenes remain usable. Visited scenes retain
player mutations and actual creator revision; they are never regenerated to
restore initial access. G3/G4/G5/G6 saves retain their original plan and get explicit
current adapters only when first creating a pending scene. They gain no compounds.

Run the executed workflow suite and actual download checks with:

```powershell
& $ResonancePython -X utf8 tools/verify_g7_authoring.py --evidence evidence/g7-owner/workflows
& $ResonancePython -X utf8 tools/verify_structure_editor.py --evidence evidence/g7-owner/browser
& $ResonancePython -X utf8 tools/worldgen_g7_diagnostic.py --journey --evidence evidence/g7-owner/diagnostic
```

The workflow suite executes these CLI forms in disposable roots, preserves sentinel
edits, installs a disposable data catalog, verifies both catalog commands, and runs
all errors in the table plus valid nonselection and optional omission. It retains
exact commands, cwd, environment, expected/actual exits and output hashes. Inherited
G6 and G5 workflows remain separately nested records. Both headless browser engines
export a real edited compound child; those exact downloaded bytes are consumed by
direct and whole-compound previews. The world remains finite at 128×128 chunks.
`UI-TEXT-HEIGHT`, broader town composition, retention/streaming and the continuous
viewport remain deferred. G7 stops at these bounded rural compounds.


# G8 — preserved settlement composition

G8 provides two installed grid layouts inside the existing 160 × 86 town footprint. **Cross-market** has two cross streets and two avenues around a rectangular circuit, with its bell common north of the first cross street. **Linked-courts** moves the avenues and puts a connecting street between them, dividing that circuit into two courts; its common sits south of the first cross street. Horizontal roadside settlements keep their 160 × 43 footprint and derive frontage from the actual country road.

The planner chooses layout identity on a separate deterministic seed stream. Building weights do not choose the layout. Country routes and bridge authority remain unchanged. Buildings, private buffers and complete approaches still belong to one 80 × 43 member chunk.

## Start with complete files

Run from the repository root with the interpreter selected in the interpreter setup above. These commands create drafts and evidence; they do not install anything:

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --init-settlement authoring/g8 --output evidence/authoring/g8-init.json
& $ResonancePython -X utf8 tools/structure_authoring.py --settlement-preview all --layout-config authoring/g8/g8_layouts.json --selection-config authoring/g8/g8_selection.json --config authoring/g8/g8_planning.json --seed 20261023 --output evidence/authoring/g8-complete.json
& $ResonancePython -X utf8 tools/structure_authoring.py --settlement-preview grid --layout cross-market --layout-config authoring/g8/g8_layouts.json --seed 20261023 --output evidence/authoring/g8-cross-market.json
& $ResonancePython -X utf8 tools/structure_authoring.py --settlement-preview grid --layout linked-courts --layout-config authoring/g8/g8_layouts.json --seed 20261023 --output evidence/authoring/g8-linked-courts.json
```

Repeated initialization preserves existing files. Reports and derived SVGs must be separate from every draft, initializer target and installed input. Aliases and hard links are checked before publishing outputs. Keep the complete downloaded building when using the layout painter; registration and lot fitting are separate checks.

## Consumed version-one layout schema

`settlement_layouts.json` contains `version: 1`, `alternative_limit`, `grid` and `roadside`. The shipped library has exactly two grid alternatives. The authoring validator permits one through four bounded alternatives, with one through four attempted alternatives. Each grid record has a unique stable `id`, `form: "grid"`, a positive finite `weight` at most 1000, `streets`, `common`, `civic_lot`, and the three frontage dimensions below. Use the initializer as the complete editable example.

| Field | Meaning and bounds |
|---|---|
| `streets` | Four through eight uniquely named records, each with exactly two distinct orthogonal `points`, inside local 160 × 86 bounds. Width comes from planning `street_width_tiles`. |
| `common` | Stable `id`, half-open `rect`, walkable `surface` (`cobblestone`, `dirt_path` or `grass`) and two horizontally adjacent `furnishing` cells for the existing stone and prayer. |
| `civic_lot` | Half-open `bounds` beside the common, exact street `join`, facing `normal` and assigned `street` ID. Must fit the complete bell buffer and approach. |
| `frontage_tiles` | Integer 14–32, controls tangent subdivision of eligible block sides. Default 18. |
| `minimum_depth` | Integer 8–20, rejects shallow private blocks. Default 10. |
| `junction_clearance` | Integer 1–8, trims segment endpoints and junction frontage. Default grid 2, roadside 3. |
| `roadside` | Stable `id` and the three frontage dimensions; the country road supplies geometry. No vertical roadside template. |

Coordinates are integer tiles relative to the settlement's upper-left corner. Rectangles exclude their right and bottom edges. A door's normal points toward its assigned street. An east-facing house therefore addresses a vertical street.

## Read the preview

The JSON contains a complete resolved plan and populated snapshots for every member of the requested forms. SVG companions show streets, common, private lots, accepted footprints, complete door spans, explicit vacancies and planned garden blocks. The controlled `--layout` option proves a chosen layout; it does not measure natural frequency.

The saved arrival is the first centerline entry of the actual incoming country route, including route ID, segment, position and direction. The composer subtracts real road bands and public ground before deriving disjoint blocks. Lots identify one block, one exact assigned road segment and a finite frontage interval. Every tile of the doorway span must project into that interval. A nearby parallel road is not interchangeable.

The common is protected accessible ground associated with the spent bell. Only the designated native stone/prayer cells are furnished. Public circulation remains walkable, and native actors cannot spawn on protected cells. Private reservations cannot borrow common space or neighboring lots.

## Edit, inspect and deliberately install

Change one geometry field in the complete draft, then preview both controlled layouts and ordinary seeds. Moving a street can remove lots, break member-local road connectivity, or make a required role impossible. Enlarging a common reduces private land. A narrower civic lot must fail clearly when the bell no longer fits; do not weaken its consumed geometry to hide that failure.

Tune candidates separately in `g8_selection.json`; see the existing selection-profile section above. Required roles are fitted atomically with one shared transform-trial budget across attempted layouts. Budget exhaustion means feasibility was unresolved; enumerated-alternative exhaustion means all attempted candidates failed. Optional failures become explained vacancies. Failed branches consume no accepted caps or reservations.

After reviewing previews, deliberately replace the corresponding files under `roguelike/data/generation/`, inspect the diff, run the catalog check, and generate a fresh disposable world. Installing a building also requires its explicit role membership. Existing worlds keep their saved resolution; editing a recipe does not regenerate pending or visited towns.

## Limits and interpretation

The current composer uses orthogonal rectangular blocks and finite choices. Narrow leftover strips are recorded gardens, not hidden failed buildings. Spatial repetition uses Manhattan distance between accepted frontage joins with stable plot-ID ties. Counts and weights are not occupancy guarantees. Three ordinary seeds and controlled examples establish bounded behavior, not long-run frequencies.

The G8 owner report records populated renderer views, real-handler travel, same-machine G7/G8 costs and centerline graph loops. G7 already had a rectangular street cycle. Wide-road tile cycles are not counted as useful alternate routes. Country-network optimization, organic cities, cross-chunk buildings and continuous rendering remain outside this release.


Complete shipped examples: `roguelike/docs/examples/g8_layouts.json`, `g8_selection.json`, `g8_planning.json`. The initializer copies the installed equivalents. The six G8 workflows execute initialization/preservation, complete controlled and roadside previews, a geometry edit, separate selection tuning, required-fit/collision failures, and deliberate disposable installation/catalog checks. Run `tools/verify_g8_authoring.py --evidence evidence/worldgen-g8/owner-authoring-01`; inherited G5–G7 workflows remain nested records. Both browser engines also consume actual downloaded building bytes on vertical frontage in both grid layouts.

Run the complete frozen gates with `tools/verify_g8_release.py --evidence evidence/worldgen-g8/owner-release-01`. See `docs/owner/WORLDGEN_G8.md` and the maintained offline wiki for evidence, costs, compatibility and the G8 stop boundary. Earlier arc sections above are historical where superseded by this section.

G8 inherited landmark demonstration: the complete `g8_landmark_preview_selection.json` restricts the featured role to the draft `g5_landmark` for controlled preview. G8 lot counts change downstream choice IDs; the old seed alone no longer promises selecting that draft. This preview policy is not installed and is not a frequency claim.

### Production installation and recovery

Before installing reviewed G8 drafts, inspect `git status --short` and the diffs of
the three generation files. Preserve any uncommitted owner edits in dated copies;
a tag identifies a commit and does not capture uncommitted bytes. Create a named
checkpoint of the accepted committed source. Deliberately copy each reviewed draft
to its matching generation filename, then inspect the exact diff, run complete
previews and catalog checks, and commit the accepted installation separately.
The disposable workflow above rehearses this without touching production data.

Recover a committed installation with a reviewed `git revert <installation-commit>`
on `main`, resolving conflicts while preserving later owner edits. For an
uncommitted installation, restore only the affected files from their preserved
dated copies after reviewing subsequent edits. Keep personal campaign backups
separate: source recovery does not rewind saved plans or visited scene mutations.

# G9 — current country-network authoring

Current fresh worlds use settings 4 / plan 7 / wg9. The complete G8 settlement,
common, selected-building and rural-owner baseline is preserved before up to two
optional country connections. The separate complete policy, exact units/ranges,
five workflows, installation/recovery and compatibility rules are authoritative in
[COUNTRY_NETWORK.md](COUNTRY_NETWORK.md). Use its complete draft rather than a
partial JSON fragment. Existing settings-3 examples explicitly exercise G8 semantics.

```powershell
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --seed 20261023 --output authoring/network-ordinary.json
& $ResonancePython -X utf8 tools/structure_authoring.py --init-network authoring/network-draft --output authoring/network-init.json
& $ResonancePython -X utf8 tools/structure_authoring.py --network-preview --network-policy authoring/network-draft/g9_country_network.json --seed 20261023 --output authoring/network-tuned.json
& $ResonancePython -X utf8 tools/verify_g9_authoring.py --evidence evidence/worldgen-g9/owner-authoring-02
```

The JSON report, exact-coordinate SVG and PNG are staged through the existing
protected-destination rules. Initialization preserves edits; previews create no
scenes, open no campaigns and do not install a policy. Zero shortcuts remains a
new G9 world with a disabled resolved result. Saved G8/G9 worlds keep their actual
resolved roads and visited state. The building painter and G5–G8 workflows remain
supported and separately exercised by the complete G9 release coordinator.
