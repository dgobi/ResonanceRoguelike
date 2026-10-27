# W5C — independent content documents

Completed in the existing production checkout on `main`. Two items, two immediate
recipes and two ordinary texts can stay open with independent exact drafts,
variant targets, structured history and useful view state. Catalogue/reference
opens reuse the existing file owner. Publication, close and reload target their
originating document; other drafts remain intact.

## Revisions and publication

- Start/local and initial live remote: `4bc0aece1871881db0412af5f256aa58571d8aca`.
- Reference/layout repair: `3a5cec23a6b022f849ca3d8efa67a1b75cd525f6`.
- Rendered footer-width followup: `ad4f6ce7cb822b46f6d4c8383c1399391ac9a3d3`.
- Malformed-map compatibility followup: `04d9424daec5cd4e0c7ede661eb25bb29c660e9b`.
- Workspace implementation: `fa066d974c93a9e36f02ef82828fc7da4dba5fcf`.
- Evidence: annotated checkpoint `checkpoint/workbench-w5c-verified-20261027-a`.

Named start and repair checkpoints precede the ownership migration commit.
All 34 W5A and 38 W5B source hashes reconciled with their recorded revisions,
including Windows line-ending differences. No prerequisite gap remained.
The owner explicitly authorized commit and push. Implementation and evidence are
published together by normal push. The annotated verified checkpoint records the
exact evidence commit and final remote `main` readback after that push; the final
handoff supplies that hash too. No force push,
new branch, development checkout or worktree was used.

## Owner workflow and boundaries

Tabs show IDs, paths and dirty dots. Switching retains invalid Source bytes,
variant inputs, structured Undo/Redo, selected text page/reader frame and pane
scroll. Close/Reload name only the affected file and offer Keep Editing or explicit
discard. Project/application close accounts for dirty legacy drafts too. A refused
project connection restores the old host connection and its document owners.

References retain the actual origin token and relation focus. Both recipes can
visit the same item draft and return correctly. Deliberately closed or replaced
origins are reported unavailable. A successful save replaces only its source tab
after a hash-verified reopen. An already-owned target is refused. If writing
succeeds but reopen fails, the exact draft and save receipt remain; Retry verified
reopen reads again without republishing, and clears the obsolete error on success.

Ownership is canonical project session plus host-established file identity,
including supported Windows case/slash aliases. Opaque instance tokens remain
separate from definition IDs. Legacy structure/pool/creature paths remain active.
One workspace sweep shares the conservative code/data/Fonts/UI stamp, checks
individual files and installs only matching epoch/token/revision/attempt results.
There is one in-flight sweep and no scan queue. Conflicting UI actions briefly
disable during a scan; final publication checks remain independent. Source
comparison confirms `publish`, `pin_inputs` and `input_stamp` are unchanged from
W5B. The eight W4D cases exercise the migrated collection and shared helpers.

Drafts remain memory-only. References, validation and previews use saved
dependencies, not other unsaved tabs. Raw and variant-ID edits retain the existing
limitation of clearing that document's structured history. No Save All, recovery
store, new family, teaching semantics, wiki or reference-pack work was added.

## Review corrections

Text mapping references match text-ID keys only. Same-spelling carrier-only
values are absent; genuine keys and explicit `text_id` declarations remain.
Malformed mapping lists still fail closed.

The pre-existing long-heading reader defect is fixed in production layout.
Oversized headings scroll with the full body through existing controls; short
headings remain fixed when usable body space permits. Frame width includes title
and footer needs. Tests use the actual factory, inventory read path, renderer and
engine reader keys with shipped fonts/UI: title lengths 20, 400, 512, 1024 and 2048
at both 960×640 and 480×320. They assert effective clipping, complete readable
body rows/pixels, heading/body reachability and separated footer, alongside
unchanged item retention, knowledge, RNG, hunger and navigation time. The two
existing short-title/long-body regressions also pass.

## Observed verification

| Gate | Result |
|---|---|
| Frontend / TypeScript | 46 tests across 12 files; typecheck passed |
| Locked Rust / clippy | 39 tests including all eight W4D cases; warnings denied |
| Complete bundled worker suite | 47 passed, one expected dependency-absence skip; 761.098 s |
| Separate dependency-absence control | Passed with existing development Python 3.11.0 |
| Final affected checks | Five text tests, final mapping regression and three actual reader tests passed |
| Normal locked package | Release executable, bundled pinned Python/resources and NSIS installer built |
| Final packaged journeys | Workspace, submap, item, recipe, pool and creature passed |
| Startup/restart | Four supported-launcher/isolated-settings scenarios passed |

The complete worker run preceded the final footer-width and malformed-map
followups; the final affected checks cover those corrections. All listed final
native journeys use the final package. Full-suite time, individual gate times
and elapsed implementation time are separate measurements, not summed.

The six-document journey uses disposable runtime data. The shipped corpus has
only one writable immediate recipe, so a second legitimate recipe source is
created only in that fixture. It verifies exact invalid draft parking, independent
history/targets, both return origins, aliases, close/reload, old-token rejection,
an external file conflict and byte-exact preservation of a legacy structure draft.
It publishes one text while another tab is selected, injects one verified-reopen
transport failure after the real write, rejects review reuse and recovers by read
only. Reviewed, saved and reopened SHA-256 all equal:

`68a52c4b10cd5c93fb99ae7a1a451fadd7dd214d2a153c32145d38ff0245365b`

Idle measurements on this machine:

| Open registered documents | Observation | Sweeps | Host time per sweep | Dependency scans | Max concurrent |
|---|---|---|---|---|---|
| 1 | 6.811 s | 2 | 34.04–34.77 ms | 1 each | 1 |
| 6 | 6.806 s | 2 | 34.98–35.17 ms | 1 each | 1 |

Deterministic tests reject overlap, queued scans and stale deliveries. A held real
native sweep confirms UI action gating until its response is released. These are
bounded-work observations, not a universal latency promise.

Visual checks covered the actual reader frames and six-document shell at full
and minimum window sizes. Development checks caught a clipped footer hint, pane
scroll capture after browser clamping, a scan/validation BUSY race and an obsolete
reopen error message; the corrected behavior was rerun. Harness changes account
for mounted hidden editors and closed details without relaxing their assertions.

W5B's unchanged physical construction/binding/pickup proof is explicitly reused.
W5C independently reran actual reader rendering/input; it does not claim another
placement campaign, clean-machine installation, natural-selection or balance test.

## Preservation and evidence

The final audit found 8126 baseline files
outside scope unchanged in bytes and modification time, including all
7 personal-save files with unchanged membership. Shipped
data, fonts/UI, launcher, wiki, owner plan and owner settings were preserved.
The pre-existing owner plan remains untracked. Generated prose, fixtures,
screenshots and logs remain ignored local artifacts.

The compact [verification receipt](w5c-verification.json) binds source hashes
(both Git and tested worktree bytes), package/runtime/installer identities,
commands, native hashes, monitoring, preservation and local artifact hashes.
The measured implementation/source interval was
45.21 minutes from baseline capture
through the final source/harness edit; it includes overlapping gates. The receipt
separately records the subsequent verification/evidence interval. Documentation
commit/push time after receipt generation is outside those measurements.

Local image/log hashes establish identity, not independent remote visual review.
Reproduction commands and bounded test fixtures are committed; no evidence archive
or new documentation framework was added.
