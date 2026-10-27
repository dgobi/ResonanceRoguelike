# Registered item and immediate-recipe authoring

`roguelike/engine/content_authoring.py:families` is the explicit first-party
registration point. The existing `item_authoring.py` and `recipe_authoring.py`
adapters own discovery identity, supported source shape, ordinary field metadata,
reference providers, semantic validation and construction/execution evidence.
Gameplay does not import these authoring modules. There are no descriptor-driven
imports, executable expressions, plugin loading or alternate content formats.

The worker dispatches discovery, inspect and exact-draft validation through the
registry. A common `family` envelope contains family/contract identity, descriptor
SHA-256, compatibility diagnostics, reference choices and typed family evidence.
The host stores one document per registered family in a collection. React mounts
one shared `Authoring` lifecycle for each document token; specialized views use
its source/history/validate/review/apply commands. One-open-document-per-family,
parked drafts, source trails and return navigation remain the interaction model.

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

Small authoring annotations:

| Annotation | Meaning |
| --- | --- |
| `x-control: scalar` | Ordinary string/number/integer/boolean control |
| `x-control: multiline` | Description textarea for a string |
| `x-control: ordered-table` | Registered keyword or requirement table |
| `x-reference` | Named source-backed reference provider |
| `x-view` | Place an ordinary field in a registered specialized view |
| `x-initial` | Explicit initial value when adding a new row; never an effective default for an existing missing key |

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
