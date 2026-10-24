# Compose streets, commons and frontage

G8 provides two installed grid layouts inside the existing 160 × 86 town footprint. **Cross-market** has two cross streets and two avenues around a rectangular circuit, with its bell common north of the first cross street. **Linked-courts** moves the avenues and puts a connecting street between them, dividing that circuit into two courts; its common sits south of the first cross street. Horizontal roadside settlements keep their 160 × 43 footprint and derive frontage from the actual country road.

The planner chooses layout identity on a separate deterministic seed stream. Building weights do not choose the layout. Original country routes and bridge authority remain intact; G9 can add optional connections after this complete baseline. Buildings, private buffers and complete approaches still belong to one 80 × 43 member chunk.

## Start with complete files

Run from the repository root with the interpreter selected in [Setup](#getting-started). These commands create drafts and evidence; they do not install anything:

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

Tune candidates separately in `g8_selection.json`; see [Town variety](#settlement-tuning). Required roles are fitted atomically with one shared transform-trial budget across attempted layouts. Budget exhaustion means feasibility was unresolved; enumerated-alternative exhaustion means all attempted candidates failed. Optional failures become explained vacancies. Failed branches consume no accepted caps or reservations.

After reviewing previews, deliberately replace the corresponding files under `roguelike/data/generation/`, inspect the diff, run the catalog check, and generate a fresh disposable world. Installing a building also requires its explicit role membership. Existing worlds keep their saved resolution; editing a recipe does not regenerate pending or visited towns.

Before production installation, inspect the three generation-file diffs and preserve uncommitted owner edits in dated copies; a Git tag captures committed state only. Create a named checkpoint of accepted source, install reviewed drafts deliberately, verify and commit that installation separately. Recover a committed installation with a reviewed `git revert <installation-commit>`, preserving later owner edits while resolving conflicts. For an uncommitted installation, restore only affected files from their dated copies after reviewing later edits. Source recovery does not rewind campaign state.

## Limits and interpretation

The current composer uses orthogonal rectangular blocks and finite choices. Narrow leftover strips are recorded gardens, not hidden failed buildings. Spatial repetition uses Manhattan distance between accepted frontage joins with stable plot-ID ties. Counts and weights are not occupancy guarantees. Three ordinary seeds and controlled examples establish bounded behavior, not long-run frequencies.

The G8 owner report records populated renderer views, real-handler travel, same-machine G7/G8 costs and centerline graph loops. G7 already had a rectangular street cycle. Wide-road tile cycles are not counted as useful alternate routes. G9 now adds bounded country connections over that baseline. Organic cities, cross-chunk buildings and continuous rendering remain outside the current scope.

## G9 country integration

Both G8 layout templates, their complete commons, public-surface dependencies, plot selection and cardinal frontage remain the baseline of current format-7 worlds. Optional country roads are considered only after those records are resolved. They cannot create a new entrance into a protected town chunk. Arrival selection uses the explicitly saved arrival road; another route ending at the same town cannot replace it. Settings version 3 remains the historical G8 plan path; settings version 4 adds the separate network contract.
