# G8: composed settlements and maintained owner handbook

G8 adds bounded local settlement composition while preserving the country network,
existing member footprints, native town behavior and saved scene ownership. New
worlds use format 6 / `wg8`. Exactly two installed grid layouts, `cross-market` and
`linked-courts`, provide different street/common arrangements; horizontal roadside
settlements derive frontage from their actual country route. Buildings and their
complete private buffers and approaches remain inside one member chunk.

This delivery executes `CODEX_G8_SETTLEMENT_COMPOSITION.md` from the owner's review
package. The original brief is retained under `evidence/worldgen-g8/before/`.
Other package documents are historical review evidence. Work used the production
checkout on `main`; no task branch, worktree or second game checkout was created.
The start was clean at `8e56d36d72537e8b32c3666dd5d19723d1afdf3a`.

## Owner entry points

- Open `Resonance_Wiki_Maintenance/Resonance_Owner_Wiki.html` directly in a browser.
  It is self-contained and works without a server. Editable chapters, reader,
  theme, complete examples, builder and validator live beside it.
- Read `roguelike/docs/STRUCTURE_AUTHORING.md` for complete executable commands.
  `--init-settlement` creates complete layout, selection and planning drafts and
  preserves existing ones. `--settlement-preview all` creates complete populated
  member snapshots and diagrams; `--layout` explicitly controls a grid example.
- The current layout file is `roguelike/data/generation/settlement_layouts.json`.
  Selection remains in `settlement_profiles.json`; world settings remain in
  `g3_config.json`, now version 3 with `settlement_layout_version: 1`.
- Final gate receipts and portable delivery inventory are indexed in
  `evidence/worldgen-g8/index.json`. Receipts, rather than the existence of an
  output folder, determine whether a run passed.

## Composition and persistence contracts

The actual incoming country-route centerline supplies arrival route, segment,
position and direction. A separate stable layout seed chooses the template.
Street bands and accessible public common are reserved before disjoint rectangular
free blocks and finite frontage intervals are proposed. Each lot owns one block,
one assigned road segment and one interval. Whole door spans must project into
that interval; footprints and buffers must fit the lot. Road-band sharing is
narrowly scoped to the assigned road and does not authorize private/common overlap.

Cross-market retains a rectangular street circuit and places the common north of
the first cross street. Linked-courts shifts the avenues, adds a transverse link
and places the common south of that street. Both have a real protected common next
to the existing spent bell. Native stone/prayer furnishing has two explicit cells;
remaining common circulation must be enterable and reachable after population.

Required roles fit atomically within one transform-trial budget shared across
bounded layout attempts. Exhausted budget and exhausted enumerated alternatives
are distinct errors. Optional failures remain explained vacant lots; shallow
leftovers are garden blocks. Accepted caps, asset-first weights, ordered schedules
and baseline role minima retain their meaning. G8 repetition compares Manhattan
distance between accepted frontage joins, then stable plot IDs; historical formats
retain their previous ordering semantics.

Format 6 stores resolved layouts, blocks, public spaces, lots, references,
reservations and consumed dependencies. It works with either POI policy version,
including zero additional parents. Historical settings version 2 still selects
G7 format 5 with mixed parents or G6 format 4 with the single-site policy. Formats
1–5 retain exact saved plans; pending scenes use explicit current adapters and
visited scenes retain their actual older provenance and mutations. Removing a
current layout/selection recipe does not recompose a pending saved town. A changed
consumed definition rejects only affected pending slices. Failed late preparation
leaves world, player, RNG, active scene/actors, cache and checkpoint head intact.

## Verification and interpretation

The same-machine G7 baseline, genuine pre-change G7 checkpoint and original CLI
collision outcomes were captured before implementation. The checkpoint includes
visited town and compound state, real container transfers, pending town and rural
owners, exact plan bytes and source provenance. Fixture positioning and stationary
turns are explicitly recorded. The Linux symlink reproduction remains historical;
this Windows session could not create symlinks, so same-volume hard-link aliases
and resolved-path checks supplied local executable coverage.

