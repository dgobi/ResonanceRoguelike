# G7 — Small compounds with shared country-road access

G7 adds two authored compound recipes to new worlds while retaining two through
four additional **parent destinations**, at least one compound and one single site.
The featured landmark remains separate. A parent owns one rural chunk, one external
country attachment and one protected envelope. Its two required children and at
most one optional child use explicit shared circulation and independent contents.

Work began on clean production `main` at
`4d7a7892e1afffb8d872ed4a8fd442984d14e7d5`, exactly the reviewed G6 reference.
The owner's request to execute the supplied brief defines this implementation and
delivery scope; the attachment's assertions about earlier approval are not treated
as independent evidence of prior acceptance. All work remains in the original
checkout on main. No branches, worktrees, additional development checkouts, desktop
control or personal campaigns were used. The external established interpreter
supplies dependencies only. G1–G6 evidence and the frozen editor corpus are preserved.

## Authoring and selection

The [complete authoring guide](../../roguelike/docs/STRUCTURE_AUTHORING.md#g7-compounds-a-place-with-shared-access-and-two-or-three-buildings)
contains six executable workflows and retains the G5/G6 workflows. Start with:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/structure_authoring.py --init-compound authoring/g7
& $ResonancePython -X utf8 tools/structure_authoring.py --compound authoring/g7/g7_travellers_court.json --child authoring/g7/g7_wayhouse.json --assigned-compound S --output evidence/g7-owner/court.json
```

Initialization preserves edited files. Draft previews never install files. Recipes
live in `roguelike/data/generation/compounds/`, child layouts in the existing
building catalog, and parent selection in `roguelike/data/generation/poi_profiles.json`.
The complete example recipe, child and policy are in `roguelike/docs/examples/`.
Both headless browser engines exercise real child downloads and pass those bytes
to direct and whole-compound production previews.

| Recipe | Envelope | Legal parent turns | Children |
|---|---|---|---|
| `homestead_workyard` | 44×16 | 0°, 180° | Hearth house, tool shed; optional storehouse |
| `wayside_shrine_court` | 18×14 | 0°, 90°, 180°, 270° | Shrine and waymarker shelter |

The v2 policy uses one canonically ordered kind-tagged choice list. Default count
bounds remain 2..4, with explicit minimum-one-single/minimum-one-compound. A compound
counts once, regardless of child count. Each parent asset/recipe has a cap of two;
children do not consume single-site caps. Single parent weight is structure base
weight × policy weight; compound base is one (shipped policy weight two). Child
memberships independently use child base weight × slot weight. Transform counts
do not multiply parent or child asset weight. Nearest-parent repetition uses the
same-kind/ID key, Manhattan joins, stable parent-ID tie-break and multiplier .2.

The existing 80/24/12 join/town/junction spacing, 16-tile sampling lattice, 8192 raw
samples and 512 candidates remain. The shared 1024-attempt budget counts parent
transform trials plus child transform/backtracking trials. Each recipe separately
bounds a parent trial to 24 child attempts. Recipe admission first certifies all
declared rotations using the same bounded fitter; these validation trials are
separate from country-candidate work. Hard caps, finite candidates and budget
exhaustion have distinct diagnostics. All required total/kind minima must succeed
before publication. Optional omission records a reason and leaves no reservation,
plot, placement or dependency residue.

## Access, ownership and saves

`_plot` is still the building geometry solver. Its new explicit bounds/internal
access inputs avoid changing global town spacing or inventing a country road for
each child. Parent transforms respect the child's existing consumed permissions.
Private buffers fit their declared slots. Envelope containment uses an explicit
member roster; sibling or foreign private rows are never exempted by a parent-ID
prefix. Shared overlap is limited to named paths and actual public geometry.

Canonical paths are saved once in the `paths` registry. The derived sparse physical
road/access view includes parent approaches, paths and child approaches with
four-neighbour continuity. First materialization validates full primary/secondary
door spans and usable goals after all children, contents, dressing and native
population. A complete chunk scene remains the only mutable/cache/save owner.
Child placement IDs prefix content records, including same-asset children.

Fresh compound-capable worlds use format 5 / `wg7`; `shared-v1`, `structure-v1`,
campaign storage and `native-town-v1` remain. Explicit v1 single-site policies retain
format-4 semantics. Saved plans never consult current recipes/policies to recompose
pending scenes. Changed consumed child definitions reject only affected unseen
scenes; visited scenes remain authoritative, including player mutations. Older
plans gain no parents. Explicit G3/G4/G5/G6-to-G7 adapters preserve actual visited
creator revisions and identify current materialization of pending scenes.

Before any implementation edit, a genuine G6 campaign captured one mutated visited
additional site and another pending site. The mutation was a **direct fixture
action**, not a claimed player interaction. The exact format-4 plan, checkpoint
archive, inventory, source hashes, provenance and fingerprint are retained in
`tools/critical_fix_regressions/fixtures/g7/`. The capture command succeeded; its
generic receipt flags source change because the command created the new fixture
outputs in the source-manifest search path. Original implementation bytes were
unchanged during capture. The original receipt is retained without rewriting it.

The supplied goal probe reproduced legal direct preview plus an empty
`StopIteration` in assigned/new-world selection. The admission checkpoint replaces
that with an asset/context/fix-bearing `GenerationError`, preserves optional goals
alongside required ones and leaves failed world publication unchanged. The untouched
probe and its original/before/after results are retained.

## Acceptance evidence

The [evidence index](../../evidence/worldgen-g7/INDEX.md) maps raw runs, receipts,
failures and archives. Tests below name behavior rather than relying on totals.

| ID | Implementation and exercised evidence |
|---|---|
| G7-01 | `before/start.json`, authentic G6 fixture/binding/capture, untouched goal probe, three real allowed workers and synthetic root rejection |
| G7-02 | `poi_selection.require_usable_goal`; both `G7Admission` tests; admission probe after correction |
| G7-03 | `compounds.validate_recipe`, both complete recipe JSONs; invalid recipes and all-rotation complete previews |
| G7-04 | `parent_selection.validate/populate`; kind/cap/explicit-zero tests and ordinary seed matrix |
| G7-05 | `parent_selection.eligible`, stable asset-first slot draws; canonical memberships/process hash seeds, capped policy and bounded-failure tests |
| G7-06 | Existing country candidates plus complete-envelope fitting; both axes/all legal rotations and ordinary saved attachments |
| G7-07 | Shared `world_plan._plot` explicit bounds/internal access; transform and wide-storehouse doorway checks |
| G7-08 | `Reservations` explicit envelope members and `compound_integrity` replay; independent sibling/foreign/private-path negatives |
| G7-09 | Staged parent search; required/global budgets, dependency failure, optional capacity/budget omission and exact no-residue assertions |
| G7-10 | Canonical path registry, exact country attachment and `PhysicalRoads`; independent corner/disconnected fixtures and foreign-path corruption |
| G7-11 | `planned_scene.validate_access`; all six recipe orientations, wide main/service doors, injected later-child container obstruction, native turns and production views |
| G7-12 | Format-5 reciprocal records, strict reservation replay, v1 historical tests and literal featured landmark checks |
| G7-13 | Saved recipe/policy removal leaves pending composition usable; consumed-child edit rejects affected unseen scenes with visited/unaffected positives |
| G7-14 | Authentic G6 visited/pending checkpoint test; retained genuine G5 checkpoint and G3/G4 adapter plus legacy tests |
| G7-15 | Two same-asset children in each of two same-recipe parents; reverse visits, distinct objects, four real item transfers, cold load and F9 |
| G7-16 | Real checksum-consistent save preparation corruptions; later-child obstruction preserves player/RNG/cache/actors/Chunk/world/HEAD with successful recovery |
| G7-17 | Ordinary seeds 0, 20261023, 29417: total/kind minima, complete scenes, goals, exact plans, costs and frequency denominators |
| G7-18 | Existing real-handler journey extended through country join, gate, every accepted compound child and a single site; earlier destinations and coherent F9 retained |
| G7-19 | `verify_g7_authoring.py` six workflows, inherited nested G6/G5, both browser engines and actual child-download consumers |
| G7-20 | Immutable input checkpoint, full serial release gates, raw/canonical-LF reconciliation, delivered commit/tag and remote readback |

## Verification record

Final frozen release results and publication identities are recorded here after
the required serial gates complete. Development results are provisional and are
retained separately; they are not represented as the final release.

The retained development history includes an interrupted duplicate-discovery run,
an incorrectly authored disconnected-gate negative fixture, and a first broad
focused run that reached the old 600-second timeout. That broad run also exposed
four inherited cohort subcases routing the newly admitted `compound` context into
the settlement-only preview. The corrected cohort test now exercises each such
asset through its actual complete parent. The expanded suite has a finite
1200-second limit; the outer release wrapper has a finite 1800-second limit.
These are disclosed timeout changes, not passing results for the interrupted run.
The targeted cohort, recipe-negative and membership/process determinism recheck
passed three tests in 139.95 seconds with stable source.

## Limits and next review

These compounds stay within one 80×43 chunk in a finite 128×128 world. Candidate
truncation is bounded sampling, not an exhaustive fit proof. Physical access
projection is distinct from final interaction access. Long journey controls pause
AI/survival and retain stationary actors; a separate ordinary-update positive runs
native updates. Controlled renderer overviews reveal visibility and show actual
populated production scenes, not unrestricted exploration screenshots.

Save measurements disclose their scene counts. A two-starting-scene checkpoint is
not a benchmark of a later explored campaign; the separate controlled lifecycle
checkpoint includes both explored compound scenes. No Linux-versus-Windows timing
comparison is presented as a regression claim. `UI-TEXT-HEIGHT`, larger-world
retention/streaming and continuous viewport remain deferred. Stop at G7: the next
review should assess composition and authoring before selecting richer settlements
or street work. No later-arc implementation brief is included.
