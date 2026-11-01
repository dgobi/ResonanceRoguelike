# AI-6: territorial objectives and bounded pursuit

Implementation and tested runtime/content/editor revision:
`d448e7d3a760bb2b27588571ad0823b667c8007b`.
Final verification-input revision: `6c1366ac428978615cd25758c43f43cce640b23c`.
It changes only two exact-inventory tests for the three commissioned rooms;
runtime/content/editor and package bytes remain those verified above.
[Verification delta](../../evidence/ai-6/verification-input-delta.json) records
the precise change and retention basis.
Start: `859713379cfc3eaa4441bf2d42215960117c4e65` on production main.
This later delivery adds only this completion record and non-consumer evidence.
[Input delta](../../evidence/ai-6/input-delta.json) verifies frozen consumers are
unchanged. The final handoff supplies the delivery commit; this record cannot
embed its own eventual hash.

An ordinary creature can now defend its original place with either direct melee
or the existing strike-and-withdraw engagement. Version-5 `territorial_guard`
wraps one locally extracted shared tactical executor: no second withdrawal
controller or demonstration-species dispatch. Versions 1-4 retain their strict
schemas, saved effective meanings, timing and existing sensory/effect contracts.
This is an active-scene objective, not recruitment, companion support or an
arbitrary behaviour graph.

The stable anchor is actual instantiated placement, saved home coordinates and
owning scene identity. Construction preview cannot bind a scene. Movement,
blockage, loading and target changes never rebase it. Removing a Ward gives no
notification: the creature guards the place. Default inner/outer radii are 4/6
Chebyshev tiles, bounded to 1-7/2-8 with outer strictly larger. Ordinary current
sight and hostility alone acquire eligible living local intruders inside the
inner radius. Hidden live coordinates, anonymous sound and debug reveal provide
no prey position. Retained sight of prey beyond the outer limit stops pursuit;
all approach, retreat, investigation and return route steps obey the domain.
Planning and commitment share occupancy, terrain, decor and diagonal legality.

Evidence timeout is charged phases since actual sight (inclusive deadline),
separate from the spatial thresholds. Pursuit spends a finite default 32 ordinary
opportunities across attacks, holds and movement. The shared tactical approach
also retains its 32-opportunity cap and existing cycle resets; these never
replenish the separate objective budget. Attacks, target invalidation
and transitions cannot refill an active encounter. Eight approach failures
without progress, expired evidence, invalid prey or exhaustion retire it and
commit to a physical return. Full paralysis prevents physical action and tactical
spending, while evidence may expire. The existing at-most-two ordinary scheduler
adds no speed or banked recovery burst.

Return prefers the original tile, otherwise a reachable legal resting tile
within one Chebyshev tile. The original anchor persists. Return permits 32 route
opportunities and eight consecutive failures, then bounded retries at 12 ordinary
opportunities or earlier after meaningful local terrain/decor/occupancy changes.
External displacement permits bounded steps toward the domain, including beyond
the shared complete-route horizon; it never grants outside predation. A blocked
return does not wander, heal, teleport, rewrite home or continuously replan.
Seen adjacent hostiles may receive one ordinary contact-defence action,
alternating with return attempts. This can reach a hostile just beyond the limit
only through existing legal melee reach, without stepping across or restarting
pursuit/withdrawal. Failed unchanged visible intrusions stay retired after arrival;
new sight following loss, changed observed position or route conditions can rearm
them. Memory is bounded to 16 local retirement references.

Idle sound investigation uses existing anonymous propagation/expiry, at most
eight opportunities and the same constrained movement path. Outside origins and
sounds during committed return are discarded, not queued. Pulses cannot refill
an investigation. Current sight engagement wins; later independently lawful sight
may identify an intruder, hearing itself never does. Movement cues occur after
actual movement, gated by normal vision. Privileged bounded diagnostics expose
home, objective/engagement phase, evidence, budgets, action, retirement reason and
fallback without advancing time.

