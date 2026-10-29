# Ordinary recipe authoring · item-preparation-1

`engine/recipe_authoring.py` is the game-owned Workbench adapter. Gameplay uses
`engine/crafting.py`, `rendering/craft_screen.py` and the engine's existing
placement/processing path; it never imports editor descriptors.

Rules admit 15 of 18 shipped, uniquely resolved single-object sources under
`data/recipes/`: 2 immediate, 2 cooking, 5 drying, 4 steeping, 2 rendering.
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
retain their catalogue. Completion constructs the captured output ID from its
current session catalogue. Acquired outputs keep saved copied instance values
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
