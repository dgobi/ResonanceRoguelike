# Material-sensitive weapon washes (SYS-3)

Binding wash carries Binding; Etching wash carries Dissolution. Both have strength
0.4. One tier-one primary makes a six-contact dose; tier two or higher makes a
twelve-contact dose of the same strength and item ID. A richer material changes
lifespan. The target still determines which available essence helps most.

## Prepare and use

Carry one suitable primary (`binding` for Binding, `caustic` for Etching), one
separate `fixative`, and a registered heatproof vessel holding **exactly 125 mL**.
Coldbell cutting / briar sap and sulphur-cap fragment / crow bile demonstrate
the two respective bands. Dried bitter or dried aromatic herb supplies fixative.
An existing finished coating cannot be used as a primary.

In Inventory, select the actual vessel, **E → Fill → 125 mL** beside reachable
water. At a stationary fire supplying burning tier two, press **C**, choose the
wash, then choose the exact primary, fixative and vessel. The primary prompt
shows tier and resulting contacts, including different instances of the same ID.
Confirm a valid nearby work tile. One primary, one fixative and the water are
committed; the vessel belongs to the work. The first of 15 charged turns passes
immediately. Heat is needed to start; it is not an ongoing maintenance cost.

Completion returns the same empty vessel and one resolved dose on that map.
Pick both up. Equip an ordinary weapon, select the desired dose in Inventory,
and press **E**. One successful application consumes one unit and one action.
Rows and details show captured contacts/strength; weapon details show remaining
contacts. Missing/stale equipment, invalid ownership and paralysis reject freely.
The dose replaces the same essence on that weapon and keeps other essence rows.

Misses and dodges do not spend contacts. A real contact spends one from every
active row, even when armour/blocking reduces damage to zero or another essence
wins. The last contact still benefits before expiry. Normal best-essence choice,
damage rounding, armour and target reactions remain in force. Binding adds no
root effect; Dissolution adds no armour damage or persistent corrosion.

## Find supplies

Newly selected successor apothecaries (`apothecary_d`, `alchemist_washes`) can
offer finished washes, practical materials, dried fixative and vessels. Rolls
are weighted and finite; a shop need not contain every ingredient. Existing
reagent stock and ordinary drying/butchery/harvesting provide alternatives.
The optional weapon-wash note describes richer material and different targets;
it grants no unlock. Older selected shops, visited geometry and depleted stock
retain their saved state. No retroactive restock is performed.

## Author and retain

In Workbench, duplicate a supported ordinary oil in **Items**, edit its single
**Weapon coating** record and ordinary properties, validate/apply/reopen.
Duplicate a supported passive recipe, choose the saved dose output, and set
steeping, duration, heatproof vessel/water and burning requirement. Under
**Requirements**, enable **Material response**, assign exactly one quantity-one
component `primary`, and set the matching tag, threshold and two budgets.
Save/reopen before room or pool references. Test a saved room through ordinary
pickups, filling, crafting and use. Reset retains captured inputs; latest saved
captures published changes; dirty drafts enter neither.

An unused owned dose captures `{version:1, essence, strength, hits}` independently
of weapon `temporary_essence` remaining contacts. A version-two wash job captures
the complete validated output and primary resolution at commitment. Later supported
definition/recipe edits cannot retune that work or an acquired dose. New sessions
and later jobs use their loaded catalogue. Missing or invalid output references
leave due work recoverable; failed delivery gives no partial reward. **E** on
nearby work offers one-action abandonment: same empty vessel, no dose or refund.

Active and distinct hot cached maps tick once per charged turn; cold maps freeze.
Save/load and inspection are free. Genuine old unused oils with no payload use
the loaded definition once on reconstruction; they cannot recover historical
settings never saved. Existing applied rows keep their exact spent state.
Version-one bone work retains its original shape and completion semantics.
Modern malformed payloads, versions and duplicate owned aliases are refused
without partial load. Independent same-ID doses are valid and remain distinct
when captured settings differ. Personal saves need no manual migration.
