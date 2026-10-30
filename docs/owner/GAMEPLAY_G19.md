# G19 — Contact and concealment fairness

29 October 2026, America/Edmonton. Production checkout `main`.
Starting revision: `596279d8ebab17634dc74df2a60d8f9f56628b5c` (delivered G18).
Implementation and final verification inputs:
`97e68fd2127b7acd7581e1e8cbe435d53757aabf`.
The delivery/evidence revision is identified by
`checkpoint/gameplay-g19-verified-20261029-a`.

## Selected rules

Melee requires distinct, in-bounds, walkable neighboring cells. Cardinal and
diagonal contact work; a diagonal needs one walkable orthogonal side. Solid
endpoints, closed doors, sealed corners, coincident cells and distant coordinates
reject. Geometry never consults player FOV. Ordinary player attacks, all shipped
movesets, monster melee and the Lurker bonus share this physical rule. Increasing
a moveset's authored range cannot unlock ranged melee. Existing living-fighter
and impairment checks run before commitment; direct monster resolution also
rejects disruption. Ability suppression still gates special abilities, rather
than disabling ordinary melee generally.

Rejected player contact retains time, weapon balance, Press, cooldowns, coatings,
HP and contact effects. Legal misses and dodges commit normally. Grass-entry
automatic strikes use the same checks, retain their existing free time policy,
and announce the grass opportunity only when accepted.

Plague Crow keeps adjacent melee and nonadjacent attacks within three Euclidean
tiles, matching its existing AI selection. The resolver enforces that envelope
even for stale/direct calls. Its nonadjacent line uses walkable endpoints,
transparent Bresenham interior cells, and at least one transparent orthogonal
side at each diagonal ray step. Actors do not occlude this route. Opaque terrain,
closed doors and sealed corners block it before damage, hit effects or a
projectile. Rendering capability does not decide legality. The declared
`min_range: 2` still starts ranged presentation; damage, sickness, speed and
targeting cadence remain unchanged. Throws deliberately retain their existing
ownership, scene, visibility, range and stricter walkable-segment flight checks.

Stone Lurker still wakes at three tiles and changes from rock to Lurker. Its
separate AmbushAI trigger remains 2.5 tiles and its speed remains `0.5`. Waking
arms one bonus opportunity. Distance, blocked terrain/corners, impairment,
suppression and disruption retain it. One legal committed attempt consumes it,
including a miss, dodge or zero damage. The bonus is separate from the unchanged
normal speed budget. Existing hibernation, pending/consumed and AI-trigger save
fields suffice; loading does not wake, strike or replay the opportunity.

Active perception derives concealment from the occupied tile on its supplied
map. The saved `_in_concealment` field remains compatible but cannot override the
current physical situation. Waiting, stationary actions, UI and rejected input
retain terrain cover. Moving out clears its effective benefit immediately,
including a Press step with no world phase. Scene arrival, supported position
restoration, F9/cold load and terrain changes need no replayed entry effect or
turn. The existing two-tile reduction, minimum one, light/darkvision behavior,
and pursuit-memory/timeout policy remain. Close observers can still see the
player. Pursuer phantoms remain remembered coordinates with no real fighter;
neither cover nor real attacks are borrowed from the unrelated active scene.

G18's timing implementation, weapon values and save schema are unchanged. Its
focused coverage retains exact fractional boundaries, Press lifecycle, phase
accounting, positive work debt, cooldown/coating behavior, strict optional-field
validation and cold/F9 restoration. No historical archive was rewritten.

## Verification and compatibility

The [baseline probe](../../evidence/gameplay-g19/before.json) records the original
distant helper acceptance, a real three-tile Lurker hit through a wall (60 to 53
HP with controlled RNG and zero dodge), and lost concealment after a wait.
These are the defects selected by G19, not G18 regressions or balance evidence.

The 21 new focused tests cover geometry, commitment/side effects, Crow line and
reach with and without projectile support, actual Crow combat, one-time bonus
accounting, terrain perception, memory, free Press movement, four Lurker save
states, cold continuation, F9, scene cache ownership/return and arrival/stairs.
Applicable existing D targeting/throw cases retain legal, blocked, stale,
unseen, canceled and invalid-confirmation behavior, item ownership and time.

The active production runner imports `tools/b1_cases.py`; its K03 fixture formerly
expected a distant callback to consume the bonus. Its identity, four-owner,
restore and non-replay checks remain. It now separately proves distant and
sealed-corner retention, then opens one corner for the exactly-once positive
attempt. D's restored-effect fixture also formerly called a disrupted attacker
directly to spend an armor charge. It now verifies rejection preserves the
charge, runs the original two expiry phases, then spends the charge through
legal contact. No cases were disabled; historical tool copies remain immutable.

The genuine G14 dismantled-crate checkpoint and its pending original apothecary
match the [pre-edit observation](../../evidence/gameplay-g19/pre-edit-historical.json)
exactly in the [final comparison](../../evidence/gameplay-g19/final-a/historical.json):
altered scene, inventory, all 51 plan dependencies and pending content agree.
Archive SHA-256:
`e4987c58eee50e43c7717b29b48c39a87c4ac43acdd86d6d8598676fd8cb53f6`.
Only disposable save roots were opened.

