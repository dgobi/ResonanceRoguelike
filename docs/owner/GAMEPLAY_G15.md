# G15 — Finite recovery from scavenging

25 October 2026, America/Edmonton. Production checkout `main`.
Starting source: `6b101d43389dba775b78cf4415c0ef638026f73c`.
Frozen runtime/data/test inputs: `65607721fe9caa4eaa7affdd5568a32eda6bdb7e`.

Herbal Dressing is one non-stackable, 0.1 kg prepared dose. Select it in `I`
and press Enter, keypad Enter or E: a living injured player recovers up to
**12 HP**, clamped to the current maximum, then the exact selected instance is
consumed and one ordinary inventory action completes. Feedback reports the
actual restored amount. Native AI, effects and survival follow the established
ordering. Full health, stale ownership and missing/dead fighter reject without
healing, consumption or world time. Closing the inventory remains free. Existing
reading/equipment actions, movement debt and HP-display policy are preserved.

## Acquisition and version policy

Use E beside a new apothecary's medicine chest, then select the dose and Enter
to take it. `apothecary_b` preserves the original 11×8 envelope, decor, entrance,
targets, rotations 0/180 and placement rules. Its chest at authored (1,1) retains
`alchemist_reagents` and independently rolls one dressing through
`apothecary_b_treatment`; the other two containers retain their original pools.
Only the grid/roadside commercial memberships change, at weight 1.0/cap 5.
Repeated search, travel, load and revisit never restock it. Capacity rejection
leaves the same dose available for a later valid transfer.

`apothecary_a`, shared pools, medicine-chest decor, G13 shed content, generation
policy, save schema, recipes, historical fixtures/evidence and the wiki are
unchanged. Existing campaigns keep their original selected assets and contents;
there is no backfill. The [genuine pre-edit G14 receipt](../../evidence/gameplay-g15/pre-edit-historical.json)
and [final comparison](../../evidence/gameplay-g15/final-a/historical.json) agree
exactly: all 51 placement dependencies pass, five old apothecaries remain selected,
and the pending old apothecary at (75,100) materializes through its original route
with its original complete fingerprint and no dressing. The visited, already
depleted shed/player snapshot also restores exactly.

## Bounded demonstration

The [final event trace](../../evidence/gameplay-g15/final-a/journey/journey.json)
uses seed 20261023 and the naturally selected apothecary in (75,100), placement
`settlement-0-cross-market-lot-42-66-N-0-building`, rotation 180. There is one
initial staging at its genuine public join (61,21), plus one disclosed setup
injury of 24 HP before the ordinary action sequence. Full-state eight-way routing
and UI selection are disclosed; the inherited entrance needs shipped diagonal
movement. Native threats, AI, effects, survival, FOV and supplies remain active.
No dose is inserted, threat cleared, invincibility enabled or later reset made.

The real chest contains its native reagents and exactly one dressing. Ordinary
movement, E search/transfer and I selection acquire it. Three retained production
views show the chest menu, readable item detail and actual recovery message.
F5 saves the acquired-but-unused dose; a genuinely separate game-loop process
cold-loads that exact snapshot and uses it. HP is **36 → 48 at the effect boundary**
and **48 after the normal turn**; the dose is gone, other possessions and equipment
remain, and use costs exactly one turn. Ordinary exit/return and another search
find no replacement. The consumed/healed state is saved and cold-loaded in a
third process. Both F9 checks follow an actual unsaved legal movement and restore
the explicitly identified snapshot exactly. Focused cache eviction/disk revisit
coverage also proves the depleted source is read rather than regenerated.

The small source recheck confirms the three supplied seed/start/candidate pairs.
It adds no all-seed placement guarantee. This is acquisition/use/persistence
evidence; normal-start discovery, recovery balance and H1's two outings remain
later work. Twelve HP remains an initial data-driven tuning value.

## Verification and delivery

Windows x64; production CPython 3.11.0, pygame 2.6.1, tcod 19.3.0, NumPy 2.4.6;
dummy SDL, app-local events and disposable save roots. No owner/desktop QA.

| Final check | Actual result | Measured duration |
|---|---|---|
| Unfiltered focused discovery | 274/274 pass | 18m 48.0s |
| Unfiltered production D gate | 3676/3676 pass; 159 workers | 8m 37.6s |
| Genuine historical comparison | Pass | 0m 2.9s |
| Subsequent bounded game-loop demonstration | Pass | 0m 25.8s |

The two existing gates ran concurrently in independent processes/roots. Actual
final gate wall time was **19m 17.5s**; overlapping durations are not added.
No total development-time claim is made. All 7 runner negative controls reject.
The [release receipt](../../evidence/gameplay-g15/final-a/release.json),
[audit](../../evidence/gameplay-g15/audit.json) and
[artifact index](../../evidence/gameplay-g15/artifact-index.json) retain actual
commands, environment, counts, time, 782 stable inputs, Git blob bindings and
12890 checked imported-source entries. Narrow development failures and their
fixture/driver corrections are distinguished in the preflight receipt and logs.

Repeat against committed inputs with a fresh evidence directory:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g15.py --evidence evidence/gameplay-g15/owner-verification
```

Checkpoints: `checkpoint/gameplay-g15-start-20261025-a`,
`checkpoint/gameplay-g15-inputs-20261025-a` and
`checkpoint/gameplay-g15-verified-20261025-a`. The local publication receipt
`.baseline/gameplay-g15-publication.json` records exact remote-main/tag readback
after delivery. G15 stops here; no further recovery systems or H1 work is included.
