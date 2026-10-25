# G13 — One useful scavenging stop

25 October 2026, America/Edmonton. Production checkout `main`.
Reviewed baseline: `3c7b51333aa4f9d1052b52caff2f19abed0f2b79`.
Final frozen runtime/data/test inputs: `cd058c9610fe8db4d4ed1034cefdd71eeb8abfe3`.

A fresh settlement can select the new stocked `tool_shed_b`. Enter from the
public approach, search its two crates and provision barrel, take the existing
Leather Satchel and useful supplies, equip the bag through inventory, and leave.
The acquired benefit and depleted storage persist.

## Installed content

The new 8×6, single-floor shed retains the old placement envelope, doorway,
rotations, buffer and road approach. Two crates separate working supplies from
the travelling bag; a barrel holds food and water. A real table, candle and
floor bundle of wood imply work interrupted. All three container targets remain
reachable in both permitted orientations. These use supported runtime fields
and existing visible assets. No item, decor, recipe or rendering definition
changes.

Three local pools supply one fixed Leather Satchel, 2–3 ordinary working
supplies, and two provisions. The other local pools cannot roll additional bags.
The bag retains its physical 0.8 kg weight and existing 10% effective carrying
reduction. The only selection edits replace the old shed reference in grid and
roadside support roles, retaining weight 1.0, cap 3 and every other setting.
The affected [authoring guide](../../roguelike/docs/STRUCTURE_AUTHORING.md)
explains the complete installed example and versioning rule.

## Demonstrated place and persistence

The [final real-event journey](../../evidence/gameplay-g13/final-d/journey/journey.json)
uses ordinary production generation at seed `20261023`. The selected shed at
chunk `(75,99)` has placement
`settlement-0-cross-market-lot-1-23-N-0-building`. The public road join is local
`(21,21)`; tools are at `(23,29)`, the bag at `(18,29)`, provisions at `(18,27)`.
The same fresh support cohort includes `(39,26)` and `(88,33)`; all three installed
scenes materialize, contain exactly one local reward, and retain their previous
placement geometry. This seed is an example, not an all-seed nearby guarantee.

The sole initial staging places the unchanged starting player at that actual
public approach. This is a bounded local outing, not a normal-start expedition.
Full-state cardinal route and UI-row selection are disclosed. The established
app-local event driver fixes gameplay RNGs to `20261020`; normal FOV, native AI,
survival and action costs remain active. No rewards are inserted, native threats
removed, invincibility enabled or health/supplies reset.

At this occurrence the tool crate contains a torch, wood and crude blade;
the barrel contains dried provisions and a water skin; the second crate holds
the bag. The player searches all three, takes the torch, provisions and bag,
equips it, exits, returns to the empty bag crate and exits again. The exact same
acquired inventory changes from **7.0 kg to 6.3 kg effective load**,
with unchanged physical mass. The full trace has 109 inputs; the saved
exit occurs 48 world turns after staging, at 60 HP. Production-rendered views show the approach, storage,
room and equipped inventory under normal visibility.

F5 saves the equipped reward and depleted site. A genuinely separate process
loads the checkpoint and compares complete player/world/scene state. A later
normal inventory action drops the bag without saving; F9 restores the earlier
checkpoint, including equipment ownership, reduced load and depleted containers.
The later unsaved drop is recorded separately from the restored snapshot.

The genuine retained G12 laboratory checkpoint restores its recorded player,
visited lab, knowledge and world exactly. All **51** saved placement dependency
closures still pass. Pending old scene `(75,99)` retains fingerprint
`c16c2366f60e69af3ea7040b2b4d30ae19770aa0a1ad03f3d89ce8f332c599fb`;
its plan identity and visited state stay unchanged. `tool_shed_a`, all its
shared dependencies and compound memberships remain available. Existing worlds
keep their chosen version and contents.

## Verification and delivery

Windows x64, established CPython 3.11.0 interpreter; pygame 2.6.1, tcod 19.3.0,
NumPy 2.4.6. Dummy SDL and disposable save roots only.

| Final check | Result |
|---|---|
| Unfiltered focused discovery | 259/259 pass |
| Unfiltered production D gate | 3676/3676 pass; 159 workers |
| Bounded G13 real-event journey, cold load and historical restore | Pass |
| Frozen input/Git binding | 768 inputs stable and bound |

The [release receipt](../../evidence/gameplay-g13/final-d/release.json) records
exact commands, environment, durations, hashes and Git bindings. The
[artifact index](../../evidence/gameplay-g13/artifact-index.json) binds the retained
outputs. Only `final-d` certifies the final inputs. `final-a` was interrupted
before a completed gate to correct the affected guide's loot-pool count.
The superseded `final-b` focused run completed 259 tests with one failure: a
second authoring catalogue count expected 57 rather than 58 installed building
candidates. Only that count and its guide text changed; the corrected cottage
access/action check and both new content checks passed before the rerun.
`final-c` was interrupted to align stale stock descriptions and trace labels
with the installed crates/barrel. Both content checks and the cottage check
passed again; the final-data real-event journey preflight also passed.
The final focused and D gate processes use separate evidence/save roots and run
concurrently, followed by the local journey. Gate durations therefore overlap.

Historical G9/G11 equality checks use the exact pre-G13 profile from the reviewed
Git commit. G5 retains the old shed's historical assigned-context certification.
All old expected worlds, fields and assertions remain. Separate new tests validate
current policy, all three ordinary selections and complete materialized contents.
Catalogue checks explicitly account for 65 structures / 56 ordinary buildings
and preservation of all 58 installed building candidates during registration.
The [development diagnostics](../../evidence/gameplay-g13/preflight.json) retain
the two corrected new-test assumptions and the visual content correction.

Repeat with committed inputs and a fresh evidence directory:

```powershell
$ResonancePython = 'G:\GameDev\RoguelikeBaseline-20261020\project\.venv\Scripts\python.exe'
& $ResonancePython -X utf8 tools/verify_g13.py --evidence evidence/gameplay-g13/owner-verification
```

The known G12 torch-as-explicit-fuel menu omission remains separate; this outing
does not depend on it. The historical independent Linux one-ULP coarse-world
comparison qualification remains; this Windows verification does not claim new
cross-platform determinism. Personal campaigns, owner drafts and the existing
wiki edition are preserved. No second destination or wider gameplay system is
commissioned by this delivery.

Starting checkpoint: `checkpoint/gameplay-g13-start-20261025-a`.
Final input checkpoint: `checkpoint/gameplay-g13-inputs-20261025-d`.
Delivery checkpoint: `checkpoint/gameplay-g13-verified-20261025-a`.
The adjacent portable delivery receipt records exact remote main/tag readback.
