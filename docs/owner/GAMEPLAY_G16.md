# G16 — Scavenged preparation at a furnished workshop

25 October 2026, America/Edmonton. Production checkout `main`.
Starting source: `d26c6776b20c89c67a9b626bbc82059f50c770e7`.
Frozen runtime/data/test inputs: `1856700882260e9a2734b05df1953c4da76e1959`.

An ordinary starter can leave the laboratory, scavenge a furnished workshop,
prepare one musk pellet and bring it home for another outing. The completed
original-game-loop expedition returns to the same laboratory alive at **60 HP**,
with **one unspent pellet**, after **476 saved-timeline turns**. The route uses
the ordinary starter equipment, one flask and one jerky. This is fixed-seed
feasibility evidence with scripted choices, not unaided discovery or H1 completion.
It establishes no general guarantee that the starting foothold is safe.

## Place, material chain and controls

`workshop_b` retains the original 12×9 envelope, double southern entrance,
grid/roadside contexts, all four rotations, frontage, buffer and approach.
Tables, hanging cloth, worn surfaces and the retained scholar note/unfinished
scene furnish the room around a clear central aisle and southern working area.
Tables and cloth are scenery. Its real crate independently rolls exactly one
`stalker_musk_gland` and one `wood_bundle` through two dedicated one-roll pools.
No finished pellet is stocked. The local preparation note explains stationary
heat, torch ignition and temporary disruption without changing knowledge flags.

Use `E` beside the crate, Enter to search and Enter on each selected material;
search again for the second object. Take the note and read it with `I`/Enter.
With the ordinary crude blade equipped, target the emptied crate through `E`,
press `X`, confirm Enter and pick up its one floor wood bundle. Other actual fuel
is also valid. In `C`, select Field Campfire and confirm a clear adjacent spot.
Placement spends two physical fuel items and retains the cutting tool. `E` the
unlit fire to ignite it using the still-burning offhand torch, a separate action.

In `C`, select musk pellet and confirm a clear drying spot within the fire's
warmth. Commitment spends the exact gland; placement is phase one of the existing
ten phases. Wait with `Z`, then pick up the completed floor pellet. Its existing
inventory-use/throw targeting spends it only on legal confirmation and briefly
disrupts nearby creatures. Esc cancels. Tactical effect/retreat meaning remains
supported by [G12](GAMEPLAY_G12.md); the primary G16 proof retains the pellet.

## Fresh-world and historical policy

Only the two grid/roadside commercial memberships switch `workshop_a` to
`workshop_b`, preserving entry order, weight 1.0 and cap 5. No forced placement
or nearby-workshop guarantee is added. Old definitions, shared texts/scenes,
G13 shed, G15 apothecary, pools, items, recipes, generation policy, save contracts
and the existing wiki edition remain unchanged. No runtime mechanic defect was
needed to complete this content route.

The [genuine pre-edit receipt](../../evidence/gameplay-g16/pre-edit-historical.json)
and [final historical comparison](../../evidence/gameplay-g16/final-a/historical.json)
agree exactly. The original G15 archive's SHA-256 is
`503309d073b96139a84fc0769ad9eb89fe53b1f1b4c89230d0af318eb20037de`.
Its player/unused dressing and visited (75,100) scene restore exactly; all 51
placement dependencies pass; four old workshops remain selected. The genuinely
pending old workshop at (76,99), placement
`settlement-0-cross-market-lot-81-3-S-0-building`, materializes with its original
complete fingerprint and no G16 backfill. No replacement historical world/archive
was manufactured. Personal campaigns were not opened.

## Ordinary-start expedition and persistence

The [final event trace](../../evidence/gameplay-g16/final-a/journey/journey.json)
begins in the actual laboratory at chunk (73,99), `sub_73_99_0`, seed 20261023.
It equips the starter blade/jacket normally, ascends and crosses east/east/south
to the naturally selected workshop at (75,100), placement
`settlement-0-cross-market-lot-1-44-S-0-building`, rotation 0, public join (21,21).
The driver reads full map/actor state to choose eight-way routes weighted by
terrain cost and threat distance, and selects actual UI rows. The established
driver seeds gameplay RNGs and `PYTHONHASHSEED` to 20261020, including each cold
process. Complete simulation replay is not claimed.

