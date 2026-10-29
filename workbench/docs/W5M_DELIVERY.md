# W5M — usable expedition equipment

The existing registered item family now authors an ordinary equipment kit alongside
all W5J supplies. Weapons, armour, shields and satchels share the same documents,
Source/history/recovery, validation, reviewed single-file publication, room
placement and production Test room. No live demonstration kit, starter loadout,
enabled assignment profile or gameplay rebalance is installed.

## Source and publication boundaries

| Boundary | Identity |
| --- | --- |
| Initial local and remote main | `a60c66680127112f467611d3986043bb48d0fa33` |
| Preserved start | `checkpoint/workbench-w5m-start-20261029` |
| Implementation and application/game package inputs | `829a2acf51539f92af314a6fe1dcab633ea9298d` |
| Final journey inputs | `checkpoint/workbench-w5m-journey-inputs-20261029` |
| Verified delivery | `checkpoint/workbench-w5m-verified-20261029` |

The [machine receipt](w5m-verification.json) binds working and committed source
bytes separately, exact accepted fixtures, package/runtime hashes, captured game
inputs, environments, commands and accessible evidence. Application/game inputs
precede later harness/evidence commits; the completed NSIS build uses those same
application bytes. A commit cannot contain its own SHA: resolve the final named
ref. The post-push handoff and ignored `remote-readback.json` record the exact
full local/remote-main match. Work stayed in production `main`, with named Git
checkpoints and the existing untracked owner plan preserved.

## Contract and controls

`expedition-items-2` admits 54 of 79 sources: the existing 42 supplies plus six
ordinary weapons, two armour definitions, one shield and three satchels. The
[executable inventory](evidence/w5m/item-inventory.json) records each source,
class/operations, binding and exclusion reason. Admission uses compatible
route/category/slot and supported consumer payloads. The multi-essence debug
blade, held lights, talismans, effects and special uses remain inspect-only.
Original-source checks prevent promotion through raw field deletion, recovery
or a forged renderer class. The Rust host independently confines item source,
target and recovery paths to the existing supply and equipment routes.

Common controls retain physical fields, ordered keywords, grouping of separate
instances and automatic ingredient-selection eligibility. Equipment adds bounded
positive damage dice, signed bonus, **additional** critical chance, ordered armour
name/material/AV layers, shield chance/reduction and a small native keyed-number
map. Category reductions override `all`, including zero; missing fallback and an
empty map give zero reduction. Keys are actual inventory labels. No array map
conversion or parallel TypeScript/Rust combat/carrying calculation was added.

Same-ID category and slot stay fixed; a new armour variant can choose an existing
armour slot. Coverage and untouched row metadata survive localized edits/reorder;
coverage is read-only and has no new anatomical meaning. Singular essence and
well-formed inherited movesets remain unchanged, with existing action-ID cooldown
identity. Base-attack evidence does not certify every inherited move. Unknown
unedited metadata remains in Source and is not advertised as a control.

The four exact legacy sources retain their absent/null handler spelling on same-ID
edits. A deliberate new-ID variant explicitly inserts `equip_toggle` in the
draft and reviewed diff; worker validation/publication independently requires it.
The shipped definitions and runtime exact-ID repair were not rewritten or expanded.
The [item guide](../../roguelike/docs/ITEM_AUTHORING.md) specifies numeric bounds,
defaults, retained behavior and activation rules. These are authoring publication
rules, not new gameplay balance limits.

Properties/Use binding distinguish validated definition and declared/legacy use.
Factory result explicitly reports unowned common copied fields; damage, armour,
shield values and satchel reductions are absent from `ITEM_STATE`. Actual equipped
observations come separately from production consumers and normal game input.

## One packaged equipment expedition

The [observations and screenshots](evidence/w5m/observations.json) retain exact
reviewed fixture bytes, actual frames, instance references and setup boundaries.
Supported controls author a 2d6+3 blade with additional critical chance, a two-layer
AV-5 jack, a shield and an explicitly bound legacy-source satchel. Layer reorder,
map add/change/remove and item undo/redo preserve unrelated source. All items are
validated, diff-reviewed, published and byte-checked reopened before placement.
A second dirty equipment document and an invalid independent text draft coexist;
neither overlays publication or capture. Equipment dependency changes stale review,
competing writes are preserved, and invalid recovery restores bytes without review.

The same room controls place the saved kit, a same-ID shield sibling, ordinary
wood, existing furnishing and an existing Stone Lurker. Source establishes the
disclosed room geometry only. Normal movement/pickup acquires every demonstrated
object; inventory Enter equips exact owned instances for one paid turn while
retaining them. Shield replacement/drop/reacquisition leaves the other sibling's
slot intact. Equipping the shield deactivates the ordinary lit starting torch;
the physical torch and accumulated burn state remain.

The native encounter uses ordinary randomness and the actual normal/incoming
attack callers. Read-only traces record the real resolver's original results,
authored weapon and shield definitions, and exact equipped instances; they do not
replace results or alter RNG. The authored AV is 5. A useful bag effect is shown
with the same physical load: unequipping can exceed capacity, ordinary pickup
refuses it, and equipping the exact bag allows admission. No demonstrated item,
slot, AV, discount, creature, health or encounter statistic is injected.

Save, leave/return and a separate pinned process preserve copied fields, exact
slot-to-inventory-row references, derived values and depleted source placements.
There is no equipment respawn. A Workbench same-ID bag revision changes a copied
name and reduces definition-owned discounts. Reset keeps the original immutable
capture; latest saved captures and normally acquires the revised bag.

A separate **ordinary** save, made from the exact UI-published definitions before
revision, retains a 27.3 kg physical load at 14.69 kg effective weight. A new
process/catalogue loads that save after revision: the old copied name and exact
inventory/slot rows remain, current reductions produce 26.585 kg against 20 kg
capacity, and ordinary subsequent pickup refuses admission without losing any
object. The depleted generated room stays authoritative. Fresh construction gets
the revised name. This proof is independent of unchanged captured restore and
latest-saved capture; it does not introduce a save format or migration.

## Verification and preservation

[Gates](evidence/w5m/gates.json) record actual Windows commands/log hashes and
environments: 74 frontend tests, TypeScript, 68 Rust tests, clippy with warnings
denied, 115 game regressions, 93 worker cases (one expected embedded-runtime skip),
a separate missing-dependency control, locked executable/NSIS packaging, the
equipment expedition, shared workspace and room-session lifecycle, and ordinary
128×128 main/default save-load. Focused equipment checks control RNG only to
assert numeric branches and exercise the actual outgoing/incoming callers,
inherited moveset dispatch/shared cooldowns, AV, reduction override/fallback/zero,
exact replacement/drop/transfer/stale selection, light displacement and all four
legacy bindings. Early environment, changing-source, runner-selector and NSIS-lock
attempts are excluded from passing final gates.

The [preservation inventory](evidence/w5m/preservation.json) checks hashes and
mtimes of original out-of-scope inputs, including the untracked owner plan.
Content/campaigns, fonts, settings, launcher, prior evidence and wiki edition are
preserved. Save-access audits remain in positively owned disposable roots. These
are local Windows observations, not an external audit, unaided expedition pacing,
encounter-balance evidence or a promise for arbitrary external definition edits.
Wiki/reference upkeep, moveset/essence/effect authoring, carried-light/talisman
authoring, new combat/coverage rules, selectors and save migrations remain outside
this delivery.
