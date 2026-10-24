# G8 network review and recommended next scope

## Recommendation

Proceed with **bounded useful country-road shortcuts**, after any concrete G8
corrections found by the main review. Preserve the completed G8 baseline plan and
augment it with at most two optional connections, under a cumulative new unique
centerline-length budget. A default cap of 25% of the baseline country's unique
centerline length is supported by the concrete seed-20261023 witness below.

This is a narrower, more defensible next arc than rebuilding the entire country
backbone or combining route generation with checkpoint compression. Preserve
geography, anchors, original roads and physical bridges, settlement composition,
accepted rural parents, exact lots and private/public ownership. New roads may
reuse existing corridors and add bounded dry-land connections around protected
places. Acceptance must depend on measured travel benefit, not merely one more
cycle or one more road record.

## What G8 achieved and what remains

The G8 completion report is accurate about the deliberate boundary: the country
routes are unchanged from G7; the new work concerns settlement streets, blocks,
commons and frontage. The exact retained plans contain 163 proposed settlement
lots and 149 occupied lots across the eleven towns. All six grid towns have
occupied horizontal and vertical frontage; twelve occupied town lots address a
vertical street. The six grid towns each have a 361-tile public common. These are
three ordinary generated worlds, not estimated probabilities.

The existing country planner in
`roguelike/generation/world_plan.py:102–121,156–208` selects fixed anchors, then
connects the destination list in sequence. The landmark is a branch from the
first settlement. Later roadside rewriting ensures a horizontal two-chunk
through-section. A* uses chunk-step costs, terrain penalties and a flat cost of
one for entering any previously used road chunk. This does not directly minimize
physical travel distance: an east/west chunk step is 80 tiles and a north/south
step is 43. Existing-road preference is a construction/reuse objective that must
be distinguished from travel-distance benefit.

### Independent centerline measurements

`measure_country_network.py` reads only complete retained final-b plans and
records each exact source SHA256. It unions cardinal unit centerline edges,
merges intersections and retracing, and computes shortest distances over that
graph. The terminal set is start, every town, capital gateway and featured
landmark. Crossing near/far nodes and additional rural sites are excluded from
this particular comparison.

| Seed | Unique country centerline tiles | Summed route-record length | Retraced length | Country cycle rank | Cut-edge share of country length |
|---|---:|---:|---:|---:|---:|
| 0 | 11,900 | 17,257 | 5,357 | 0 | 100.0% |
| 20261023 | 24,631 | 39,616 | 14,985 | 5 | 94.0% |
| 29417 | 11,833 | 20,908 | 9,075 | 2 | 95.8% |

Retraced length can be useful corridor reuse; it is not automatically wasted
construction. A cut edge is a bridge of the zero-width road-centerline graph,
not a claim that off-road player movement becomes impossible. Existing country
networks already have cycles in two of these seeds. G8's local street cycles are
also real; do not claim the game has no loops.

| Seed | Worst terminal pair by centerline/Manhattan ratio | Centerline distance | Manhattan lower bound | Ratio |
|---|---|---:|---:|---:|
| 0 | Capital gateway ↔ landmark | 6,383 | 3,273 | 1.950 |
| 20261023 | Town 1 ↔ capital gateway | 23,641 | 3,665 | 6.450 |
| 29417 | Town 2 ↔ capital gateway | 9,324 | 3,232 | 2.885 |

The corresponding median ratios across all 15/21/21 unordered terminal pairs are
1.061, 1.879 and 1.067. Manhattan distance ignores geography and cannot establish
that an excess is avoidable. The conservative feasibility probe below resolves
that uncertainty for the most serious example.

## Concrete conservative witness

`check_macro_corridors.py` reproduced the exact current saved plan for each seed
using fresh in-memory worlds. It created no local scenes or campaigns. An
independent Dijkstra search used exact tile lengths and the following restrictions:

- Existing hard terrain exclusions: world boundary, deep mountain, capital
  except the destination.
- No new river crossing. Any edge touching a river chunk must already belong to
  the baseline country network.
