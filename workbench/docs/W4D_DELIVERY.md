# W4D — atomic review lifecycle and publication authorization

Verified 27 October 2026, America/Edmonton. W4D repairs the shared host boundary:
only the current reviewed draft can reserve publication; cancelled, edited or
superseded validation cannot install evidence. The existing writer is retained.

## Revision and scope

Local `main`, `origin/main` and live remote `main` began at
`7a2114d305788892620175a6e9e50a7c4567f65d`. There were no intervening changes.
The only pre-existing owner work was the untracked approved Workbench plan.
Work stayed in the production checkout, with local checkpoints
`checkpoint/workbench-w4d-start-20261027-a` and
`checkpoint/workbench-w4d-verified-20261027-a`. No branch, extra checkout,
worktree, reset, force push or history rewrite was used.

Implementation SHA: **b16c900ea0bbefffa91fcd3a7cbc96423f5f3547**. This report and
[compact receipt](w4d-verification.json) form the subsequent evidence commit;
resolve it with `git log -1 --format=%H -- workbench/docs/W4D_DELIVERY.md`.
The final handoff records that SHA and live remote readback. A commit need not
contain its own SHA. Detailed local logs and publication readback remain under
ignored `.artifacts/w4d/`.

App/worker remain **0.8.0**, protocol **7**, game contract **g2-2**, layout
capability **direct-creatures-1**. This is a private host/UI lifecycle repair;
there is no new content schema, IPC command, renderer filesystem permission or
save API. Node 24.15.0, npm 11.12.1, Rust 1.95.0/MSVC and bundled CPython 3.11.0
were used with the existing npm/Cargo/Python locks.

## What changed

`admit_apply` checks the live document token and review token, consumes the
review, captures the project/document/exact payload, and reserves publication
under one session lock. There is no earlier authorization snapshot to revive.
The immutable transaction then runs outside that lock. Duplicate Apply cannot
reuse the consumed review, including after failure.

One small `Operation` guard identifies the active request through output parsing
and final installation. `begin_validation` rejects conflicting requests as
`BUSY` without revoking anything; an accepted request advances the document's
attempt and revokes its old review before preflight, including early failures.
`install_validation` checks operation identity, project epoch, document identity,
revision and attempt under the same mutex before installing evidence. Opening a
document also owns its completion. An obsolete guard cannot clear a newer
request's busy/applying state or resources. Disk polling cannot revoke a newer
attempt based on an older scan.

Accepted cancellation advances the epoch and revokes review/attempt authority,
retaining all independent document sources and parked renderer drafts. A reserved
file transaction refuses Cancel, edit, close and competing requests as `BUSY`.
The renderer advances cancellation state only after acceptance; request leases
prevent obsolete success, error and finally handlers from replacing newer UI
state. Pending source edits use the existing status line; rejected edits restore
the last acknowledged text. The ordinary saved preview and byte-checked reopen
remain available after Apply.

Python execution, input/output transfer, hashing/scans and publication run outside
the session lock. The existing owned-child reap and temporary-root cleanup remain
in use. `pin_inputs` through the complete atomic writer are text-identical to the
baseline after line-ending normalization (hash in the receipt): source identity,
Windows dependency pins, reviewed-byte hashing, production revalidation,
containment/no-link checks, no-clobber variants, backup/rollback and reopen checks
are retained.

## Deterministic observations and regressions

Before fixing the state logic, the existing admission and installation blocks
were extracted into the helpers used by the commands. Three safety assertions
failed deterministically: a barrier let invalidation win before reservation yet
the copied review was admitted; accepted cancellation allowed later review
installation; same-revision revocation followed by a failed replacement allowed
older completion to restore authority. All three pass after repair.

These observations establish unsafe admission/review state on the baseline.
**They do not establish observed Windows file corruption:** baseline publication
was deliberately not attempted. Extraction-patch and failure-log hashes are
retained in the receipt; full artifacts remain local.

| Scheduled boundary | Final evidence |
| --- | --- |
| Invalidation wins before Apply reservation | Barrier test rejects; original/destination unchanged; fresh validation can reserve afterward |
| Document replacement, close, switch or cancellation before reservation | Stale authority rejected; no destination in either project |
| Successful result ready, cancellation before installation | Real production installation helper rejects the old owner; no token installed |
| Edit or failed accepted replacement | Attempt/revision barrier rejects old completion; no restored review |
| New request before obsolete completion/cleanup | Old install and guard cannot overwrite new review or clear its busy owner |
| Duplicate Apply / revocation ordering | At most one consumed authorization; actual writer publishes once, or admission rejects without writing |
| Apply reserved before Cancel/edit/close | Explicit `BUSY`; revision unchanged; no claimed cancellation followed by publication |
| Publication stage failures | Consumed review stays unusable; guard releases; fresh validation succeeds |

The matrix exercises submap and item documents through the same helpers as the
commands. Existing independent-document, Windows rollback, external replacement,
path, metadata, source entitlement and no-clobber tests remain. Completion tests
use prepared results at the actual Rust installation boundary; they are not
claims of running Python at that barrier. Active replacement validation is now
excluded by an enforced busy invariant, tested before changing any attempt state.
Cancellation permits a new request; the old owner still cannot complete it.

