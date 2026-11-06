# Practical vessels and resonant preparation (SYS-1)

Carry a registered vessel, open Inventory, select its physical row and press **E**.
The row shows a short instance identity and current/capacity mL. Choose **Fill**
beside visible, reachable drinking-water terrain; **Transfer** chooses another
carried vessel; **Drink** uses up to 250 mL; **Empty** asks before discarding water.
Amount choices include the saved catalogue's supported preparation batches (currently 125 and 250 mL), 250 mL, available
room/water and, for transfer, all source water. Oversized choices are refused.
Esc cancels freely. One successful handling action pays one ordinary charged
phase through the existing action scheduler. Denial, inspection and cancellation
spend neither water nor time. Full paralysis prevents handling.

| Vessel | Capacity | Empty weight | Heat-suitable |
| --- | ---: | ---: | --- |
| Clay pot | 500 mL | 0.6 kg | Yes |
| Copper steeping kettle | 1,000 mL | 0.9 kg | Yes |
| Waxed water flask | 2,000 mL | 0.2 kg | No |
| Small steeping cup, authoring example | 150 mL | 0.25 kg | Yes; fits washes, too small for 250 mL bone work |

Water adds 1 kg per litre to the actual object's empty weight. Existing satchel
reductions apply once to the combined load. Filled-vessel pickup and filling obey
carrying capacity. Transfers conserve quantity, including between identical item
definitions. Dropping, containers and saves retain each physical object's state.
Busy vessels belong to their work and cannot be selected from inventory.

## Prepare the existing bone tincture

Obtain one automatically eligible item that itself has **resonant tier 2 and
bony tier 2**, and a heatproof vessel holding **exactly 250 mL** of water. Fill
only a batch or transfer excess away. Carrying a separate heatproof tool does
not make an unsuitable carrier valid. A strong stationary fire is required:
the existing burning tier 2 and stationary-fire conditions both apply.

Open **C**, choose resonant bone tincture, select the actual vessel when offered,
then confirm a reachable clear work tile beside the fire. Confirmation commits
the material and water and leaves the selected vessel with the work. The first
of 35 processing turns passes immediately. Completion places that same empty
vessel and exactly one existing `resonant_bone_tincture` dose on the work tile.
Collect them and use the dose to learn through the existing Deep Tongue handler;
**L** opens the lexicon. A category with no remaining learnable word can yield an
inert dose, as before.

**E** on nearby work offers deliberate abandonment, explicitly losing the committed
ingredients and water. Esc leaves it working. Confirming returns only the empty
vessel at your feet and pays one action. Missing output definitions or failed
floor placement retain the job for retry or abandonment, even if its visual marker
has disappeared. Active and hot cached maps progress once per ordinary turn;
cold maps stay frozen until loaded. Heat is checked at commitment under the
existing processing rules; no continuous fire simulation has been introduced.

## Find and author alternatives

Existing apothecary reagent stock can contain resonant bone. SYS-1 `apothecary_c` shops use the `alchemist_preparation` pool for clay pots, copper
kettles, waxed carriers and the optional **steeping note**. Earlier selected
apothecaries retain their original pool and stock rules, including pending shops.
The existing clay-pot recipe remains another route. Stock is weighted and finite;
visited shops do not refill. The note explains the relationship and does not
unlock or gate the recipe. The same work can be done at another site.

In Workbench, open a supported inert material such as `clay_pot`, **Begin edit**
or **Save as new variant**, then use Properties' water-vessel capacity and
heat-suitability controls. New vessels are reusable, nonstackable and start empty.
Validate, review/apply and reopen before placing them in a saved room. Special
use bindings, including canonical flint throwing and equipment, cannot be hidden
behind vessel handling. The small cup demonstrates another supported identity
without runtime ID branches.

Open the bone-tincture recipe's Requirements to edit **Batch water (mL)** and
**Require heat-suitable vessel**. A 125 mL batch fits the small cup. The output
remains the existing bone tincture and the work remains steeping. Save/apply the
recipe, then **Test latest saved version** to exercise it. **Reset current test**
retains the previous capture; unsaved drafts do not enter either capture. The
synthetic requirement probe shows allocation and an unowned output only. Test
room play establishes actual commitment, time, recovery and completion.

## Saved contract and limits

Definition `vessel` is exactly `{version:1, capacity_ml:1..10000, contents:"water"}`.
Saved `vessel` contains that effective `config`, a persistent 32-hex `id`, integral
`water_ml` within capacity, and `contents` null when empty or `"water"` otherwise.
The saved capacity governs owned instances after definition edits. New definitions
govern new instances. Duplicate identities, conflicting use/consumption fields,
unknown versions, extra keys, bool-as-number and malformed contents are rejected.
New canonical clay created from a definition without `vessel` stores the narrow
`vessel_absent_version:1` marker, preserving that deliberate absence on JSON and
pickle load. Genuine historical clay has no marker and uses the migration below.

Recipe `vessel_process` is exactly `{version:1, water_ml:1..10000, heatproof:bool}`.
The saved job owns a captured requirement and empty implement, plus the existing
output/timer/marker/message fields. Effective capacity, water and ownership are
validated before a save or load installs state. The job timer is bounded 0..10000.

Compatible old empty canonical clay pots acquire the fixed 500 mL empty capability.
Owned names and other fields are preserved. Old nonempty/unknown contents or
conflicting owned use fields are retained without reinterpretation. Existing skins,
rain/refill routes, owned tinctures and old processing jobs retain their contracts;
old jobs do not invent a returned vessel. This feature supports water only: no
mixtures, liquid effects, nested storage, rain filling of new vessels, purification,
spoilage, continuous heat or global away-time simulation.

Saved pre-SYS-1 placement dependencies accept only the exact shipped clay-pot
definition plus its approved default capability. All other source changes still
require matching definitions; new plans retain the complete descriptor hash and
detect later capacity changes or removal. No saved selection is restocked or rerolled.

## Material-sensitive washes (SYS-3)

New selections use successor `apothecary_d` and `alchemist_washes`, retaining the
useful preparation stock while offering finite finished washes and their inputs.
Existing selected C shops and depleted containers remain unchanged. The new
[weapon washes](MATERIAL_WEAPON_PREPARATIONS.md) consume exactly 125 mL and return
the same empty vessel. Their additive version-two job captures the chosen primary
and a validated output snapshot. Version-one bone work keeps its exact historical
shape and completion behavior; no material response is invented for it.
