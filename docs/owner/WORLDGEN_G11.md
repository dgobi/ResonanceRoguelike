# G11 — Wilderness entrance access and safe returns

Implemented and verified 24 October 2026; delivered 25 October 2026,
America/Edmonton. Production checkout `main`.
Reviewed and reproduced G10 baseline: `7e48d4059a8c68bb98bb5c7f6d2fa49aa0a01a9b`.
Frozen runtime/test inputs: `970107db947d341bec315cdb5a31ce19a34a75bd`.

New campaigns preserve an actual reciprocal exterior connection through entrance
placement and completed wilderness composition. Seed 20261023, Drowned Wood
`(44,8)`, Arnevel Vault (`submap_44_8_0`) now has a reachable entrance and a usable
surface return. Existing campaigns retain their historical pending-generation
route and all visited state. The known G10 pending-scene defect remains possible
in those campaigns; no automatic migration or visited-scene rescue is included.

## Repair and preserved contracts

G10's entrance at `(14,5)` sealed the selected arrival and stair into a 79-cell
component with no boundary. This was reproduced before runtime changes using the
supplied probe on the established Windows dependency interpreter.

The corrected route selects the north edge `(14,0)`, matching neighbor `(44,7)` at
`(14,42)`. The bounded placement search rejects 20 inaccessible candidates and
selects the authored entrance at `(29,5)`. No terrain repair or carving is needed.
The source submap ID, owning chunk, name, type and return/link ownership remain.

The final same-process exact-scene pair took 0.180 seconds on the retained G10
route and 0.240 seconds on the corrected route. This is a modest local sample,
not a general latency guarantee; per-scene costs accompany all 64 sampled cases.

The exterior witness is selected after water, road and authored ownership
composition. It uses narrow natural-field strips and saved plan slices to check
the reciprocal cell, never materializing neighbor scenes. Outward world edges
and protected authored interiors cannot be witnesses. Reciprocal edge cells are
reserved from later dressing. If overlays split the original arrival component,
the corrected route may select another existing playable component while keeping
mandatory road anchors. Required arrival, previous stairs, new stair and exterior
must stay connected; unrelated decorative pockets may remain disconnected.

The existing 300-candidate ordering and bare-stair fallback remain bounded.
Fallbacks satisfy the same access predicate. Completed populated scenes validate
again, including scenes without submaps. Static access uses existing eight-way,
openable-door and blocking-decor rules; dynamic actors remain temporary occupants.

Surface schema remains 1. New worlds save surface policy version 2 with validated
`access_revision: 1`, also recorded in scene provenance. G10 version-1 policies
retain their exact old behavior; G9 schema-0 worlds retain their supported route.
Raw field sampling, installed profile values, field seed domain, world size,
geography, complete format-7 G9 plans and `GENERATION_REVISION = wg9` are unchanged.
Saved policies reproduce pending decisions despite installed tuning edits/removal.

## Demonstrated journey and preservation

The controlled access journey starts with one disclosed fixture position in the
normally generated neighbor `(44,7)` at `(14,42)`. From its first boundary input,
all travel, doors, stairs and inventory actions use real game handlers. It enters
`(44,8)`, walks to Arnevel Vault, descends, returns to the owned surface stair,
consumes the ordinary starting water flask, walks out and crosses back to the
matching neighbor cell. No repositioning occurs in the target or underground.
Native actors, AI, survival and normal FOV remain active; invincibility is off.
The script uses full-state path selection and does not establish unaided discovery.
Initial setup uses the existing debug-travel handler to prepare the neighbor,
then places the player at the stated edge. That handler first computes normal
visibility from its generated central arrival; daylight passive memory from setup
can remain visible in the neighbor images. No visibility reveal is used for the
normal-FOV captures. The journey takes 30 movement inputs and 54 turns and ends
at 60/60 health.

F5, a new-engine load, F9 and a separate fresh-process load preserve the actual
terrain, actors, links/returns, player/transport/RNG state and empty water skin.
They also reproduce a subsequent pending corrected scene at `(45,8)`.
Normal-FOV approach, entrance, return and exit images are separate from the
explicitly revealed completed-scene comparison.

The separate existing G10 normal-start excursion is replayed with its original
controls: laboratory ascent, waystone interaction, off-road harvesting, four
boundaries, starting-water consumption and return under native gameplay systems.
This is a bounded ordinary-play demonstration, not a whole-world survival claim.
The final ordinary replay takes 190 movement inputs and 220 turns, ends at 60/60
health, and retains its harvested sulphur-cap fragment and empty water skin.

A genuine pre-edit G10 checkpoint retains a real waystone mutation plus exact
visited and pending fingerprints for `(44,8)`, `(73,100)` and `(72,103)` through
ordinary loading and F9. Inherited genuine G9 tests remain part of the full suite.
The compact fixture lives in `tools/critical_fix_regressions/fixtures/g11/`.

## Verification and delivery

Final results and source binding are recorded in
[`release.json`](../../evidence/worldgen-g11/final-d/release.json).
The [artifact index](../../evidence/worldgen-g11/artifact-index.json) links the
baseline, focused receipts, production result and actual journeys.

- Expanded unfiltered focused suite: **246/246 tests pass**, including eight G11 tests.
- Unfiltered production D gate: **3,675/3,675 checks pass across 159 workers**.
- Controlled access journey, actual-checkpoint fresh-process load and ordinary
  normal-start excursion: **pass**.
- All runtime/test inputs remain unchanged through those final checks.

The earlier `final-c` focused attempt was stopped before completion when source
review corrected overlapping water-core/bank projection precedence. Only `final-d`
certifies the final source; the interrupted log and reason remain available.

The targeted tests cover the exact regression; a late blocking-decor cut that the
old validator accepts; multiple-link bare-stair fallback; all 60 supplied discovery
scenes plus four targeted road/water/world-edge scenes; water-core precedence
under overlapping bank rectangles; unchanged raw fields and
three complete ordinary-seed macro plans; genuine G10 preservation; checksum-
consistent missing, invalid and downgraded contracts/provenance; and atomic late
failure with unchanged active world/player, cache, RNG, checkpoint files and Git
HEAD followed by successful retry. The sample is not a prevalence estimate.

All 749 frozen inputs bind to the tested Git commit: 471 match exact committed
bytes and 278 differ only in the checkout's existing CRLF line-ending conversion.
The release records raw input hashes and committed blob identities separately.

Run the same bounded delivery checks with the established dependency interpreter:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g11.py --evidence evidence/worldgen-g11/owner-verification
```

The gate requires committed runtime/test inputs and a fresh evidence directory.
It runs the unfiltered focused suite, established unfiltered production D gate,
controlled G11 access journey and existing ordinary G10 excursion. Disposable
production save roots remain under `.baseline`; the retained production receipt
embeds worker results without duplicating disposable campaigns.

The existing `E04 / UI-TEXT-HEIGHT` deferral remains. The authoritative wilderness
guide is clarified; the current owner wiki edition is unchanged. Additional
terrain tuning, roads, POIs, reader UI, balance and campaign migration remain
outside this repair.

The immutable delivery checkpoint is
`checkpoint/worldgen-g11-verified-20261025-a`; the starting checkpoint is
`checkpoint/worldgen-g11-start-20261024-a`. The portable delivery ZIP contains
the source patch, genuine compatibility witness, before/after/access evidence,
full final receipts, per-member hashes and `publication.json`. Its adjacent
receipt records the archive hash and exact remote main/tag readback without a
self-referential committed hash.
