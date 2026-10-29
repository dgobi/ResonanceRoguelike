# W5O — reusable contextual container loot

Native contextual pools now use the registered shared workspace. An owner can
edit and compare independent pools, save a useful item, link saved pools to a
real room container, acquire/use its actual contents, retain partially looted
state across cold load, and revise/reset/test latest without rerolling generated
containers. No canonical reward pack or world assignment was installed.

## Revisions and preservation

| Boundary | Identity |
| --- | --- |
| Starting local and remote `main` | `07dffb08dc857518edc6883b11f6ab67b2c2a738` |
| Start checkpoint | `checkpoint/workbench-w5o-start-20261029` |
| Application/game implementation and package inputs | `30dac9298c402c1ff4c919312a6f6d97de8d758e` |
| Package-input checkpoint | `checkpoint/workbench-w5o-package-inputs-20261029` |
| Connected journey and initial retained evidence | `88e7602a52bbad8d6a0144ed9112139680d38dcd` |
| Completed delivery | `checkpoint/workbench-w5o-verified-20261029` |

The [verification receipt](w5o-verification.json) binds working and Git-normalized
committed bytes, 77 package inputs, runtime/package identities, accepted fixtures,
captures, commands and failed-attempt distinctions. Application inputs precede
later harness/evidence commits. A commit cannot contain its own SHA; resolve the
final named ref. The final handoff and ignored `remote-readback.json` report the
full exact local/remote `main` equality after the commissioned push.

Work stayed in production `main`, with no branch, worktree or development copy.
Only positively owned disposable runtime/content/settings/save fixtures were
created. Preservation covers 8,400 pre-existing files, including the untracked
owner plan; 8,370 unchanged pre-existing files remain byte-identical.
The untracked owner plan, live content, campaigns, settings, fonts, launcher,
historical fixtures, wiki edition and reference pack were not changed. The
receipt discloses the early test-constructor metadata-isolation omission below.

## Contract and migration

`pool` / `contextual-loot-1` retains native JSON and `contextual_loot_pool`.
The [executable inventory](evidence/w5o/pool-inventory.json) admits all seventeen
current immediate object sources, with 1–8 rows each. These are observations,
not an ID whitelist. Same-ID edits retain exact source identity/path. A variant
requires a distinct safe case-insensitively unique ID matching a new filename
beside its source and changes no container reference.

The pool singleton and alternate save/validation lifecycle are removed. A thin
navigation dispatch and read-only `pool_context` compatibility alias use the
same registered owner/context. Two pools and an unrelated document can remain
dirty together. Existing host confinement, original-source checks, shared
revision/attempt invalidation, cancellation, one-use review, final freshness,
rollback and byte-checked reopen apply. Ordinary buildings keep their existing
document lifecycle; their saved dependency/catalogue refresh remains usable.

Description, omitted/fixed/range counts and ordered rows have structured controls.
Add/remove/up/down moves complete source row spans. Table, Source and properties
share pool undo/redo. Recovery retains invalid text and target/operation intent,
never old review authority. An admitted invalid value remains repairable;
unsupported original nested/array sources stay inspect-only even after candidate
shape changes. Larger sources may be reduced deliberately to the 64-row
Workbench publication bound. Otherwise valid larger saved dependencies retain
native consumption without that authoring bound.

Exact-source operations preserve untouched metadata, order, escaping, key
presence, whitespace and line endings. Source may deliberately change inactive
metadata; warnings retain W3A's lack-of-gameplay-effect distinction. BOM bytes
remain inspectable/recoverable but cannot publish when the loader skips them.
See the complete [authoritative pool guide](../../roguelike/docs/POOL_AUTHORING.md)
for defaults, numeric rules, source policy and activation boundaries.

The three inherited gaps are repaired:

* The actual roller skips zero-weight rows at random zero, cumulative boundaries
  and rounded fallback. Requested-count draws, row order, without-replacement
  sampling, repeated IDs/pool occurrences and caller RNG streams are retained.
  All [1,700 frozen shipped-pool outputs](evidence/w5o/seeded-before.json) match
  before/after. Only focused arithmetic-edge tests control RNG.
* Every saved item reference, including zero-weight rows and reference-only held
  lights, uses the actual factory, exact `Item`/ID and existing `ITEM_STATE`
  persistence validation. Invalid construction blocks review. A selected factory
  failure aborts staged container construction before ownership publication.
* Original/target pool and item identities resolve all case-insensitive source
  locations, including array pointers. Missing, duplicated, case-aliased,
  loader-skipped and staged/loaded mismatches block publication.

Pool weights follow the finite nonnegative native contract; safe-integer bounds
apply to requested counts. Nonempty total must remain finite and positive even
for zero requests. Unknown quantity/condition/text fields gain no semantics.
There is no second item schema or TypeScript/Rust sampler. Pool authoring can
retain the real loader's earlier pool/item snapshot when a referencing building's
later catalogue compilation fails, allowing repair without weakening gameplay
startup or candidate validation.

Saved room and building consumers repeat source/physical dependency checks,
including ordinary weighted container alternatives. The usage list remains
explicitly partial: direct supported room and ordinary-building containers with
exact file/field/occurrence locations. [Fresh saved-source usage evidence](evidence/w5o/declared-usages.json)
includes both routes; an empty list proves neither unused nor unreachable.