The direct focused development run passed all 216 tests in 553.083 seconds with
no inherited `PYTHONPATH`; all source inputs remained stable. Subsequent final
receipts bind the complete intended inputs and repeat normal unfiltered discovery.
No failing test was removed or skipped to obtain the result.

Ordinary seeds are **0, 20261023 and 29417**, with no frequency extrapolation.
Diagnostics retain exact plans, zero visited scenes at planning completion, all
town members, start/capital/crossing/landmark and every accepted rural parent.
Country-route records compare byte-for-value with the same-machine G7 baseline.
Composition records include normal/role/asset counts, explicit vacancies, blocks,
common/private areas, fit trials, subtree bytes and arrival-to-door travel.

Travel metrics use shortest four-neighbour tile steps over complete populated
member terrain, with openable doors and stationary blocking actors. Their endpoints
are the saved arrival and a named required entrance. Centerline metrics merge
intersections/shared segments and contract degree-two runs; cycle rank is E−V+C.
Alternate-path witnesses remove an edge from a contracted run. G7 already had a
rectangular cycle. Route self-labels and cycles inside wide road bands are not used
as loop evidence. Actual populated-scene access is checked separately.

The actual-handler journey uses production movement, doors, stairs, interactions,
boundary travel and F5/F9. It retains stationary native actors, pauses AI/survival
updates and makes the player invincible. It walks the bridge, other settlement,
landmark, compound children and single site, plus G8 common, both street axes,
residential/commercial contents and native civic features. Its explored checkpoint
contains those mutations; scene counts, bytes, save/cold-load/F9 times and scene
fingerprints are recorded. Separate lifecycle tests run ordinary native updates.

Populated production renderer views cover both controlled grids and the ordinary
roadside form, with complete member mosaics and separate ownership diagrams.
Visibility is deliberately revealed. Controlled grid schedules emphasize occupied
cardinal frontage and are not ordinary distribution samples. Narrow garden strips,
rectangular blocks and a large paved common are consequences of this bounded
template system, not evidence of an organic-city generator.

## Completion matrix

The pre-freeze development diagnostic (`diagnostic-development-a`) measured the
following on the established Windows interpreter. Final gate timings are retained
separately; these are three samples, not a general performance guarantee.

| Seed | G7 / G8 planning seconds | G7 / G8 compact plan bytes | G7 / G8 slowest measured scene seconds |
|---|---|---|---|
| 0 | 1.249 / 0.774 | 600,599 / 598,641 | 0.427 / 0.271 |
| 20261023 | 2.139 / 1.729 | 738,766 / 709,155 | 0.441 / 0.306 |
| 29417 | 1.794 / 1.377 | 679,457 / 659,676 | 0.449 / 0.329 |

Fewer lots/accepted buildings offset the added block/common metadata in this
sample. Every ordinary grid has occupied horizontal and vertical frontage, but
not every ordinary grid has all four normals; controlled complete examples prove
all four for each shipped layout. The additional centerline cycles in some
linked-courts towns include intersections with the unchanged country geometry.
The report retains explicit alternate paths instead of claiming every counted
cycle is equally useful.

The development journey walked 38,805 steps and saved 354 scene files totaling
195,744,304 bytes. Save took 7.946 seconds, cold load 6.615 seconds and F9 7.128
seconds; the worst observed boundary transition was 0.442 seconds. Its broad
country travel explains the scene count. This exposes existing storage cost; it
does not add compaction or a frame-time target.

Evidence paths below are relative to `evidence/worldgen-g8/`. `final-a` is the
intended frozen gate run; the evidence index records any superseding final run
without concealing failed development attempts.

