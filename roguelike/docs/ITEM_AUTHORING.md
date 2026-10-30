# Expedition item authoring (W5M)

The registered item family uses `expedition-items-2`. Begin edit changes the same
ID; **Save as new variant** creates a distinct ID beside a verified source.
IDs are machine identities. Display-name edits never redirect references.

One unique single-object source under `data/items/components`, `butchery` or
`consumables` may author common properties when its category matches its route
and it is an ordinary inert material, `eat` food, `drink` drink or `heal_minor`
treatment. The original category and use identity stay fixed for both operations.
Raw Source, recovery and descriptor flags cannot promote unsupported originals.
Arrays, ambiguous/case-colliding IDs, corpses, lights,
readable items, effects and special preparations remain inspect-only. Rules admit
42 shipped sources: 30 materials, nine foods, two drinks and one treatment.
Equipment adds six ordinary weapons, two armour definitions, one shield and three
satchels: 54 of 79 total sources. Run `workbench/scripts/equipment-inventory.py`
with an output JSON path for operation/class eligibility and exclusion reasons.
This is an executable inventory, not an ID allowlist.

`empty_water_skin` is reference-only: rain/filling matches its exact ID and creates
canonical `water_skin`. `resonant_tincture` stays inspect-only because its
`on_use_effects` list is not executed by the current factory/use path. Use binding
explains the inactive metadata.

G20's exact `flint_shard` identity is a narrow runtime exception: a null declared
or saved `on_use` still offers a six-tile, one-unit clatter throw through owned
capability dispatch. The shard retains cutting tier 1 and is lost on confirmation.
Inventory supplies that use guidance without rewriting the stored description or
handler. Its shipped source bytes/definition remain historical so old pending
workshop dependencies still agree. **Use binding** reports this exact-ID
capability; explicit nonempty instance handlers win, and a new-ID material variant
does not inherit it. This does not enable general material throwing or effect editing.

## Controls and source fidelity

Common controls edit name, multiline description, existing tile, nonnegative
weight in kg, inventory grouping, ordered keyword tag/tier records and **Eligible
for automatic ingredient selection** (`consumed_on_use`). This controls automatic
crafting-material admission; recipe roles and ordinary handler outcomes determine
disposal. False still permits explicit matching material choice. Grouping combines
display rows while retaining distinct owned objects and weights.

Food adds `nutrition` and `eat_message`; drink adds `hydration`, `drink_message`
and optional `empty_form`; treatment adds `heal_amount`. Inert materials show no
dose controls. Localized parser edits retain unknown/nested metadata, formatting,
omitted defaults and supported nulls. Opening or changing an unrelated field never
normalizes doses. Deleting advanced fields cannot promote an original.
`harvest_from`, `gather_from`, `liquid`, `liquid_volume` and `_essence_note` remain
unchanged by ordinary controls: variants gain no discovery route or partial-volume
drinking from these declarations. Tile controls reference existing art.

Validation rejects bool-as-number, nonfinite/negative numbers, invalid keyword
tags/tiers and missing tile IDs. Authored integers must be exact JavaScript
integers (maximum 9007199254740991). Explicit nonnull treatment amounts must be
positive integers. No rounding or coercion occurs.

## Actual dose meanings

Properties explains saved `survival.json` values on explicit validation. Factory
evidence is labelled **Unowned factory construction**: copied fields/defaults do
not prove acquisition, ordinary use, action cost or persistence.

Food/drink numbers at or below 1 are fractions; above 1 they divide by saved
hunger/thirst maximum (currently 1000/800). `0.35` means 35%; nutrition `300`
means 30%; `1.0` means 100%; nutrition `1.01` means 0.101%. Absent/null nutrition
uses 300 and hydration 400. Restoration clamps at current need, followed by normal
turn changes. Zero restores zero and still uses the whole item. These are neither
calories nor millilitres.

Treatment uses `heal_amount or 3`: absent/null and historical zero use 3 HP. New
authored zero is rejected. Healing caps at missing HP. Full-health/dead/missing/
stale treatment retains its item and costs no turn. Other handlers may return
false after a paid action; false is not a general failure/no-action signal.
Opening a deferred confirmation still costs no turn.