The real owner workflow is duplicate ordinary host -> Composite -> **Fixed
territorial post** -> choose **Territorial engagement** -> configure -> validate
-> review/apply -> reopen. Recipe changes require a new ID. Engagement and valid
same-recipe tuning are supported on the same ID; existing saved actors retain
their effective profile. Inactive wander radius is explicit. Direct melee restores
and requires canonical inactive withdrawal defaults; strike/withdraw exposes its
trigger, distance, full hold and finite withdrawal budget. Contradictory radii,
malformed types, unsupported fields/hosts/effects and cross-scene flags are
rejected by the game-owned validator. Art/body, unknown metadata, exact-source
publication and undo/redo remain owned.

`barrow_sentinel` and `barrow_watcher` are matched new-ID Hollow Revenant variants:
combat, perception, speed, body/art, territory and clocks match; engagement differs.
Open `ai6_sentinel_post` or `ai6_watcher_post` in Workbench and Test room. Step east
into the defended region, then wait to compare real melee with a qualifying hit
followed by actual withdrawal. Actual packaged controls created, configured,
validated, published and reopened both variants and all three rooms. A saved
Sentinel radius change 4 -> 3 prevented that first-step acquisition. Reset kept
the original captured dependencies; latest-saved used radius 3 and excluded a
dirty radius-2 draft. Radius 4 was then restored for the matched shipped examples.
[Authoring receipts](../../evidence/ai-6/authoring.json) bind all six final
publication files to actual controls. Development publication is distinct from
[final-package lifecycle evidence](../../evidence/ai-6/final-native-receipt.json.gz).
The [feature guide](../../roguelike/docs/TERRITORIAL_AI.md) documents the controls
and exact clocks, return, scene and information policies.

`barrow_ward_store_b` preserves the small store, one existing Faceted Ward,
existing note and modest crate. Its Sentinel at source (17,5) covers the Ward
(20,4) and eastern passage; the western opening remains a different approach.
Only this variant enters ordinary fresh-world selection beside preserved A,
with equal weights and unchanged 0.35 overall authored-barrow chance. Reports
recognize both legitimate stores and retain unknown present contents, inhabitants
and safety. Old selections, absence records, visited state, death and taken Wards
are not converted or regenerated.

The five compact [gameplay/compatibility scenarios](../../evidence/ai-6/play-responses.json.gz)
use normal rules and disclose staging. Seed 20261027, 128x128 real new-world
selection chose B at (64,115), `submap_64_115_0`; the native generated surface and
actual entrance constructed it. An ordinary player was staged at that naturally
selected entrance, not walked there from the laboratory. Normal starting blade/
jack use, visibility, damage and legal combat defeated its guard; Ward pickup,
revisit and independent cold load retained both consequences. A separate ordinary
withdrawal survived real damage and watched the guard physically return (56/60 HP).
The controlled sound comparison provisions one existing flint shard, then uses
real throw range/visibility, consumption, sound, time and AI. The same eastern
Ward-access/withdrawal route cost 14 HP without it and 10 with it, leaving the
guard alive at its original 14 HP in both. This demonstrates a useful situational
cost difference, not guaranteed safety, universal counterplay or a balance claim.

Same-scene F5/F9 and separate-process cold comparisons during engagement and
return preserve anchor, effective profile, evidence, budgets and commitment,
without action or aging from inspection. A successful actual departure clears
prey/sound and movement credit while preserving position, HP and home; revisit
allows ordinary return movement. Failed actual departure retains commitment.
The genuine pre-AI-6 SaveManager archive retains its phase-484 v4 hunter
commitment exactly. An independently captured pre-change 64x64 serialized-world
fixture retains selected A identities and frozen reports exactly through current
restoration. These are two disclosed disposable compatibility fixtures, not a
personal historical campaign or a claim of whole-game replay. See
[provenance](../../evidence/ai-6/legacy-provenance.json).