| ID | Delivered source / contract | Executed evidence |
|---|---|---|
| G8-01 | Production checkout preservation and historical witness | `before/start.json`, `before/guard/`, `before/witness/` |
| G8-02 | `authoring_outputs.py`, self-contained focused runner | `before/collision-hardlink/`, `authoring-protection-c/`, `focused-development/`, final focused parent/log |
| G8-03 | Shared wiki source/authoring/product model | `wiki-integration/`, final wiki contract/repeat/drift/integrity receipts |
| G8-04 | `settlement_layout.py`, two shipped profiles, public ground | final focused `g8-cardinal-layouts.json`, final visuals |
| G8-05 | Actual saved arrival, route-driven blocks | final diagnostic country equality, complete plans and diagrams |
| G8-06 | Cardinal lot fitting, full doorway spans | final focused `g8-frontage-fixtures.json`, browser G8 consumers |
| G8-07 | Actual horizontal roadside segment and explicit exclusions | final diagnostic roadside records and authoring previews |
| G8-08 | Reciprocal lots/blocks/public ownership and exact replay | final focused checksum-corruption and frontage fixtures |
| G8-09 | Atomic alternatives and shared bounded required fitting | layout tests, inherited required-fit tests, authoring required-no-fit |
| G8-10 | Role weights/caps/minima and stable spatial repetition | selection tests and final diagnostic composition records |
| G8-11 | Final populated access, protected common, native semantics | native-update lifecycle tests, actual journey, renderer views |
| G8-12 | Format 6 and explicit historical/current adapters | final focused `g8-policy-combinations.json`, historical fixtures |
| G8-13 | Saved resolution and affected dependency scope | final focused `g8-late-rollback.json` |
| G8-14 | Genuine G7, reverse visits, independent state and rollback | final focused `g8-genuine-g7-restore.json`, lifecycle checkpoints |
| G8-15 | Ordinary matrix, lazy deterministic plans and topology/costs | final diagnostic `run.json` and plans |
| G8-16 | Real journey and explored checkpoint | final diagnostic journey and progress receipts |
| G8-17 | Six new workflows plus inherited workflows; actual downloads | final authoring `workflows.json`, both browser receipts |
| G8-18 | Corrected main chapters and standalone editable handbook | final wiki edition/reader/integrity receipts and HTML |
| G8-19 | Frozen serial gates, archive inventory and remote readback | final `release.json`, `index.json`, delivery manifest/readback |

## Reproduce and maintain

Use the established dependency interpreter while importing this checkout. Run
`tools/verify_g8_release.py --evidence evidence/worldgen-g8/<new-run>` from the
repository root. It executes serial finite gates: guard, clean-parent focused,
both browser engines, new/inherited authoring, catalogs, ordinary diagnostics and
journey, production views, wiki, then the unfiltered production gate including
negative controls. Each gate has an 1800-second ceiling; focused discovery has
its existing 1200-second child ceiling. Changing unified runtime inputs requires
the full frozen sequence again. Development failures remain separate.

Wiki source revision, authoring hashes and products have distinct scopes. Pin a
reviewed real source commit, edit chapters, build, validate and drift-check. A later
wiki-only delivery commit does not invalidate unchanged source. Missing/changed/
added source, missing/changed wiki inputs and stale HTML fail closed. Source links
remain pinned. The old edition 1.0/Linux audit is preserved as history. The
repository instructions now require affected owner guidance and wiki maintenance
with workflow-changing features; this creates no scheduled background job.

The portable review ZIP includes selected source changes, owner documents,
standalone HTML, editable maintenance source, evidence and intentional historical
fixtures. Its manifest records every retained member's size/hash/CRC. Personal
campaigns, dependencies, browser profiles, disposable worker saves and a redundant
full source checkout are omitted. Remote commit/tag readback is stored outside
self-referential committed content in the delivery receipt.

No G9 work is included: strategic road optimization, more world density, vertical
roadside towns, organic layouts, cross-chunk buildings, capital redevelopment,
streaming and continuous rendering remain future decisions.
