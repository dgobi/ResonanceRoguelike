# W5B — ordinary found-text authoring

Completed 27 October 2026 in the production checkout on `main`. An eligible
ordinary text can now become a unique variant, be composed with ordered multiline
page controls, previewed by the production reader, validated and deliberately
published through the shared document service, and reopened byte-exactly.
The separate physical-use proof reads that saved variant from an existing letter
through production population, pickup, inventory use and reader input.

## Reconciled prerequisite

Execution began at W5A evidence revision
`0f716fbc7ccfc92ac2c4dd412726a82ede66290e`. The complete issued W5A brief, delivery,
receipt and relevant implementation were reconciled before W5B changes. All 34
final-worktree source hashes in its receipt matched. Item/recipe documents use the
registered collection and shared lifecycle; the `consumed_on_use` descriptor
extension has source-bound automatic ingredient-selection consumer evidence and
a fixed-package native proof. No material W5A acceptance gap was found.

W5A migration: `b43dd4fef1ce8a5e7663b15088c244a6c73d2588`, with corrections
`91abc3f11daf794ac62990ae3e4eb7d4c253c9be`,
`ef9a7b1a0ec506e8bee0e2477cdb98f91f90983b` and
`b85e12514dc2f173cac0fcd2e65de6b3b58fbafa`. Its scalar-extension implementation is
`c4997595b6e3e074a0b3998f902878d9fa085f76`.

The initial live remote readback was the review's W4D revision
`3d4c0cfdde151fa562bbf1dc2e1e9e5cc35b9a97`. W5A was present locally, but had not
been pushed: its receipt explicitly recorded no push authorization in that
session. The owner subsequently authorized commit and push upon completion of
this task. A later pre-publication fetch observed remote `main` already at the
W5A evidence revision, matching the local baseline with no divergence. The W5B
push advances that history normally; no history was reset, rewritten or
force-pushed. The initial and final observations are retained separately.

## Registration and change locality

`engine/text_authoring.py` owns ordinary eligibility, the descriptor, validation,
direct declared references and the production preview adapter. The explicit
`content_authoring` registration supplies the text root and variant-only policy.
The current unchanged corpus contains **89 definitions / 101 pages**: **51**
ordinary candidates and **38** unsupported records. Support follows capability,
not an exemplar ID. Original entitlement and candidate validity are checked
separately. Malformed/ambiguous originals cannot gain permission through repair
of a candidate. Case-folded ID collisions include differently cased filenames
that the production loader still loads.

The shared corrections required by this real family are bounded:

- Descriptor-driven `ordered-records` reuses the recipe row splice/move code.
  Fresh parser locations address each accepted edit; moves retain complete raw
  page objects. Free string suggestions and explicit creation values distinguish
  absent optional keys from displayed defaults. Existing recipe behavior remains.
- Registered preview adapters receive bounded view inputs through the existing
  validation request. A preview revokes older review authority and never installs
  a new review. Frames use the existing bounded JSON channel; there is no new
  worker service, writer, document slot or text-specific IPC command.
- The host-owned root table replaces named item/recipe admission tests and adds
  the text root independently of renderer descriptors. It rejects the mapping
  basename at any depth, including case variants, and retains path/link checks.
- Workspace visibility follows the active registered family. The conservative
  code/data dependency stamp now also covers saved Fonts/UI files. It has not
  been narrowed. `input_stamp` changed; the publication and input-pinning
  functions themselves remain unchanged from the reconciled baseline.
- Inspection retains the measured catalogue hash after a loader error, so an
  unchanged malformed definition presents raw source and actual diagnostics
  rather than a false `SOURCE_CHANGED` failure. The new malformed-source cases
  exposed this shared error path.

The new page control and registered reader view required a normal desktop build.
W5A's unchanged-package scalar extension proof is reused only for its own scope;
it is not claimed for W5B.

## Source, publication and reader behavior

Source remains authoritative. Tests cover no-op bytes, BOM/CRLF handling,
multiline Unicode/quotes/backslashes/blank paragraphs, markers, missing versus
false `trailing`, unknown root/page metadata, complete-object moves, current
locations, add/remove and Undo/Redo. Invalid raw drafts remain repairable with
unsafe structured controls disabled. Empty page lists, wrong field types,
duplicate IDs, reserved mapping targets and malformed contracts fail safely.

Title, condition, ordered page text and optional ending markers are editable.
Condition suggestions are not an enum: shipped fallback values remain valid.
`type`, `reads_as`, `lacunae` and page `damaged` remain visible metadata with no
invented consumer behavior. Teaching, active root/page deep tongue and special
rendering are inspect-only. The reference provider states its limited coverage:
saved explicit item/layout/building `text_id` declarations and direct map entries.

Preview calls `ItemFactory.create → ItemSystem._use_read → TextReader.render`,
with saved fonts, UI art and lexicon, the ordinary letter's weathered-temple
panel and fresh empty language knowledge. Bounded 960×640 PNG frames support
each page and overflow, and carry exact candidate, contract/descriptor,
project/code/data/resources, runtime and page/scroll identities. Edit, dependency,
source, cancellation, view-selection and replacement-request changes invalidate
prior evidence. No personal player, save or world generation is used by preview.

