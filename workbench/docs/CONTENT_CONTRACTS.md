# Registered content authoring

`roguelike/engine/content_authoring.py:families` is the explicit first-party
registration point. `item_authoring.py`, `recipe_authoring.py`, `text_authoring.py`,
`typography_authoring.py`, `creature_authoring.py` and `room_authoring.py`
adapters own discovery identity, supported source shape, ordinary field metadata,
reference providers, semantic validation and construction/execution evidence.
Gameplay does not import these authoring modules. There are no descriptor-driven
imports, executable expressions, plugin loading or alternate content formats.

The worker dispatches discovery, inspect and exact-draft validation through the
registry. A common `family` envelope contains family/contract identity, descriptor
SHA-256, compatibility diagnostics, reference choices and typed family evidence.
The host stores registered documents by discovered file identity within the
canonical project root. Windows case and slash aliases resolve to the same owner;
definition IDs and record pointers are metadata, not ownership keys. Each open
instance has an opaque token. React keeps one `Authoring` lifecycle mounted per
token, including hidden specialist views, so switching tabs retains exact source,
history, variant inputs and view state. Legacy structure/pool slots
remain included in shared lookup, invalidation and project close.

`open_document` reuses an existing file owner. Explicit reload or verified reopen
passes `replaceToken`; publication reopen also passes `expectedSha256`. The host
checks the originating revision/attempt and target bytes before replacing the
token. Failure preserves the original instance. A target owned by another open
document is refused. `close_document` removes only its registered token; late
results cannot install into a closed or replacement instance. Reserved publication
still refuses close/cancellation with BUSY. Reference return state names an actual
origin token and retains its relation focus; closed/replaced origins are explicit.

One `workspace_disk` sweep covers live registered and legacy documents. It reserves
the existing operation slot, hashes conservative dependencies once, and reads
individual files. It never overlaps or queues another sweep. Host installation
checks epoch/token/revision/attempt; renderer delivery checks the captured local
version and subscription lifetime. Per-document timers are removed. Final apply
still independently pins and rechecks exact source/dependency bytes. Monitoring
does not narrow dependencies, cache stamps across sweeps, or create review authority.

## Descriptor vocabulary

The declared dialect is JSON Schema **2020-12**, with a deliberately small
`resonance-controls-1` subset. This is a control description, not a complete
JSON Schema validator. Unsupported keywords or controls produce capability
diagnostics and deny authoring; they are not silently treated as implemented.

Supported annotations are `type`, `properties`, `required`, `items`,
`additionalProperties`, `title`, `description`, `default`, `readOnly`, `minimum`
and `maximum`. Root objects describe ordinary strings, multiline descriptions,
finite numbers, exact integers and booleans. Arrays are registered ordered tables
with object rows and scalar cells. Arbitrary nested-object forms, schema unions,
conditionals, `$ref` resolution and general recursive schemas are unsupported.
Unknown JSON metadata is preserved by the source editor, independently of the
descriptor's enumerated authoring controls.

Descriptors now declare `production_route` explicitly. Registration chooses that
route; it is not inferred from the family name. Every inspected family supplies
an effective operation subset, narrowed by its original source capability. The
host freezes that subset and compares it with fresh original-source policy at
validation/apply. Trusted adapter authorization compares original and candidate
fields; a candidate or recovery envelope cannot expand source permission.

Small authoring annotations:

| Annotation | Meaning |
| --- | --- |
| `x-control: scalar` | Ordinary string/number/integer/boolean control |
| `x-control: multiline` | Description textarea for a string |
| `x-control: ordered-table` | Registered keyword or requirement table |
| `x-control: ordered-records` | Reusable ordered object records with descriptor-defined scalar/multiline cells |
| `x-suggestions` | At most 32 string suggestions; free text remains valid, not a restrictive enum |
| `x-reference` | Named source-backed reference provider |
| `x-view` | Place an ordinary field in a registered specialized view |
| `x-initial` | Explicit initial value when adding a new row; never an effective default for an existing missing key |

W5B adds `ordered-records`; it shares the existing localized array splice/move
implementation with recipe rows. Creation inserts only explicit `x-initial`
values, so a new page has text but no unsolicited `trailing:false`. Each operation
reparses the current source. Moves carry the full source object, including unknown
metadata. A new desktop build supplies this control vocabulary and reader view;
W5A's compatible scalar fixed-build proof does not claim otherwise.

