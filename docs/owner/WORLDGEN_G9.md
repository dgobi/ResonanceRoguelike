# G9: bounded country connections and portable owner wiki

G9 preserves the complete G8 world and adds up to two optional country connections.
The ordinary required pair, settlement-1 to capital-gateway on seed 20261023,
improves from **23,625 to 8,063 four-neighbour physical steps (65.87%)**.
The accepted settlement-1/settlement-3 connection adds **5,265 / 24,631 unique
country-centerline edges (21.37%)**, below the shared 25% cap. No physical bridge
cells are added. Seeds 0 and 29417 honestly add no qualifying connection.

## Delivery and source

Work uses the owner's original production checkout on main. The initial checkout
was clean at `b94a0b0db3685f7484632701f0486f3b0b79101e`. No development copy,
branch, worktree, desktop control, personal campaign or force push is used.
The explicitly invoked brief authorizes scoped commits and publication to the
existing remote main, with immutable checkpoints and readback. Its original ZIP
inventory and exact extracted instructions remain under `evidence/worldgen-g9/before/`.

Implementation checkpoints separate wiki correction, planning, lifecycle and owner
workflows. The final input commit and final gate status are recorded in
`evidence/worldgen-g9/index.json`; release completion is not inferred from earlier
partial development runs. This report is being completed alongside release validation.

## Runtime and owner contract

Fresh worlds use format 7 / wg9, settings 4, network policy 1, existing shared-v1
and structure-v1 contracts. Explicit settings 3 retains historical G8. The composer
first completes the entire G8 baseline, then proposes connections without scenes.
Original destinations, all routes/crossings, town layout/commons/plots/selected
assets, rural parent/child ownership and dependencies remain exact. G8 river and
layout decision streams remain explicit; fresh wg9 scene randomness can differ.

The installed complete policy is `roguelike/data/generation/country_network.json`.
[COUNTRY_NETWORK.md](../../roguelike/docs/COUNTRY_NETWORK.md) documents every range,
search and ranking rule, five workflows, staged JSON/SVG/PNG outputs, and deliberate
install/revert/recovery. The complete draft is included in both authoritative and
wiki examples. The building painter retains its existing building purpose.

Primary endpoints include start, all settlements, capital gateway and landmark.
Every unordered pair remains in comparisons (15, 21 and 21 pairs for the ordinary
seeds). Construction is a unique unit-edge union; physical travel is full-width
road/deck/access BFS. Macro costs are positive 80/43 tile lengths. Reuse has zero
new construction but real traversal cost. Candidate search is finite; it does not
claim a terrain-respecting optimum. Default named marginal benefit is at least
500 steps and 25%, recalculated after each accepted connection. Scores balance
worst detour reduction, aggregate saving per new edge, named saving and construction.

Full-width bands, corners, protected town/building/compound/capital/submap chunks,
private/common reservations and all touched local slices are checked. Original
arrival/frontage/attachment references remain explicit. New roads use normal
reservation replay, before private rows while preserving original order. Existing
decks may be reused with narrowly scoped ownership records; no new water crossing
is permitted. Saved resolved routes, not today's policy, own pending generation.
Checksum-consistent corruption rejects before state installation. Late failure
preserves player/world/RNG/actors/cache/checkpoint HEAD and recovers after removal.

## Ordinary and controlled evidence

| Seed | Added links | New unique edges / baseline | Search expansions | Country cycle rank before/after | Country cut-edge steps before/after |
|---|---:|---:|---:|---:|---:|
| 0 | 0 | 0 / 11900 | 7538 | 0 / 0 | 11900 / 11900 |
| 20261023 | 1 | 5265 / 24631 | 26128 | 5 / 6 | 23155 / 3056 |
| 29417 | 0 | 0 / 11833 | 6623 | 2 / 2 | 11341 / 11341 |

All physical pairs are non-increasing and each physical union has one component.
The accepted route adds 15,786 full-width road cells and touches 86 complete scenes.
Each is materialized and checked for boundary continuity and native access.
Removing its distinct 5,265-step new country run from the diagnostic centerline
graph leaves a 20,837-step original corridor between the same junctions. This
proves a country alternative, not a road-width or local town cycle. Graph cut
edges are not river bridge objects; removal is a proof fixture, not gameplay.

A controlled seed-3 fixture lowers admission to 1 step / 1% and accepts two links.
Their shared union is 2,944 new edges, overlapping construction is counted once,
and the second pair is evaluated at its marginal 3,226 before / 2,586 after
physical steps. Exact rounded budget passes; one less edge rejects. This fixture
does not replace the shipped-policy ordinary sample. Small independent fixtures
cover anisotropic costs, ring/parallel-run topology, diagonal non-joins, full-band
corners, protected commons, existing-deck reuse, new-water rejection and a globally
connected but locally disconnected slice. Hash seeds, equivalent unordered inputs
and reverse scene visits exercise determinism separately from intentional policy order.

The genuine format-6/wg8 checkpoint was captured before runtime edits using real
F5, common interactions and eight native updates, with explicitly labelled fixture
positioning and paused phases. It retains independent compound mutations and both
visited/pending town and country scenes. Exact archive bytes, source, plan and
fingerprints are retained. Historical formats 1–6 fixtures remain intact; no new
wg9 output is relabelled as genuine G8 history.