| Milestone | Turn | HP | Hunger / thirst | Torch turns used |
|---|---:|---:|---:|---:|
| Real laboratory start | 480 | 60 | 0 / 0 | 0 |
| Both native crate materials owned | 721 | 60 | .241 / .31125 | 241 |
| Exact gland committed; drying phase one complete | 733 | 60 | .253 / .32625 | 253 |
| One finished pellet picked up | 744 | 60 | .264 / .340 | 264 |
| Same laboratory reached with pellet | 956 | 60 | .126 / .24375 | 476 |

The crate is explicitly emptied, dismantled once and its output taken. That wood
and the crate's native wood are spent on the fire; the native gland is spent on
the preparation. Blade, jacket, talisman, torch, found note and finished pellet
remain owned. The starting flask and jerky are used normally during the return;
the empty water skin remains. The torch retains 124 of its 600 burning turns.
Normal AI, FOV, survival and turn ordering remain active. Threat avoidance is a
route choice; there is no staging, teleportation, inserted supply, synthetic
injury/recovery, threat clearing, invincibility or resource reset.

F5 preserves actual drying with nine phases remaining. A genuinely separate
original-game-loop process cold-loads that exact complete snapshot, finishes
the nine phases normally, takes the pellet and walks north/west/west before
descending into the original laboratory. One ordinary unsaved wait before F9
is explicitly observed and rolled back to the named drying snapshot. The 476-turn
summary is the saved timeline and excludes that rolled-back phase.

The returned pellet and altered workshop are saved. A third process restores the
complete laboratory/player snapshot and reads the saved workshop with generation
forbidden: the crate is absent and no gland, wood or pellet is left on its floor.
Focused cache eviction/disk revisit agrees. There is no second long itinerary or
universal offscreen catch-up. Four normal-FOV production views show furnishing,
the complete note, the pellet result and the laboratory return.
Inspect the [room](../../evidence/gameplay-g16/final-a/journey/outbound/g16-furnished-workshop-normal-fov.png),
[note](../../evidence/gameplay-g16/final-a/journey/outbound/g16-readable-musk-note.png),
[pellet result](../../evidence/gameplay-g16/final-a/journey/cold-return/homeward/g16-owned-pellet-normal-fov.png)
and [laboratory return](../../evidence/gameplay-g16/final-a/journey/cold-return/homeward/g16-returned-laboratory-with-pellet.png).

## Verification and delivery

Windows x64; production CPython 3.11.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6;
dummy SDL, app-local events and disposable save roots. Python 3.12 exact-float
portability is outside this scope; historical receipts were not rounded or edited.

| Final check | Actual result | Measured duration |
|---|---|---|
| Unfiltered focused discovery | 278/278 pass | 30m 58.4s |
| Unfiltered production D | 3676/3676 pass; 159 workers | 15m 35.6s |
| Genuine G15 historical comparison | Exact agreement | 0m 2.3s |
| Ordinary-start game-loop expedition and cold loads | Pass; pellet returned unspent | 0m 34.6s |

The existing focused and production gates overlap in independent processes/roots.
Actual final verification wall time is **31m 35.6s**; overlapping durations are not
added. No total development-time claim is made. All seven runner negative controls
reject. The [release receipt](../../evidence/gameplay-g16/final-a/release.json),
[audit](../../evidence/gameplay-g16/audit.json) and
[artifact index](../../evidence/gameplay-g16/artifact-index.json) retain actual
commands, environment, counts, timings, 795 stable source/Git bindings
and 12890 checked ordinary-worker imported-source entries.

Four focused G16 tests cover rotation/workspace access, actual selection in both
contexts, native material transfer/processing/depletion and genuine historical
compatibility. Existing G12–G15 coverage supplies unchanged costs, capacity,
salvage, effect and ownership contracts. The old G5 cohort explicitly uses old
profiles for `workshop_a`; original coverage remains. Catalogue expectations are
67 total / 58 ordinary structures and 60 preserved registration candidates.
The [preflight receipt](../../evidence/gameplay-g16/preflight.json) retains narrow
results and disclosed development driver/selector corrections. Only optional
bounded limits were added to the existing event driver; previous defaults remain.

Repeat from the repository root with committed inputs and a fresh directory:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g16.py --evidence evidence/gameplay-g16/owner-verification
```

Named checkpoints: `checkpoint/gameplay-g16-start-20261025-a`,
`checkpoint/gameplay-g16-inputs-20261025-a` and
`checkpoint/gameplay-g16-verified-20261025-a`. The local publication receipt
`.baseline/gameplay-g16-publication.json` records remote main/tag readback after
the authorized push. G16 stops here. Underground encounters, H1's second connected
outing, alternative approaches and recovery balance remain later bounded work.
