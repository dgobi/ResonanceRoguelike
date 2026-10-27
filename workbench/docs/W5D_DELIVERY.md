# W5D — durable drafts and reliable save recovery

Completed in the production checkout on `main`. Registered item, recipe and
found-text drafts now survive deliberate close, cold native restart and the tested
abrupt-exit boundaries. Exact accepted text and target intent are auxiliary copies;
recovery grants no review, validation or publication authority.

## Revisions and publication

- Reviewed local and initial remote: `4936bfbe2ee2f5d3081553cdf772087caf4eca32`.
- Separate reopen repair: `21f3abdcc004d8cf88b292f3914ecc7ed58a140d`.
- Recovery implementation: `f45bc32b8222c6aa73cc1136114e9c43b4e3078d`.
- Final runtime/test extraction: `a29227c7999476c4f5a8bce571b56cd28c511f52`
  (includes `32e44d7`, resolved-error/async-close followup).
- Final native test inputs: `b7e3a63ebb5b5547519372dc38737f34a83102bb`; its only additional change
  is the separate-process lock assertion. Packaged runtime bytes are unchanged.
- Evidence: annotated `checkpoint/workbench-w5d-verified-20261027-a`, which records
  the exact evidence commit and final remote `main` readback after normal push.

Named start, repair, implementation and input checkpoints were created without
branches, worktrees, history rewriting or additional development checkouts. All
53 W5C receipt-listed Git source hashes reconciled. The owner explicitly authorized
committing and pushing implementation **and** evidence; the final handoff supplies
the exact remote SHA. The receipt binds both Git and actual tested worktree bytes.

## Behavior and safety boundaries

Publication candidate/target and current draft remain separate. Accepted raw,
structured or target changes after a write cause Retry to refuse replacement,
leaving the newer work intact. Coverage is checked before the read, after the
read and through final asynchronous acknowledgement/installation. A host-owned
completed-write handoff can reacquire its unchanged successor after a lost
successful response. It verifies target bytes, refuses another owner/newer draft,
never validates an obsolete token and never repeats apply.

Per-user Tauri application-local storage contains bounded version-1 file records:
canonical project/source identity, historical family/contract, original exact
baseline/hash, accepted exact text/variant intent, monotonic generation and an
optional completed-publication fact. Live document/review tokens, permissions,
diagnostics, preview frames and complete host documents are absent. Diagnostic
config/recovery roots isolate every automated run. `project.json` stays a preference.

Accepted edit commands retain host sequencing and BUSY refusal. A non-resetting
500 ms timer coalesces checkpoints without semantic validation or dependency scans.
Each record uses a flushed temporary file and atomic replacement. Process locks
isolate active record writers and retirement rights. Failed writes preserve the
previous complete record and current memory; failed keep/close flushes leave the
owner open. Explicit discard or exact covered publication/reopen retires only
that record, with delayed commands unable to recreate its retired generation.

Recover drafts remains reachable without worker/contract success, including when
a stored source/project is unavailable. Text is inspectable/copyable, with baseline
and current-disk comparison. Editing requires normal discovery and current
eligibility on the matching source file. Changed/missing/unsupported sources are
retained rather than merged or rebound by runtime ID. An open owner is focused
and preserved. Restored drafts have empty history and require fresh validation.

Publication facts remain distinct from newer accepted work. A crash after the
actual writer but before recording its fact retains the prior draft; an identical
intended target can be reconciled deliberately as read evidence. A different
target remains a conflict. Newer recovery generations cannot be retired by an
older successful write. Item edit policy and recipe/text variant-only policy remain.

Legacy structure/pool/creature drafts remain memory-only and retain deliberate
close protection. Project/application keep requires resolving those drafts first.
Host close also flushes accepted registered records. Clean-tab/session layout,
full history, unsaved dependencies, general merging and Save All are excluded.

## Newly observed verification

| Gate | Result |
|---|---|
| Locked frontend / TypeScript | 52 tests in 14 files; typecheck passed |
| Locked Rust / clippy | 49 tests; all eight W4D cases retained; warnings denied |
| Complete bundled worker suite | 47 passed; one expected dependency-absence skip; 753.446 s |
| Separate missing-dependency control | 1 passed using the existing development interpreter |
| Normal locked package | Release executable, pinned runtime/resources and NSIS installer built |
| Packaged recovery journey | Passed across 5 native processes, including cold and abrupt restart |
| Packaged workspace journey | Six owners, legacy preservation and lost successful reopen response passed |
| Startup/restart | Four isolated launcher/project-switch scenarios passed |

The recovery journey keeps two text drafts and one item draft with independent
targets, including invalid JSON, Unicode, escaping and accepted CRLF/BOM policy.
It checks rejected optimistic text, failed checkpoint/close flush and retry,
legacy close refusal, fresh tokens/validation, raw/structured post-save edits,
refused obsolete-owner edits, cold saved-file reconciliation, precise retirement,
abrupt termination of only its owned process, and inspection/comparison/discard
with a failed worker handshake. A second native process using the actual writer
cannot overwrite the application's locked record. Deterministic tests additionally
cover reordered generations, malformed neighbors, supported/unsupported changed
contracts, changed/missing source, project isolation, pre-fact publication,
termination at replacement, and actual Windows sharing-lock failure.

The final item candidate, disk and reconciled reopen hashes all equal:

`f5e7033507ca144a742ec6bca19df1512c0b1e3b0808712c80a01b4513d919ba`

The separately abrupt-exited invalid text checkpoint and its restarted record
both hash to `7e43faa08f26df2c7493c7bf5fc564b0f3004dbf1fd924e9a2c2c543cd6f59d6` (generation 4).
All captured/restored hashes and generations are in the compact receipt.

Observed host checkpoint calls: 15; min/median/max
0.275/0.454/3.567 ms. The configured crash
window is 500 ms after the first accepted pending edit **plus scheduling and write
time**. Pending/unacknowledged edits are not durable. The receipt also retains
acceptance-to-completion timings, alongside explicit flush costs and injected
failure/retry. Native gates overlapped; these are not unloaded performance promises.
The existing shared freshness sweep remains bounded with one in-flight scan.

Both baseline reopen regressions failed before repair as expected. Their runs used
the pre-existing W5C package without a new executable hash capture. Final native
runs hash the actual executable. Pre-final harness corrections (item action label,
close IPC loss and awaiting async owner removal) and resolved-error cleanup are
recorded rather than treated as passing verification.

## Preservation, reproducibility and limits

The audit found **8145 outside-scope baseline files unchanged in bytes and
mtime**, including all 7 personal-save files with unchanged membership. The owner
plan stays untracked and unchanged. Owner settings and launcher hashes match W5C.
Shipped catalogue, fonts/UI, gameplay and wiki remain unchanged. Source comparison
finds the publication writer, input pinning, dependency stamp, destination policy,
validation command and apply admission unchanged from W5C.

Run the commands in [w5d-verification.json](w5d-verification.json) from `workbench/`
unless its row gives another cwd. Tests and native journeys are committed;
generated fixture projects, recovery stores, logs and screenshots are ignored
local artifacts. Artifact hashes identify those local files, not independent
remote inspection. The report does not claim a clean-machine installation.
W5C's unchanged production-reader/long-heading and W5B physical-letter evidence
are reused; no new campaign, placement journey or font matrix was commissioned.

The owner guide is [Workbench recovery](../README.md#recover-unfinished-item-recipe-and-text-drafts).
**W5E — Game typography profiles** is the retained next bounded requirement after
W5D review. No typography implementation, general settings editor, new family,
wiki rebuild or reference-pack maintenance was included.
