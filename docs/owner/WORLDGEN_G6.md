# G6 — Independent places along country roads

G6 keeps the featured landmark and adds two through four independent rural sites
to new worlds. Each site owns one authored building, a complete protected approach
and an exact attachment to an existing country road. The four initial assets are
`roadside_shrine_a`, `hunter_cabin`, `shepherds_hut_a` and `waymarker_shelter_a`.
No new building geometry, town forms, world dimensions or rural AI policy was added.

Work began on clean production `main` at
`6f255435f567b99f172e20c38ca2e2d660ff629e`, exactly the reviewed G5 source.
The owner requested execution of the attached brief; its implementation and delivery
steps supplied the scope. Statements in the package about prior authorization were
not treated as independent evidence of earlier owner acceptance. Work stayed in
this checkout, using the existing external interpreter only for dependencies.
Personal campaigns, the frozen 65-document corpus and G1–G5 evidence were preserved.
No alternate development checkout, desktop control or routine owner testing was used.

## Controls and authoring

Edit `roguelike/data/generation/poi_profiles.json` for new-world selection. The
[authoring guide](../../roguelike/docs/STRUCTURE_AUTHORING.md#g6-additional-country-road-sites)
contains six complete G6 workflows and preserves the earlier G5 and legacy recipes.
Use `roguelike/docs/examples/g6_wayhouse.json` as a complete editable layout and
`g6_poi_example.json` as a complete draft registration policy. The existing editor
exports the actual candidate JSON; direct and assigned-site CLI previews validate
those downloaded bytes before deliberate installation.

The default desired count is one deterministic inclusive draw from 2 to 4.
Selection may fall short of desired only after reaching the configured minimum;
the saved reason distinguishes caps, finite candidates and fit budget exhaustion.
Below minimum, no candidate world is published. A zero minimum is an explicit
owner configuration, not the default. All accepted extras remain required saved
obligations even above minimum.

The initial hard cap is two of each asset across additional sites; the featured
landmark is excluded. Effective weight is placement base weight × site weight ×
soft repetition multiplier. The default 0.2 penalty compares with the nearest
accepted site's join by Manhattan world-tile distance, breaking ties by site ID.
It is a local preference, not a hard distinct-ID quota. Rejected candidates consume
neither caps nor ownership.

Default join spacing is 80 world tiles, town-extent clearance 24, and perpendicular
junction/bend clearance 12. These are three separate Manhattan measurements.
One site per allowed storage chunk also applies: no towns, featured chunk, river
chunks, submap anchors, capital or locus chunks. Supported rural locations are
plains, forest and heath. Footprint, buffer, full entrance span and complete access
fit within one 80×43 chunk. Spur length still has one authority: `max_spur_tiles`
in `g3_config.json`, default 12.

Samples use a fixed 16-tile world-coordinate lattice. Enumeration is capped at
8192 raw road-side examinations, candidate consideration at 512 and transform
fitting at 1024. Equivalent overlapping/retraced corridor candidates are deduplicated
before the deterministic seeded order. Town streets and site approaches are not
eligible parents. Perpendicular band intersections identify junctions; straight
collinear reuse does not falsely exclude the backbone.

## Durable ownership and roads

Fresh plans use format 4 / `wg6`, retaining `shared-v1`, `structure-v1`, the existing
campaign save schema and `native-town-v1`. The `sites` registry contains additional
sites only; the required featured `landmark` retains its original literal identity.
Each site records `id`, `kind`, `profile`, `chunk`, `node`, `plot`, `placement`,
required target index `goal`, and `attachment`. The attachment records parent road,
segment index, world join, canonical positive-axis tangent, side, frontage normal
and entrance ID. Placement remains the single authority for asset, transform,
buffer, entrances, targets and approach geometry.

Validation checks relationships in both directions, including counts, caps,
one-site-per-chunk, exact parent band, perpendicular access, entrance identity,
reservations, spacing and required nodes. A nearby different road cannot satisfy
a wrong parent. Sites do not create fake settlements, TownData buildings or a
second inventory owner. Complete scene creation uses existing factories, receipts,
dressing, population and final doorway/content checks. Late failures do not install
scene/cache/actor/player/visit/plan/checkpoint changes.

The physical road projection is derived and disposable. It allocates only occupied
full-width road, bridge-deck and access cells (hard ceiling two million), not a dense
world grid. Shared cells and four-neighbour orthogonal steps connect; diagonal-only
corner contact does not. T-joins, crossings, band-only overlap and retracing are
covered by independent small oracle cases. Reported physical distances are shortest
unit tile steps on that union. Existing per-route detour ratios are labeled separately.
Canonical routes are never split, rerouted or replaced by this diagnostic graph.

Formats 1/2/3 retain their exact saved plans without site synthesis or policy
normalization. Visited `wg3`/`wg4`/`wg5` scenes keep their actual provenance and
mutations. Pending scenes use explicit `g3-to-g6-v1`, `g4-to-g6-v1`, `g5-to-g6-v1`
adapters; new v4 scenes use `g6-v1`. An authentic G5 checkpoint was captured before
any game implementation edit, with a visited mutated house and an unvisited town
member. Its plan equals the supplied independently generated G5 JSON value tree.
The checkpoint loads with replanning forbidden, preserves the old scene, creates
the pending scene through the G5 adapter and survives save/F9 with unchanged plan digest.

Selection-only edits do not affect pending saved sites. A consumed-definition edit
still blocks only affected pending materialization, with asset/dependency context.
Visited mutable scenes and unrelated pending scenes remain authoritative. Load
validation does not compare player-mutated tiles with a regenerated blueprint.

## Selection correction

Both supplied before probes reproduced on the actual reviewed G5 checkout. The
required-role search now explores each feasible transform of an asset before
abandoning that asset/slot when a later role fails. Asset weighting still occurs
once before transform alternatives. A budget unit is one geometric transform fit,
or one no-frontage asset trial; profile inspection is bounded to eight permitted
options per asset. Budget exhaustion reports unresolved feasibility separately
from exhausting all enumerated alternatives. Every accepted mutation, dependency
and reservation is staged. The original same-seed witness, genuine geometric
failure, small budget and dependency-failure rollback cases are retained.

Fresh unordered weighted memberships are canonicalized. Explicit schedules remain
ordered. Saved policies are not rewritten. The opening correction passed all 177
then-discovered focused tests before its separate commit and checkpoint.

## Acceptance evidence

The [evidence index](../../evidence/worldgen-g6/INDEX.md) locates raw results,
source receipts, retained failures, browser downloads, diagrams and production
rendering. Controlled fixtures are not ordinary frequency observations.

| ID | Source and executed evidence |
|---|---|
| G6-01 | `before/` probes, untouched G5 capture script/checkpoint/binding; clean start tag. |
| G6-02 | `world_plan.plot_options`, staged fitter and `settlement_selection.populate_settlement`; `G6Selection` same-seed, infeasible and budget cases; dependency rollback case. |
| G6-03 | Canonical selection resolution and POI candidates; `G6Selection` membership permutation; `G6Sites` candidate/membership and reverse-visit cases; inherited deterministic generation tests. |
| G6-04 | `poi_selection.validate/resolve/populate`; count/type/context/location/cap/budget negatives, explicit zero and atomic default-minimum failure. |
| G6-05 | `poi_selection.eligible`; nearest-join/tie weight assertion, cap-limited shortfall and two-shrine independent ownership case. |
| G6-06 | Format-4 `sites`, `poi_policy`, `site_selection`; `plan_integrity` reverse ownership and real preparation negatives. |
| G6-07 | Canonical road-derived candidates, protected chunks, junction/town/site clearance and shared production reservations; ordinary rejection totals and assigned fixtures. |
| G6-08 | Saved attachment and exact segment/frontage/access validation; all four assigned normals; wrong-parent negatives and physical corner oracle. |
| G6-09 | `road_network.PhysicalRoads`; independently calculated T, crossing, band-only, retraced, disconnected, corner-only and bridge cases. |
| G6-10 | Physical validation before v4 publication; count and bounded-budget shortfalls, below-minimum world rollback, malformed accepted-site omissions. |
| G6-11 | All four assets across permitted direct transforms and 16 complete assigned scenes; actual receipts/targets, main/service blocking-content negatives. |
| G6-12 | Two same-asset sites, reverse visits, distinct live containers, real transfers, cold load and F5/F9 fingerprints; production PNGs. |
| G6-13 | Original G5 checkpoint/plan and explicit pending adapter; retained G3/G4/legacy tests; no historical site/road synthesis. |
| G6-14 | Saved POI policy bypass, affected-only pending dependency failure, visited/unaffected positives; inherited structure-v1 load/F9 cases. |
| G6-15 | Checksum-consistent malformed site records through real `_prepare`; late materialization rollback and inherited coherent recovery positives. |
| G6-16 | Three installed-policy diagnostic seeds, zero scenes at planning completion, every accepted site's complete scene and goals, physical metrics and truthful asset denominators. |
| G6-17 | Extended `g3_journey` through real movement/boundary/content handlers, physical road paths to two sites and coherent F9 start rollback. |
| G6-18 | Six documented G6 workflows, complete draft/policy, repeated initialization sentinel, disposable installation, expected-negative commands and actual browser downloads. |
| G6-19 | Frozen 65-document hash checks, live 64-document catalog, both headless browsers, plan/gameplay visuals and rural ordinary-update positive. |
| G6-20 | Sequential frozen-input release runner: full focused, browser, authoring/catalog, diagnostic/journey and unfiltered production gates, then remote reconciliation. |

## Verification and delivery record

All ten final commands passed against frozen input
`991eb9f4e18f53efc3f0c9fc02648fbd70183068`, with unchanged source throughout.
The final documentation/evidence commit changes no tested input. Its immutable
identity is `checkpoint/worldgen-g6-verified-20261024-a`; the delivery message
records the observed delivered SHA after comparing local HEAD, remote main and
the remote tag. No branch or existing checkpoint history is rewritten.

| Final gate | Actual result | Wrapper seconds |
|---|---|---:|
| Focused discovery | 189 tests; no skips, failures or errors | 268.064 |
| Chromium + Firefox | 36 checks each, including actual downloaded site candidates | 33.403 |
| Authoring workflows | 19 recorded commands and 2 actions, including invocation of the retained G5 workflow's 22 commands and 4 actions; five explicit G6 expected-negative commands | 31.873 |
| Catalog / catalog freshness | 64 live assets, zero errors, 238 classified legacy warnings; current editor catalog | 0.272 / 0.250 |
| Diagnostic and real journey | All three ordinary seeds, all complete sites and extended handler journey pass | 126.922 |
| Headless plan renders | Overview plus horizontal/vertical attachments; inspected separately from gameplay PNGs | 1.023 |
| Unfiltered production | 3,675/3,675 checks; 159/159 valid workers | 398.150 |
| After probes | All three same-seed transform cases and legal mirror witness accepted; equivalent memberships agree | 0.538 / 0.277 |

The production run retains seven runner-negative controls and thirteen deliberate
crash workers. Expected failures are reported as such, not exit-zero positives.
Browser versions are Chromium 156.0.8078.4 and Firefox 157.0, using Playwright
1.64.1. Both independently round-trip the unchanged 65 original documents and
64 current live documents. Codec coverage is not a claim that every editor control
was exercised on every asset.

All final receipts reconcile the same 660 runtime/test/fixture/editor/guide inputs:
421 are byte-identical to Git and 239 differ only by checkout CRLF versus Git LF.
There are no tested-content changes. Archive inventories verify 569 development
members and 625 final members, with SHA-256/size and CRC checks; raw workers and
retained failures remain available. The archives omit disposable worker save
payloads while retaining the explicit authentic G5 compatibility fixture.

| Checkpoint suffix (`checkpoint/worldgen-g6-…`) | Commit | Purpose |
|---|---|---|
| start-20261023-a | 6f25543 | Clean reviewed G5 source |
| selection-20261023-a | d614bbc | Required-transform correction, canonical memberships and genuine G5 witness |
| sites-20261023-a | 1e366aa | POI policy, format 4, attachments, physical graph and compatibility |
| lifecycle-20261023-a | c3fdcb1 | Ownership, rollback, ordinary updates and journey extension |
| authoring-20261023-a | f4a0528 | Complete owner recipes and actual browser-download paths |
| final-gate-inputs-20261023-a | c760d32 | First freeze; historical worker-root rejection retained |
| final-gate-inputs-20261024-b | 991eb9f | Corrected guard and inspected overview; all final gates pass |
| verified-20261024-a | Resolve tag | Documentation/evidence delivery with identical tested inputs |

The ordinary installed-policy results (three worlds, eight additional sites) are:

| Seed | Desired / accepted | Naturally accepted additional assets | Physical cells / components |
|---|---|---|---|
| 0 | 2 / 2 | waymarker shelter, shepherd's hut | 38,106 / 1 |
| 20261023 | 3 / 3 | shepherd's hut, roadside shrine, hunter cabin | 75,756 / 1 |
| 29417 | 3 / 3 | roadside shrine, waymarker shelter, roadside shrine | 37,115 / 1 |

Each world separately retains exactly one featured landmark. There are no ordinary
count shortfalls in this sample. Across additional sites, shrine appears three
times, hut twice, waymarker twice and cabin once. These are eight accepted
occurrences, not eight worlds or a frequency guarantee. Individual worlds have
zero-selection assets, and seed 29417 has a deliberate legal duplicate.

The three plans have 594,641 / 735,062 / 669,561 compact JSON bytes. Compared with
the supplied G5 plans, net growth is 5,531 / 8,765 / 3,004 bytes; this also includes
changed required-role composition, so it is not an isolated per-site cost. The
new site registry, resolved policy and bounded diagnostics occupy 1,473 / 2,229 /
2,320 bytes. No derived physical graph is saved. Plans complete with zero local
scenes; the diagnostic times 15 / 18 / 18 destination scenes respectively, including
every accepted site, plus the required crossing checked separately.

On the final Windows run, planning took approximately 0.69 / 1.02 / 0.83 seconds.
Site enumeration and fitting remained separately measured in the raw report;
the physical projection took approximately 0.03 / 0.07 / 0.04 seconds. The slowest
complete destination scene was under 0.20 seconds. These are bounded observations
on this machine, not universal latency thresholds or a cross-machine comparison.

The real journey took **37,781 steps and 586 exact boundary transitions**. It
visited start, the required crossing, both town forms, the featured landmark and
two additional sites from their saved parent-road joins. It took actual container
contents at the shepherd's hut (2→1 items) and shrine (1→0), using production
interaction handlers. The derived road legs to those sites were 10,127 and 592
shortest four-neighbour tile steps respectively. No site-interior teleport was used.
The worst observed transition was 0.198 seconds; 352 surfaces had been visited
before F9. Stationary native actors, paused AI/survival turns and invincibility
are disclosed controls; a separate eight-turn rural test runs ordinary updates.

The journey's **starting** checkpoint contains two scenes and 18,967,925 bytes,
with save 0.744 seconds and restore 0.427 seconds. F9 returns the coherent initial
world, position, contents and checkpoint identity. Separately, the controlled
two-shrine ownership test measures an **explored four-scene** checkpoint of
19,971,203 bytes and verifies distinct mutations through cold load and F9. Neither
measurement is presented as a long-campaign storage benchmark.

## Retained failures and limits

The supplied G5 defects and original probe observations remain unchanged. The first
G5 witness attempt compared Python tuples with JSON lists; the next assumed an
unselected hunter cabin. The successful untouched-G5 capture compared canonical
JSON values and used a naturally selected house. Both failed command receipts remain.

The initial G6 diagnostic hit an old reporting helper that knew only town/landmark
owners; all three failures were retained before adding rural-owner reporting. The
first obstruction fixture put a container on a closed non-walkable door and failed
at content placement; the corrected fixture uses an open entrance so the final
primary/service access checks reject the blocking content. The first authoring run
correctly rejected the stale editor catalog; the catalog was rebuilt and workflows
passed. These are separate from ordinary installed-world results.

The first final freeze, `c760d32`, passed 189 focused tests, both browsers,
authoring/catalog and the complete extended journey. Its production workers then
rejected the newly isolated G6 evidence directory before gameplay execution because
the historical worker guard allowed only `.baseline`. The correction adds only
the explicit `evidence/worldgen-g6` disposable root and verifies its marker/source
identity; production and personal save roots remain outside that allowlist. The
failed jobs, process errors and result totals are retained. The subsequent freeze
is `991eb9f4e18f53efc3f0c9fc02648fbd70183068`; all final gates passed on it.

The one-building/one-chunk limit, existing rural population policy and finite world
remain intentional. `UI-TEXT-HEIGHT` remains deferred. No performance claim compares
these Windows runs with the review's Linux timings. Large-campaign retention/cache
optimization, multi-building compounds, richer street/network generation and
continuous viewport work remain outside G6. The next step is owner review of the
resulting sites and connections before deciding which later scope to pursue.
