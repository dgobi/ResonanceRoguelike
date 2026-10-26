# G17 — Creatures in authored underground rooms

25 October 2026, America/Edmonton. Production checkout `main`.
Reviewed starting source: `5ae5d1356bd5f37e442694c664354f79096c8e38`.
Certified implementation inputs: `796b8fe02f73fab1e79572ba690c15e4db2d691f`.

An owner can place one existing non-player creature with a direct authored
underground special, inspect its actual production placement and play an
encounter whose living and defeated states survive saves and revisits. Invalid
construction fails before the destination is published. The editable example
is documentation, outside native world selection. G17 completes this bounded
authoring dependency; H1 and a native underground destination remain unfinished.

## Authoring and preview

```json
{"type":"creature","x":7,"y":2,"creature_id":"hollow_revenant"}
```

Use a direct top-level `authored_submap` special. Coordinates must be integers
within the source grid. IDs resolve in the supplied data root; `player`, missing
and unknown IDs fail. Weighted creatures, contradictory type/kind, counts,
groups, stat/loot overrides and creatures in ordinary buildings, plazas or
entrance layouts remain unsupported. One record creates one `CreatureFactory`
actor. The existing transform centers/translates; no rotation/mirror is added.

Initial cells must be walkable, satisfy creature-specific terrain admission,
and avoid blocking decor, any batch blocking container, other authored actors,
the actual player arrival and physical up/down stairs. Swimming cannot override
walls or decor. A closed-door start uses the engine's existing actual arrival
selector for the reservation. Floor items can coexist with actors; corridor
guards are allowed. Entire batches resolve before occupancy admission and all
factories finish before object-layer mutation. Scene construction remains staged
before cache, metadata and departing-owner publication. Internal town/zone
population retains its policy; authored records cannot opt into that policy.