## Native proof and verification

Preflight ran four isolated startup/restart/project-switch checks and the existing
W4C native route (77.469 s) before the shared-state change. Final verification is
on the runtime source hashes in the receipt:

| Command from `workbench/` | Result |
| --- | --- |
| `npm.cmd test` / `npm.cmd run typecheck` | 32 passed / passed |
| `cargo test --locked --manifest-path src-tauri/Cargo.toml` | 31 passed, including eight W4D regressions |
| `cargo clippy --locked --manifest-path src-tauri/Cargo.toml -- -D warnings` | Passed |
| `worker/runtime/python.exe -X utf8 -B -m unittest discover -s worker -p test_*.py -v` | 38 collected: 37 passed, one embedded-runtime skip; 349.461 s |
| From `worker/`: `G:/GameDev/RoguelikeBaseline-20261020/project/.venv/Scripts/python.exe -X utf8 -B -m unittest test_bridge.BridgeTests.test_dependency_absence_structured -v` | Skipped distinct case passed separately, 0.652 s |
| `npm.cmd run bundle -- -- --locked` | Passed; release executable/resources and 26.25 MiB NSIS installer |
| `npm.cmd run test:submaps` | Passed; 79.814 s; real response gates, parked item, exact variant/reopen |
| `npm.cmd run test:creatures` | Passed; 83.873 s; direct-reference request and five parked drafts |
| `npm.cmd run test:authoring` | Passed; 66.591 s ordinary writer journey, plus 10.411 / 10.144 s interruption/restart checks |
| `WORKBENCH_STARTUP_SMOKE=1 npm.cmd run test:startup` | Four isolated launcher/restart/switch checks passed; 10.260 / 5.827 / 12.046 / 4.968 s |
| `WORKBENCH_TEST_MODE=submap-worker-{cancel,exit,malformed,timeout}`; `npm.cmd run test:desktop` | All passed; timeout observed at 90.325 s; each retained draft validated successfully on retry |
| `worker/runtime/python.exe -B scripts/check-preservation.py`; `git diff --check` | Passed; no game/source/save/plan differences |

The native submap journey holds two real successful host responses in the
test-owned WebView's fetch path. After Cancel, direct host Apply with the old
token rejects, exact source remains, and releasing the obsolete response cannot
restore a verdict or clear the newer preview. This is a renderer completion test,
separate from the Rust pre-install test. No privileged production hook was added.

The same session parks an item draft, moves the creature marker `(7,2)` to `(6,2)`,
checks invalid placement and exact diff, then deliberately publishes and reopens
`w4c_guard_room.json`. Actual G17 construction observes one `Actor` at `(41,20)`,
origin `(35,18)`, HP `14/14`. Saved/reopened SHA-256 is
`7be26e6ff9c4a0f0eaddde6e62664ece450297e2238fc97981f6048b16d93b4b`, matching the
existing retained W4C example. The parked item source remains byte-exact.

Successful native routes use the supported release executable and bundled
Python/bridge offline, with isolated data/settings. Fault controls alone use the
diagnostic executable override. A one-shot marker/file event controls the fault;
the next request forwards to real production validation to prove same-session
recovery. Receipts separately record these diagnostic results and elapsed times.
No desktop mouse/keyboard was controlled and no owner QA was required.

## Preservation and limits

The actual W4C-baseline-to-final tracked diff is Workbench-only: no game source,
active data, game guide, save format, world selection or wiki change. The inherited
preservation manifest is explicitly older (`7745f72ea5446af22d3f340c30043d3752ef0f54`),
not the W4D Git baseline. Its 7,972 source files and seven save files retain bytes
and recorded metadata; personal saves were hashed only, never opened as fixtures.
The approved plan remains untracked with SHA-256
`bcf41ab230fea7aa43a2a2f26b2826bd6d0d53ec814c788903badc642910f49a`.
Per-user project settings still match W4C's recorded SHA-256
`4c8efc27e9b2f11ee6868ca994a76579b7ecb93a84b0f1afbfd4ce72e1101620`.
The desktop shortcut still targets `wscript.exe` and `Launch Workbench.vbs`;
launcher/restart smoke runs select the owner checkout automatically using
isolated settings, without a Python override or `release/deps` executable.

Initial test iterations included an old-canvas startup race in the runner, a
read-only Tauri invoke interception that was replaced with a fetch response gate,
repeated identical CRLF textarea events during pending-edit acknowledgement, and
overlapping build/launch file locks. Those
failed/aborted runs are not passing evidence. Final results follow the corrections.
The final frontend CRLF no-op/pending-edit correction followed the Rust/worker
suites; their source stayed unchanged. TypeScript, typecheck, packaging and every
selected native journey were rerun after that correction. Runtime source hashes
were frozen before those native checks; later changes were evidence only. Test
durations overlap and are not summed as wall time. Installer creation is not
clean-machine installation or signing evidence.

The full-game campaign suite and additional historical editor journeys were not
rerun: game/preview call paths did not change, and the selected native routes cover
the changed host/UI paths. No encounter playtest, simulation, new editor family,
persistent recovery, expanded content capability or later Workbench stage began.
