# G18 — Action timing and save reliability

29 October 2026, America/Edmonton. Production checkout `main`.
Starting revision: `92bc185f0bbf60ee4a69125798ddcff65908b33a`.
Implementation: `2447e2652019768f42060eb4906b2e7a018aabfb`.
Final verification inputs (including free-action expiry and the corrected harvest fixture):
`323f5d7d159711f905895655f62ccefcb94eb9a3`.
The delivery/evidence commit is identified by
`checkpoint/gameplay-g18-verified-20261029-a`.

## Selected behavior

Accepted movesets settle their authored time once, including misses and dodges.
Weapon adjustments use signed integer millionths of a phase, with whole
adjustments truncated toward zero and a residual strictly between -1 and +1
phase. The deliberate precision is one millionth; authored 0.8/1.0/1.2 costs
are exact at that precision. Ordinary actions and 1.0-cost attacks preserve
the residual. Terrain/work debt and movement-speed credit keep their existing
meanings. No shared nonnegative numeric validator was relaxed.

| Neutral-start actions | Charged phases per attack | Total |
|---|---|---|
| 1.0 | 1 | 1 |
| 0.8 | 1 | 1, retaining 0.2 saving |
| Five 0.8 | 1, 1, 1, 1, 0 | 4 |
| Five 1.2 | 1, 1, 1, 1, 2 | 6 |
| 0.8 then 1.2 | 1, 1 | 2, neutral balance |
| Rejected attack | 0 | Balance unchanged |

Every charged phase uses the existing `_advance_turn` pipeline once. Skipped
phases do not tick needs, light, cooldowns, effects, AI or processing. Extra
phases do not replay attack/contact/death/kill hooks. Settlement stops on death.
Rejections retain cooldown, coatings, target state and an existing Press
opportunity. Bump attacks now report commitment so rejected attacks are free.

A Heavy Blade Press kill pays its normal settlement first, including existing
work debt, then grants one nonstacking immediate adjacent local step. Any legal
direction works through ordinary movement controls. The step waives its base
phase while retaining physical movement, occupancy, FOV, entry hooks/hazards and
terrain/needs/work surcharges. It neither spends nor earns movement-speed credit;
it still counts against sprint's physical-move duration. World-phase bonus
durations tick only for phases actually charged.

Another committed action expires Press, including wait, bump attack, door
opening, inventory use/equipment/reading, harvesting, interaction, crafting, perk acquisition and free sprint
activation. Inspection, menus, saves, cancellation, blocked steps and genuine
rejections preserve it. Successful stairs/chunk travel expire it without changing
their established costs; stairs still charge zero phases. Death clears it.
The description and ordinary log explain the step, terrain costs and expiry.

Inventory consumption remains a separate result from commitment. Minimal result
plumbing makes inspection/failed use free while retaining G15's one ordinary
phase for successful use, equipment changes and reading, without draining old
work debt. No general action scheduler or moveset-effect completion was added.

## Persistence and compatibility

The component-v1 engine record has two optional additions: the strictly bounded
integer `_weapon_time_balance` and boolean `_free_move_pending`. Present values
validate strictly, including rejection of booleans as numbers, floats as the
integer balance, nonfinite values and endpoints. Neutral fields are omitted
without changing the meaning of an absent field. Every restore resets absent
fields, including F9 after divergent unsaved play. The sparse neutral encoding
preserves genuine historical serialized fingerprints. Existing positive
`_move_debt` is retained; no historical origin is guessed.

The [actual before probe](../../evidence/gameplay-g18/before.json) used an owned
crude blade, legal low HP and the ordinary Desperate Slash key. It charged one
phase but produced `-0.19999999999999996` work debt; the real writer rejected
`component_state.engine._move_debt`. The final writer succeeds with nonnegative
work debt and a separate -0.2 weapon residual. A separate process restores it,
pays authored cooldown waits normally, and charges 1, 1, 1, 0 for the next four
Desperate Slashes. That cold continuation commits four attacks for three
weapon phases and pays 28 separate cooldown-wait phases.

Before/pending/consumed/expired checkpoints are tested with same-session F9 and
separate-process load. Cold pending movement costs 0 then 1; neutral/consumed/
expired movement costs 1 then 1. Restored actors and physical remains match;
load does not replay an attack or kill. Invalid fields in real checksummed
published test generations reject without replacing the current player/world/
scene or timing state. The writer also rejects false-like values of wrong type.
Checkpoint publication, transactional load and recovery machinery are unchanged.

The [pre-edit historical observation](../../evidence/gameplay-g18/pre-edit-historical.json)
and [final comparison](../../evidence/gameplay-g18/final-c/historical.json)
agree exactly on the genuine G14 dismantled-crate checkpoint, its altered scene,
inventory and all 51 plan dependencies, plus the pending original apothecary.
Archive SHA-256: `e4987c58eee50e43c7717b29b48c39a87c4ac43acdd86d6d8598676fd8cb53f6`.
The new missing-field test separately retains 2.25 positive work debt. Full
existing discovery retains additional historical-save and recovery coverage.
Only disposable save roots were used; personal campaigns were never opened.

