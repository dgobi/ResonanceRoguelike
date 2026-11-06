# Ordinary recipe authoring · item-preparation-3

`engine/recipe_authoring.py` is the game-owned Workbench adapter. Gameplay uses
`engine/crafting.py`, `rendering/craft_screen.py` and the engine's existing
placement/processing path; it never imports editor descriptors.

SYS-1 adds a bounded `vessel_process` requirement for the existing bone-tincture
output. Requirements controls edit its exact water batch and heatproof condition.
The selected physical vessel is a separate allocation slot, owned by the job
after confirmation; completion returns it empty with one dose. It is not a
retained tool. Saved jobs capture their requirement and effective vessel. See
[Practical vessels](PRACTICAL_VESSELS.md) for the 250 mL/35-turn default, another
authorable vessel, recovery, ordinary acquisition and compatibility.

Rules admit 17 of 20 shipped, uniquely resolved single-object sources under
`data/recipes/`: 2 immediate, 2 cooking, 5 drying, 6 steeping, 2 rendering.
Each supports exact-source same-ID edits and deliberate safe new-ID variants.
Execution class is fixed by the original. `campfire` remains gameplay-usable but
authoring read-only; `hungering_oil` uses unsupported legacy `apply_turns`;
`coldbell_extract_deprecated` stays read-only. Removing excluded candidate fields
cannot grant permission. Recipe IDs never determine source paths: for example
`dry_resonant_herb` is stored in `dry_coldbell.json`.

Common controls are name, description, category (UI grouping), `known` (absent
true), ordered components, retained tools, ambient conditions and `result_item`.
At least one material requirement is required. `known:false` is active catalogue
content shown as unknown and refused by CraftScreen; no learning route is added.

| Requirement | Production meaning |
| --- | --- |
| components | Each tag/tier row needs quantity distinct physical materials, default one. Protected `consumed_on_use:false` items require an affirmative component choice, even as the sole matching definition. |
| tools | Distinct physical slots retained after commitment. |
| requires_single_item list | One automatically eligible physical material satisfies every tag/tier record. |
| requires_single_item object | `tags` all hold on each of `max_quantity` distinct automatic materials. Despite its name, this is required quantity, absent one. |
| requires_ambient | Conditions, with tier default one; quantity has no physical meaning. |

CraftScreen distinguishes automatic materials from protected matches available
through **Enter → Choose materials**. Conjunction counts include automatic
materials only; no conjunction chooser exists. Tools show retained matches.
Per-row counts are potential matches, not a combined allocation: each physical
slot requires a distinct instance. Production confirmation rechecks knowledge,
conditions, placement and exact ownership before spending.

One multi-tag object cannot fill multiple material/tool slots. Repeated rows
stay separate. There is no conjunction preference channel: protected tag matches
are not eligible automatic materials. Controls preserve list/object form,
unknown nested metadata and omitted defaults. Workbench bounds are physical
quantities 1–32, exact tiers 0 through `2^53−1`, 64 rows per list and 64 total
physical slots, including conjunction quantities. Booleans, unsafe/nonfinite
numbers, malformed shapes and unresolved/ambiguous references are refused.

| Passive field | Actual meaning |
| --- | --- |
| processing_turns | Positive exact integer; absent 20. Confirmation advances the first tick. |
| processing_source | cooking/drying/steeping/rendering; absent drying. Exactly cooking places on fire; others beside fire. |
| processing_decor | Existing supported drying_herb/cooking_meat, or empty/absent no marker. Cooking ignores this field and preserves the fire. |
| placement_message | Literal prompt. Absent uses “Where will you set it to work?”; empty remains empty. |
| completion_message | Optional literal, `{item_name}`, escaped braces. No other fields/access/conversions/specifications. Absent/empty uses processing_messages.json source/default fallback. |
| result_item | One unique saved factory-valid item. Permission to construct is separate from permission to edit its use/effects. |

Inactive metadata, including passive `result_message`, is preserved. No control
interprets `apply_turns` as processing duration. Passive work implicitly needs
stationary_fire plus declared conditions. An owned, equipped active offhand
light supplies burning only while provides_burning and burn checks pass; it
cannot replace the stationary fire. Production map/occupancy/warmth checks
govern placement. No continuous fuel/heat maintenance rule is added.