## Packaged connected journey

The [observations](evidence/w5o/observations.json), reviewed diffs and five exact
fixtures establish the journey in the locked Windows executable and pinned
runtime. Controls publish `w5o_biscuit`, `w5o_provisions` and `w5o_lights`.
The first pool uses fixed `[3]`, two distinct biscuit entries and a wood bundle;
one weight is deliberately omitted and another is 7. The second has an omitted
count/weight and one saved reference-only torch. Source/table history, row
addition/edit/reorder/removal, omitted defaults and nested escaped metadata are
exercised. Two pool drafts plus malformed unrelated text survive a real host
restart; an invalid unfinished variant has no recovered review authority.

The existing ordinary-building → pool → item return preserves its building draft.
Room → pool → item → row/container return also passes, and a changed recorded
pool location is explicitly stale. Real external conflict preserves competing
bytes; a saved dependency change revokes the pool review before fresh validation.
Parked item/pool/text drafts never overlay another verdict or capture.

Source supplies only disclosed 19×11 room geometry, arrival and return. Room
controls place one crate at source `(5,6)` and deliberately link ordered pools
`[w5o_provisions,w5o_lights]`. Exact accepted records and actual four-item
production contents are asserted before game launch. Production origin is
`(31,16)`, arrival `(34,24)`, crate `(36,22)` and return `(33,24)`; scene/context
inputs and source/contract/dependency hashes are retained, not inferred from the
pool ID alone.

Ordinary movement/interaction and container selection transfer the exact rolled
biscuit instance. Inventory Enter consumes it and improves hunger at normal cost.
A second exact biscuit remains owned; distinguishable wood and torch remain in
the open partially looted crate. Normal save, stairs away/return and a genuinely
separate pinned `--load` process retain inventory/copied fields, residual contents,
open state and absent consumed/taken rewards. Reopening does not reroll.
No inventory/object replacement, needs/health fixture or RNG override is used;
the normal player profile, starter supplies, needs, AI and FOV remain.

Workbench then revises the same pool ID to one bone at fixed `[1]`. Reset retains
the original immutable manifest and four original contents. Latest saved uses a
different capture with the revised pool and yields bone plus torch. This is a
small retest rather than another equipment/preparation expedition.

## Ordinary save with a fresh catalogue

Before the UI revision, a separate headless production fixture stages two known
room identities and a foyer with the shared six-item starting loadout in an
explicit disposable ordinary save root. Normal
movement, container input, exact transfers and inventory use consume one biscuit,
retain the other, and leave wood/torch in the generated room. The recorded second
room is pending and has no cache. This is distinct from frozen Test room restore;
no natural-world discovery or overland itinerary is claimed.

After the actual UI revision, a different process/catalogue loads that ordinary
save. Every supported physical field, residual content/state and acquired
inventory ownership matches. Consumed/taken contents remain absent through
reopening/revisit. First construction of the recorded pending room consumes the
revised saved pool and produces distinct bone/torch objects. Existing refusal to
regenerate a missing owned cache is covered by the unchanged ownership/cold-map regressions. Process
memory IDs are explicitly separate from serialized identity/ownership comparisons.
No save schema, visited regeneration, offscreen or assignment policy changes.

## Verification and limits

[Gates](evidence/w5o/gates.json) bind Windows commands/environments/log hashes:
79 frontend tests, TypeScript, 69 Rust tests, clippy with warnings denied,
334 broad game regressions with stable source hashes, the final three focused
consumer cases, 102 worker cases (one expected embedded-runtime skip), a separate
missing-dependency control, locked executable/NSIS, connected loot journey,
adapted legacy pool/item journeys, shared workspace lifecycle, room-session
capture/cancellation/reset/cold/fault lifecycle and ordinary 128×128 main/default
save-load. Pinned CPython is 3.11.0 with the repository's exact dependency versions;
Node is 24.15.0. Working and Git-normalized bytes have separate identities.

The final three consumer cases add explicit temporary save-root injection before
Engine construction and assert no cached baseline. This harness-only correction
followed the broad run and retained every gameplay assertion; the original fixture
could probe default constructor save metadata but invoked no save/load. Broad
application/game results and the final isolated focused rerun are bound separately.

[Excluded attempts](evidence/w5o/attempts.json) distinguish fixed implementation
issues (unfinished recovery intent and receipt/control overlap) from harness
corrections: actual production centering, invalid-variant host refusal, main key
dispatch, closing both container prompt/cursor, intended worker cwd, UTF-8 output,
explicit BUSY retries, transient memory IDs, updated W5M read-only expectations
and an overlapping fixed debugger port. Failed attempts are not relabeled as
success; only final passing runs certify completion.

This is controlled authored-room evidence, not survival balance, natural
discovery, every special item behavior or a whole-game usage graph. Definition
validation, unowned factory evidence, production preview, native use, immutable
reset and ordinary fresh-catalogue activation remain distinct. No canonical
pack, starter redistribution, new loot semantics, surface-editor migration,
global transaction framework, save migration, wiki or reference-pack work.
