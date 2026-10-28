# W5H — play, reset and revise saved rooms

Workbench now launches an eligible saved ordinary room in the actual game from
**Test room**, with independent **Stop**, **Reset current test** and **Test latest
saved version** actions. The running game retains captured inputs while editing,
validation, publication and parked-draft recovery remain usable. Gameplay saves,
caches and diagnostics have an explicit disposable owner.

## Source boundaries

| Boundary | Revision / checkpoint |
| --- | --- |
| Reviewed local and initial remote main | `3ee22ef3c77cd56df75441076873840ef3b66fc7` |
| Start | `checkpoint/workbench-w5h-start-20261027` |
| Geometry repair, committed before extension | `03b19adb10c7a794082c346b84e867a03b3e2a29` |
| Implementation / Windows application package | `68bb14bdac7245d5d6e62a27b10225ac7c58ff23` |
| Lifecycle/native verification corrections | `dc751ade5e90ccaef913341fd5fd8e9dd19cbfa7` |
| Final selected-project game preflight | `3282b0570a7839140a0361ec4fb1f7431944c4e9` |
| Final verification / receipt assembly inputs | `05bca75c52fa29ee2983a9d39721cb2314dd65f8` |
| Evidence identity | `checkpoint/workbench-w5h-verified-20261028`; exact remote SHA in the verified external handoff |

Work stayed directly on production `main`. No task branch, worktree or additional
development checkout was created. Named start/geometry/implementation/package/
test checkpoints retain the boundaries. Disposable fixtures contain runtime
inputs and evidence. The owner plan remains untracked and unchanged.

The application package contains the host, frontend, bridge and embedded runtime;
it imports game code from the selected project through the frozen payload. After
the package revision, production Rust/TS/bridge inputs remain unchanged. Later
changes are verification fixtures and the selected-project Python preflight
correction. The final native run captures that corrected Python, and the receipt
compares its actual bytes with the working tree. Git and working-byte hashes are
both retained, including Windows line-ending differences.

## Geometry repair

Mounted forms rebase dimensions, arrival and fallback proposals when their
authoritative source fields change. Absent optional fields and dimension-derived
defaults work correctly. Unrelated painting and hiding/showing mounted documents
retain pending proposals; controls are not keyed by draft bytes. Removed or
unsupported resize-fill entries resolve to a usable legend entry.

The actual React controls pass Source → Undo/Redo → one-field edit sequences for
dimensions, arrival and fallback, including companion-coordinate preservation,
optional defaults, painting, mounted switching and fill changes. Localized source
operations and one-action history remain. [Repair evidence](W5H_REPAIR.md) was
committed before the game extension.

## Saved admission, frozen inputs and gameplay

The native boundary resolves an owned document token and rechecks saved bytes,
accepted draft intent, publication/reopen acknowledgement and ordinary immediate
layout policy. Dirty/conflicting/missing sources, protected/template/unsupported
sources and ambiguous identities cannot bypass it through renderer flags or a
cached review. Fresh captured validation uses the registered room contract,
production loader, room compiler/population/access and required readable inputs.
Warnings and loadable unsupported records retain their existing semantics.
Test admission does not create/consume an authoring publication review.

Bounded allowlisted enumeration captures code/configuration, consumed data,
saved typography, glyph/fonts, UI, sprite map and sprite sheets. It excludes save,
Git, environment, cache, recovery and previous-session trees before descent.
Per-file copy/hash checks and complete final saved-input freshness checks reject
mixed inputs and linked/reparse/resource escapes. The embedded runtime is copied
and verified too. Accepted payload/runtime files are read-only, imports/cwd are
controlled and every bootstrap rechecks captured bytes. Mutable files live outside
the payload. Legitimate typography and optional plain-UI fallbacks are disclosed;
required selected-renderer assets must load.

The preflight also constructs the actual normal player, equips/uses a real torch,
builds the small foyer and enters the assigned room through production descent
before accepting a replacement. A failed capture/preflight retains the previous
test, including a still-running process. Other parked drafts are excluded.

`SaveManager(save_root=...)` is injected before any startup/cache probing; no global
save directory is mutated. The game-owned `room_test.py` runs the actual renderer,
input loop, factories, AI, reader, movement, combat, FOV and persistence. A physical
foyer stair links one distinct SubMap instance to the selected layout. Normal
ascent/return retain cached ownership. Boundary travel explains the staged limit.
The shared normal six-item player profile has needs/carrying and ordinary death,
with usable carried/equipped light. Per-engine debug configuration enables normal
F5/F9 without editing the owner's config. Quit/death cannot enter campaign restart.

## Packaged author → play → revise observations

The final Windows run uses actual packaged Workbench controls and its pinned
runtime, with disposable project/settings/recovery/session roots. Source editing
is one supported control in the journey: it saves/reopens a 13×9 ordinary room
containing a physical letter bound to `lab_note_primary_b`, a crate/storage pool
and a creature variant whose sight radius is deliberately set to one.