Save/reopen supplies before referencing them in a recipe, then save room
references. Each publication is an independent single-file transaction. Parked
drafts overlay neither validation nor captures; saving an unreferenced definition
does not roll back if a later dependency save fails. Original source, descriptor,
all saved content/resources and relevant game code bind evidence and reviews.
Invalid recovery retains source but never restores a review. Host safe-path and
root checks remain independent of renderer controls and Python permissions.

The synthetic requirement probe discloses potential definitions, current
automatic matches, actual production allocation, missing conditions, known state
and unowned output construction. Only immediate recipes perform synthetic
inventory exchange; they advance no turn in ordinary gameplay. Passive probes
never place, tick or deliver work. Burning-only fixtures fail the implicit
stationary_fire condition. Synthetic conditions establish no usable map tile.

Actual passive placement spends nothing until valid confirmation. Cancellation,
load and failed placement retain inputs with no turn cost or reservation.
Confirmation revalidates exact owned instances and current conditions, consumes
materials, retains tools, records the job and advances one ordinary turn.
A three-turn job has two remaining immediately afterward. Completion produces
one object on the owning map floor, followed by ordinary pickup/capacity/use.

Jobs capture output ID, remaining turns, marker, source, completion text and
on-fire state. They store no recipe ID and never reread the recipe while ticking.
Fresh catalogues load saved recipe revisions for later jobs; existing sessions
retain their catalogue. Ordinary work and version-one bone work construct the captured output ID from
the current session catalogue. Version-two material-sensitive washes instead
restore their validated captured output, including dose strength/contact budget;
the current output reference must still be available and supported. Acquired outputs keep saved copied instance values
and established dynamic references described in [item authoring](ITEM_AUTHORING.md).

Output construction and instance validation precede destructive completion.
Invalid historical completion templates use plain “item name is ready.” text.
Missing/invalid output leaves the due job at zero and its owned marker intact,
with one active diagnostic per failure state rather than a turn-by-turn flood.
A restored definition and fresh catalogue permit completion without restart,
refund, substitution or queue migration. Missing-owned-cache refusal remains.
Active and distinct hot surface/underground maps tick once per simulated turn;
cold maps freeze. No wall-clock/offscreen catch-up is added.

W5H Reset reuses immutable captured inputs; latest-saved tests capture revisions.
Compatibility fixtures use separate ordinary saves and explicit disposable roots.
See [W5K delivery](../../workbench/docs/W5K_DELIVERY.md) for source-bound evidence.

## Material-sensitive vessel preparations (SYS-3)

A supported passive source, including the bone tincture, can be duplicated into
a wash after its output dose has been saved. Choose a supported coating output,
steeping, stationary heat with burning tier at least two, and a heatproof vessel.
**Requirements** exposes exact batch water and **Material response**. Assign one
quantity-one component the `primary` role, choose its matching material tag,
and set the higher-tier threshold and two contact bands. Threshold is 2..100;
contacts are 1..100 with the high band strictly greater. The primary minimum
is at least one and below the higher threshold. Other slots cannot claim that
role. Base dose contacts are replaced, not added. **Preparation** edits duration.
The shipped washes use one separate fixative, 125 mL and 15 charged turns.

The ordinary chooser selects actual primary and fixative objects, including
same-ID objects with different saved keywords. Highest valid integral matching
tier determines the band. Duplicate rows never add tiers. A finished coating
cannot supply the primary, even if its keywords match. Exact slot allocations
and the resolved primary are rechecked at confirmation; stale choices are free.
The requirement probe displays a synthetic resolved dose and role only. Use a
saved Test room for actual acquisition, work, use and combat. Save dose, recipe,
then room/pool in that order; Reset/latest/dirty rules remain unchanged.

See [Material-sensitive washes](MATERIAL_WEAPON_PREPARATIONS.md) for ownership,
ordinary supply and compatibility. `hungering_oil` recipe execution remains
inspect-only; admitting its ordinary dose does not admit its legacy recipe.
