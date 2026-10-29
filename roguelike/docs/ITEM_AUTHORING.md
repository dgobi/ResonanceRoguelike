# Usable supplies authoring (W5J)

The registered item family uses `usable-supplies-1`. Begin edit changes the same
ID; **Save as new variant** creates a distinct ID beside a verified source.
IDs are machine identities. Display-name edits never redirect references.

One unique single-object source under `data/items/components`, `butchery` or
`consumables` may author common properties when its category matches its route
and it is an ordinary inert material, `eat` food, `drink` drink or `heal_minor`
treatment. The original category and use identity stay fixed for both operations.
Raw Source, recovery and descriptor flags cannot promote unsupported originals.
Arrays, ambiguous/case-colliding IDs, corpses, equipment, satchels, lights,
readable items, effects and special preparations remain inspect-only. Rules admit
42 shipped sources: 30 materials, nine foods, two drinks and one treatment.
This is an executable inventory, not an ID allowlist.

`empty_water_skin` is reference-only: rain/filling matches its exact ID and creates
canonical `water_skin`. `resonant_tincture` stays inspect-only because its
`on_use_effects` list is not executed by the current factory/use path. Use binding
explains the inactive metadata.

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

## Preparation references

Saved materials and usable supplies can be referenced by ordinary item-output
recipes under `item-preparation-1`; see [recipe authoring](RECIPE_AUTHORING.md).
Automatic eligibility remains distinct from a tag match. Components can request
an affirmative protected-material choice; conjunctions remain automatic-only.
Save/reopen supplies before recipe references and room placements. Preparation
completion constructs the recorded output ID; already acquired outputs retain
this guide's copied-value and dynamic-reference policy.
