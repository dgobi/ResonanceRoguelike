# Contextual loot authoring

Workbench registers `pool` / `contextual-loot-1` with the native
`contextual_loot_pool` route. Immediate single-object
`data/loot_pools/<safe-id>.json` files support same-ID edits and deliberate variants.
The shipped 17-source inventory is coverage, never a permission whitelist.
Original format, exact identity, source locations and registered operation supply
authority. Nested/array sources are inspect-only; `data/loot/` is unrelated.
An admitted field with an invalid value can be repaired. Larger sources may be
reduced deliberately. Neither Source nor recovery can promote an unsupported
original. A variant needs a distinct safe case-insensitively unique ID matching
its filename beside the source, and changes no container link.

Open a direct room or ordinary-building container, then **Open pool**, then
**Open item**. Shared tabs retain independent drafts; opening an existing source
focuses its owner. Return restores the recorded row/container when its draft is
unchanged. A changed recorded location is explicitly stale rather than selecting
another row. Item source permission stays independent: a valid reference-only
held light can be loot without acquiring behavior-editing authority.

Pool description, count representation and ordered entries use exact-source
edits. Add/remove/up/down moves complete row source spans and metadata. **Undo
pool / Redo pool** covers table, Source and properties, including invalid text.
Recovery checkpoints preserve exact text and target/operation intent, never old
reviews. Validate again after recovery. Structured edits preserve unknown keys,
nested metadata, escaping, ordering and line endings. Source may deliberately
edit inactive metadata; warnings disclose its lack of gameplay meaning.

| Native field | Effective behavior |
| --- | --- |
| `description` | Authoring metadata only. |
| omitted `roll_count` | `[1,1]`, displayed without insertion. |
| `[n]` / `[min,max]` | Fixed / inclusive requested count; exact integers 0–`2^53−1`, ascending; bool, null, fractions and unsafe integers invalid. |
| omitted `items` / `[]` | Valid empty pool. |
| ordered entries | Saved `item_id` references; repeated IDs remain separate entries and physical items. |
| omitted weight | Effective 1; **Use default 1** deliberately removes the override. |
| explicit weight | Finite nonnegative number. Every nonempty pool needs finite positive total, even with zero requests. |
| publication bound | At most 64 rows in a Workbench candidate. No runtime bound or rejection of an otherwise valid unchanged larger dependency. |

Changing count representation is deliberate; opening and unrelated edits retain
omitted/fixed/range forms. **Omit empty items** restores the supported omission.
Quantity, conditions, text overrides, nested pools, rarity and collection modes
acquire no semantics through Source.

`Validator.pool` and the production roller remain authoritative. Requested draws
are capped to entries, weighted without replacement **by entry**, and stop when
remaining weight is zero. Positive rows alone are eligible, including random zero,
exact cumulative boundaries and rounded upper-bound fallback. No extra RNG draw,
reseed or alternative sampler is introduced. Ordered/repeated pool occurrences
each roll with the existing caller RNG. Scene context and realized container
position/decor affect results; a pool ID alone is not a reproducibility key.

Validation resolves all case-insensitive source locations for original/target
pool and every item, retaining paths and array pointers. Missing, duplicate,
case-aliased, loader-skipped or mismatched definitions block publication. Every
row, including zero weight, constructs an unowned `Item` with the real factory
and checks its exact ID and existing persisted `ITEM_STATE` fields. These checks
do not roll, mutate saved definitions or prove ordinary use. If a bad saved pool
causes a referencing building's catalogue compilation to fail, pool authoring
retains the real loader's earlier pool/item snapshot to permit repair. Gameplay
startup and candidate validation remain strict.

Saved direct room and ordinary-building containers repeat source and physical
dependency checks. Failed selected construction aborts the staged production
scene before ownership publication. Parked drafts never overlay saved inputs.
The declared usage list covers direct containers in supported authored rooms and
ordinary buildings with exact file/field/occurrence information. It is a partial
graph; an empty list does not prove unused or unreachable.

Pool validation proves definition/dependency acceptance. A production preview
separately records actual rolled contents with complete source, contract and scene
inputs. Test room uses a saved immutable capture and ordinary movement,
interaction, transfers and use. Save each dependency and room separately.

| Activation boundary | Behavior |
| --- | --- |
| Source save | Changes definitions for the next catalogue, not an already running catalogue. |
| Fresh construction | A new catalogue uses current saved pools/items. The W5O pending authored-room demonstration covers its room route. |
| Pending planned surface | Its saved selected semantic closure is checked before construction. A same-ID consumed building, pool or item change can reject it with the existing changed-dependency diagnostic. Restore matching definitions or start a fresh world; no automatic replanning/migration. |
| New building variant | Retains the old building identity and explicit memberships. Shared pool/item edits can still invalidate the old building's pending selected dependencies. Legacy category-folder selection can discover added building files. |
| Generated container | Saved physical contents and closed/open/looted state remain authoritative. Opening/revisiting/loading never rerolls. |
| Taken/consumed item | Exact transfers and consumption persist; removed items do not return. |
| Existing physical item | Retains supported copied fields; established definition-owned combat/carrying properties keep their separate behavior. |
| Reset | Original immutable capture with fresh disposable state. |
| Test latest saved | Fresh capture of current saved definitions. |
| Missing owned map cache | Refuses unsupported regeneration; no new loot is minted. |

Containers hold live `Item` instances; ordinary access does not reconstruct IDs.
Historical dictionary-entry restoration remains supported without a schema change.
See [room testing](ROOM_TEST_RUNTIME.md), [structures](STRUCTURE_AUTHORING.md) and
[item ownership/activation](ITEM_AUTHORING.md#equipment-ownership-and-activation).