Production environment: Windows x64, CPython 3.11.0, pygame 2.6.1, tcod 19.3.0,
NumPy 2.4.6, dummy SDL. Commands from this checkout:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/critical_fix_regressions/verify_fixes.py --timeout 3600 --evidence evidence/gameplay-g19/final-a/focused
& $ResonancePython -X utf8 tools/verify_d.py --evidence .baseline/gameplay-g19-final-a
& $ResonancePython -X utf8 tools/verify_g19.py --evidence evidence/gameplay-g19/final-a/demo
& $ResonancePython -X utf8 tools/g15_historical.py --output evidence/gameplay-g19/final-a/historical.json --baseline evidence/gameplay-g19/pre-edit-historical.json
```

| Final check | Actual result | Process duration |
|---|---|---|
| Unfiltered focused discovery | 378/378 tests pass, including all 23 G18 tests | 22m 43.6s |
| Unfiltered production D | 3704/3704 assertions; 159 valid workers | 9m 57.3s |
| Original-loop demonstration and cold continuations | Pass, 86 checks | 11.3s |
| Genuine historical checkpoint comparison | Exact agreement | 2.4s |

The processes overlap: actual final verification wall time is **22m 43.6s**, not
the sum or total development time. D retains seven runner negative controls,
146 ordinary workers and 13 intentional crash workers. The
[release receipt](../../evidence/gameplay-g19/final-a/release.json) and
[D audit](../../evidence/gameplay-g19/final-a/d-audit.json) retain commands,
environment, measured intervals and full results. Both full gates agree with the
current raw manifest of 825 source inputs; D binds 14624 imported-source records.
The [Git comparison](../../evidence/gameplay-g19/source-binding.json) records raw
working/Git hashes and explicit CRLF/LF agreement for all ten changed Python
inputs. Tested working bytes correspond to `97e68fd`; the delivery commit adds
only documentation/evidence. No required final gate was waived.

## Ordinary-input demonstration and limits

The [original-loop receipt](../../evidence/gameplay-g19/final-a/demo/journey.json)
and three production-rendered captures disclose a staged clear laboratory patch,
tall grass, a wall, a stationary-home Revenant seven tiles away, and a factory
Lurker at distance three behind the wall. Its fixed RNG controls combat; ordinary
app-local key events, AI, survival, terrain costs, renderer and saves remain real.
Entering grass charges its authored surcharge. Two ordinary waits retain cover
and pay normally. Inspection, inventory, rejection and F5 remain free in cover.
A staged pending Press step moves onto exposed terrain with no world phase;
F9 restores the covered/pending checkpoint. Moving the awake Lurker into legal
contact then yields one bonus and one separately observed normal-budget attack.
Pending and consumed checkpoints are cold-loaded without replay.

The cold pending continuation isolates the Lurker's normal AI while proving
blocked/distant retention followed by exactly one legal bonus miss. Unit-cost
cover in one focused test deliberately isolates zero-phase entry; actual tall
grass costs remain exercised in the ordinary demonstration and G18 composition
coverage. Staged actors and restored states do not establish natural frequency,
acquisition, balance, unaided discovery or a complete expedition. H1 remains open.

Development corrections retained in the task evidence: initial fixtures had not
activated the reality bubble and assumed `0.8` Lurker speed instead of the actual
`0.5`; those fixtures were corrected. The first demonstration geometry let the
wall obscure the observer, and an exposed control moved just outside its actual
seven-tile sight radius; the final arrangement independently exercises cover.
A tracing mock initially obscured the bonus caller; a forwarding observer now
records actual callers without changing combat. These failed attempts are not
completion evidence. Focused development then passed 56 tests, and the selected
legacy Lurker/restore runners passed 170 assertions before final unfiltered gates.

The enduring project compass, retained Workflow 1.0 reference, current `AGENTS.md`,
approved Emergent Expeditions compass and supplied implementation proposal's H1
direction were read; [reference hashes](../../evidence/gameplay-g19/authority.json)
identify the actual available copies. The arc names Workflow 1.1, which was not
available locally; current task/production working instructions govern this run.
This delivery
is the selected fairness repair, without changing reward placement, authoring
contracts, progression, FOV/pathfinding, pursuit architecture or the wiki.
The owner's unrelated proposed Workbench plan remains untracked and untouched.
Sound-driven investigation is the next intended capability and was not started.

Checkpoints: `checkpoint/gameplay-g19-start-20261029-a`,
`checkpoint/gameplay-g19-inputs-20261029-a`, and
`checkpoint/gameplay-g19-verified-20261029-a`. G19 explicitly authorizes publishing
the scoped commits on `main` and these references to `origin`. Remote `main` and
the verified reference identify the delivery/evidence revision; the execution
handoff reports their complete SHA after readback. The tested implementation
revision above is its parent. No force-push or unrelated owner commit is involved.