The G9 journey uses real movement, doors, boundary and interaction handlers. It
walks the accepted route forward and backward, an original corridor, and the fixed
settlement-1/capital pair over both unions. It also retains inherited common,
residential/commercial content, both street axes, required bridge, landmark, other
town, compound and single-site coverage. Invincibility, stationary native actors
and paused AI/survival are disclosed; ordinary native updates have a separate
positive. F5, cold load and F9 compare the actually explored checkpoint, including
all visited surface fingerprints and independent contents. Physical BFS steps
remain distinct from diagonal-capable movement input counts.

## Costs and limits

The final diagnostic records serial G8-settings and G9 planning, graph analysis,
network/search decisions, subtree bytes, all required town/rural scenes, every
shortcut scene, worst observed real boundary transition, checkpoint scene count,
bytes and save/cold-load/F9 time. The genuine pre-edit full G8 journey is a separate
retained run: 354 checkpoint scenes and 38,805 movement inputs. Lightweight wiki
checks overlapped part of that original capture; its timing is disclosed rather
than described as an isolated benchmark. Final release gates execute serially.

Development profiling found repeated exact water-rectangle checks. A chunk index
narrows the same exact comparisons without changing permissions or full plan
identity. No universal frame-time claim follows from three seeds. G9 adds bounded
planning/validation work and the coverage journey visits more places; different
checkpoint scopes are not evidence of storage improvement. No cache eviction,
compaction, retention change, denser settlements, organic roads, new bridges,
capital redevelopment, larger worlds or continuous viewport is included.

## Maintained wiki

Edition 1.3 updates main world-generation, settlement tuning/layout, rural/compound,
authoring, save/state, troubleshooting, verification, maintenance and code-map
chapters. The dark standalone reader and editable sources remain in
`Resonance_Wiki_Maintenance/`. Source commit, wiki authoring/tests and products bind
separately. Text freshness normalizes only CRLF/CR to LF and retains path membership,
revision, BOM and trailing newline. Raw hashes/sizes remain provenance; binary is exact.
Downloads separately advertise their actual UTF-8/LF/no-BOM payload hashes/sizes.
Both Chromium and Firefox download and hash actual files, including the G9 draft.

Five wiki contract tests cover equivalent newlines, substantive/binary changes,
changed/missing/added helper inputs, stale HTML, repeat builds and later docs-only
commits. All root verification helpers, contract tests, chapters, examples and
consumed source are bound. Dependency/browser versions are execution evidence,
not inventories of installations. No silent repinning or disabled comparisons.

## Completion matrix

All paths below are relative to repository root. Final receipts supersede partial
development runs; original attempts remain under their named directories.

| ID | Requirement and evidence |
|---|---|
| G9-01 | `before/start.json`, package inventory, guard admission/outside rejection, genuine witness, complete pre-edit three-seed baseline and independent network measures. |
| G9-02 | `wiki-correction/final/` contract/reader receipts; repaired raw/canonical/payload identities and complete helper binding. |
| G9-03 | Installed/default draft policy, strict policy and disabled/zero/exhaustion fixtures; five owner workflows. |
| G9-04 | `final/diagnostic/results/run.json` complete baseline identities and full baseline-plan files against original G8 plans. |
| G9-05 | Final all-pair distances and reconciled topology; small anisotropic/union/ring/diagonal fixtures. |
| G9-06 | Deterministic finite candidate traces, two-link marginal/overlap/shared-budget fixture and exact budget negatives. |
| G9-07 | Ordinary 23625→8063 fixed-pair evidence, independent 5265-step removed-run / 20837-step surviving corridor. |
| G9-08 | 86 actual touched scenes, boundary continuity, populated access, protected-owner/deck/replay/local-slice fixtures and views. |
| G9-09 | Explicit format/settings dispatch, G8 public/common/native regressions, mixed/single/zero POI tests. |
| G9-10 | Genuine G8 visited/pending checkpoint, historical adapters, removed-current-policy cold/F9 and independent state fingerprints. |
| G9-11 | Sixteen checksum-consistent corruptions, late post-validation failure with full-state/disk snapshot and recovery. |
| G9-12 | Three ordinary worlds, no-road results, lazy/deterministic checks, serial cost/subtree/scene/storage measures. |
| G9-13 | Final real forward/reverse/original/fixed-pair itinerary plus explored F5/cold-load/F9 checkpoint. |
| G9-14 | `final/authoring/`, both real browser-export consumers, safe output/initializer/catalog collision negatives. |
| G9-15 | Main chapters/examples and edition-1.3 HTML, separate source/authoring/product manifest and both-engine actual downloads. |
| G9-16 | Frozen final receipts, machine-readable index, ZIP member SHA256/size/CRC inventory, scoped commits/tags and external publication readback. |

Paths beginning `before/`, `final/` or `wiki-correction/` are inside
`evidence/worldgen-g9/`. The portable archive excludes personal campaigns,
dependencies, browser profiles, disposable worker saves and a redundant checkout.
Intentional historical compatibility ZIP fixtures are retained. Exact omission
inventory and publication readback accompany the final archive outside any
self-referential committed metadata.