A drink may have no replacement (absent/null/empty string), or one saved, uniquely
resolved, factory-valid ordinary inert return. Self, active-use, equipment, light
and effect-bearing returns are rejected. The canonical empty skin is a precise
reference-only exception to editability. Label, ID and source have an ordinary
navigation/return trail. Saved return bytes and survival settings join existing
conservative stamps; changes stale validation/reviews and capture. Exchange occurs
before hydration. Failed construction/capacity leaves the original and thirst
intact. Success replaces only the selected instance and prevents a second
consumption; inventory rows refresh while the screen stays open.

## Save, place, use and revise

Validate, review the diff, confirm one-file apply and byte-check reopen each supply.
Then reference saved IDs through existing room placement or supported pool controls.
Parked drafts never overlay another document's validation or capture. A saved
unreferenced item is valid: it does not automatically join loot, harvesting,
gathering, crafting or assignment. A later failed room save does not roll it back.

**Reset current test** retains immutable captured inputs; **Test latest saved
version** captures revisions. See [room test runtime](ROOM_TEST_RUNTIME.md).

| Operation | Activation / persistence |
| --- | --- |
| Same-ID common field, dose or message edit | Later construction uses updated definitions. Versioned saved items retain copied name, description, tile, weight, grouping, handler, doses/messages, keywords and crafting eligibility. |
| Same-ID drink `empty_form` edit | Not copied into `ITEM_STATE`; use reads the definition in the current session, including for an older restored drink. |
| Return definition edited | Return is newly constructed from the session catalogue. |
| New variant ID | Distinct definition; no instance renaming, reference redirection or migration. |
| Source changed while game runs | Existing session retains its catalogue. Initialize a fresh catalogue to exercise changes. |
| Room/profile edits | Profile affects future world creation; same-ID room affects later first construction, including pending assigned rooms; generated scenes retain saved state. |

No save-schema bump, global immutable catalogue, survival rebalance or generalized
vessel mechanics are included. Returned objects are not automatically refillable;
canonical skin filling does not reproduce a custom drink variant.

## Ordinary equipment controls and publication rules

Equipment uses the same item documents, history, Source, recovery, validation,
review and single-file apply as supplies. Save/reopen each item before placing
its saved ID through room or supported pool controls. Independent parked drafts
never overlay validation or capture. Source and current runtime consumers join
the conservative dependency stamp; changing either stales review/capture.

| Class and compatible route | Locked category/slot | Editable definition properties |
| --- | --- | --- |
| Weapon, `items/weapons` | `weapon` / `weapon` | `damage_dice`, `damage_bonus`, `crit_chance` |
| Armour, `items/armor` | `armor` / original armour slot | Ordered `armor_layers`: name, material, AV; add, remove, reorder |
| Shield, `items/shields` | `shield` / `offhand` | `block_chance`, `block_value` |
| Satchel, `items/equipment/satchel` | `equipment` / `satchel` | Native keyed `weight_reductions` object |

All four also have the common controls above. A deliberate new armour variant may
choose `armor_head`, `armor_torso`, `armor_arms` or `armor_legs`. Same-ID edits keep
their slot; other classes keep their class slot in either operation. Raw Source,
recovery or a descriptor label cannot promote an unsupported original or edit
locked behavior. Singular essence/strength and well-formed inherited movesets are
retained read-only; new IDs retain their action IDs and shared cooldown identity.
The base-attack check does not certify every move. Multi-essence debug equipment,
held lights, talismans, effects, coatings, corpses and special-use items remain
inspect-only. Unedited metadata is preserved; it is not an active control.

Ordinary equipment requires `equip_toggle`. Four exact shipped IDs have a legacy
missing-handler repair on owned use: `revelation_lens`, `leather_satchel`,
`herbalist_pouch`, `component_satchel`. Use binding distinguishes declared absence
or null from that effective binding. A new-ID variant deliberately inserts
`"on_use":"equip_toggle"` in the draft/reviewed diff; candidate validation and
publication independently require it. Same-ID edits retain the original absent/
null spelling. Explicit handlers remain explicit. No global fallback or shipped
definition cleanup is installed.