All certification below was independently executed for this task on the frozen
revision, Windows CPython 3.11.0 with pinned dependencies, Node 24 and pinned Rust.
No historical pass count substitutes for current gates. After the two stale
inventory assertions were corrected, focused and production-D reran unfiltered.
The other task-executed gates are retained because neither corrected test is a
consumer input to them; their actual source/package bytes are unchanged. The
first focused result (550/552) is preserved separately. Focused fixtures additionally
cover ordinary nonplayer intrusion, neutrality/death/foreign scenes, hidden
crossing, unreachable-target suppression, material rearm, constrained movement,
occupied/blocked posts, far displacement, sound spam, malformed saved state,
actual venom-victim paralysis and the ordinary opportunity scheduler.

| Gate | Executed result |
| --- | --- |
| Unfiltered focused | 552 passed |
| Unfiltered production-D | 3704 passed across 159 workers; seven runner negative controls |
| Complete affected Workbench worker | 49 passed |
| Frontend / host / startup | 94 / 71 / 15 passed |
| Typecheck / clippy / portable and debug builds | Passed |
| Final NSIS build and executable recertification | Startup, desktop, AI-6 and retained AI-3 native passed |
| AI-6 ordinary/controlled scenario family | Five grouped scenarios, including paired sound comparison |
| Independent AI-6 cold comparisons | Four passed |
| Retained-recipe ordinary play families | AI-3 and AI-5 rerun in this task, six scenarios each |


[Commands, environment and package identity](../../evidence/ai-6/release.json),
[compressed input manifest](../../evidence/ai-6/inputs.json.gz), full result/log
artifacts and [summary](../../evidence/ai-6/gates.json) retain source-bound evidence.
The affected worker corpus includes strict authoring, protected hosts/metadata,
creature corpus, rooms and new-world assignments. Unfiltered focused coverage
exercises AI-1 through AI-5; their real AI-3/AI-5 play families and retained AI-3
native lifecycle were rerun. [Material development failures and repairs](../../evidence/ai-6/attempts.json)
include the omitted extraction argument, rejected changing-input capture, editor
encoding correction and corrected natural-entrance fixture metadata. Superseded
runs are not reported as certification.

Portable package: `workbench/src-tauri/target/release/resonance-workbench.exe`.
SHA-256: `cbec0b5b88166aaa589fb8a2995a749eeb06cf981789cc29db94b0543954a8cd`.
NSIS installer: `workbench/src-tauri/target/release/bundle/nsis/Resonance Workbench_0.9.0_x64-setup.exe`; SHA-256 `7d47ac2f0cd89ec0807f01dfb469f51dc080a6efdece2e9247eb15667b8fa205`.
Packaging changed executable bundle metadata after the first portable run;
[final-byte recertification](../../evidence/ai-6/bundle-recheck.json) reran startup,
desktop and both native lifecycle families against the hash above.
[Package identities](../../evidence/ai-6/package.json) retain both boundaries.
Installer installation and clean-machine provisioning were not rerun.

[Preservation](../../evidence/ai-6/preservation.json) confirms the unrelated owner
proposal remains untracked and byte-identical, personal campaigns were not opened,
and no task branch/worktree or wiki maintenance was performed. The named start,
implementation and verified-input checkpoints are published with main. Input
checkpoint a is superseded by b after the verification-only correction; their
remote objects and peeled revisions are read back in
[publication evidence](../../evidence/ai-6/publication.json). The completion
checkpoint `checkpoint/ai-6-complete-20261101-a` identifies this later report/
evidence delivery; final remote readback is retained locally in
`.baseline/ai-6/final-publication.json` and the final handoff.

Scope stops at AI-6: one local objective, two supported tactics, one ordinary
room variant. No ally support, broader population pass, cross-scene simulation,
vessel/process work, arbitrary composition, full replay or human-enjoyment claim.