Edit the [complete room](../../roguelike/docs/examples/g17_authored_creature_room.json)
and [sidecar](../../roguelike/docs/examples/g17_authored_creature_room.access.json).
It contains one Revenant at source (7,2), a wood bundle on that cell and a
stocked existing crate at (8,4). Source (2,5) is the arrival/return stair. In the
80×43 scene the origin is (35,18), actor (42,20) and arrival (37,23).
See the [authoring guide](../../roguelike/docs/STRUCTURE_AUTHORING.md).

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/structure_authoring.py roguelike/docs/examples/g17_authored_creature_room.json --route authored_submap --access roguelike/docs/examples/g17_authored_creature_room.access.json --output .baseline/g17-room-preview.json
& $ResonancePython -X utf8 tools/verify_g17.py --evidence evidence/gameplay-g17/owner-verification
```

The [certified preview](../../evidence/gameplay-g17/final-a/example-preview.json)
uses the compiler, centering, factory and scene builder used in play. Receipts
bind source path/asset/record, original and final coordinates, actual actor
serialization/count, semantic creature-definition SHA-256, candidate/catalog
identity and world/scene seeds/address. Actors are separate from item/container
objects. Its revealed diagram and access checks inspect static geometry and
initial occupancy. Hostility and encounter balance are separate concerns.

## Controlled original-loop encounter

The [event-loop receipt](../../evidence/gameplay-g17/final-a/journey/journey.json)
uses the unchanged example in a disclosed disposable linked fixture. Setup
binds it in memory, omits the generated surface's native occupants and clears
one 3×3 surface link while retaining the real surface provenance. The destination
is built exclusively by the production authored route. Ordinary starter gear
is equipped through inventory controls. Normal AI, FOV, combat, time and survival
remain active afterward; no actor is inserted, deleted or killed directly and
no health/invincibility change manufactures success.

Normal stair input enters exactly one factory-created Revenant at (42,20).
Ordinary movement/combat wounds it to **10/14 HP**.
A separate original-loop process cold-loads the exact player/scene snapshot and
full actor state, including wound, position, AI/home/memory and action accumulator,
then defeats it normally. The continued combat costs
**8 turns** and takes player HP from
**59 to 56**.
Normal turn cleanup removes the defeated actor and retains its physical remains.
The actual return link is used for exit/re-entry; generation is forbidden during
that cache revisit. F5 saves the defeated state. A third process cold-loads it,
exits, evicts the scene cache and re-enters from disk with generation forbidden.
No actor respawns; the one normal remains item and unrelated floor/container
owners survive. All three new completion fields agree with driver exhaustion.
Existing save/F9 tests supply unchanged rollback coverage; G17 adds no new
rollback claim or actor persistence system.

The driver uses full-state movement/UI choices and the established RNG seed
20261020 in each process. This is controlled authoring/runtime evidence, not
native selection, discovery, general balance or a normal-start expedition.
Normal-FOV [arrival](../../evidence/gameplay-g17/final-a/journey/living/g17-authored-arrival-normal-fov.png),
[defeat](../../evidence/gameplay-g17/final-a/journey/cold/combat/g17-defeated-with-normal-remains.png)
and [cold revisit](../../evidence/gameplay-g17/final-a/journey/cold/cold/revisit/g17-cold-disk-revisit-no-respawn.png)
views accompany the trace.

## Preservation and measured gates

The genuine G16 returned-pellet archive remains untouched, SHA-256
`0867c43c7b39adf64ef13e26dadaccefa82730046021e62c7d1213682685287d`.
Its [pre-edit observation](../../evidence/gameplay-g17/pre-edit-historical.json)
and [final comparison](../../evidence/gameplay-g17/final-a/historical.json)
agree exactly: saved player/laboratory, altered visited workshop, all
51 plan dependencies and pending BSP construction.
The witness `submap_73_97_0` at (73,97), type barrow, seed 107361, blank layout ID
and generated:false, retains its complete construction fingerprint. No old
world was fabricated and no personal campaign was opened.

All game data, starting laboratory, world assignment, BSP algorithm, save schema,
AI/combat, recipes/items, G13–G16 definitions/evidence and wiki remain unchanged.
Blank `layout_id` still means BSP regardless of submap type. Authored layouts
without creatures retain their route. The manifest is `g2-2`; its refreshed editor
catalogue reflects the existing 67 structures without installing this example.
Saved `structure-v1` placement hashes and world/scene revision remain unchanged.

Production environment: Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0,
NumPy 2.4.6; dummy SDL, app-local events and disposable saves. The known Python
3.12 exact-float receipt issue is separate scope; no calculation or historical
fixture was rounded or rewritten.

| Final check | Actual result | Measured duration |
|---|---|---|
| Unfiltered focused discovery | 286/286 pass | 27m 23.6s |
| Unfiltered production D | 3676/3676 accepted assertions; 159 valid workers | 11m 22.4s |
| Existing CLI example/access preview | Pass | 0m 00.5s |
| Editor catalogue consistency | Pass | 0m 00.2s |
| Genuine G16 historical comparison | Exact agreement | 0m 02.1s |
| Controlled encounter and two cold processes | Pass | 0m 15.9s |

The independent focused and production processes overlap. Final verification
wall time is **27m 43.5s**, not the sum of those durations
or total development time. Eight new focused tests cover admission, transforms,
actual arrival, water, occupancy, atomic publication/ownership, preview provenance,
unchanged internal/lab behavior and the genuine historical witness. Existing tests
retain unchanged combat/save/ownership coverage.

The [release receipt](../../evidence/gameplay-g17/final-a/release.json),
[audit](../../evidence/gameplay-g17/audit.json) and
[artifact index](../../evidence/gameplay-g17/artifact-index.json) bind actual commands,
environment, results, 793 source/Git inputs and
12890 ordinary-worker imported-source entries. All
7 runner negative controls reject; the
146 ordinary and 13 intentional crash workers reconcile.
Raw working-file hashes and explicit CRLF/LF Git comparisons are retained.
[Preflight](../../evidence/gameplay-g17/preflight.json) records the bounded development
checks and fixture/assertion corrections; no required final gate was waived.

Checkpoints: `checkpoint/gameplay-g17-start-20261025-a`,
`checkpoint/gameplay-g17-inputs-20261025-a` and
`checkpoint/gameplay-g17-verified-20261025-a`. Authorized publication is verified
by remote main/tag readback in `.baseline/gameplay-g17-publication.json`.
G17 stops here. Native destination/reward selection, connected outings, alternate
approaches and H1 completion belong to a later brief.