Publication rejects booleans as numbers, nonfinite values, duplicate JSON keys,
unresolved tiles/keywords, malformed rows/maps and ambiguous identities. Defaults
are displayed without inserting keys; explicit null is not omission. Unsupported
numeric shapes remain inspectable and are never normalized by an unrelated edit.

* Damage expressions are positive `NdM`, 1–100 dice and 1–1,000 sides; the permissive
  combat parser's fallback cannot authorize new damage. Absent dice use the existing
  unarmed `1d4` fallback, which ignores a weapon bonus. Bonus is a signed integer
  within ±2147483647; dice plus bonus must fit that magnitude. This bounds authoring
  execution, not global gameplay loading or balance.
* Critical and block chances are finite fractions in `[0,1]`. Weapon critical
  chance is **additional** to current base 0.05 and the head-hit bonus. Base range
  uses `combat.roll_dice`; it promises neither turn damage nor encounter balance.
* Armour has 1–32 layers, nonempty name/material and nonnegative integer AV.
  Shield reduction is a nonnegative integer. Each and summed item AV fit signed
  32-bit magnitude. AV uses `_sum_item_av`; coverage and other row metadata survive
  edits/reordering. Coverage is read-only and does not select protected body parts
  in current combat. Names/materials do not add material physics. Explicit new rows
  default to `new layer`, `leather`, AV 0, with no invented coverage.
* Satchel keys are production inventory labels (`Weapons`, `Armour & Shields`,
  `Consumables`, `Preparations`, `Components`, `Tools`, `Light Sources`,
  `Miscellaneous`) plus `all`. Fractions are in `[0,1]`. A category overrides
  `all`, including zero; it is not added. Missing `all` means zero fallback; `{}`
  is valid. Add/change/remove preserves the JSON object, remaining key order and
  unedited bytes. Raw category IDs such as `component` are refused.

## Equipment ownership and activation

Properties and Use binding describe stored definitions and validated binding.
Factory result is **unowned construction** of copied common fields. Damage,
armour layers, shield values and bag reductions are not copied into `ITEM_STATE`.
Neither of those views proves acquisition, ownership, action costs or combat.
Focused production-consumer checks and the packaged journey provide that evidence.

| Boundary | Existing behavior |
| --- | --- |
| Saved physical instance | Retains copied name, description, tile, weight, keywords, grouping, handler and stored instance state. Fresh construction uses current definitions. |
| Weapon and shield | Ordinary attack callers read the session catalogue, including for an older owned same-ID item. |
| Armour | AV recomputes from current definitions at equip/restore boundaries. |
| Satchel | Current-definition reductions apply only while the exact owned bag is equipped. Base instance weights are never rewritten. The gain depends on actual carried categories/load. |
| Equipment references | Exact owned inventory/save rows; same-ID siblings are distinct. Replacement, drop, consumption and transfer clean up only the selected instance. |
| Running game | Keeps its loaded catalogue; source publication does not hot-reload it. |
| Reset / latest saved | Reset uses the original immutable capture; latest saved constructs a new capture from revised saved dependencies. |
| Generated room | Saved map, ownership and depletion remain authoritative; source revisions do not regenerate it. |

A fresh-catalogue restore with a reduced bag discount can legitimately be over
capacity. Objects, copied weights and slot references survive; subsequent pickup
uses the existing admission check. No dropping, migration or save rejection is
introduced to force the inventory under capacity. Equipping is a paid ordinary
inventory action that retains the object (`False` from the handler means not
consumed). Shields displace and deactivate an ordinary lit offhand item while
retaining that physical item and its burn state. No action, combat, light or
carrying rules are changed by authoring.

## Preparation references

Saved materials and usable supplies can be referenced by ordinary item-output
recipes under `item-preparation-1`; see [recipe authoring](RECIPE_AUTHORING.md).
Automatic eligibility remains distinct from a tag match. Components can request
an affirmative protected-material choice; conjunctions remain automatic-only.
Save/reopen supplies before recipe references and room placements. Preparation
completion constructs the recorded output ID; already acquired outputs retain
this guide's copied-value and dynamic-reference policy.