- No new entry/exit edges through any existing settlement, rural owner,
  building or capital chunk, including the endpoint chunks. Existing road edges
  remain usable inside them.
- No new chunk containing a submap.

It deliberately does not claim the existing soft biome/elevation preferences
are equivalent to this shortest-distance search. It tests whether a conservative
geometrically available corridor exists, while leaving its production scoring,
finite policy and complete materialization to the next implementation.

For **seed 20261023, Town 1 → capital gateway**:

| Measure | Result |
|---|---:|
| Existing full-width road/deck/access-union shortest path | 23,625 tile steps |
| Candidate centerline length | 6,309 tiles |
| Full-width union shortest path after addition | 6,303 tile steps |
| Reduction | 17,322 steps / 73.32% |
| Added unique country centerline | 5,903 tiles |
| Reused centerline on the candidate | 406 tiles |
| Added length / baseline country unique length | 23.97% |
| Added width-three road cells | 17,691 |
| Added cells inside protected place/private/approach/common rectangles | 0 |
| Added physical bridge-deck cells | 0 |
| Normal current `validate_plan` | Passed without source changes |

`probe_augmentation_replay.py` adds that route to a copy of the retained G8 plan
in memory. All original route, crossing and reservation records remain exact.
Every other plan subtree remains unchanged, including nodes, waters, towns,
plots, buildings, public spaces, rural parents and consumed dependencies. This
uses current format-6 vocabulary as a feasibility probe; it is not a delivered
new planning policy and does not establish a G9 persistence contract.

The analogous conservative worst-pair candidates for seeds 0 and 29417 reduce
travel by only 1.35% and 0.88%, while costing 33.9% and 46.9% of baseline country
length. A 25% total budget rejects those candidates. Other candidate pairs in
those worlds were not exhaustively optimized; do not claim those worlds have no
useful possible shortcut. A valid zero-addition outcome should remain allowed.

The PNG/SVG map uses exact saved coordinates and clearly labels this as an
uninstalled feasibility witness. Existing travel figures refer to the full-width
road/deck/access union; the orange route drawn is its zero-width centerline
analogue. These graph paths ignore off-road movement and transient actors. No
candidate scene has been populated or traversed through production handlers.

## Implementation traps that the next brief should address

1. **Augmentation should follow baseline composition.** Compute and validate the
   G8-equivalent geography/anchor/road/settlement/rural plan first, then stage
   optional additions. New routes must not feed back into town selection,
   rural candidate enumeration, required-role fits or native semantic choices.
   Compare exact preserved projections with the baseline for the same seed and
   settings. The entire full plan cannot remain byte-identical once additions
   and new policy/version metadata exist.

2. **Reservation replay order matters.** New road rows appended after existing
   private approaches can fail despite only reusing existing public road cells.
   This is reproduced in seeds 0 and 29417: the naive append conflicts with an
   old single-site or civic approach. Placing the new infrastructure rows before
   existing private rows allows old narrowly scoped `public_road` permissions to
   replay successfully. Old rows and IDs need not be rewritten. Do not grant
   broad road/private overlap permission to bypass the validator.

3. **Existing bridge geometry and crossing ownership are different.** Reusing a
   physical bridge in another complete route may require additional route/water
   ownership records. The probe creates those exact records from existing deck
   geometry without adding physical deck cells. Report unique deck geometry
   separately from raw crossing-record count. Alternatively, redesign a narrow
   shared-crossing reference only if justified; do not silently drop required
   route-owned validation.

4. **Arrival must remain stable.** `settlement_layout.py:147–148,231–232` derives
   canonical arrival from the first incoming country route. Append new route
   records after original records and keep the old incoming identity/arrival
   unchanged. A route-list reorder must not accidentally change civic ordering
   or saved arrivals. A future general network rewrite would need explicit
   selection of a primary arrival; this bounded arc can preserve the incumbent.

5. **Local connectivity is stronger than global connectivity.**
   `planned_scene.py:187–190` requires every road tile in a chunk to be reachable
   from the local road component after population. Route candidates must
   preserve this and all bridge, door, common and usable-goal guarantees. The
   macro witness passes exact current plan validation, but production scene
   creation and actual movement still belong in implementation acceptance.