| Observed identity | Value |
| --- | --- |
| Saved/reopened room v1 SHA-256 | `c7d18e9ee1622af8b600109cbe86be151ba4d62795759e8381127ac48c0e1ffa` |
| Saved/reopened same-ID v2 SHA-256 | `f1ada5153b544a08f44b9abeb1742b064cb8f5c51f4101a9c1f9bf2b88cf7e4a` |
| Captured game/data/resource inputs | 531 files |
| Captured pinned runtime | 1,809 files; manifest `da918acc87d9602b2c45585e22dfe008f0cd08524627131bd86f2e19db3a86a5` |
| Seed / profile | `20261027` / `ordinary-player-v1` |
| Actual initial → revised arrival | `[37,23]` → `[38,23]` |
| Specifically added object | `wood_bundle` at `[35,18]`, on the changed `flagstone` tile; weight 1, fuel/fibrous tier 1 |

Normal app-local pygame keys exercise movement/look, pickup of the exact letter,
the actual reader, container opening/transfer, real creature AI turns and physical
ascent/return. Actual sprite frames show torch lighting/FOV. These are controlled
staging and scripted choices, not encounter-balance evidence.

Normal F5/F9 preserves relevant inventory, actor, terrain, container, entry/return
and scene state. A genuinely different Python process uses the supported frozen
`--load` bootstrap and restores that checkpoint. Its audit records 68 save-path
operations, all confined to the explicit test root. A copied owned checkpoint
with its required scene removed refuses loading instead of regenerating it.

While gameplay runs, a same-ID room revision is validated and published; an
independent invalid item draft stays checkpointed/recoverable. The old test keeps
its old room/code/data/font/sprite bytes. Reset works even with a later invalid
unsaved target draft, retains manifest/seed/profile, restores initial contents and
discards the former mutable root. Latest-saved capture starts fresh and realizes
the changed arrival/terrain and the specifically added component above.

Stop, normal game quit, unexpected child exit, cancellation, double launch,
project replacement and abrupt packaged host death are observed. After abrupt
host death the owned game exits, an unrelated sentinel remains alive, and a later
capture cleans the abandoned dead-owner payload. Session/snapshot/PID-bound
readiness requires a real frame; stale identities cannot replace current status.
Separate Windows Job Object tests also prove non-cooperating-child reaping and
abrupt owner death. Pipe diagnostics are bounded and independent of the worker.

A focused packaged run makes the ordinary starting torch inert: actual preflight
refuses the replacement while preserving the previous running PID/snapshot. It
also removes optional UI panels, observes the explicit `UI_FALLBACK` warning and
a usable actual plain-panel game frame. An additional headless ordinary `main()`
run generates its normal 128×128 world, reaches the starting laboratory, preserves
the ordinary debug default, and saves/loads through the default relative save
owner in a disposable fixture. Only a verification frame observer is supplied;
normal construction, Engine.run and SaveManager execute.

## Gates and preservation

| Locally executed gate | Result |
| --- | --- |
| Frontend / TypeScript | 65 tests pass / typecheck passes |
| Actual mounted geometry fixture | Pass |
| Rust / clippy | 66 tests pass / warnings denied |
| Full stable worker suite | 66 pass, one expected dependency-absence skip; negative control passes separately |
| Production persistence/combat/scene/G17/access/destinations/readers/session injection | 58 pass |
| Windows release / NSIS | Locked build passes; source/release bridge and all captured runtime files reconcile |
| Final packaged room journey | Pass, including cold bootstrap, reset/revision and real lifecycle faults |
| Final packaged compatibility | Lost-reopen workspace, ordinary pools, submap scheduling/publication faults and four startup/project-change/restart scenarios pass |
| Focused preflight / ordinary standalone startup | Pass |

The receipt retains failed early attempts distinctly: effect-timing assertions,
Windows diagnostic reader locks, the cold fixture's prior Stop marker, odd-width
centering, a Python environment lacking packages in an isolated child and native
monitor/signal-exit harness assumptions. The real handoff acknowledgement issue
was corrected in implementation. Native fault fixtures retry only no-write BUSY
contention and retain exact competing-byte checks. No failed run is relabelled.

Across final verification, **8,191** inventoried files retain both hash and mtime;
the seven differences are explicit final task source/test corrections. Existing
content, fonts, settings/launcher sources, owner plan, wiki edition and reference
pack remain preserved. Snapshot enumeration never descends personal save trees;
save isolation evidence uses explicit disposable sentinel roots and path auditing.
No owner save content supplies this evidence. Generated rooms, saves, full
manifests, logs and concise visually inspected screenshots follow the existing
ignored `.artifacts/` convention and are hashed in the [machine receipt](w5h-verification.json).

These are current local Windows observations, separately identified as source
review, mounted/headless fixtures, actual packaged controls/frames and fresh
process restoration. The brief's historical W5G independent review and reported
Windows evidence are not relabelled as independent repetitions by this run.

This delivery supports saved ordinary immediate layouts, one fixed scenario
profile/seed and one game per Workbench instance. Capture requires the packaged
or prepared embedded Windows runtime; mutable development virtual environments
are refused clearly. Natural-world assignment, unsaved overlays, multi-file
publication, deterministic combat replay, configurable loadouts, persistent test
libraries, campaign migration and wiki/reference-pack rebuilding remain outside
W5H. The final evidence checkpoint and remote-main readback supply the handoff
identity without a self-hash commit loop.