An optional trusted family `authoring_preview` adapter receives the validated
candidate, disposable loaded data, selected project and bounded view inputs.
The shared `validate_document` command takes optional `previewInputs`; supplying
them revokes any earlier review and never installs a publication review, even
when semantic validation passes. A later normal validation is required to apply.
There is no text-specific IPC command, document slot, worker service or writer.
PNG frames use the existing bounded JSON output channel (2 MiB per frame beneath
the host's 16 MiB output cap); data URLs do not broaden filesystem permissions.
Receipts bind candidate/descriptor/contract, project code/data/resources, runtime
and page/scroll selection. The conservative dependency stamp still includes all
Python and data JSON, extended to the saved Fonts/UI resource trees.

Host filesystem admission uses a fixed `CONTENT_ROOTS` table independent of
descriptors. A family registration still needs an explicitly permitted host root;
renderer metadata cannot add one. Reserved basenames are rejected at every depth.
The text registration allows variants under `roguelike/data/texts/` and excludes
`text_item_map.json`. Generic workspace visibility uses the active document token.

For example, a supported optional boolean can be added to a family's
`SCHEMA["properties"]` with `type: "boolean"`, its factual title/help and the
consumer's effective default. No central field list or boolean renderer changes.
The semantic adapter must already accept the field and prove its consumer
behavior. A new runtime mechanic still requires game implementation and tests.

W5A's extension is `consumed_on_use`, labelled **Eligible for automatic ingredient
selection**. The factory defaults it to true. False excludes the instance from
automatic material allocation; an explicit matching material choice can still
select it. Recipe roles determine material consumption and retained tools. This
field does not govern ordinary item-use disposal. The extension adds only local
item descriptor metadata plus tests/guidance; the compiled application, packaged
bridge and bundled Python remain fixed during the native extension proof.

Defaults are displayed only when the key is absent. Opening or viewing does not
insert keys. Explicit false, null and invalid raw values remain distinct; the
actual game validator rejects unsupported values. `readOnly` is descriptive,
never a publication permission. Controls use parser offsets and localized text
edits, including table row moves, retaining unknown nested metadata, line endings
and other source spans. Raw/variant-ID edits retain the existing history-reset
behavior. Invalid syntax keeps exact Source available and freezes unsafe controls.

## Authority and freshness

Registered item, recipe, text, typography and creature documents use the host's versioned recovery
envelope. It stores exact accepted source/target intent, original baseline and
historical family/contract identity, never a live token, review, descriptor-granted
permission, preview or verdict. Restoring requires current discovery, original
source comparison and fresh host eligibility. Supported descriptor changes are
inspected again; validation is always fresh. Recovery never creates dependency
overlays or changes variant-only recipe/text policy. Completed publication facts
remain separate from newer drafts and permit only verified read reconciliation.
See the [recovery workflow](../README.md#recover-unfinished-registered-drafts).

Compatibility is the supported vocabulary, not a hardcoded item-contract version
in the desktop. Freshness binds the original discovered source, descriptor hash,
contract string, exact candidate and source/dependency identities. Compatible
descriptor additions are read from the selected project's Python modules without
rebuilding the desktop or packaged bridge. Reopen obtains the new contract; old
reviews are invalidated by game-source changes. This does not promise unrestricted
hot reload or updates to every installed application.

The host obtains policy only from the trusted worker and independently confines
paths to supported roots. Renderer-supplied family IDs, schemas and verdicts grant
no write authority. Python rechecks original source eligibility separately from
candidate validity. An unsupported source cannot become writable by changing its
candidate shape. Duplicate IDs, arrays and keyed objects retain their previous
inspection/publication limits. Items retain eligible component edit/variant
rules; immediate recipes require a unique new variant.

W4D operation ownership, token/revision/attempt checks, cancellation, one-time
review consumption and reserved-publication BUSY handling remain active. The
writer retains input pinning, reviewed-byte checks, production revalidation,
path/link restrictions, backup/rollback, no-clobber variants and hash-checked
reopen. Publishing a recipe changes what a new session loads. Publishing an item
variant does not assign it to loot, world selection or an existing instance.

References: [JSON Schema annotations](https://json-schema.org/understanding-json-schema/reference/annotations)
and [Microsoft jsonc-parser](https://github.com/microsoft/node-jsonc-parser).
These explain defaults and text edit facilities; the repository's semantic and
source-fidelity tests establish the supported behavior here.

The repeatable native proof is `node scripts/run-contracts.mjs` from `workbench/`.
It uses the supported release executable, isolated settings/data, the committed
pre-extension game module and the current production module. It runs the existing
recipe journey, replaces only that disposable project's item authoring module,
then checks descriptor freshness, the new control, publication/reopen and fixed
application/resource bytes. It never rewrites the production data catalogue.

## Fixed typography family (W5E)

`typography_authoring.py` registers edit-only `game-typography-1` with ordinary
scalar/reference controls and typed `typography-preview` (960×960 specimen plus
960×640 reader), separate from `reader-frame`. `engine/typography.py` owns the
production roles, parsing, no-link resource resolution, coverage and loading;
gameplay does not import the adapter. The worker passes the verified project root
explicitly to resource-aware family adapters while data is staged in scratch.

The registration's optional `exact_file` and independent host `TYPOGRAPHY`
admission authorize only `roguelike/data/display/typography.json`. Host operation,
identity/version and recovery-target checks complement semantic validation.
Descriptors cannot broaden filesystem policy. Recovery supports only this fixed
source/target and edit intent; invalid JSON remains exact and cannot restore
validation authority. Unknown fields remain non-executable metadata.

The thirteen assignments and selected byte hashes are included in preview
receipts. Existing code/data/Fonts/UI stamps remain conservative, shared and
bounded by the existing monitor. A typography candidate overlays only its own
isolated preview initialization; found-text previews identify saved typography.

## Source-specific creature operations (W5F)

`creature-common-1` registers the maximum `edit`/`variant` operations, plus an
`effective_operations` subset obtained from verified original inspection. The
host freezes that subset with the opened source; frontend controls, validation,
review/apply and recovery all honor it. Candidate context and stored metadata
cannot enlarge it. Special Actor sources receive only `edit`; ordinary Actor
sources receive both; unsupported sources receive neither. Exact unchanged
read-only Actor construction can still be inspected without a publication review.

Nested family matching admits entity discovery, while the host independently
limits creature writing and recovery targets to `roguelike/data/entities/creatures/`.
Collisions use the complete entity namespace, including player. The registered
`creature-properties`, `creature-references` and `creature-factory` views handle
bounded fighter/perception paths through existing localized source primitives;
they have no separate document slot, history, persistence service or writer.

Original-source immutable-field comparison and operation-specific identity rules
are enforced in the game adapter. Changes to source, ability registry, selectors
or schema invalidate applicable evidence through existing code/data freshness.
See the [creature guide](../../roguelike/docs/CREATURE_AUTHORING.md) for bounds,
construction/reference meanings and saved-instance activation semantics. Recipe
and text variant-only rules are unchanged.

## Registered spatial rooms (W5G)

`authored-room-1` registers family `room` on production route `authored_submap`.
Eligible single-object ordinary sources immediately under `data/layouts/` support
same-ID edits at the exact existing file and new-ID variants beside it. The exact
G17 documentation template supports unfinished drafting and new-ID variants in
`data/layouts/`, with no documentation writes. `starting_lab` is protected by
identity and source filename. Unsupported/ambiguous originals cannot be promoted
by deleting fields or changing candidate identity. Nested layouts are excluded
because the production catalogue discovers only immediate files.

The shared host independently admits those immediate destinations and that one
documentation source exception. `variant_directory` supplies the same host-owned
template → layouts mapping for publication and recovery intent. An unfinished
`variant:false` template draft retains its logical source without inventing an ID;
stored invalid text and incomplete target inputs never authorize a write. A
published fact must name an immediate layout file. Other documentation sources
are not admitted. The worker stages the template candidate inside disposable
layout data while retaining its logical source/target paths and original hash.

The registered spatial view uses the existing `LayoutCanvas`, `MapView`, exact
draft/history and shared lifecycle. Structured map receipts are a typed scene
result, separate from the reader/typography PNG union. A room review requires
compiler, factory/population and derived static access evidence for the exact
candidate, fresh original policy and saved dependencies. Apply repeats those
checks with the reviewed seed. No second writer, recovery service or sidecar is
introduced. Map receipts distinguish source/translated positions, authored start,
actual arrival, relocated items and their exact transient ownership, constructed
carrier/text/actor identities, selected pools and realized container contents.

References use recursive object/array indices for items/texts/creatures/pools;
decor uses its actual list registry. Choices identify sources, readability and
missing/ambiguous definitions. Parked dependency drafts are excluded from room
validation. Save dependencies first, then validate/publish the room. Source,
dependency and request freshness binding remains shared with W4D/W5F.

Recovery admission is deliberately broader than publication admission. An
eligible text/recipe/template can recover accepted exact text before choosing a
variant, including invalid JSON. Explicit forbidden variants remain refused;
fresh source eligibility/baseline, generation, ownership and claim-before-read
checks remain mandatory. A restored preview or review grants no authority.

See [structure authoring](../../roguelike/docs/STRUCTURE_AUTHORING.md) for the
route's actual geometry, carrier, arrival and saved-scene semantics.