## Ordinary-input demonstration and verification

The [original-loop receipt](../../evidence/gameplay-g18/final-c/demo/journey.json)
and [momentum view](../../evidence/gameplay-g18/final-c/demo/press-momentum-feedback.png)
use actual weapon definitions, normal inventory controls, app-local Pygame
events and the original renderer. Setup explicitly stages a clear laboratory
patch, 25 player HP, factory weapons, a durable AI-disabled target and a wounded
1-HP Press target. The durable target is moved away for the Press demonstration.
Cold arithmetic continuation suppresses AI processing after factory restore
reattaches it; cooldowns, waits and other phase systems remain active. These are
bounded timing demonstrations, not acquisition, discovery, combat balance or an
expedition. No cooldowns are cleared in this demonstration.

| Ordinary input | World turn afterward | Relevant result |
|---|---|---|
| Equip crude blade through inventory | 481 | One paid action |
| Desperate Slash (R), F5 | 482 | -0.2 residual, valid save |
| Equip Heavy Blade, killing Press (Q) | 484 | Attack pays; opportunity pending |
| Blocked Up | 484 | Pending preserved |
| Down | 484 | Physical step; pending consumed |
| Down | 485 | Second step pays |
| F9 to pending checkpoint, wait | 485 | Pending restored, then wait expires it |

The 23 new focused tests cover the cost table, intervening ordinary actions,
phase/contact/death accounting, rejection gates, Press routes, real harvesting,
terrain/speed composition, delayed grant, death, writer validation and cold/F9
persistence. Existing G14, G15, harvesting, sprint and combat coverage is reused.

Production environment: Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0,
NumPy 2.4.6; dummy SDL and disposable save roots. Commands from this checkout:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --timeout 3600 --evidence evidence/gameplay-g18/final-c/focused
& $ResonancePython -X utf8 tools/verify_d.py --evidence .baseline/gameplay-g18-final-c
& $ResonancePython -X utf8 tools/verify_g18.py --evidence evidence/gameplay-g18/final-c/demo
& $ResonancePython -X utf8 tools/g15_historical.py --output evidence/gameplay-g18/final-c/historical.json --baseline evidence/gameplay-g18/pre-edit-historical.json
```

| Final check | Actual result | Process duration |
|---|---|---|
| Unfiltered focused discovery | 357/357 tests pass | 32m 19.9s |
| Unfiltered production D | 3676/3676 assertions; 159 valid workers | 15m 30.6s |
| Original-loop demonstration and cold continuations | Pass | 34.6s |
| Genuine historical checkpoint comparison | Exact agreement | 5.5s |

The final processes overlap. Their measured wall time is **32m 19.9s**, not
the sum of process durations or total development time. D retains all seven
runner negative controls, 146 ordinary workers and 13 intentional crash workers.
The [release receipt](../../evidence/gameplay-g18/final-c/release.json),
[audit](../../evidence/gameplay-g18/audit.json) and
[artifact index](../../evidence/gameplay-g18/artifact-index.json) retain commands,
environment, results and hashes. Both full gates agree with the current raw
manifest of 822 source inputs; D binds 14605 imported-source records. The
[Git comparison](../../evidence/gameplay-g18/source-binding.json) records raw
working/Git hashes and explicit CRLF/LF comparisons for all ten changed source
inputs. The artifact index also retains raw working and staged Git hashes so
Windows line-ending normalization is explicit. Tested working bytes correspond
to committed revision `323f5d7`; the
delivery commit adds documentation and evidence without changing runtime code.
No required final gate was waived and no blocker remains for G18.

Development corrections: the first added harvest fixture selected an entity
without a harvest profile and was replaced by the actual Revenant definition.
The initial D attempt used an unapproved disposable output root and the existing
guard rejected its workers. Final D uses `.baseline`; no guard was changed.
A cold arithmetic probe initially allowed restored AI to kill the low-HP fixture
during waits; it now explicitly isolates AI and has a finite wait budget.
The intermediate final-b gates were stopped after 59 passing D workers when source
review identified missing expiry on direct free crafting/perk commits; final-c
reruns everything against the completed source. No failed or interrupted attempt
is treated as completion evidence.

Checkpoints: `checkpoint/gameplay-g18-start-20261029-a`,
`checkpoint/gameplay-g18-inputs-20261029-a`,
`checkpoint/gameplay-g18-inputs-20261029-b`,
`checkpoint/gameplay-g18-inputs-20261029-c`, and the verified tag above.
No push authorization was supplied in this execution session; delivery is local.
The owner's unrelated proposed Workbench plan is preserved untracked. Wiki,
canonical rewards/acquisition, other weapon effects, authoring contracts and
W5Q selection behavior are unchanged. The next attack/contact and stationary
concealment repair remains separately scoped.
