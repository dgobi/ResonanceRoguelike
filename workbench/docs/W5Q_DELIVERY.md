# W5Q — saved settlement membership and ordinary-world inspection

The owner can now enroll a saved building through Workbench, recover and revise
its native membership, publish/reopen the fixed selection file, and inspect an
actual selected placement from an ordinary saved-policy world. The W5P transformed
entrance diagnostic now locates the actual blocked source cell in all eight
orientations. No canonical building or membership was installed.

## Revisions and preservation

| Boundary | Revision / local checkpoint |
| --- | --- |
| Starting local and remote `main` | `f34ab95d7ee82735afb61fac41ddb873bab149a3` |
| Start | `checkpoint/workbench-w5q-start-20261029` |
| Entrance correction | `aaa7f0d1890b6ea7ad1f93ae34026800c59da638` |
| Main implementation | `03203bbb936424f768a53defa43bec97be93aea0` |
| Final implementation/package inputs, including saved-row navigation | `43506c5b89d1a4ef98c931c1b33718d3203536e7` |
| Final package checkpoint | `checkpoint/workbench-w5q-linked-package-inputs-20261029` |
| Final delivery | Resolve `checkpoint/workbench-w5q-verified-20261029` |

Work stayed in the production checkout on `main`, without a task branch, worktree
or additional development checkout. Later commits retain verification harnesses
and evidence. The [source-bound receipt](w5q-verification.json) distinguishes
working bytes, Git-normalized bytes, 83 package inputs, captured game inputs,
runtime identities, actual execution and retained coverage. The final handoff
reports the full remote `main` readback; its local copy is
`workbench/.artifacts/w5q/remote-readback.json`.

The owner plan remains untracked. Canonical data, campaigns, settings, fonts,
launcher, historical evidence, wiki edition and reference pack are preserved.
The [preservation inventory](evidence/w5q/preservation.json) verifies 8,450
unchanged pre-gate files; the one subsequently changed file is the explicitly
scoped workspace verification harness. The inventory was captured after initial
implementation edits and excludes those paths; it is not presented as a complete
pre-edit byte inventory or proof that every personal path was unread. New preview
and replay code constructs no Engine or SaveManager. Existing save tests bind
their disposable roots, and the ordinary-main wrapper audits owned save access.

## Native contract and completed journey

`selection` / `settlement-membership-1` registers exactly
`roguelike/data/generation/settlement_profiles.json`, with `fixed-file` identity
metadata and native `{version, profiles}` source. Registry, renderer, host,
recovery and publication agree on that identity. No root ID, variant target,
derived `base_weight`, new native policy version or editor field is inserted.
Original source authority precedes staging. Case aliases, unsupported original
shapes/versions, alternate targets and hidden variant intent are rejected.
The selector retains its UTF-8 BOM rejection. Invalid editable values remain
repairable without world generation; malformed draft text recovers exactly.

All seven non-civic tables have add/remove and asset/weight/cap controls. Civic
membership and all other policy are protected through controls, Source and
recovery. Span edits retain untouched ordering, escaping and line endings.
Source and controls share undo/redo, including undo from malformed JSON.
Saved references resolve to unique actual ordinary sources independently of
definition-editing capability. Eligibility uses placement context and connected
road relation, with saved placement weight separate from membership weight.
Native validation owns duplicates, finite positive weights, integer caps,
nonempty pools and minima. Rows navigate while read-only, reuse existing owners
and return to exact profile/role/row context; changed origin text is stale.

The [packaged native journey](evidence/w5q/native-observations.json) recovered
independent building, selection and item drafts after host restart, rejected a
recovered civic edit, saved/reopened the building, explicitly added its membership,
rejected zero weight and repaired it through controls. It demonstrated exact
Source/control history and both exact and stale returns. A parked building draft
remained independent of the saved inputs used for generation.

The first explicit seed, **20261029**, selected **six** `w5p_lodge` instances in
grid/residential across settlements, with membership weight 5, placement weight 1
and cap 3 per settlement. The stopping rule allowed at most three listed seeds;
only the first was sampled. No competitor was removed or protected setting
changed. An actual selected 270° placement, whose frontage is its service entrance,
constructed through `create_surface`; full required entrance spans and
placement-owned readable/container receipts passed. The independently owned
featured `roadside_shrine_a` landmark also constructed with attributed receipts.

Deliberate removal, publication and byte-checked reopen restored the affected
table's original membership. A fresh ordinary world at the **same seed** selected
zero lodges through this route, while the saved building bytes stayed unchanged.
The old result became historical/stale. Both [accepted policy versions and the
building](evidence/w5q/fixtures/) are exact retained bytes. The
[independent replay](evidence/w5q/ordinary-replay.json) reproduced both native plan
identities and their equality with freshly saved `settlement_selection.resolve`.
Compact full plans, saved-input manifests and construction receipts are retained.

Every sample uses ordinary `world_gen.generate_world`, 128 × 128 dimensions,
normal saved configuration and the full candidate pools. Inspection deterministically
replays verified input and plan identities before resolving one placement and
materializing its chunk. It does not join an old placement list to a newly loaded
scene. One bounded scene is returned per inspection; the 16 MiB response and
90-second operation limits remain. Zero selection is valid; failures do not
trigger source edits or automatic seed search. The controlled W5P injection
helper remains separate from this implementation and evidence.

## Verification and limits

The [gate receipt](evidence/w5q/gates.json) records commands, runtimes, log hashes
and source boundaries: 88 frontend tests, TypeScript, 71 Rust tests, clippy with
warnings denied, 113 worker tests with one expected embedded-runtime skip
and separate missing-dependency control, and 334 broad game tests with stable
game source. It also records the complete selector native journey, seven-owner
workspace lifecycle, retained room capture/reset/latest/cold/fault lifecycle,
and ordinary 128 × 128 startup/default-slot save/load. Runtime is pinned Windows
CPython 3.11.0 with the required dependencies, Node 24.15.0 and Rust 1.95.0.

The room lifecycle ran on the immediately preceding package; the later renderer
change only enables selection-row navigation while read-only. Its host/runtime/game
inputs are unchanged. The final primary journey and workspace lifecycle ran on
the final package. The worker run crossed frontend/harness-only edits; exact
worker/game Python inputs stayed unchanged. These boundaries and all failed
attempts remain explicit instead of repeating expensive checks solely for evidence
formatting. The ordinary-main fixture reports optional sprite fallback warnings;
sprite rendering and installer UX are not certified.

The [diagnostic replay](evidence/w5q/entrance-diagnostic.json) binds the exact W5P
accepted fixture: all eight positive orientations pass; blocking source `(5,10)`
rejects all eight and consistently reports native `(5,10)`, its native span identity,
the actual transformed field/cell and scene cell. The asymmetric regression also
asserts those locations. Placement transforms and full-span checking are unchanged.

Membership edits activate in new plans. Existing captured policies/base weights,
selected IDs/roles/transforms and plan identities remain self-contained; generated
caches retain physical state. The existing `test_selection_only_edits_keep_pending`
and G3/G5 dependency/cache/missing-cache tests passed in the broad suite. Consumed
same-ID building/pool/item edits still face their separate pending-surface gate.
No save format change, migration, campaign rescan or compatibility waiver was added.

These are revealed initial construction and static access observations, not player
interaction, FOV, natural discovery frequency, balance or fun. Layout/road policy,
extra POI/compound editing, automatic registration, canonical rebalancing, surface
play sessions, new gameplay and wiki rebuilding remain deferred. The directly
affected Workbench and structure-authoring guides are updated.