6. **Travel and construction need separate measures.** Cost real movement in
   physical tile units. Count new construction as the set difference of exact
   unique centerline edges and road cells. Reusing a chunk is not equivalent to
   reusing an edge or full-width corridor. Positive costs and an admissible
   heuristic must remain compatible with any terrain preferences. Explain
   denominator and tie rules. A loop count alone is not an objective.

7. **Optional failure must leave a valid baseline.** Candidate/no-benefit,
   insufficient-budget, protected-geometry conflict and exhausted-search
   outcomes should be explicit and atomic. A corrupt saved accepted route must
   fail save preflight, not be treated as an optional planning omission. Keep
   finite candidate, expansion and total-work limits and deterministic stable
   ordering. Do not hide a required baseline generation failure behind a
   shortcut fallback.

8. **Saved-world semantics need a deliberate contract.** A new saved network
   policy or header must be handled consistently across validators, slicing,
   materializer adapters, metadata and provenance. Current code has several
   exact `version == 6` G8 guards. Do not blindly replace all with `>= 6` without
   establishing each supported contract. Keep G8 plans exact; capture a genuine
   visited/pending G8 witness before edits; no retroactive shortcut installation.
   The global generation revision is also a random seed input, so distinguish
   unchanged resolved baseline plan geometry from fresh scene content created
   under a new revision.

9. **Owner controls should stay small and reviewable.** Expose enabled/disabled,
   finite optional connection count, cumulative new-length cap, minimum travel
   benefit and bounded work through one documented policy. Preview complete
   ordinary plans, show accepted/rejected candidates and before/after routes,
   and maintain the wiki. Do not introduce a general graph editor or a new
   location/density selector.

## Why storage is a later, separate decision

The final G8 index records a 354-scene checkpoint of 195,744,304 bytes, saving in
7.169 seconds, cold loading in 3.907 seconds and F9 in 4.195 seconds. The completion
report also gives explicitly labelled earlier development timings. These do not
contradict one another.

`engine/save_manager.py:114–117,211–237,304–326,332–345` shows whole-scene ownership
and a complete immutable checkpoint assembled from cold checkpoint, session disk,
hot cache and active state. Inactive scenes are also checked before installation.
The measured cost is real and relevant to future large-world work, but this review
has not established a correctness failure or isolated an optimization. Combining
retention/deduplication/compression with network generation would entangle save
compatibility and recovery with a separately testable route-quality change.

G9 should continue measuring actually explored checkpoint bytes/times and retain
current save/lifecycle guarantees. A shorter route may reduce the number of
visited scenes for a fixed itinerary; describe that as less exploration caused
by changed routes, not as a storage-engine improvement. A later review can choose
storage/retention based on a dedicated fixed-scene-count profile.

## Reproduce

Run from the shared scratch root, using the existing dependency environment for
scripts that import the game and ordinary system Python for pure JSON/plot work:

```sh
python3 g8-review-evidence/network/measure_country_network.py \
  --repo resonance-review --output g8-review-evidence/network/country-network-metrics.json
review-env/bin/python -B g8-review-evidence/network/check_macro_corridors.py \
  --repo resonance-review --metrics g8-review-evidence/network/country-network-metrics.json \
  --output g8-review-evidence/network/macro-corridor-witnesses.json
review-env/bin/python -B g8-review-evidence/network/probe_augmentation_replay.py \
  --repo resonance-review --witnesses g8-review-evidence/network/macro-corridor-witnesses.json \
  --output g8-review-evidence/network/augmentation-replay.json
python3 g8-review-evidence/network/render_network_witness.py \
  --repo resonance-review --witnesses g8-review-evidence/network/macro-corridor-witnesses.json \
  --replay g8-review-evidence/network/augmentation-replay.json \
  --out g8-review-evidence/network/seed-20261023-network-witness
```

The scripts accept explicit repository/output paths and can be relocated. They
do not modify the checkout. The parent review owns final source-preservation
verification, artifact packaging and publication.