The native text journey publishes only in an ignored disposable fixture:
`roguelike/data/texts/lab/w5b_found_letter.json`. Reviewed, saved and reopened
SHA-256 are all
`5ed718958af32739faf49fe272723ba9e675bf38527a6e693ddcdeb553b17005`.
It also verifies parked item/recipe drafts, cancellation and late completion,
preview without review authority, stale resource evidence, same-ID refusal,
reserved-target refusal, collision failure and one-time review consumption.

Publication creates one new loader-discoverable identity. It does not bind an
object or place anything. Reopened texts support inspection or another variant;
same-ID revision remains deferred because recovery knowledge uses
`(text_id, page_idx, span_idx)`. See [text guidance](../../roguelike/docs/TEXT_AUTHORING.md)
and [content contracts](CONTENT_CONTRACTS.md).

## Physical-use proof and limits

After native publication, the bundled runtime reloads the exact saved parsed
definition with `DataLoader`. A valid fixture-only 11×7 room binds the existing
`letter` at source `(3,3)`, with arrival and return stairs. Production structure
validation, `create_submap`, generation and population construct it;
`populate` still defaults to `map_text=False`.

Normal input walks three turns from generated arrival `(37,23)` to the physical
letter at `(38,21)`, picks it up in one turn, selects it in the actual inventory
and reads it in one turn. The saved title and three pages arrive in order.
All **91 / 4 / 1** visual rows are reachable, with damage/redaction and ending
markers preserved. Reader navigation and closing cost zero turns, retain the
letter, and leave knowledge, RNG and hunger unchanged. The disposable save root
remains empty. This establishes controlled binding/use, not natural acquisition,
world selection, campaign balance or a new gameplay location.

## Verification and preservation

The machine-readable [verification receipt](w5b-verification.json) records final
commands/results, source/package identities, test receipt hashes, measured wall
time, implementation revision and remote readback. Local detailed logs and images
remain under ignored `.artifacts/w5b/` and `.artifacts/desktop-texts/`.

| Final gate | Observed result |
| --- | --- |
| Locked frontend tests / typecheck | 39 tests across 11 files passed; typecheck passed |
| Rust tests / clippy | 34 tests passed, including all eight W4D deterministic cases; clippy passed |
| Full bundled worker suite | 47 collected: 46 passed, one dependency-absence skip; 622.532 seconds |
| Dependency-absence case | Passed separately with the existing development interpreter; no development checkout created |
| Relevant G12 reader regressions | Both passed, including later pages, paragraphs, mixed span identity, long tokens, glyphs and no reader turns |
| Windows bundle | Release executable/resources and NSIS installer built successfully |
| Packaged native workflows | Text, migrated item, migrated recipe and legacy submap workflows passed |
| Supported launcher/startup smoke | Fresh VBS launch, saved-choice restart, project change and changed-project restart passed |
| Preservation / diff checks | No unexpected byte/mtime changes; `git diff --check` passed |

The embedded interpreter explicitly retains site-packages even under `-S`;
its missing-dependency skip is covered by that separate one-case run. All final native
receipts match the final packaged worker hash, with no console errors, external
requests or remaining worker temporary roots. Reader frames and page controls
were also inspected visually. Final text evidence records the revised candidate
whose hash equals the subsequent reviewed/saved/reopened bytes.

The baseline preservation audit compares bytes and mtimes outside the explicitly
scoped existing files. It covers 8,120 unchanged files, all seven personal save
files and unchanged save membership. The untracked owner plan, owner settings,
supported VBS launcher, shipped texts/layouts/maps and wiki are preserved.
Fixture prose and generated outputs stay in tests or ignored artifacts.

No clean-machine installation or historical full-game campaign is claimed.
An intermediate installer build encountered a test-owned executable lock; the
test process exited, packaging was rerun successfully, and final native checks
used that completed package. Only final successful runs are acceptance evidence.

## Revision and timing handoff

Implementation: `89d4fb7cb0675379b2fc3a3a12119933914b348d`. A normal
`git push origin main` succeeded, and `git ls-remote origin refs/heads/main`
returned that exact revision. The separate following evidence commit contains
this delivery and the receipt; it is named by
`checkpoint/workbench-w5b-verified-20261027-a`, with its exact SHA and final remote
readback in the execution handoff. The start checkpoint is
`checkpoint/workbench-w5b-start-20261027-a` at the W5A evidence baseline.

Measured wall time was **2,968.873 seconds (49 minutes 29 seconds)**, from
`2026-10-27T19:47:24Z` baseline capture through `2026-10-27T20:36:53.220583Z`
receipt generation and implementation push. Earlier preflight and the subsequent
documentation commit/final push are outside that measured interval. Individual
test durations overlap and are not summed into wall time.
