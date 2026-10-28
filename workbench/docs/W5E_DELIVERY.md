# W5E — game typography profiles

Workbench now edits the thirteen existing proportional game-font roles through
the singleton `roguelike/data/display/typography.json`. The shipped assignments,
nominal sizes and callout aliases preserve the previous appearance. A fresh game
initialization reads the saved profile. The three recovery repairs preceded the
typography implementation in their own commit.

## Revisions and publication

| Boundary | Revision |
|---|---|
| Reviewed checkout and initial remote | `7b737f85f23c3538192a66f334dfe9a7f82c607a` |
| Separate recovery correction | `4520f22018ad06253e92b406c3eb4bc73c3ba286` |
| Typography implementation and guides | `714000daa408769697c3af32999f7a9732f9255c` |
| Final packaged frontend/host inputs | `f283647b2657f457f13abfeb176ed734185ea651` |
| Final game resolver and regression inputs | `cd8a8d7193d89e8d42bedd9ef8d61439c42fdb02` |
| Evidence and exact remote readback | Annotated `checkpoint/workbench-w5e-verified-20261027-a` and final handoff |

All 61 W5D receipt-listed Git source hashes reconciled. Work stayed on production
`main`, with named start, recovery, implementation and test-input checkpoints.
There were no additional development checkouts, branches or history rewrites.
The invoked brief explicitly authorizes the normal push of implementation and
evidence. The final evidence commit cannot embed its own hash; the verified
checkpoint and external handoff identify it and the remote readback.

## Recovery and authority

The actual RecoveryPanel handlers bind inspection to selected key, generation,
request and current list. Deferred A/B responses, closing/reopening, old refreshes
and late results after actions cannot change the verified action target. Discard
confirmation names the project, source and generation. Actions stay unavailable
without a matching inspection.

Restore and reconciliation claim first, then read and check generation while
holding the claim. Deleted or advanced records fail instead of being recreated.
Failed requests release only claims they newly acquired, including checkpoint
failure. Reconciliation refuses any live source owner, including source A after
a successful variant write to B and failed reopen. Tests establish that its next
accepted draft still checkpoints. Deliberate reconciliation of an identical
intended target without a persisted publication fact remains available and never
repeats publication.

Python discovery, independent Rust admission and recovery envelopes authorize
only the canonical typography path and edit operation. Forged variants, alternate
targets and changed identity/version fail. The ordinary shared editor retains
Source, local field edits, metadata, undo/redo, references, diagnostics, validation,
one-time review and verified reopen. No family-specific document slot or settings
writer was added. Existing variant-only families retain semantic inspection of
their source without gaining same-source publication authority.

## Production rendering and resource behavior

Startup and authoring use the same production resolver. It resolves all thirteen
fonts before installation, using bounded regular TTF bytes directly inside the
selected project's Fonts directory. Linked/reparse paths, traversal, missing,
corrupt and oversized resources fail. Trusted resource roots are passed explicitly
through staged validation. No system font substitution or font-file writes occur.

An absent profile uses all defaults without creating it. A malformed, unsupported
or unusable saved profile warns and falls back to the complete known-default map;
unavailable defaults fail clearly. Candidate preview is strict and cannot present
fallback output as the requested candidate. Structurally supported profiles with
invalid font references remain correctable; malformed/unsupported sources remain
inspect-only. Saved changes apply at the next initialization because consumers
cache fonts and metrics.

Printable ASCII and documented functional symbols are checked using Pygame
FreeType coverage while rendering remains through `pygame.font`. Packaged Windows
negative controls confirm missing `↑` in IM Fell Regular and `≥` in Junicode Bold:
FreeType reports absence, while SDL metrics are non-null and rendered pixels equal
the missing-character sentinel. Defaults' checkmark, sprint pips and decorative
storm gaps remain warnings. The reader's optional corruption alphabet now excludes
missing glyphs for the selected prose face, retaining its ASCII fallback and
existing page/span, knowledge and turn semantics.

A meaningful native failure was found and retained: corrupt bytes could crash the
FreeType constructor, and the packaged `pygame.font` constructor could return an
unusable handle without raising. The resolver now checks `font.size("A")` before
coverage probing; this safely reports the SDL error. Final packaged tests cover
both candidate rejection and whole-default startup fallback for corrupt bytes.

The typed `typography-preview` contains a **960×960** all-role specimen and a
**960×640** production reader frame with ordinary prose and known Deep Tongue.
It records requested/resolved resources, exact font hashes, nominal sizes, measured
sample dimensions, diagnostics, candidate/source/contract/runtime evidence and
fallback status. The reader enters through actual item creation/use and
`TextReader.render`. Other previews continue using saved typography. External
profile/font changes revoke preview/review evidence through the existing bounded
sweep while preserving accepted drafts.

## Observed verification

| Gate | Result |
|---|---|
| Locked frontend and TypeScript | 57 tests in 16 files; typecheck passed |
| Locked Rust and clippy | 54 tests, including all eight W4D cases; warnings denied |
| Complete bundled worker suite | 54 passed, one expected dependency-absence skip; 490.336 s |
| Separate missing-dependency control | 1 passed using an existing development interpreter |
| Packaged typography tests | 7 passed, including 42 reader layouts and actual HUD/menu/callout consumers |
| Existing production-reader regressions | 3 passed: long headings/tokens, language spans and no-turn navigation |
| Locked package | Release executable, pinned Python payload and NSIS installer built |
| Typography native journey | 3 real app processes, separate fresh production initialization and fallback |
| Existing native gates | Recovery across 5 processes; six-document workspace/lost reopen; found-text authoring and physical use; 4 startup/restart scenarios |

The typography journey independently selects **IM Fell English Regular** for
headings, **IM Fell English Italic** for prose and **Foulis Greek** for damage.
Other assignments and deliberately formatted metadata remain byte-exact.
Undo/redo, Source, real preview and host rejection of forged variant intent pass.
Selected font-byte changes invalidate the displayed preview and consume a real
review without writing content; fresh validation restores publication authority.
External profile changes retain the draft and show conflict state.

Accepted selections survive restart at generation **5** with SHA256
`a663f4f90e723f23740991afe87380dfcfad86628ac790a292225de0e32bb5be`.
An exact BOM/CRLF/Unicode invalid JSON draft survives the next restart at generation
**6**, hash `cb55e284c9da22e24ba5d72e5608532668478925eedf5bdf6977e39cf4032cf6`.
Both restores require fresh review. The eventual reviewed, saved and reopened
profile all match the first hash; another document's recovery remains unchanged.
A new packaged-Python process initializes production DisplayConfig, reader, HUD,
perk menu and callout consumers with the published map. An invalid present profile
then produces complete-default fallback without rewriting its bytes.

The 42 reader fixtures span all seven faces, 960×640/480×320 and title lengths
20/512/2048. They accumulate `_visible_rows` across scroll steps and check clipping, scrolling, surface
heights and footer separation. Bounded HUD/message-log, perk-list and all callout
role/alias fixtures exercise actual consumers. These are isolated production
rendering fixtures, not a full campaign or every-screen layout certification.

## Provenance, preservation and limits

[w5e-verification.json](w5e-verification.json) records exact commands, source Git
and tested-worktree hashes, font/profile hashes, package identities, native evidence
and artifact hashes. Frontend/host/package gates used `f283647`; the only later
implementation change is game-side corrupt-font handling. The receipt verifies
unchanged packaged inputs and binds the final native fixture's resolver bytes to
`cd8a8d7`. Final worker, packaged typography, native typography and existing-reader
checks cover that resolver. Earlier existing-family native fixtures use the prior
loader with valid fonts; their evidence is identified as such. Preliminary selector,
BUSY-timing and corrupt-font failures are corrections, not passing gate results.

All **8146** outside-scope baseline files retain their bytes and mtimes, including
all **7** personal-save files with unchanged membership. Owner plan, launcher and
settings hashes match prior evidence; the owner plan remains untracked. Existing
content, font assets and wiki edition are preserved. The receipt also confirms
unchanged input pinning, dependency stamp, validation and apply-admission functions.

Native logs, screenshots and disposable projects are ignored local artifacts;
committed hashes identify them rather than claiming independent remote inspection.
The installer input contains 1809 unchanged pinned runtime files. Diagnostic runs
added Python bytecode caches beside the unpacked release runtime; the receipt
distinguishes those observations from the shipped payload. No clean-machine install
is claimed. Recovery still promises completed accepted checkpoints, not pending
edits or full session/history restoration. No universal Unicode guarantee, font
imports, size sliders, live replacement, bitmap/procedural glyph redesign, save
migration, wiki rebuild or reference-pack maintenance is included.

Owner guidance: [choose game typography](../README.md#choose-game-typography) and
[authoritative roles and glyph limits](../../roguelike/docs/RENDERING.md#proportional-game-typography).
